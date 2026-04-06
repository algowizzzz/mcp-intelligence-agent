"""
MemoryMiddleware — persistent cross-session memory injection.

Stores and retrieves user/worker-scoped memories from SQLite.
Before each model call, retrieves relevant memories and prepends them to the
system prompt so the model can recall facts from previous sessions.

Standalone helpers:
  extract_and_store_memories(messages, worker_id, user_id, llm=None, db_path=None)
      — call at the end of a conversation to persist notable facts.

Class methods:
  MemoryMiddleware.clear_memories(worker_id, user_id, db_path)
  MemoryMiddleware.get_memories(worker_id, user_id, db_path, limit=20)
"""
from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from langchain.agents.factory import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "./data/memory.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    importance REAL DEFAULT 0.5,
    created_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    expires_at TEXT,
    source_summary TEXT
);
"""

_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_memory_worker_user ON memory_entries (worker_id, user_id);
"""


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_db(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    conn.execute(_INDEX_SQL)
    conn.commit()
    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at(ttl_days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()


# ---------------------------------------------------------------------------
# Similarity: keyword overlap (TF-IDF-style word intersection)
# ---------------------------------------------------------------------------

def _word_set(text: str) -> set[str]:
    """Extract lowercase words with length >= 3."""
    import re
    return {w for w in re.findall(r"\b[a-zA-Z0-9_]{3,}\b", text.lower())}


def _similarity(query: str, candidate: str) -> float:
    """Return a [0, 1] Jaccard-like score between query and candidate text."""
    q_words = _word_set(query)
    c_words = _word_set(candidate)
    if not q_words or not c_words:
        return 0.0
    intersection = q_words & c_words
    union = q_words | c_words
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Core data access
# ---------------------------------------------------------------------------

def _fetch_memories(
    worker_id: str,
    user_id: str,
    db_path: str,
    limit: int = 20,
    query_text: str = "",
    min_similarity: float = 0.0,
) -> list[dict]:
    """Fetch unexpired memories for worker+user, ranked by similarity if query_text given."""
    now = _now_iso()
    with _get_db(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, content, importance, created_at, last_accessed, source_summary
            FROM memory_entries
            WHERE worker_id = ? AND user_id = ?
              AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY importance DESC, last_accessed DESC
            LIMIT ?
            """,
            (worker_id, user_id, now, limit * 3),  # over-fetch then re-rank
        ).fetchall()

    memories = [dict(r) for r in rows]

    if query_text:
        for m in memories:
            m["_score"] = _similarity(query_text, m["content"])
        memories = [m for m in memories if m["_score"] >= min_similarity]
        memories.sort(key=lambda m: (-m["_score"], -m.get("importance", 0.5)))
    else:
        memories.sort(key=lambda m: -m.get("importance", 0.5))

    return memories[:limit]


def _update_last_accessed(memory_ids: list[str], db_path: str) -> None:
    if not memory_ids:
        return
    now = _now_iso()
    with _get_db(db_path) as conn:
        conn.executemany(
            "UPDATE memory_entries SET last_accessed = ? WHERE id = ?",
            [(now, mid) for mid in memory_ids],
        )
        conn.commit()


def _store_memory(
    worker_id: str,
    user_id: str,
    content: str,
    db_path: str,
    importance: float = 0.5,
    ttl_days: int = 90,
    source_summary: str = "",
) -> str:
    memory_id = str(uuid.uuid4())
    now = _now_iso()
    with _get_db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO memory_entries
              (id, worker_id, user_id, content, importance, created_at, last_accessed, expires_at, source_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (memory_id, worker_id, user_id, content, importance, now, now,
             _expires_at(ttl_days), source_summary),
        )
        conn.commit()
    return memory_id


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class MemoryMiddleware(AgentMiddleware):
    """Inject relevant cross-session memories before each model call.

    Args:
        db_path: SQLite database path (default: ./data/memory.db).
        max_memories: Maximum number of memories to inject (default: 5).
        min_similarity: Minimum keyword-overlap similarity score [0,1] (default: 0.75).
        ttl_days: Days before a memory expires (default: 90).
        enabled: Set False to disable entirely (no-op pass-through).
    """

    def __init__(
        self,
        db_path: str | None = None,
        max_memories: int = 5,
        min_similarity: float = 0.75,
        ttl_days: int = 90,
        enabled: bool = True,
    ):
        self.db_path = db_path or _DEFAULT_DB_PATH
        self.max_memories = max_memories
        self.min_similarity = min_similarity
        self.ttl_days = ttl_days
        self.enabled = enabled

    @property
    def name(self) -> str:
        return "memory"

    # ------------------------------------------------------------------
    # Context extraction helpers
    # ------------------------------------------------------------------

    def _get_context(self, runtime) -> tuple[str, str]:
        """Return (worker_id, user_id) from runtime config."""
        try:
            cfg = runtime.config.get("configurable", {}) if runtime else {}
            return cfg.get("worker_id", ""), cfg.get("user_id", "")
        except Exception:
            return "", ""

    def _get_query_text(self, messages: list) -> str:
        """Extract the most recent human message text as query for similarity ranking."""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                content = msg.content
                if isinstance(content, str):
                    return content[:500]
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            return block.get("text", "")[:500]
        return ""

    def _build_memory_block(self, memories: list[dict]) -> str:
        lines = []
        for m in memories:
            date_str = m.get("created_at", "")[:10]
            lines.append(f"- [{date_str}] {m['content']}")
        return "=== MEMORIES FROM PAST SESSIONS ===\n" + "\n".join(lines)

    def _inject_memories(self, request: ModelRequest, memory_block: str) -> ModelRequest:
        """Prepend memory block to the system message (or create one)."""
        if request.system_message:
            new_system = SystemMessage(
                content=f"{memory_block}\n\n{request.system_message.content}"
            )
            return request.override(system_message=new_system)
        # No system message — insert as first message
        messages = [SystemMessage(content=memory_block)] + list(request.messages)
        return request.override(messages=messages)

    def _run(self, request: ModelRequest) -> ModelRequest:
        if not self.enabled:
            return request

        worker_id, user_id = self._get_context(request.runtime)
        if not worker_id or not user_id:
            return request

        query_text = self._get_query_text(list(request.messages))

        try:
            memories = _fetch_memories(
                worker_id=worker_id,
                user_id=user_id,
                db_path=self.db_path,
                limit=self.max_memories,
                query_text=query_text,
                min_similarity=self.min_similarity,
            )
        except Exception as exc:
            logger.warning("MemoryMiddleware: failed to fetch memories — %s", exc)
            return request

        if not memories:
            return request

        # Update last_accessed in background (best-effort)
        try:
            import threading
            ids = [m["id"] for m in memories]
            threading.Thread(
                target=_update_last_accessed,
                args=(ids, self.db_path),
                daemon=True,
            ).start()
        except Exception:
            pass

        memory_block = self._build_memory_block(memories)
        logger.debug(
            "MemoryMiddleware: injecting %d memories for worker=%s user=%s.",
            len(memories), worker_id, user_id,
        )
        return self._inject_memories(request, memory_block)

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        return handler(self._run(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable,
    ) -> ModelResponse:
        return await handler(self._run(request))

    # ------------------------------------------------------------------
    # Class-level admin methods
    # ------------------------------------------------------------------

    @classmethod
    def clear_memories(cls, worker_id: str, user_id: str, db_path: str | None = None) -> int:
        """Delete all memories for a worker+user. Returns number of rows deleted."""
        db_path = db_path or _DEFAULT_DB_PATH
        with _get_db(db_path) as conn:
            cur = conn.execute(
                "DELETE FROM memory_entries WHERE worker_id = ? AND user_id = ?",
                (worker_id, user_id),
            )
            conn.commit()
            return cur.rowcount

    @classmethod
    def get_memories(
        cls,
        worker_id: str,
        user_id: str,
        db_path: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """List memories for admin UI. Returns list of dicts (no similarity filtering)."""
        db_path = db_path or _DEFAULT_DB_PATH
        return _fetch_memories(
            worker_id=worker_id,
            user_id=user_id,
            db_path=db_path,
            limit=limit,
            query_text="",
            min_similarity=0.0,
        )


# ---------------------------------------------------------------------------
# Standalone extraction helper
# ---------------------------------------------------------------------------

def extract_and_store_memories(
    conversation_messages: list,
    worker_id: str,
    user_id: str,
    llm=None,
    db_path: str | None = None,
    ttl_days: int = 90,
) -> list[str]:
    """Extract memorable facts from a conversation and store them.

    Args:
        conversation_messages: List of LangChain message objects.
        worker_id: Worker scope for the memory.
        user_id: User scope for the memory.
        llm: Optional LangChain chat model for smart extraction.
             If None, simple heuristic extraction is used.
        db_path: SQLite database path (default: ./data/memory.db).
        ttl_days: Days until the memory expires.

    Returns:
        List of stored memory IDs.
    """
    db_path = db_path or _DEFAULT_DB_PATH
    stored_ids: list[str] = []

    if llm is not None:
        facts = _extract_with_llm(conversation_messages, llm)
    else:
        facts = _extract_heuristic(conversation_messages)

    for fact in facts:
        if not fact.strip():
            continue
        try:
            mid = _store_memory(
                worker_id=worker_id,
                user_id=user_id,
                content=fact.strip(),
                db_path=db_path,
                ttl_days=ttl_days,
                source_summary="auto-extracted",
            )
            stored_ids.append(mid)
            logger.debug("MemoryMiddleware: stored memory id=%s for user=%s.", mid, user_id)
        except Exception as exc:
            logger.warning("MemoryMiddleware: failed to store memory — %s", exc)

    return stored_ids


def _extract_heuristic(messages: list) -> list[str]:
    """Simple heuristic: pull human messages that look like factual statements."""
    import re
    facts: list[str] = []
    factual_indicators = (
        "my ", "i am ", "i'm ", "i have ", "i use ", "i work ",
        "we use ", "our ", "the company ", "the system ", "prefer",
        "always ", "never ", "typically ", "usually ",
    )
    for msg in messages:
        if not isinstance(msg, HumanMessage):
            continue
        content = msg.content if isinstance(msg.content, str) else ""
        for sentence in re.split(r"[.!?\n]", content):
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 300:
                continue
            low = sentence.lower()
            if any(low.startswith(ind) for ind in factual_indicators):
                facts.append(sentence)
    return facts[:10]  # cap at 10 facts per conversation


def _extract_with_llm(messages: list, llm) -> list[str]:
    """Use LLM to extract memorable facts from conversation."""
    history_text = "\n".join(
        f"[{getattr(m, 'type', 'message').upper()}]: {getattr(m, 'content', '')}"
        for m in messages
        if isinstance(getattr(m, "content", ""), str)
    )[:8000]

    prompt = [
        SystemMessage(content=(
            "Extract up to 5 memorable, reusable facts about the user or their domain from "
            "this conversation. Return ONLY a JSON array of short strings (each ≤ 120 chars). "
            'Example: ["User prefers VaR over ES", "Works at JPMorgan risk team"]. '
            "Return [] if nothing memorable is found."
        )),
        HumanMessage(content=history_text),
    ]

    try:
        response = llm.invoke(prompt)
        content = getattr(response, "content", "[]")
        import json
        facts = json.loads(content)
        if isinstance(facts, list):
            return [str(f) for f in facts if isinstance(f, str)]
    except Exception as exc:
        logger.warning("MemoryMiddleware._extract_with_llm: failed — %s", exc)

    return []
