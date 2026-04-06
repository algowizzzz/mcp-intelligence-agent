"""
agent.middlewares — pluggable middleware for the SAJHA Intelligence Platform.

Available middleware
--------------------
DanglingToolCallMiddleware
    Repairs orphaned AIMessage.tool_calls before each model call by injecting
    synthetic ToolMessage(content="[interrupted]", status="error") for every
    tool_call_id that has no corresponding ToolMessage in the history.

LoopDetectionMiddleware
    Detects repeated identical tool calls (same tool + same args) using an
    MD5-hashed sliding window per thread.  Embeds a warning at warn_threshold
    hits and strips all tool_calls at hard_limit hits.

ToolErrorHandlingMiddleware
    Catches uncaught tool exceptions and returns a graceful error ToolMessage
    instead of crashing the agent run.  GraphBubbleUp is always re-raised so
    HITL interrupts are never swallowed.

SubagentLimitMiddleware
    Caps the number of parallel task() sub-agent calls in a single AIMessage
    to max_concurrent (clamped to [2, 4]).  Excess calls are dropped and a
    note is appended to the AIMessage content.

RetryMiddleware
    Exponential backoff retry for transient tool failures (429, 503, timeouts,
    rate limits) BEFORE ToolErrorHandlingMiddleware catches them.  Non-retryable
    errors (4xx except 429, validation errors, GraphBubbleUp) are re-raised
    immediately.

TokenBudgetMiddleware
    Proactive per-query token budget enforcement.  Tracks cumulative token usage
    per thread_id, injects a budget-warning message at warn_pct (default 80%),
    and raises BudgetExceededError at 100%.

HumanInTheLoopMiddleware
    Gates sensitive tool calls behind human approval.  Matches tool names against
    fnmatch trigger patterns, emits hitl_required SSE events, and polls for
    respond() signals up to timeout_seconds before auto-rejecting.

MemoryMiddleware
    Persistent cross-session memory injection.  Retrieves relevant memories from
    SQLite using keyword-overlap similarity and prepends them to the system prompt.

AuditMiddleware
    Event logging to JSONL for all model calls, tool invocations, tool results,
    and errors.  Redacts sensitive keys before writing.  Fire-and-forget IO via
    background threads.

BudgetExceededError
    Exception raised by TokenBudgetMiddleware when a thread exhausts its token
    budget.  Caught by agent_server to emit a budget_exceeded SSE event.
"""

from .dangling_tool_call import DanglingToolCallMiddleware
from .loop_detection import LoopDetectionMiddleware
from .tool_error_handling import ToolErrorHandlingMiddleware
from .subagent_limit import SubagentLimitMiddleware
from .retry import RetryMiddleware
from .token_budget import TokenBudgetMiddleware, BudgetExceededError
from .hitl import HumanInTheLoopMiddleware
from .memory import MemoryMiddleware
from .audit import AuditMiddleware

__all__ = [
    "DanglingToolCallMiddleware",
    "LoopDetectionMiddleware",
    "ToolErrorHandlingMiddleware",
    "SubagentLimitMiddleware",
    "RetryMiddleware",
    "TokenBudgetMiddleware",
    "BudgetExceededError",
    "HumanInTheLoopMiddleware",
    "MemoryMiddleware",
    "AuditMiddleware",
]
