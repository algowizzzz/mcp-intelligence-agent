"""
SummarisationMiddleware — rolling context compression engine for the B-Pulse platform.

Design:
- Triggers at CONTEXT_TRIGGER_TOKENS (default 180,000 — 90% of the 200k context window)
- Groups messages into ExchangeUnit objects so tool_use/tool_result pairs are never split
- Keeps last CONTEXT_TAIL_MESSAGES=6 exchange units verbatim
- Compresses head exchanges via a single LLM call
- Anti-frequency guard: at least CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES=20 exchanges
  must pass between consecutive compression events per thread
- Returns {'messages': ..., '_summary_occurred': True, 'exchanges_compressed': N,
           'tokens_before': X, 'tokens_after': Y} when compression fires
- Uses weighted token counting: text at 4 chars/token, JSON at 2.5 chars/token
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from langchain.agents.factory import AgentMiddleware
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from .prompt import SUMMARISE_PROMPT, get_system_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds (all overridable via environment variables)
# ---------------------------------------------------------------------------
_CONTEXT_MAX_TOKENS = int(os.getenv('CONTEXT_MAX_TOKENS', '200000'))
_CONTEXT_TRIGGER_TOKENS = int(os.getenv('CONTEXT_TRIGGER_TOKENS', '180000'))
_CONTEXT_TARGET_PCT = float(os.getenv('CONTEXT_TARGET_PCT', '0.18'))
_CONTEXT_TAIL_MESSAGES = int(os.getenv('CONTEXT_TAIL_MESSAGES', '6'))
_CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES = int(
    os.getenv('CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES', '20')
)

_TARGET_TOKENS = int(_CONTEXT_MAX_TOKENS * _CONTEXT_TARGET_PCT)  # ~36,000


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

def count_tokens_accurate(messages: list) -> int:
    """
    Accurate token count for Claude models.
    Weighted approach: plain text at 4 chars/token, JSON/tool content at 2.5 chars/token.
    Optionally uses tiktoken if USE_TIKTOKEN=true is set and the package is available.
    """
    use_tiktoken = os.getenv('USE_TIKTOKEN', 'false').lower() == 'true'
    if use_tiktoken:
        try:
            import tiktoken
            _enc = tiktoken.get_encoding('cl100k_base')
            total = 0
            for msg in messages:
                content = msg.content if hasattr(msg, 'content') else ''
                if isinstance(content, list):
                    content = json.dumps(content)
                total += len(_enc.encode(str(content))) + 4
            return total
        except ImportError:
            pass  # Fall through to weighted heuristic

    total = 0
    for msg in messages:
        content = msg.content if hasattr(msg, 'content') else str(msg)
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = json.dumps(block)
                    total += max(1, len(text) // 2)   # JSON is denser
                else:
                    total += max(1, len(str(block)) // 4)
        elif isinstance(content, str):
            total += max(1, len(content) // 4)
        else:
            total += max(1, len(str(content)) // 4)
        total += 4  # per-message overhead
    return total


def get_total_context_tokens(system_prompt: str, messages: list) -> int:
    """Count tokens for system prompt + message history together."""
    # Wrap system_prompt as a minimal object that count_tokens_accurate can handle
    class _FakeMsg:
        def __init__(self, text):
            self.content = text
    system_tokens = count_tokens_accurate([_FakeMsg(system_prompt)])
    message_tokens = count_tokens_accurate(messages)
    return system_tokens + message_tokens


# ---------------------------------------------------------------------------
# Exchange unit grouping
# ---------------------------------------------------------------------------

@dataclass
class ExchangeUnit:
    """
    An atomic unit: 1 user message + all associated AI tool_use messages
    + all corresponding tool_result messages + 1 final AI response.

    CRITICAL INVARIANT: tool_use and tool_result messages are NEVER in
    different exchange units and are NEVER separated during compression.
    """
    messages: List[BaseMessage] = field(default_factory=list)
    token_count: int = 0
    has_tool_calls: bool = False

    def add(self, msg: BaseMessage, tokens: int):
        self.messages.append(msg)
        self.token_count += tokens
        msg_type = getattr(msg, 'type', '')
        content = getattr(msg, 'content', '')
        if msg_type == 'tool' or (
            msg_type == 'ai' and isinstance(content, list) and
            any(isinstance(b, dict) and b.get('type') == 'tool_use' for b in content)
        ):
            self.has_tool_calls = True


def group_into_exchanges(messages: list) -> List[ExchangeUnit]:
    """
    Walk messages in order and group them into ExchangeUnit objects.

    Algorithm:
    - A HumanMessage starts a new exchange unit
    - All AIMessage and ToolMessage entries until the next HumanMessage
      belong to the same unit
    """
    units: List[ExchangeUnit] = []
    current: Optional[ExchangeUnit] = None

    for msg in messages:
        msg_type = getattr(msg, 'type', '')
        tokens = count_tokens_accurate([msg])

        if msg_type == 'human':
            # Start a new exchange unit
            current = ExchangeUnit()
            units.append(current)
            current.add(msg, tokens)
        elif current is not None:
            # AI, tool, system — belong to the current exchange unit
            current.add(msg, tokens)
        else:
            # Messages before any HumanMessage (e.g., initial SystemMessage)
            # Put them in their own unit
            orphan = ExchangeUnit()
            orphan.add(msg, tokens)
            units.append(orphan)

    return units


# ---------------------------------------------------------------------------
# LLM summarisation call
# ---------------------------------------------------------------------------

def _call_summarizer_llm(head_messages: list, max_summary_tokens: int = 4000) -> str:
    """Call the LLM to produce a summary of head_messages."""
    from .llm_factory import create_llm
    llm = create_llm()

    history_text = '\n\n'.join(
        f'[{getattr(m, "type", "message").upper()}]: {getattr(m, "content", "")}'
        for m in head_messages
    )
    prompt_filled = SUMMARISE_PROMPT.replace('{max_tokens}', str(max_summary_tokens))

    prompt_msgs = [
        SystemMessage(content=prompt_filled),
        HumanMessage(content=history_text),
    ]
    response = llm.invoke(prompt_msgs)
    return getattr(response, 'content', str(response))


# ---------------------------------------------------------------------------
# Core compression function
# ---------------------------------------------------------------------------

def compress_context(
    messages: list,
    system_prompt: str,
) -> tuple[list, Optional[str], dict]:
    """
    Compress conversation history if it exceeds CONTEXT_TRIGGER_TOKENS.

    Returns:
        (new_messages, summary_text_or_None, metadata_dict)

    metadata_dict keys (only populated when summary_text is not None):
        exchanges_compressed: int
        tokens_before: int
        tokens_after: int
    """
    tokens_before = get_total_context_tokens(system_prompt, messages)

    if tokens_before < _CONTEXT_TRIGGER_TOKENS:
        return messages, None, {}

    units = group_into_exchanges(messages)

    if len(units) <= _CONTEXT_TAIL_MESSAGES:
        # Not enough exchanges to compress; MessageTrimmer is the last resort
        logger.warning(
            'Summariser: trigger reached but not enough exchange units to compress '
            '(%d units, tail=%d). Skipping.',
            len(units), _CONTEXT_TAIL_MESSAGES
        )
        return messages, None, {}

    tail_units = units[-_CONTEXT_TAIL_MESSAGES:]
    head_units = units[:-_CONTEXT_TAIL_MESSAGES]

    if not head_units:
        return messages, None, {}

    tail_tokens = sum(u.token_count for u in tail_units)
    target_summary_tokens = max(2000, _TARGET_TOKENS - tail_tokens)

    head_messages = [m for u in head_units for m in u.messages]

    try:
        summary_text = _call_summarizer_llm(head_messages, max_summary_tokens=target_summary_tokens)
    except Exception as exc:
        logger.error('Summariser: LLM call failed — %s. Skipping compression.', exc)
        return messages, None, {}

    summary_msg = SystemMessage(
        content=(
            f'## Conversation Summary\n\n{summary_text}\n\n'
            f'---\n*{len(head_messages)} earlier messages summarized — '
            f'{len(head_units)} exchanges compressed*'
        )
    )

    tail_messages = [m for u in tail_units for m in u.messages]
    new_messages = [summary_msg] + tail_messages

    tokens_after = get_total_context_tokens(system_prompt, new_messages)

    metadata = {
        'exchanges_compressed': len(head_units),
        'tokens_before': tokens_before,
        'tokens_after': tokens_after,
    }

    logger.info(
        'Summariser: compressed %d exchanges. tokens %d → %d (%.1f%% → %.1f%%)',
        len(head_units),
        tokens_before,
        tokens_after,
        tokens_before / _CONTEXT_MAX_TOKENS * 100,
        tokens_after / _CONTEXT_MAX_TOKENS * 100,
    )

    return new_messages, summary_text, metadata


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class SummarisationMiddleware(AgentMiddleware):
    """
    Before-agent hook that compresses conversation history when the token
    budget reaches CONTEXT_TRIGGER_TOKENS (default 180k).

    Anti-frequency guard: at least CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES
    full exchange turns must pass between consecutive compressions per thread.

    When compression fires, returns a state patch containing:
        {
            'messages': <new compressed message list>,
            '_summary_occurred': True,
            'exchanges_compressed': N,
            'tokens_before': X,
            'tokens_after': Y,
        }
    agent_server.py reads _summary_occurred to emit the SSE event.
    """

    def __init__(self):
        # Per-thread exchange counters (in-process only; reset on restart)
        self._exchange_counts: dict[str, int] = {}
        self._last_summary_exchange: dict[str, int] = {}

    @property
    def name(self) -> str:
        return 'summariser'

    def _get_thread_id(self, runtime) -> str:
        try:
            return runtime.config.get('configurable', {}).get('thread_id', '')
        except Exception:
            return ''

    def _get_system_prompt(self, runtime) -> str:
        try:
            worker_id = runtime.config.get('configurable', {}).get('worker_id', '')
            if worker_id:
                return get_system_prompt(worker_id)
        except Exception:
            pass
        # Fallback: import the module-level constant
        try:
            from .prompt import SYSTEM_PROMPT
            return SYSTEM_PROMPT
        except Exception:
            return ''

    def _run(self, state, runtime):
        """Core synchronous logic (shared by before_agent and abefore_agent)."""
        # Prevent double-fire if _summary_occurred is already in state
        if state.get('_summary_occurred'):
            return None

        thread_id = self._get_thread_id(runtime)

        # Update exchange counter
        self._exchange_counts[thread_id] = self._exchange_counts.get(thread_id, 0) + 1
        current_count = self._exchange_counts[thread_id]
        last_summary = self._last_summary_exchange.get(thread_id, 0)

        exchanges_since_last = current_count - last_summary
        if exchanges_since_last < _CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES:
            return None  # Anti-frequency guard: too soon after last compression

        messages = list(state.get('messages', []))
        system_prompt = self._get_system_prompt(runtime)

        new_messages, summary_text, metadata = compress_context(messages, system_prompt)

        if summary_text is None:
            return None  # No compression needed or failed

        # Record that we summarised at this exchange count
        self._last_summary_exchange[thread_id] = current_count

        return {
            'messages': new_messages,
            '_summary_occurred': True,
            **metadata,
        }

    def before_agent(self, state, runtime):
        return self._run(state, runtime)

    async def abefore_agent(self, state, runtime):
        # The LLM call inside _run is synchronous; for production async usage
        # this could be refactored to use ainvoke, but it is safe to call here
        # because LangGraph runs the hook in a thread pool when needed.
        return self._run(state, runtime)
