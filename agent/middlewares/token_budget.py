"""
TokenBudgetMiddleware — proactive per-query token budget enforcement.

Tracks cumulative token usage per thread_id across model calls.
- If usage >= 100% of budget: raises BudgetExceededError (caught by agent_server
  to emit a budget_exceeded SSE event).
- If usage >= warn_pct (default 80%): injects a warning message into the prompt
  so the model knows to wrap up its analysis.

Usage tracking is accumulated in a class-level dict keyed by thread_id.
Call TokenBudgetMiddleware.cleanup(thread_id) at the end of each query to reset.
"""
from __future__ import annotations

import logging
from typing import Callable

from langchain.agents.factory import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when a thread has consumed its full token budget for the current query."""

    def __init__(self, used: int, budget: int):
        self.used = used
        self.budget = budget
        super().__init__(
            f"Token budget exceeded: used {used:,} / {budget:,} tokens for this query."
        )


class TokenBudgetMiddleware(AgentMiddleware):
    """Per-query token budget enforcement with proactive warning injection.

    Args:
        max_tokens_per_query: Hard token ceiling per query. None = disabled (no-op).
        warn_pct: Fraction of budget at which to inject a warning message (default 0.80).
    """

    # Class-level usage tracker: thread_id → tokens used this query
    _usage: dict[str, int] = {}

    def __init__(
        self,
        max_tokens_per_query: int | None = None,
        warn_pct: float = 0.80,
    ):
        self.max_tokens_per_query = max_tokens_per_query
        self.warn_pct = warn_pct

    @property
    def name(self) -> str:
        return "token_budget"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_thread_id(self, runtime) -> str:
        try:
            return runtime.config.get("configurable", {}).get("thread_id", "")
        except Exception:
            return ""

    def _extract_usage(self, response) -> int:
        """Pull input_tokens + output_tokens out of a ModelResponse."""
        try:
            msg = response.output if hasattr(response, "output") else response
            um = getattr(msg, "usage_metadata", None)
            if um is None:
                return 0
            if isinstance(um, dict):
                return int(um.get("input_tokens", 0)) + int(um.get("output_tokens", 0))
            return int(getattr(um, "input_tokens", 0)) + int(getattr(um, "output_tokens", 0))
        except Exception:
            return 0

    def _inject_warning(self, request: ModelRequest, remaining: int) -> ModelRequest:
        """Inject a budget-warning notice into the last HumanMessage or as a SystemMessage."""
        warning_text = (
            f"[BUDGET WARNING: ~{remaining:,} tokens remaining for this query. "
            "Wrap up your analysis soon.]"
        )
        messages = list(request.messages)

        # Try to append to the last HumanMessage
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], HumanMessage):
                original_content = messages[i].content
                if isinstance(original_content, str):
                    messages[i] = HumanMessage(
                        content=f"{original_content}\n\n{warning_text}"
                    )
                else:
                    # list-content (multimodal) — append a text block
                    messages[i] = HumanMessage(
                        content=list(original_content) + [{"type": "text", "text": warning_text}]
                    )
                return request.override(messages=messages)

        # No HumanMessage found — prepend as a SystemMessage
        if request.system_message:
            new_system = SystemMessage(
                content=f"{warning_text}\n\n{request.system_message.content}"
            )
            return request.override(messages=messages, system_message=new_system)

        # Fallback: insert as first message
        messages.insert(0, SystemMessage(content=warning_text))
        return request.override(messages=messages)

    def _check_and_modify(self, request: ModelRequest, thread_id: str) -> ModelRequest:
        """Check budget and optionally inject warning. Raises BudgetExceededError if over budget."""
        if self.max_tokens_per_query is None:
            return request

        used = self.__class__._usage.get(thread_id, 0)
        budget = self.max_tokens_per_query

        if used >= budget:
            logger.warning(
                "TokenBudgetMiddleware: thread=%s budget exceeded (%d/%d tokens).",
                thread_id, used, budget,
            )
            raise BudgetExceededError(used=used, budget=budget)

        remaining = budget - used
        warn_threshold = int(budget * self.warn_pct)

        if used >= warn_threshold:
            logger.info(
                "TokenBudgetMiddleware: thread=%s warning threshold reached (%d/%d). Injecting warning.",
                thread_id, used, budget,
            )
            request = self._inject_warning(request, remaining)

        return request

    # ------------------------------------------------------------------
    # wrap_model_call — check budget before calling the model
    # ------------------------------------------------------------------

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        thread_id = self._get_thread_id(request.runtime)
        request = self._check_and_modify(request, thread_id)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable,
    ) -> ModelResponse:
        thread_id = self._get_thread_id(request.runtime)
        request = self._check_and_modify(request, thread_id)
        return await handler(request)

    # ------------------------------------------------------------------
    # after_model — accumulate token usage
    # ------------------------------------------------------------------

    def _accumulate(self, state, runtime) -> None:
        """Extract usage from latest AI message in state and accumulate."""
        if self.max_tokens_per_query is None:
            return
        thread_id = self._get_thread_id(runtime)
        if not thread_id:
            return
        try:
            messages = state.get("messages", []) if isinstance(state, dict) else getattr(state, "messages", [])
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
            if tokens > 0:
                self.__class__._usage[thread_id] = self.__class__._usage.get(thread_id, 0) + tokens
                logger.debug(
                    "TokenBudgetMiddleware: thread=%s accumulated +%d tokens (total=%d).",
                    thread_id, tokens, self.__class__._usage[thread_id],
                )
        except Exception as exc:
            logger.debug("TokenBudgetMiddleware: could not accumulate usage — %s", exc)

    def after_model(self, state, runtime) -> dict | None:
        self._accumulate(state, runtime)
        return None

    async def aafter_model(self, state, runtime) -> dict | None:
        self._accumulate(state, runtime)
        return None

    # ------------------------------------------------------------------
    # Class-level lifecycle helpers
    # ------------------------------------------------------------------

    @classmethod
    def cleanup(cls, thread_id: str) -> None:
        """Remove usage tracking for a completed thread/query."""
        cls._usage.pop(thread_id, None)

    @classmethod
    def get_usage(cls, thread_id: str) -> int:
        """Return current token usage for the given thread_id."""
        return cls._usage.get(thread_id, 0)
