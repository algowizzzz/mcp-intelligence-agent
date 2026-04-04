# REQ-05 — Summarization Engine: Claude Code-Style Context Management
**Status:** Pending Implementation
**Version:** 1.0
**Date:** 2026-04-04
**Scope:** Replace the current reactive, single-level summarization with a robust rolling compression engine modeled after Claude Code's approach — automated, conservative, transparent to the user, and keeping context utilization below 20% after each compression.

---

## 1. Background & Current State

### 1.1 Existing Architecture

The platform already has a summarization scaffold. Key components:

| Component | File | Current State |
|---|---|---|
| `SummarisationMiddleware` | `agent/summariser.py` | Implemented but has significant gaps |
| `MessageTrimmer` | `agent/agent.py` lines 14–51 | Character-based trimming (200k chars) |
| Token counting | `agent/summariser.py` line 16–17 | Heuristic: `len(str(content)) // 4` |
| Trigger threshold | `CONTEXT_WARN_TOKENS=120000` | Environment variable, defaults to 120k estimated |
| Tail preserve | `_TAIL_KEEP = 10` messages | Last 10 messages always kept verbatim |
| Persistence | `MemorySaver` in-memory | Lost on server restart |
| Frontend awareness | Token counter in header | Cumulative only, no context fullness gauge |

### 1.2 Model Context Window

Model: `claude-sonnet-4-20250514` (or configured via `ANTHROPIC_MODEL` env var)
Context window: **200,000 tokens**
Maximum output: **8,192 tokens** (configurable)

### 1.3 Current Gaps

1. **Inaccurate token counting** — character/4 heuristic is off by 20–30%
2. **Single-level compression** — one summary replaces head; no rolling/multi-level approach
3. **Frontend unaware** — client only sees cumulative tokens, not context fullness
4. **No preemptive trigger** — summarization fires on the NEXT request, potentially too late if a single tool result is very large
5. **Tool result pairs may split** — MessageTrimmer can remove a `tool_result` while keeping the `tool_use`, causing agent confusion
6. **In-memory only** — conversation state lost on restart; no long-term history
7. **No user visibility** — no indication in chat that summarization occurred
8. **Too aggressive at 120k** — fires at 60% of context; goal is to fire conservatively and bring usage back to <20%

---

## 2. Design Goals

The new engine must behave like Claude Code's context management:

1. **Conservative triggering** — only summarize when approaching a meaningful threshold (target: 80% of context window = 160,000 tokens)
2. **Aggressive compression** — after summarization, context usage must drop to ≤20% (40,000 tokens)
3. **Transparent to user** — a compact notice appears in chat ("💡 Conversation summarized — context refreshed")
4. **Accurate token counting** — use the actual Claude tokenizer approximation, not char/4
5. **Tool pair integrity** — never split a `tool_use` / `tool_result` pair during compression
6. **Persistent state** — conversation history survives server restarts (SQLite checkpoint)
7. **Frontend gauge** — the header token counter shows context utilization as a progress indicator
8. **Not too frequent** — after one summarization event, at least 20 full exchanges should be possible before the next

---

## 3. Token Counting Improvement

### 3.1 Replace Heuristic with Anthropic-Aligned Estimator

The `claude-sonnet-4-20250514` model uses the same tokenizer as other Claude models. A reliable approximation:

```python
# Replace in agent/summariser.py and agent/agent.py:

def count_tokens_accurate(messages: list) -> int:
    """
    Accurate token count for Claude models.
    Anthropic uses a variant of cl100k_base; average is ~3.8 chars/token for English.
    For system prompts and tool schemas (JSON), ratio is ~2.5 chars/token.
    We use a weighted approach: text at 4 chars/token, JSON at 2.5 chars/token.
    """
    total = 0
    for msg in messages:
        content = msg.content if hasattr(msg, 'content') else str(msg)
        if isinstance(content, list):
            # Multi-part message (tool_use + tool_result blocks)
            for block in content:
                if isinstance(block, dict):
                    text = json.dumps(block)
                    # JSON is denser
                    total += max(1, len(text) // 2)
                else:
                    total += max(1, len(str(block)) // 4)
        elif isinstance(content, str):
            total += max(1, len(content) // 4)
        # Add per-message overhead (role prefix, separators)
        total += 4
    # Add system prompt estimate if available
    return total
```

**Optionally** install `tiktoken` for better accuracy:
```bash
pip install tiktoken
```
```python
import tiktoken
_enc = tiktoken.get_encoding("cl100k_base")

def count_tokens_accurate(messages: list) -> int:
    total = 0
    for msg in messages:
        content = msg.content if hasattr(msg, 'content') else ''
        if isinstance(content, list):
            content = json.dumps(content)
        total += len(_enc.encode(str(content))) + 4  # +4 for message overhead
    return total
```

### 3.2 Track System Prompt Tokens

The system prompt is injected fresh on each request. It must be counted as part of context usage:

```python
def get_total_context_tokens(system_prompt: str, messages: list) -> int:
    system_tokens = count_tokens_accurate([{'content': system_prompt}])
    message_tokens = count_tokens_accurate(messages)
    # Tool schema tokens (approximate — schemas are static per session)
    tool_schema_tokens = _cached_tool_schema_tokens()
    return system_tokens + message_tokens + tool_schema_tokens
```

Tool schema tokens should be estimated once at startup and cached.

---

## 4. Summarization Engine Design

### 4.1 Thresholds

```python
# Environment variables (add to .env / deployment config)
CONTEXT_MAX_TOKENS = 200000       # Claude Sonnet 4 context window
CONTEXT_TRIGGER_PCT = 0.80        # Trigger at 80% = 160,000 tokens
CONTEXT_TARGET_PCT  = 0.18        # Target after summarization = 18% = 36,000 tokens
CONTEXT_TAIL_MESSAGES = 6         # Always keep last 6 complete exchanges verbatim
CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES = 20  # Don't summarize more than once per 20 exchanges

# Derived constants (computed from above)
_TRIGGER_TOKENS = int(CONTEXT_MAX_TOKENS * CONTEXT_TRIGGER_PCT)  # 160,000
_TARGET_TOKENS  = int(CONTEXT_MAX_TOKENS * CONTEXT_TARGET_PCT)   # 36,000
```

### 4.2 Message Grouping: Exchange Units

Before any trimming or summarization, messages must be grouped into **exchange units** — logical pairs (or groups) that must not be split:

```python
class ExchangeUnit:
    """
    An atomic unit of conversation that should not be split.
    An exchange consists of:
    - 1 user message
    - 1 or more tool_use AI messages
    - Corresponding tool_result messages
    - 1 final AI response to the user
    """
    messages: List[BaseMessage]
    token_count: int
    has_tool_calls: bool
```

The grouping algorithm:
1. Walk messages in order
2. When a `HumanMessage` is seen, start a new exchange unit
3. All subsequent `AIMessage` and `ToolMessage` entries until the next `HumanMessage` belong to the same unit
4. A unit with tool calls includes both the `tool_use` AIMessage AND all corresponding `tool_result` ToolMessages

**CRITICAL INVARIANT:** `tool_use` and `tool_result` messages are NEVER in different exchange units and are NEVER separated during compression.

### 4.3 The Compression Algorithm

```python
def compress_context(messages: list, system_prompt: str) -> tuple[list, str | None]:
    """
    Returns (new_messages, summary_text_or_None).
    new_messages is the compressed list to replace state['messages'].
    summary_text is the text of what was summarized (for UI display).
    """
    total = get_total_context_tokens(system_prompt, messages)

    if total < _TRIGGER_TOKENS:
        return messages, None  # No compression needed

    # Group into exchange units
    units = group_into_exchanges(messages)

    # Always keep last CONTEXT_TAIL_MESSAGES exchange units verbatim
    tail_units = units[-CONTEXT_TAIL_MESSAGES:]
    head_units = units[:-CONTEXT_TAIL_MESSAGES]

    if not head_units:
        # Can't compress — all messages are in the tail
        # MessageTrimmer will handle overflow via hard truncation
        return messages, None

    # Estimate tokens after compression
    tail_tokens = sum(u.token_count for u in tail_units)
    target_summary_tokens = max(2000, _TARGET_TOKENS - tail_tokens - system_tokens)

    # Summarize the head exchanges
    head_messages = [m for u in head_units for m in u.messages]
    summary = call_summarizer_llm(head_messages, max_summary_tokens=target_summary_tokens)

    # Build new message list: [SystemMessage(summary)] + tail_messages
    summary_msg = SystemMessage(
        content=f"## Conversation Summary\n\n{summary}\n\n"
                f"---\n*{len(head_messages)} earlier messages summarized — "
                f"{len(head_units)} exchanges compressed*"
    )
    tail_messages = [m for u in tail_units for m in u.messages]
    new_messages = [summary_msg] + tail_messages

    # Verify compression achieved target
    new_total = get_total_context_tokens(system_prompt, new_messages)
    assert new_total <= _TARGET_TOKENS * 1.2, f"Compression insufficient: {new_total} > {_TARGET_TOKENS}"

    return new_messages, summary
```

### 4.4 Summarization Prompt (Enhanced)

Replace the current `SUMMARISE_PROMPT` in `agent/prompt.py`:

```python
SUMMARISE_PROMPT = """You are a context compressor for a financial risk intelligence session on the B-Pulse platform.

Compress the conversation history below into a precise, information-dense summary.

MANDATORY PRESERVATION — include ALL of the following if present:
- Every counterparty name with its exposure, limit, rating, and any breaches
- Every specific figure: notional amounts, MTM values, PFE, VaR, utilization percentages, dates
- Every file or workflow referenced (exact filenames, section paths)
- Every tool call and its key output: what was asked, what was returned, what source was cited
- Any decisions made, action items, or unresolved questions raised by the user
- Any errors, 404s, or data gaps the agent reported

OMIT entirely:
- Greetings, pleasantries, filler phrases
- Repeated boilerplate from tool schemas or error messages
- Intermediate reasoning steps that did not produce a final answer

FORMAT REQUIREMENTS:
- Plain prose paragraphs (no markdown headers)
- Maximum {max_tokens} tokens
- Third-person past tense ("The user asked...", "The agent retrieved...", "The analysis found...")
- Conclude with: "PENDING: [any unresolved questions or action items]"

Output only the summary text, no preamble."""
```

### 4.5 Anti-Frequency Guard

Track the exchange count since last summarization. Do not trigger again until at least `CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES` exchanges have occurred:

```python
class SummarisationMiddleware:
    def __init__(self):
        self._last_summary_exchange_count: dict[str, int] = {}  # thread_id → exchange count at last summary
        self._exchange_counts: dict[str, int] = {}              # thread_id → total exchange count

    def before_agent(self, state, runtime):
        thread_id = runtime.config.get('configurable', {}).get('thread_id', '')
        self._exchange_counts[thread_id] = self._exchange_counts.get(thread_id, 0) + 1
        last = self._last_summary_exchange_count.get(thread_id, 0)
        exchanges_since_last = self._exchange_counts[thread_id] - last

        if exchanges_since_last < CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES:
            return None  # Too soon — skip

        new_messages, summary = compress_context(state['messages'], get_system_prompt())
        if summary:
            self._last_summary_exchange_count[thread_id] = self._exchange_counts[thread_id]
            return {'messages': new_messages, '_summary_occurred': True}
        return None
```

---

## 5. Persistent Conversation Storage

### 5.1 Replace MemorySaver with SQLite Checkpointer

**File:** `agent/agent.py`

```python
# Current (in-memory only):
checkpointer = MemorySaver()

# Replace with:
from langgraph.checkpoint.sqlite import SqliteSaver

_DB_PATH = os.getenv('CHECKPOINT_DB_PATH', './sajhamcpserver/data/checkpoints.db')
checkpointer = SqliteSaver.from_conn_string(_DB_PATH)
```

Install: `pip install langgraph-checkpoint-sqlite`

This gives conversation persistence across server restarts at no additional infrastructure cost. When PostgreSQL is deployed (REQ-07), the checkpointer should migrate to `langgraph-checkpoint-postgres`.

### 5.2 Thread Cleanup Policy

Add a background task that runs daily to clean up old threads:

```python
# In agent_server.py, add a startup background task:
@app.on_event('startup')
async def cleanup_old_threads():
    cutoff = datetime.utcnow() - timedelta(days=int(os.getenv('THREAD_RETENTION_DAYS', '30')))
    # Delete threads older than cutoff from SQLite checkpoint DB
    # Delete corresponding entries from threads.jsonl
    pass
```

---

## 6. SSE Events for Context Status

### 6.1 New Event Type: `context_status`

After each LLM response, emit a `context_status` event with the current token usage:

```python
# In agent_server.py, after on_chat_model_end:
yield f"data: {json.dumps({'type': 'context_status', 'tokens_used': total_tokens, 'tokens_max': 200000, 'pct': round(total_tokens / 200000 * 100, 1)})}\n\n"
```

### 6.2 New Event Type: `summary_occurred`

When `SummarisationMiddleware` compresses the context, emit:

```python
yield f"data: {json.dumps({'type': 'summary_occurred', 'exchanges_compressed': N, 'tokens_before': X, 'tokens_after': Y})}\n\n"
```

---

## 7. Frontend Requirements

### 7.1 Context Gauge in Header

Replace the current plain token counter `<span id="token-display">0 tok</span>` with a progress indicator:

```html
<div id="context-gauge-wrap">
  <div id="context-gauge-bar">
    <div id="context-gauge-fill" style="width: 0%"></div>
  </div>
  <span id="context-gauge-label">0%</span>
  <span id="token-display">0 tok</span>
</div>
```

```css
#context-gauge-wrap {
    display: flex;
    align-items: center;
    gap: 6px;
}
#context-gauge-bar {
    width: 80px;
    height: 6px;
    background: #333;
    border-radius: 3px;
    overflow: hidden;
}
#context-gauge-fill {
    height: 100%;
    background: #4ade80;  /* green */
    transition: width 0.5s ease, background 0.3s ease;
}
/* Warning state: 60–80% */
#context-gauge-fill.warn { background: #facc15; }
/* Critical state: >80% */
#context-gauge-fill.critical { background: #f87171; }
```

```javascript
function updateContextGauge(tokensUsed, tokensMax) {
    var pct = Math.min(100, Math.round(tokensUsed / tokensMax * 100));
    var fill = $('context-gauge-fill');
    var label = $('context-gauge-label');
    fill.style.width = pct + '%';
    fill.className = pct >= 80 ? 'critical' : pct >= 60 ? 'warn' : '';
    label.textContent = pct + '%';
    $('token-display').textContent = formatTokens(tokensUsed) + ' tok';
}

// Handle new SSE event:
else if (type === 'context_status') {
    updateContextGauge(evt.tokens_used, evt.tokens_max);
}
```

### 7.2 Summary Notice in Chat

When a `summary_occurred` SSE event is received, insert a system notice into the chat:

```javascript
else if (type === 'summary_occurred') {
    var notice = document.createElement('div');
    notice.className = 'summary-notice';
    notice.innerHTML =
        '<span class="summary-icon">💡</span>' +
        '<span class="summary-text">Conversation context compressed — ' +
            evt.exchanges_compressed + ' earlier exchanges summarized. ' +
            'Context usage reset from ' + Math.round(evt.tokens_before / 2000) + '% to ' +
            Math.round(evt.tokens_after / 2000) + '%.' +
        '</span>';
    $('chat-messages').appendChild(notice);
}
```

```css
.summary-notice {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    margin: 8px 0;
    background: rgba(74, 222, 128, 0.06);
    border: 1px solid rgba(74, 222, 128, 0.15);
    border-radius: 6px;
    font-size: 12px;
    color: #9ca3af;
    font-style: italic;
}
.summary-icon { font-size: 14px; }
```

### 7.3 Context Warning Banner (Optional, for >80%)

When context gauge reaches >80%, show a dismissible banner above the chat input:

```javascript
function showContextWarning() {
    if ($('context-warning-banner')) return;  // Only show once
    var banner = document.createElement('div');
    banner.id = 'context-warning-banner';
    banner.className = 'context-warning';
    banner.innerHTML =
        'Context nearing limit — this conversation will be automatically compressed on the next message. ' +
        '<a href="#" onclick="archiveAndContinue()">Archive & start fresh</a> ' +
        '<button onclick="this.parentNode.remove()" class="dismiss-btn">✕</button>';
    $('chat-input-area').prepend(banner);
}
```

---

## 8. Environment Configuration

Add the following to `.env` and document in deployment guide:

```bash
# Summarization Engine
CONTEXT_MAX_TOKENS=200000
CONTEXT_TRIGGER_PCT=0.80              # Trigger compression at 80%
CONTEXT_TARGET_PCT=0.18               # Target ≤18% after compression
CONTEXT_TAIL_MESSAGES=6               # Exchange units to preserve verbatim
CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES=20

# Persistence
CHECKPOINT_BACKEND=sqlite             # 'sqlite' or 'postgres' (see REQ-07)
CHECKPOINT_DB_PATH=./sajhamcpserver/data/checkpoints.db
THREAD_RETENTION_DAYS=30

# Token counting
USE_TIKTOKEN=true                     # Use tiktoken for accuracy (requires pip install tiktoken)
```

---

## 9. Interaction with Existing Components

### 9.1 MessageTrimmer (Hard Fallback)

`MessageTrimmer` in `agent/agent.py` remains as a **last-resort hard fallback**. It should only fire if `SummarisationMiddleware` failed or if a single message is so large it exceeds the target:

- Change its character limit from `200_000` to `800_000` (200k tokens × 4 chars/token) to avoid premature triggering
- It only removes AI messages that are NOT part of a tool pair
- Log a warning whenever it fires (it should be rare after the summarizer is working)

### 9.2 Agent Server Context Count Injection

The `agent_server.py` must pass the current conversation length to the frontend after each response. This requires counting messages in the LangGraph state after the run completes:

```python
# After agent.astream_events() completes:
final_state = await agent.aget_state(config)
if final_state and final_state.values:
    msg_count = len(final_state.values.get('messages', []))
    total_tokens = count_tokens_accurate(final_state.values.get('messages', []))
    yield f"data: {json.dumps({'type': 'context_status', 'tokens_used': total_tokens, 'tokens_max': 200000, 'pct': round(total_tokens / 200000 * 100, 1), 'message_count': msg_count})}\n\n"
```

---

## 10. Testing Plan

| Test | Scenario | Expected Result |
|---|---|---|
| SUM-TEST-001 | Send 5 short messages | No compression triggered (well below threshold) |
| SUM-TEST-002 | Send 20 messages with large tool outputs totalling >160k tokens | Compression triggered; summary notice appears in chat; gauge resets to <20% |
| SUM-TEST-003 | After compression in TEST-002, ask "what did we discuss earlier?" | Agent correctly references the prior conversation summary |
| SUM-TEST-004 | Verify tool pairs not split | Create a conversation with many tool calls; after compression, confirm no orphaned tool_use messages |
| SUM-TEST-005 | Restart server mid-conversation | With SQLite checkpoint: conversation resumes with same context (no data loss) |
| SUM-TEST-006 | Send message immediately after compression | Second compression does NOT trigger (anti-frequency guard) |
| SUM-TEST-007 | Context gauge accuracy | After each response, gauge % matches actual token usage within ±5% |
| SUM-TEST-008 | >80% context warning | Banner appears when gauge exceeds 80% |

---

## 11. Acceptance Criteria

- [ ] Summarization triggers at ≥80% context usage (160k tokens), not before
- [ ] After summarization, context usage is ≤20% (40k tokens)
- [ ] Tool use / tool result message pairs are never split during compression
- [ ] Compression fires at most once per 20 exchanges (anti-frequency guard)
- [ ] Summary notice appears in chat UI after each compression event
- [ ] Context gauge in header shows accurate percentage with color coding (green/yellow/red)
- [ ] Conversation persists across server restarts (SQLite checkpointing)
- [ ] `context_status` SSE event emitted after every LLM response
- [ ] SUM-TEST-001 through SUM-TEST-008: All pass

---

## 12. Out of Scope

- Multi-session context sharing (separate conversations cannot share context)
- User-initiated "Archive & Continue" (nice-to-have, Phase 2)
- Hierarchical multi-level summaries (Phase 2 — single level is sufficient for 200k context)
- Per-user summary storage in cloud (covered by REQ-07 DB migration)
