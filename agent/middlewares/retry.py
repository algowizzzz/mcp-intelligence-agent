"""
RetryMiddleware — exponential backoff retry for transient tool failures.

Wraps tool calls BEFORE ToolErrorHandlingMiddleware catches them.
Retries on transient errors (429, 503, rate limits, timeouts) with
exponential backoff + jitter. Non-retryable errors (4xx except 429,
validation errors, GraphBubbleUp) are re-raised immediately.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Callable

from langchain.agents.factory import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphBubbleUp

logger = logging.getLogger(__name__)

# Keywords/substrings that indicate a retryable transient error
_RETRYABLE_SUBSTRINGS = (
    "429",
    "503",
    "502",
    "rate limit",
    "service unavailable",
    "connection reset",
    "timeout",
    "connectionerror",
    "timeouterror",
)

# Keywords that indicate a non-retryable client / validation error
_NON_RETRYABLE_SUBSTRINGS = (
    "invalid",
    "required",
)

# HTTP 4xx codes (except 429) are not retryable
_NON_RETRYABLE_4XX = {str(c) for c in range(400, 500) if c != 429}


def _is_retryable(exc: Exception) -> bool:
    """Return True if the exception represents a transient, retryable error."""
    # Never retry LangGraph control-flow bubbles
    if isinstance(exc, GraphBubbleUp):
        return False

    msg = str(exc).lower()
    exc_type = type(exc).__name__

    # Check non-retryable 4xx HTTP codes first
    for code in _NON_RETRYABLE_4XX:
        if code in msg:
            return False

    # Validation / input errors are not retryable
    for substr in _NON_RETRYABLE_SUBSTRINGS:
        if substr in msg:
            return False

    # Check exception type name
    if exc_type.lower() in ("connectionerror", "timeouterror"):
        return True

    # Check message substrings
    for substr in _RETRYABLE_SUBSTRINGS:
        if substr in msg:
            return True

    return False


class RetryMiddleware(AgentMiddleware):
    """Exponential backoff retry middleware for transient tool call failures.

    Attempt schedule (base_delay=1.0, jitter=0.2 by default):
        attempt 1 → fail → wait ~1s → attempt 2 → fail → wait ~2s → attempt 3 → re-raise
    """

    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, jitter: float = 0.2):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.jitter = jitter

    @property
    def name(self) -> str:
        return "retry"

    def _delay(self, attempt: int) -> float:
        """Return seconds to wait after `attempt` (0-indexed)."""
        base = self.base_delay * (2 ** attempt)
        noise = random.uniform(-self.jitter, self.jitter)
        return max(0.0, base + noise)

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable,
    ) -> ToolMessage:
        last_exc: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                return handler(request)
            except GraphBubbleUp:
                raise
            except Exception as exc:
                if not _is_retryable(exc):
                    raise
                last_exc = exc
                if attempt < self.max_attempts - 1:
                    delay = self._delay(attempt)
                    tool_name = request.tool_call.get("name", "unknown") if isinstance(request.tool_call, dict) else getattr(request.tool_call, "name", "unknown")
                    logger.warning(
                        "RetryMiddleware: tool=%s attempt=%d/%d failed (%s). Retrying in %.2fs.",
                        tool_name,
                        attempt + 1,
                        self.max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable,
    ) -> ToolMessage:
        last_exc: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                return await handler(request)
            except GraphBubbleUp:
                raise
            except Exception as exc:
                if not _is_retryable(exc):
                    raise
                last_exc = exc
                if attempt < self.max_attempts - 1:
                    delay = self._delay(attempt)
                    tool_name = request.tool_call.get("name", "unknown") if isinstance(request.tool_call, dict) else getattr(request.tool_call, "name", "unknown")
                    logger.warning(
                        "RetryMiddleware: tool=%s attempt=%d/%d failed (%s). Retrying in %.2fs.",
                        tool_name,
                        attempt + 1,
                        self.max_attempts,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]
