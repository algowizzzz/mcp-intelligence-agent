"""
LoopDetectionMiddleware — detect and break repeated identical tool calls.

Problem:
    Agents can enter infinite loops, calling the same tool with the same
    arguments over and over.  This wastes tokens, burns API budget, and
    never resolves without external intervention.

Fix:
    After each model response, fingerprint the tool calls in the AIMessage
    using an MD5 hash of the sorted (tool_name, serialised_args) pairs.
    Track these hashes in a per-thread sliding window of the last
    _WINDOW_SIZE entries.

    warn_threshold (default 3):
        When the same hash appears >= warn_threshold times, embed a
        "[LOOP DETECTED ...]" warning in the AIMessage content so the
        model is nudged to try a different approach.

    hard_limit (default 5):
        When the same hash appears >= hard_limit times, strip ALL
        tool_calls from the AIMessage and embed a "[LOOP HARD STOP ...]"
        message so the agent is forced to respond in text and the loop
        is broken unconditionally.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections import deque
from typing import Any

from langchain.agents.factory import AgentMiddleware, ModelResponse
from langchain_core.messages import AIMessage, BaseMessage

logger = logging.getLogger(__name__)

_WINDOW_SIZE = 20


def _hash_tool_calls(tool_calls: list[Any]) -> str:
    """
    Produce a stable MD5 fingerprint for a list of tool calls.

    Each entry is normalised to (name, serialised_args) and the list is
    sorted before hashing so call order does not affect the fingerprint.
    """
    pairs: list[tuple[str, str]] = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            name = tc.get("name", "")
            args = tc.get("args", {})
        else:
            name = getattr(tc, "name", "")
            args = getattr(tc, "args", {})

        try:
            serialised = json.dumps(args, sort_keys=True, default=str)
        except Exception:
            serialised = str(args)

        pairs.append((name, serialised))

    pairs.sort()
    raw = json.dumps(pairs)
    return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324 — not security-sensitive


def _extract_tool_calls(ai_msg: AIMessage) -> list[Any]:
    """Return the tool_calls list from an AIMessage, handling both styles."""
    tool_calls = getattr(ai_msg, "tool_calls", None) or []
    if tool_calls:
        return tool_calls

    # Content-block style (Anthropic tool_use blocks)
    content = getattr(ai_msg, "content", [])
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]

    return []


def _prepend_text(ai_msg: AIMessage, note: str) -> AIMessage:
    """
    Return a *new* AIMessage with *note* prepended to its text content.

    Handles both plain-string content and list-of-blocks content.
    """
    content = getattr(ai_msg, "content", "")

    if isinstance(content, str):
        new_content: Any = f"{note}\n\n{content}" if content else note
    elif isinstance(content, list):
        # Prepend as a text block
        text_block = {"type": "text", "text": note}
        new_content = [text_block] + list(content)
    else:
        new_content = note

    return AIMessage(
        content=new_content,
        tool_calls=list(getattr(ai_msg, "tool_calls", []) or []),
        id=getattr(ai_msg, "id", None),
        response_metadata=dict(getattr(ai_msg, "response_metadata", {}) or {}),
    )


def _strip_tool_calls(ai_msg: AIMessage, note: str) -> AIMessage:
    """
    Return a new AIMessage with ALL tool_calls removed and *note* embedded.

    Also strips tool_use blocks from list-style content.
    """
    content = getattr(ai_msg, "content", "")

    if isinstance(content, str):
        new_content: Any = f"{note}\n\n{content}" if content else note
    elif isinstance(content, list):
        # Remove tool_use blocks, keep text/image blocks
        kept = [b for b in content if not (isinstance(b, dict) and b.get("type") == "tool_use")]
        text_block = {"type": "text", "text": note}
        new_content = [text_block] + kept
    else:
        new_content = note

    return AIMessage(
        content=new_content,
        tool_calls=[],  # deliberately empty
        id=getattr(ai_msg, "id", None),
        response_metadata=dict(getattr(ai_msg, "response_metadata", {}) or {}),
    )


class LoopDetectionMiddleware(AgentMiddleware):
    """
    Detect repeated identical tool calls and intervene progressively.

    Parameters
    ----------
    warn_threshold:
        Number of times the same tool-call fingerprint must appear in the
        sliding window before a warning is embedded in the AIMessage.
        Default: 3.
    hard_limit:
        Number of times the same fingerprint must appear before ALL tool
        calls are stripped and a hard-stop message is embedded.
        Default: 5.
    """

    def __init__(self, warn_threshold: int = 3, hard_limit: int = 5) -> None:
        self.warn_threshold = warn_threshold
        self.hard_limit = hard_limit
        # thread_id → deque of hash strings (sliding window of last _WINDOW_SIZE calls)
        self._window: dict[str, deque[str]] = {}

    @property
    def name(self) -> str:
        return "loop_detection"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_thread_id(self, runtime) -> str:
        try:
            return runtime.config.get("configurable", {}).get("thread_id", "") or ""
        except Exception:
            pass
        # Fallback: try langgraph.config.get_config()
        try:
            from langgraph.config import get_config
            cfg = get_config()
            return cfg.get("configurable", {}).get("thread_id", "") or ""
        except Exception:
            return ""

    def _record_and_check(self, thread_id: str, fingerprint: str) -> tuple[int, str]:
        """
        Add *fingerprint* to the sliding window for *thread_id*.

        Returns (count_in_window, action) where action is one of:
            "ok"    — below warn threshold
            "warn"  — at or above warn_threshold, below hard_limit
            "stop"  — at or above hard_limit
        """
        if thread_id not in self._window:
            self._window[thread_id] = deque(maxlen=_WINDOW_SIZE)

        self._window[thread_id].append(fingerprint)
        count = self._window[thread_id].count(fingerprint)

        if count >= self.hard_limit:
            return count, "stop"
        if count >= self.warn_threshold:
            return count, "warn"
        return count, "ok"

    def _process(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        """
        Core logic shared by after_model and aafter_model.

        Inspects the latest AIMessage in state["messages"], hashes its tool
        calls, and either warns or hard-stops if a loop is detected.
        """
        messages: list[BaseMessage] = list(state.get("messages", []))
        if not messages:
            return None

        # Find the last AIMessage
        ai_msg: AIMessage | None = None
        ai_idx: int = -1
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], AIMessage):
                ai_msg = messages[i]
                ai_idx = i
                break

        if ai_msg is None:
            return None

        tool_calls = _extract_tool_calls(ai_msg)
        if not tool_calls:
            return None  # No tool calls — nothing to loop-detect

        fingerprint = _hash_tool_calls(tool_calls)
        thread_id = self._get_thread_id(runtime)
        count, action = self._record_and_check(thread_id, fingerprint)

        if action == "ok":
            return None

        tool_names = [
            (tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "unknown"))
            for tc in tool_calls
        ]

        if action == "warn":
            note = (
                f"[LOOP DETECTED \u2014 you have called "
                f"{', '.join(tool_names)} {count} time(s) with identical arguments. "
                f"Try a different approach.]"
            )
            logger.warning("LoopDetectionMiddleware: %s (thread=%s)", note, thread_id)
            new_ai = _prepend_text(ai_msg, note)

        else:  # "stop"
            note = (
                f"[LOOP HARD STOP \u2014 tool calls disabled due to repeated loop "
                f"({count} identical call(s) detected for "
                f"{', '.join(tool_names)}). Provide a final answer using only "
                f"the context already available.]"
            )
            logger.error("LoopDetectionMiddleware: %s (thread=%s)", note, thread_id)
            new_ai = _strip_tool_calls(ai_msg, note)

        new_messages = list(messages)
        new_messages[ai_idx] = new_ai
        return {"messages": new_messages}

    # ------------------------------------------------------------------
    # AgentMiddleware hooks
    # ------------------------------------------------------------------

    def after_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return self._process(state, runtime)

    async def aafter_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return self._process(state, runtime)
