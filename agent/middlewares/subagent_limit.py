"""
SubagentLimitMiddleware — cap the number of parallel sub-agent task() calls.

Problem:
    A lead agent in a multi-agent framework may generate more parallel task()
    calls than the thread pool can safely handle, causing resource exhaustion
    or scheduling deadlocks.

Fix:
    After each model response, count AIMessage tool_calls where the function
    name is "task".  If the count exceeds max_concurrent, keep only the first
    max_concurrent calls and drop the rest.  A note is appended to the
    AIMessage content explaining how many tasks were dropped and why.

    max_concurrent is clamped to the range [2, 4].
"""
from __future__ import annotations

import logging
from typing import Any

from langchain.agents.factory import AgentMiddleware
from langchain_core.messages import AIMessage, BaseMessage

logger = logging.getLogger(__name__)

_MIN_CONCURRENT = 2
_MAX_CONCURRENT = 8


class SubagentLimitMiddleware(AgentMiddleware):
    """
    Limit the number of parallel task() sub-agent calls per model response.

    Parameters
    ----------
    max_concurrent:
        Maximum number of task() tool calls allowed in a single AIMessage.
        Clamped to [2, 4].  Default: 3.
    """

    def __init__(self, max_concurrent: int = 3) -> None:
        self.max_concurrent: int = max(
            _MIN_CONCURRENT, min(_MAX_CONCURRENT, max_concurrent)
        )

    @property
    def name(self) -> str:
        return "subagent_limit"

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _process(self, state: Any, runtime: Any) -> dict[str, Any] | None:
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

        tool_calls = list(getattr(ai_msg, "tool_calls", []) or [])
        task_indices = [
            i for i, tc in enumerate(tool_calls)
            if (tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")) == "task"
        ]

        if len(task_indices) <= self.max_concurrent:
            return None  # Within limit — nothing to do

        # Keep the first max_concurrent task() calls; drop the rest
        indices_to_drop = set(task_indices[self.max_concurrent:])
        new_tool_calls = [tc for i, tc in enumerate(tool_calls) if i not in indices_to_drop]
        dropped = len(indices_to_drop)

        note = (
            f"[Note: {dropped} sub-agent task(s) were dropped to stay within "
            f"concurrency limit of {self.max_concurrent}]"
        )
        logger.warning(
            "SubagentLimitMiddleware: dropped %d task() call(s) "
            "(limit=%d). %s",
            dropped,
            self.max_concurrent,
            note,
        )

        # Rebuild content with the appended note
        content = getattr(ai_msg, "content", "")
        if isinstance(content, str):
            new_content: Any = f"{content}\n\n{note}" if content else note
        elif isinstance(content, list):
            text_block = {"type": "text", "text": note}
            new_content = list(content) + [text_block]
        else:
            new_content = note

        new_ai = AIMessage(
            content=new_content,
            tool_calls=new_tool_calls,
            id=getattr(ai_msg, "id", None),
            response_metadata=dict(getattr(ai_msg, "response_metadata", {}) or {}),
        )

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
