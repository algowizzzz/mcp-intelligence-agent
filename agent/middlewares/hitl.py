"""
HumanInTheLoopMiddleware — approval gating for sensitive tool calls.

After the model produces an AIMessage with tool_calls, checks each tool name
against a list of fnmatch patterns (triggers). If a match is found:
  1. Emits a hitl_required SSE event with tool details and a unique hitl_id.
  2. Polls for approval/rejection (via respond() class method) up to timeout_seconds.
  3. On approve: lets the tool_call proceed unchanged.
  4. On reject/timeout: removes the tool_call from the AIMessage and emits an SSE
     rejection event.

agent_server.py calls HumanInTheLoopMiddleware.respond(hitl_id, approved) from
the POST /api/chat/hitl-response endpoint.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from fnmatch import fnmatch
from typing import Callable

from langchain.agents.factory import AgentMiddleware
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)


class HumanInTheLoopMiddleware(AgentMiddleware):
    """Gate sensitive tool calls behind a human approval step.

    Args:
        triggers: List of fnmatch patterns matched against tool names.
                  Example: ["delete_*", "send_email", "execute_*"]
                  If None or empty, no tools are gated.
        timeout_seconds: How long to wait for human approval before auto-rejecting.
    """

    # Class-level registry: hitl_id → {event, approved, timestamp, tool_name, tool_args}
    _pending: dict[str, dict] = {}
    _pending_lock = threading.Lock()

    def __init__(
        self,
        triggers: list[str] | None = None,
        timeout_seconds: int = 300,
    ):
        self.triggers = triggers or []
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "hitl"

    # ------------------------------------------------------------------
    # Class-level API (called by agent_server endpoint)
    # ------------------------------------------------------------------

    @classmethod
    def respond(cls, hitl_id: str, approved: bool) -> bool:
        """Signal approval or rejection for a pending HITL gate.

        Returns True if the hitl_id was found and updated, False if unknown.
        """
        with cls._pending_lock:
            if hitl_id not in cls._pending:
                return False
            cls._pending[hitl_id]["approved"] = approved
            cls._pending[hitl_id]["event"].set()
            return True

    @classmethod
    def list_pending(cls) -> list[dict]:
        """Return a snapshot of all pending HITL gates (for admin UI)."""
        with cls._pending_lock:
            return [
                {
                    "hitl_id": hid,
                    "tool_name": v["tool_name"],
                    "tool_args": v["tool_args"],
                    "timestamp": v["timestamp"],
                }
                for hid, v in cls._pending.items()
                if v.get("approved") is None
            ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _matches_trigger(self, tool_name: str) -> bool:
        return any(fnmatch(tool_name, pattern) for pattern in self.triggers)

    def _emit_sse(self, payload: dict) -> None:
        """Best-effort SSE emission via agent_server's stream writer context var."""
        try:
            from agent_server import get_stream_writer  # type: ignore[import]
            writer = get_stream_writer()
            if writer:
                writer(json.dumps(payload))
        except Exception:
            pass

    def _register_pending(self, hitl_id: str, tool_name: str, tool_args: dict) -> threading.Event:
        event = threading.Event()
        with self.__class__._pending_lock:
            self.__class__._pending[hitl_id] = {
                "event": event,
                "approved": None,
                "timestamp": time.time(),
                "tool_name": tool_name,
                "tool_args": tool_args,
            }
        return event

    def _cleanup_pending(self, hitl_id: str) -> None:
        with self.__class__._pending_lock:
            self.__class__._pending.pop(hitl_id, None)

    def _wait_for_decision(
        self,
        hitl_id: str,
        event: threading.Event,
        tool_name: str,
        tool_args: dict,
    ) -> bool:
        """Block (with polling) until approved/rejected or timeout. Returns True if approved."""
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            signalled = event.wait(timeout=0.5)
            if signalled:
                with self.__class__._pending_lock:
                    result = self.__class__._pending.get(hitl_id, {}).get("approved")
                if result is not None:
                    return bool(result)
        # Timeout
        logger.warning("HumanInTheLoopMiddleware: hitl_id=%s timed out after %ds.", hitl_id, self.timeout_seconds)
        return False

    def _process_message(self, state, runtime, is_async: bool = False) -> dict | None:
        """Core logic shared by after_model / aafter_model."""
        if not self.triggers:
            return None

        messages = (
            state.get("messages", []) if isinstance(state, dict)
            else getattr(state, "messages", [])
        )
        if not messages:
            return None

        last_msg = messages[-1]
        if not isinstance(last_msg, AIMessage):
            return None

        tool_calls = list(getattr(last_msg, "tool_calls", None) or [])
        if not tool_calls:
            return None

        # Filter tool_calls that match any trigger
        gated_indices = []
        for i, tc in enumerate(tool_calls):
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            if self._matches_trigger(name):
                gated_indices.append(i)

        if not gated_indices:
            return None

        approved_calls = list(tool_calls)

        for i in gated_indices:
            tc = tool_calls[i]
            tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            hitl_id = "hitl-" + uuid.uuid4().hex[:8]

            event = self._register_pending(hitl_id, tool_name, tool_args)

            self._emit_sse({
                "type": "hitl_required",
                "tool": tool_name,
                "args": tool_args,
                "hitl_id": hitl_id,
                "timeout": self.timeout_seconds,
            })

            logger.info(
                "HumanInTheLoopMiddleware: gating tool=%s hitl_id=%s (timeout=%ds).",
                tool_name, hitl_id, self.timeout_seconds,
            )

            approved = self._wait_for_decision(hitl_id, event, tool_name, tool_args)
            self._cleanup_pending(hitl_id)

            if not approved:
                logger.info(
                    "HumanInTheLoopMiddleware: tool=%s hitl_id=%s rejected/timed out.",
                    tool_name, hitl_id,
                )
                self._emit_sse({
                    "type": "hitl_rejected",
                    "tool": tool_name,
                    "hitl_id": hitl_id,
                    "reason": "timeout" if True else "rejected",
                })
                approved_calls[i] = None  # mark for removal

        # Rebuild AIMessage with only approved tool_calls
        final_calls = [c for c in approved_calls if c is not None]

        if len(final_calls) == len(tool_calls):
            return None  # No changes needed

        new_msg = AIMessage(
            content=last_msg.content,
            tool_calls=final_calls,
        )
        new_messages = list(messages[:-1]) + [new_msg]
        return {"messages": new_messages}

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def after_model(self, state, runtime) -> dict | None:
        return self._process_message(state, runtime, is_async=False)

    async def aafter_model(self, state, runtime) -> dict | None:
        # Polling uses threading.Event.wait() which is safe to call from async
        # context (releases GIL); for production, consider asyncio.Event instead.
        return self._process_message(state, runtime, is_async=True)
