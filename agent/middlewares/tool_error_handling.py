"""
ToolErrorHandlingMiddleware — catch tool exceptions and return graceful ToolMessages.

Problem:
    An uncaught exception inside a tool implementation propagates all the way
    up through LangGraph and terminates the entire agent run, losing all
    intermediate work and presenting a raw traceback to the caller.

Fix:
    Wrap every tool call in try/except.  On any exception (other than
    GraphBubbleUp, which must propagate so HITL interrupt logic works)
    return a ToolMessage with status="error" so the agent can reason about
    the failure and continue.

Note:
    GraphBubbleUp is re-raised BEFORE the general except clause so that
    human-in-the-loop interrupts are never swallowed by this middleware.
"""
from __future__ import annotations

import logging
import traceback
from typing import Callable

from langchain.agents.factory import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphBubbleUp

logger = logging.getLogger(__name__)


class ToolErrorHandlingMiddleware(AgentMiddleware):
    """Catch uncaught tool exceptions and convert them to error ToolMessages."""

    @property
    def name(self) -> str:
        return "tool_error_handling"

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    @staticmethod
    def _error_message(tool_name: str, tool_call_id: str, exc: Exception) -> ToolMessage:
        """Build a synthetic error ToolMessage for a failed tool call."""
        error_summary = f"{type(exc).__name__}: {exc}"
        logger.error(
            "ToolErrorHandlingMiddleware: tool '%s' (id=%s) raised %s\n%s",
            tool_name,
            tool_call_id,
            error_summary,
            traceback.format_exc(),
        )
        return ToolMessage(
            content=(
                f"Error: Tool {tool_name} failed: {error_summary}. "
                "Continue with available context."
            ),
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )

    # ------------------------------------------------------------------
    # AgentMiddleware hooks
    # ------------------------------------------------------------------

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage],
    ) -> ToolMessage:
        tool_name = request.tool_call.get("name", "unknown_tool")
        tool_call_id = request.tool_call.get("id", "")
        try:
            return handler(request)
        except GraphBubbleUp:
            raise
        except Exception as exc:
            return self._error_message(tool_name, tool_call_id, exc)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable,
    ) -> ToolMessage:
        tool_name = request.tool_call.get("name", "unknown_tool")
        tool_call_id = request.tool_call.get("id", "")
        try:
            return await handler(request)
        except GraphBubbleUp:
            raise
        except Exception as exc:
            return self._error_message(tool_name, tool_call_id, exc)
