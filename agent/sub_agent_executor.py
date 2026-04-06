"""sub_agent_executor.py — Two-pool ThreadPoolExecutor sub-agent runner (REQ-13).

Uses the DeerFlow pattern: a scheduler pool submits tasks to an execution pool.
This avoids nested asyncio.gather deadlocks — each sub-agent gets its own
asyncio.run() call in a dedicated thread rather than competing on the parent loop.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage

# _worker_ctx lives in agent/tools.py — imported from there so sub-agents
# inherit the same ContextVar that SAJHA header injection reads.
from agent.tools import _worker_ctx


class SubAgentExecutor:
    """Runs a sub-agent task asynchronously in a two-pool executor architecture.

    Class-level pools are shared across all instances so the total thread
    budget is bounded regardless of how many parallel tasks are spawned.

    Pool roles
    ----------
    _scheduler_pool : Receives execute_async() submissions immediately and
        blocks on future.result() so we get per-task timeout enforcement
        without touching the parent event loop.
    _execution_pool : Each scheduler thread submits the async coroutine
        here via asyncio.run(), giving it an isolated event loop.
    """

    _scheduler_pool: ThreadPoolExecutor = ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="sa-sched"
    )
    _execution_pool: ThreadPoolExecutor = ThreadPoolExecutor(
        max_workers=8, thread_name_prefix="sa-exec"
    )
    _registry: dict[str, dict] = {}
    _registry_lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        prompt: str,
        tools: list,
        parent_worker_ctx: dict,
        llm: Any,
        create_agent_fn: Any,
        max_result_chars: int = 8000,
        timeout_seconds: int = 120,
    ) -> None:
        self._prompt = prompt
        self._tools = tools
        self._parent_worker_ctx = parent_worker_ctx
        self._llm = llm
        self._create_agent_fn = create_agent_fn
        self._max_result_chars = max_result_chars
        self._timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_async(self, task_id: str) -> None:
        """Submit the task to the scheduler pool and return immediately.

        Sets registry status to 'running' before returning so callers can
        poll without a race window.
        """
        with self._registry_lock:
            self._registry[task_id] = {
                "status": "running",
                "result": None,
                "error": None,
                "ai_messages": [],
                "_ai_messages_cursor": 0,
                "started_at": time.time(),
            }
        self._scheduler_pool.submit(self._run_in_executor, task_id)

    @classmethod
    def get_status(cls, task_id: str) -> dict:
        """Return a snapshot of the registry entry, or {'status': 'not_found'}."""
        with cls._registry_lock:
            entry = cls._registry.get(task_id)
            if entry is None:
                return {"status": "not_found"}
            return {
                "status": entry["status"],
                "result": entry["result"],
                "error": entry["error"],
                "started_at": entry["started_at"],
            }

    @classmethod
    def poll_messages(cls, task_id: str) -> list[str]:
        """Return new ai_messages since the last poll (consumed — not re-delivered)."""
        with cls._registry_lock:
            entry = cls._registry.get(task_id)
            if entry is None:
                return []
            cursor = entry["_ai_messages_cursor"]
            all_msgs = entry["ai_messages"]
            new_msgs = all_msgs[cursor:]
            entry["_ai_messages_cursor"] = len(all_msgs)
            return list(new_msgs)

    # ------------------------------------------------------------------
    # Internal — scheduler thread
    # ------------------------------------------------------------------

    def _run_in_executor(self, task_id: str) -> None:
        """Runs in a scheduler thread.

        1. Propagates the parent worker context into this thread's ContextVar.
        2. Submits the async coroutine to the execution pool.
        3. Waits on the future with a timeout — marks timed_out if exceeded.
        """
        # Propagate worker context so SAJHA header injection works in the
        # sub-agent's thread (ContextVar is per-task, not per-thread, but
        # asyncio.run creates a new task so we set it inside _aexecute too).
        _worker_ctx.set(self._parent_worker_ctx)

        future: Future = self._execution_pool.submit(
            asyncio.run, self._aexecute(task_id)
        )
        try:
            future.result(timeout=self._timeout_seconds)
        except TimeoutError:
            with self._registry_lock:
                entry = self._registry.get(task_id, {})
                if entry.get("status") == "running":
                    entry["status"] = "timed_out"
                    entry["error"] = (
                        f"Sub-agent task timed out after {self._timeout_seconds}s"
                    )
        except Exception as exc:
            with self._registry_lock:
                entry = self._registry.get(task_id, {})
                if entry.get("status") == "running":
                    entry["status"] = "failed"
                    entry["error"] = str(exc)

    # ------------------------------------------------------------------
    # Internal — execution thread (asyncio.run context)
    # ------------------------------------------------------------------

    async def _aexecute(self, task_id: str) -> None:
        """Runs inside asyncio.run() in the execution pool.

        Creates an ephemeral agent (no checkpointer — sub-agents are
        fire-and-forget, results flow back through the registry), streams
        events, and writes the final result to the registry.
        """
        # Re-set ContextVar in this new async task's context.
        _worker_ctx.set(self._parent_worker_ctx)

        try:
            system_prompt = self._parent_worker_ctx.get("system_prompt", "")
            agent = self._create_agent_fn(
                system_prompt=system_prompt,
                tools=self._tools,
                checkpointer=None,
            )
        except TypeError:
            # create_agent_for_worker(system_prompt, tools) — no checkpointer kwarg
            from agent.agent import create_agent_for_worker
            agent = create_agent_for_worker(
                system_prompt=self._parent_worker_ctx.get("system_prompt", ""),
                tools=self._tools,
            )

        inp = {"messages": [HumanMessage(content=self._prompt)]}
        config = {"configurable": {"thread_id": task_id}}

        final_text: str = ""
        ai_message_texts: list[str] = []

        try:
            async for event in agent.astream_events(inp, config, version="v2"):
                etype = event.get("event", "")

                if etype == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk is not None and hasattr(chunk, "content"):
                        content = chunk.content
                        if isinstance(content, str) and content:
                            final_text += content
                        elif isinstance(content, list):
                            for block in content:
                                if (
                                    isinstance(block, dict)
                                    and block.get("type") == "text"
                                    and block.get("text")
                                ):
                                    final_text += block["text"]
                                elif hasattr(block, "text") and block.text:
                                    final_text += block.text

                elif etype == "on_chat_model_end":
                    # Capture each complete AI turn as a poll-able message.
                    output = event["data"].get("output")
                    if output is not None:
                        text_fragment = ""
                        if isinstance(output, AIMessage):
                            content = output.content
                            if isinstance(content, str):
                                text_fragment = content
                            elif isinstance(content, list):
                                for block in content:
                                    if (
                                        isinstance(block, dict)
                                        and block.get("type") == "text"
                                    ):
                                        text_fragment += block.get("text", "")
                                    elif hasattr(block, "text"):
                                        text_fragment += block.text or ""
                        if text_fragment.strip():
                            ai_message_texts.append(text_fragment.strip())
                            with self._registry_lock:
                                entry = self._registry.get(task_id)
                                if entry:
                                    entry["ai_messages"].append(text_fragment.strip())

                elif etype == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = event["data"].get("input", {})
                    msg = f"[tool_call] {tool_name}({tool_input})"
                    with self._registry_lock:
                        entry = self._registry.get(task_id)
                        if entry:
                            entry["ai_messages"].append(msg)

        except Exception as exc:
            with self._registry_lock:
                entry = self._registry.get(task_id)
                if entry:
                    entry["status"] = "failed"
                    entry["error"] = str(exc)
            return

        # Prefer the assembled streaming text over individual turn captures;
        # fall back to the last captured ai_message if streaming was empty.
        result_text = final_text.strip() or (
            ai_message_texts[-1] if ai_message_texts else ""
        )
        truncated = result_text[: self._max_result_chars]
        if len(result_text) > self._max_result_chars:
            truncated += (
                f"\n\n[... truncated — {len(result_text):,} chars total, "
                f"showing first {self._max_result_chars:,}]"
            )

        with self._registry_lock:
            entry = self._registry.get(task_id)
            if entry:
                entry["status"] = "completed"
                entry["result"] = truncated
