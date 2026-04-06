"""
AuditMiddleware — event logging to JSONL for all agent activity.

Logs each model call, tool invocation, tool result, and error as a JSON line
to a JSONL file (default: ./data/audit/agent_audit.jsonl).

Each event includes:
  id, session_id, worker_id, user_id, event_type, event_seq,
  tool_name, tool_args (redacted), tool_result (truncated),
  model_tokens, error_msg, duration_ms, created_at

Writes are fire-and-forget via threading.Thread for non-blocking IO.
Sensitive field values are redacted before logging (configurable patterns).
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from langchain.agents.factory import AgentMiddleware, ModelRequest, ModelResponse, ToolCallRequest
from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)

_DEFAULT_LOG_PATH = "./data/audit/agent_audit.jsonl"
_DEFAULT_REDACT_PATTERNS = [
    "password",
    "api_key",
    "token",
    "secret",
    "credential",
]
_MAX_RESULT_CHARS = 2000


class AuditMiddleware(AgentMiddleware):
    """Comprehensive audit logging for all agent events.

    Args:
        log_path: Path to the JSONL audit log file.
        enabled: Set False to disable all logging.
        retention_days: Informational only (not enforced by this class; use a cron job).
        redact_patterns: List of case-insensitive key patterns to redact from tool_args.
    """

    # Class-level per-session event sequence counters
    _event_seq: dict[str, int] = {}
    _seq_lock = threading.Lock()

    def __init__(
        self,
        log_path: str | None = None,
        enabled: bool = True,
        retention_days: int = 365,
        redact_patterns: list[str] | None = None,
    ):
        self.log_path = log_path or _DEFAULT_LOG_PATH
        self.enabled = enabled
        self.retention_days = retention_days
        self.redact_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (redact_patterns if redact_patterns is not None else _DEFAULT_REDACT_PATTERNS)
        ]
        # Per-instance wrap_tool_call timing tracker: tool_call_id → start_time
        self._tool_start_times: dict[str, float] = {}
        self._tool_start_lock = threading.Lock()

    @property
    def name(self) -> str:
        return "audit"

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _get_session_id(self, runtime) -> str:
        try:
            return runtime.config.get("configurable", {}).get("thread_id", "")
        except Exception:
            return ""

    def _get_worker_id(self, runtime) -> str:
        try:
            return runtime.config.get("configurable", {}).get("worker_id", "")
        except Exception:
            return ""

    def _get_user_id(self, runtime) -> str:
        try:
            return runtime.config.get("configurable", {}).get("user_id", "")
        except Exception:
            return ""

    def _get_runtime_from_request(self, request):
        return getattr(request, "runtime", None)

    def _next_seq(self, session_id: str) -> int:
        with self.__class__._seq_lock:
            n = self.__class__._event_seq.get(session_id, 0) + 1
            self.__class__._event_seq[session_id] = n
            return n

    # ------------------------------------------------------------------
    # Redaction
    # ------------------------------------------------------------------

    def _redact_value(self, value) -> str:
        return "[REDACTED]"

    def _redact_dict(self, d: dict) -> dict:
        """Recursively redact sensitive keys from a dict."""
        if not isinstance(d, dict):
            return d
        result = {}
        for k, v in d.items():
            if any(p.search(str(k)) for p in self.redact_patterns):
                result[k] = self._redact_value(v)
            elif isinstance(v, dict):
                result[k] = self._redact_dict(v)
            elif isinstance(v, list):
                result[k] = [
                    self._redact_dict(item) if isinstance(item, dict) else item
                    for item in v
                ]
            else:
                result[k] = v
        return result

    def _redact_args(self, args) -> dict:
        if isinstance(args, dict):
            return self._redact_dict(args)
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
                if isinstance(parsed, dict):
                    return self._redact_dict(parsed)
            except Exception:
                pass
        return {"_raw": str(args)}

    # ------------------------------------------------------------------
    # Core write
    # ------------------------------------------------------------------

    def _write_event(self, event: dict) -> None:
        """Write event dict as a JSON line. Non-blocking via thread."""
        if not self.enabled:
            return

        def _write():
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
                line = json.dumps(event, default=str) + "\n"
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception as exc:
                logger.warning("AuditMiddleware: failed to write event — %s", exc)

        threading.Thread(target=_write, daemon=True).start()

    def _base_event(
        self,
        event_type: str,
        session_id: str,
        worker_id: str,
        user_id: str,
    ) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "worker_id": worker_id,
            "user_id": user_id,
            "event_type": event_type,
            "event_seq": self._next_seq(session_id),
            "tool_name": None,
            "tool_args": None,
            "tool_result": None,
            "model_tokens": None,
            "error_msg": None,
            "duration_ms": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # wrap_model_call — log model_call event + timing
    # ------------------------------------------------------------------

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        runtime = self._get_runtime_from_request(request)
        session_id = self._get_session_id(runtime)
        worker_id = self._get_worker_id(runtime)
        user_id = self._get_user_id(runtime)

        start = time.perf_counter()
        response = handler(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        tokens = self._extract_tokens(response)
        event = self._base_event("model_call", session_id, worker_id, user_id)
        event["model_tokens"] = tokens
        event["duration_ms"] = duration_ms
        self._write_event(event)

        return response

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable,
    ) -> ModelResponse:
        runtime = self._get_runtime_from_request(request)
        session_id = self._get_session_id(runtime)
        worker_id = self._get_worker_id(runtime)
        user_id = self._get_user_id(runtime)

        start = time.perf_counter()
        response = await handler(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        tokens = self._extract_tokens(response)
        event = self._base_event("model_call", session_id, worker_id, user_id)
        event["model_tokens"] = tokens
        event["duration_ms"] = duration_ms
        self._write_event(event)

        return response

    def _extract_tokens(self, response) -> int | None:
        try:
            msg = response.output if hasattr(response, "output") else response
            um = getattr(msg, "usage_metadata", None)
            if um is None:
                return None
            if isinstance(um, dict):
                return int(um.get("input_tokens", 0)) + int(um.get("output_tokens", 0))
            return int(getattr(um, "input_tokens", 0)) + int(getattr(um, "output_tokens", 0))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # wrap_tool_call — log tool_call + tool_result events
    # ------------------------------------------------------------------

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable,
    ) -> ToolMessage:
        runtime = getattr(request, "runtime", None)
        session_id = self._get_session_id(runtime)
        worker_id = self._get_worker_id(runtime)
        user_id = self._get_user_id(runtime)

        tc = request.tool_call
        tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
        tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})

        # Log tool_call event
        call_event = self._base_event("tool_call", session_id, worker_id, user_id)
        call_event["tool_name"] = tool_name
        call_event["tool_args"] = self._redact_args(tool_args)
        self._write_event(call_event)

        start = time.perf_counter()
        try:
            result = handler(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            self._log_tool_result(result, tool_name, session_id, worker_id, user_id, duration_ms)
            return result
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            err_event = self._base_event("tool_error", session_id, worker_id, user_id)
            err_event["tool_name"] = tool_name
            err_event["error_msg"] = str(exc)[:500]
            err_event["duration_ms"] = duration_ms
            self._write_event(err_event)
            raise

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable,
    ) -> ToolMessage:
        runtime = getattr(request, "runtime", None)
        session_id = self._get_session_id(runtime)
        worker_id = self._get_worker_id(runtime)
        user_id = self._get_user_id(runtime)

        tc = request.tool_call
        tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
        tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})

        # Log tool_call event
        call_event = self._base_event("tool_call", session_id, worker_id, user_id)
        call_event["tool_name"] = tool_name
        call_event["tool_args"] = self._redact_args(tool_args)
        self._write_event(call_event)

        start = time.perf_counter()
        try:
            result = await handler(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            self._log_tool_result(result, tool_name, session_id, worker_id, user_id, duration_ms)
            return result
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            err_event = self._base_event("tool_error", session_id, worker_id, user_id)
            err_event["tool_name"] = tool_name
            err_event["error_msg"] = str(exc)[:500]
            err_event["duration_ms"] = duration_ms
            self._write_event(err_event)
            raise

    def _log_tool_result(
        self,
        result,
        tool_name: str,
        session_id: str,
        worker_id: str,
        user_id: str,
        duration_ms: float,
    ) -> None:
        result_content = ""
        if isinstance(result, ToolMessage):
            c = result.content
            result_content = c if isinstance(c, str) else json.dumps(c, default=str)
        else:
            result_content = str(result)

        result_event = self._base_event("tool_result", session_id, worker_id, user_id)
        result_event["tool_name"] = tool_name
        result_event["tool_result"] = result_content[:_MAX_RESULT_CHARS]
        result_event["duration_ms"] = duration_ms
        self._write_event(result_event)

    # ------------------------------------------------------------------
    # after_model — log model_call token usage from state
    # ------------------------------------------------------------------

    def _log_from_state(self, state, runtime) -> None:
        """Log model usage extracted from state messages (supplemental)."""
        session_id = self._get_session_id(runtime)
        worker_id = self._get_worker_id(runtime)
        user_id = self._get_user_id(runtime)

        try:
            messages = (
                state.get("messages", []) if isinstance(state, dict)
                else getattr(state, "messages", [])
            )
            if not messages:
                return
            last = messages[-1]
            um = getattr(last, "usage_metadata", None)
            if um is None:
                return
            if isinstance(um, dict):
                tokens = int(um.get("input_tokens", 0)) + int(um.get("output_tokens", 0))
            else:
                tokens = int(getattr(um, "input_tokens", 0)) + int(getattr(um, "output_tokens", 0))

            if tokens <= 0:
                return

            # Check for budget warning flag from TokenBudgetMiddleware if set in state
            event_type = "model_call"
            try:
                if isinstance(state, dict) and state.get("_budget_warning"):
                    event_type = "budget_warning"
            except Exception:
                pass

            event = self._base_event(event_type, session_id, worker_id, user_id)
            event["model_tokens"] = tokens
            self._write_event(event)
        except Exception as exc:
            logger.debug("AuditMiddleware: failed to log from state — %s", exc)

    def after_model(self, state, runtime) -> dict | None:
        # after_model token logging is covered by wrap_model_call.
        # This hook is kept as an extension point (e.g., loop detection).
        return None

    async def aafter_model(self, state, runtime) -> dict | None:
        return None
