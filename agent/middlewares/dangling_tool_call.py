"""
DanglingToolCallMiddleware — repair orphaned tool_calls before each model call.

Problem:
    SummarisationMiddleware or MessageTrimmer can remove ToolMessages from the
    history while leaving the AIMessage that generated those tool_calls.  When
    the Anthropic API receives an AIMessage whose tool_call_ids have no matching
    ToolMessage it raises a format error and kills the agent run.

Fix:
    Before each model call, scan all messages.  For every AIMessage that
    carries tool_calls, check whether each tool_call_id has a corresponding
    ToolMessage somewhere later in the list.  If not, inject a synthetic
    ToolMessage(content="[interrupted]", status="error") immediately after the
    AIMessage so the conversation is always well-formed.
"""
from __future__ import annotations

import logging
from typing import Callable

from langchain.agents.factory import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

logger = logging.getLogger(__name__)


def _collect_tool_message_ids(messages: list[BaseMessage]) -> set[str]:
    """Return the set of tool_call_ids that already have a ToolMessage."""
    ids: set[str] = set()
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.tool_call_id:
            ids.add(msg.tool_call_id)
    return ids


def _repair(messages: list[BaseMessage]) -> list[BaseMessage]:
    """
    Walk through *messages* and insert synthetic ToolMessages for any
    AIMessage tool_calls that have no matching ToolMessage.

    Returns a new list; the original is not mutated.
    """
    # Build a full index of covered ids first so we can check in one pass.
    covered = _collect_tool_message_ids(messages)

    result: list[BaseMessage] = []
    injected = 0

    for msg in messages:
        result.append(msg)

        if not isinstance(msg, AIMessage):
            continue

        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            # Also check content-block style (list of dicts with type==tool_use)
            content = getattr(msg, "content", [])
            if isinstance(content, list):
                tool_calls = [
                    b for b in content
                    if isinstance(b, dict) and b.get("type") == "tool_use"
                ]

        for tc in tool_calls:
            # tool_calls entries are dicts or ToolCall objects
            tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
            tc_name = (
                tc.get("name") if isinstance(tc, dict)
                else getattr(tc, "name", "unknown_tool")
            )
            if tc_id and tc_id not in covered:
                synthetic = ToolMessage(
                    content="[interrupted]",
                    tool_call_id=tc_id,
                    name=tc_name,
                    status="error",
                )
                result.append(synthetic)
                covered.add(tc_id)
                injected += 1
                logger.debug(
                    "DanglingToolCallMiddleware: injected synthetic ToolMessage "
                    "for tool_call_id=%s (tool=%s)",
                    tc_id,
                    tc_name,
                )

    if injected:
        logger.info(
            "DanglingToolCallMiddleware: repaired %d dangling tool_call(s).", injected
        )

    return result


class DanglingToolCallMiddleware(AgentMiddleware):
    """Repair dangling AIMessage tool_calls before every model call."""

    @property
    def name(self) -> str:
        return "dangling_tool_call"

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        repaired = _repair(list(request.messages))
        return handler(request.override(messages=repaired))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable,
    ) -> ModelResponse:
        repaired = _repair(list(request.messages))
        return await handler(request.override(messages=repaired))
