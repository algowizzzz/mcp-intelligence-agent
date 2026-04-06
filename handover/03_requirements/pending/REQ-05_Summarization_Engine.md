# REQ-05 — Summarization Engine: Claude Code-Style Context Management
**Status:** Pending Implementation
**Version:** 1.1 (Updated 2026-04-04 — 180k trigger, SQLite in /data, gauge in both UIs, permanent system notice)
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
| Trigger threshold | `CONTEXT_WARN_TOKENS=120000` | Defaults to 120k — too aggressive |
| Tail preserve | `_TAIL_KEEP = 10` messages | Last 10 messages always kept verbatim |
| Persistence | `MemorySaver` in-memory | Lost on server restart |
| Frontend awareness | Token counter in header | Cumulative only, no context fullness gauge |

### 1.2 Model Context Window

Model: `claude-sonnet-4-20250514` (or configured via `ANTHROPIC_MODEL` env var)
Context window: **200,000 tokens**
Maximum output: **8,192 tokens** (configurable)

### 1.3 Current Gaps

1. **Inaccurate token counting** — character/4 heuristic is off by 20–30%
2. **Single-level compression** — one summary replaces head; no rolling approach
3. **Frontend unaware** — client only sees cumulative tokens, not context fullness %
4. **No preemptive trigger** — summarization fires on the NEXT request, potentially too late if a single tool result is very large
5. **Tool result pairs may split** — `MessageTrimmer` can remove a `tool_result` while keeping `tool_use`, causing agent confusion
6. **In-memory only** — conversation state lost on restart; no long-term history
7. **No user visibility** — no indication in chat that summarization occurred
8. **Triggers too early at 120k** — fires at 60% of context; should be 90% (180k tokens)

---

## 2. Design Goals

The new engine must behave like Claude Code's context management:

1. **Conservative triggering** — only summarize at 90% of context window (180,000 tokens)
2. **Aggressive compression** — after summarization, context usage must drop to ≤20% (40,000 tokens)
3. **Transparent to user** — a compact permanent system notice appears in chat (like Claude Code's "Context compacted" inline notice — not a banner, not dismissable, just part of the thread)
4. **Accurate token counting** — use the actual Claude tokenizer approximation, not char/4
5. **Tool pair integrity** — never split a `tool_use` / `tool_result` pair during compression
6. **Persistent state** — conversation history survives server restarts (SQLite in `/data/`)
7. **Frontend gauge in both UIs** — context gauge shown in `mcp-agent.html` header AND `admin.html` header
8. **Not too frequent** — after one summarization event, at least 20 full exchanges should pass before the next

---

## 3. Token Counting Improvement

### 3.1 Replace Heuristic with Anthropic-Aligned Estimator

```python
# Replace in agent/summariser.py and agent/agent.py:

def count_tokens_accurate(messages: list) -> int:
    """
    Accurate token count for Claude models.
    Weighted approach: text at 4 chars/token, JSON/tool content at 2.5 chars/token.
    """
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
        total += 4  # per-message overhead
    return total
```

**Optionally** install `tiktoken` for better accuracy (`pip install tiktoken`):
```python
import tiktoken
_enc = tiktoken.get_encoding("cl100k_base")

def count_tokens_accurate(messages: list) -> int:
    total = 0
    for msg in messages:
        content = msg.content if hasattr(msg, 'content') else ''
        if isinstance(content, list):
            content = json.dumps(content)
        total += len(_enc.encode(str(content))) + 4
    return total
```

### 3.2 Track System Prompt and Tool Schema Tokens

System prompt and tool schemas are injected fresh on each request and must be counted:

```python
def get_total_context_tokens(system_prompt: str, messages: list) -> int:
    system_tokens = count_tokens_accurate([{'content': system_prompt}])
    message_tokens = count_tokens_accurate(messages)
    tool_schema_tokens = _cached_tool_schema_tokens()  # estimated once at startup
    return system_tokens + message_tokens + tool_schema_tokens
```

---

## 4. Summarization Engine Design

### 4.1 Thresholds

```python
# Environment variables (add to .env)
CONTEXT_MAX_TOKENS = 200000          # Claude Sonnet 4 context window
CONTEXT_TRIGGER_TOKENS = 180000      # Trigger at 180,000 tokens (90% of window)
CONTEXT_TARGET_PCT = 0.18            # Target after summarization = 18% = ~36,000 tokens
CONTEXT_TAIL_MESSAGES = 6            # Always keep last 6 complete exchange units verbatim
CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES = 20  # Anti-frequency guard

# Derived
_TARGET_TOKENS = int(CONTEXT_MAX_TOKENS * CONTEXT_TARGET_PCT)  # ~36,000
```

### 4.2 Message Grouping: Exchange Units

Before any trimming, group messages into **exchange units** — logical groups that must never be split:

```python
class ExchangeUnit:
    """
    An atomic unit: 1 user message + all associated AI tool_use messages
    + all corresponding tool_result messages + 1 final AI response.
    """
    messages: List[BaseMessage]
    token_count: int
    has_tool_calls: bool
```

Algorithm:
1. Walk messages in order
2. When a `HumanMessage` is seen, start a new exchange unit
3. All `AIMessage` and `ToolMessage` entries until the next `HumanMessage` belong to the same unit

**CRITICAL INVARIANT:** `tool_use` and `tool_result` messages are NEVER in different exchange units and are NEVER separated during compression.

### 4.3 Compression Algorithm

```python
def compress_context(messages: list, system_prompt: str) -> tuple[list, str | None]:
    total = get_total_context_tokens(system_prompt, messages)

    if total < CONTEXT_TRIGGER_TOKENS:
        return messages, None  # No compression needed

    units = group_into_exchanges(messages)

    tail_units = units[-CONTEXT_TAIL_MESSAGES:]
    head_units = units[:-CONTEXT_TAIL_MESSAGES]

    if not head_units:
        return messages, None  # Can't compress — all in tail; MessageTrimmer handles overflow

    tail_tokens = sum(u.token_count for u in tail_units)
    target_summary_tokens = max(2000, _TARGET_TOKENS - tail_tokens)

    head_messages = [m for u in head_units for m in u.messages]
    summary = call_summarizer_llm(head_messages, max_summary_tokens=target_summary_tokens)

    summary_msg = SystemMessage(
        content=f"## Conversation Summary\n\n{summary}\n\n"
                f"---\n*{len(head_messages)} earlier messages summarized — "
                f"{len(head_units)} exchanges compressed*"
    )
    tail_messages = [m for u in tail_units for m in u.messages]
    new_messages = [summary_msg] + tail_messages

    return new_messages, summary
```

### 4.4 Summarization Prompt

Replace `SUMMARISE_PROMPT` in `agent/prompt.py`:

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

```python
class SummarisationMiddleware:
    def __init__(self):
        self._last_summary_exchange_count: dict[str, int] = {}
        self._exchange_counts: dict[str, int] = {}

    def before_agent(self, state, runtime):
        thread_id = runtime.config.get('configurable', {}).get('thread_id', '')
        self._exchange_counts[thread_id] = self._exchange_counts.get(thread_id, 0) + 1
        last = self._last_summary_exchange_count.get(thread_id, 0)

        if (self._exchange_counts[thread_id] - last) < CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES:
            return None  # Too soon

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
# Current (in-memory, lost on restart):
checkpointer = MemorySaver()

# Replace with:
from langgraph.checkpoint.sqlite import SqliteSaver

_DB_PATH = os.getenv('CHECKPOINT_DB_PATH', './sajhamcpserver/data/checkpoints.db')
checkpointer = SqliteSaver.from_conn_string(_DB_PATH)
```

Install: `pip install langgraph-checkpoint-sqlite`

SQLite file location: `sajhamcpserver/data/checkpoints.db`. Added to `.gitignore` (runtime artifact — do not commit).

When PostgreSQL is deployed (REQ-07), migrate to `langgraph-checkpoint-postgres`.

### 5.2 Thread Cleanup Policy

```python
@app.on_event('startup')
async def cleanup_old_threads():
    cutoff = datetime.utcnow() - timedelta(days=int(os.getenv('THREAD_RETENTION_DAYS', '30')))
    # Delete threads older than cutoff from checkpoints.db and threads.jsonl
    pass
```

---

## 6. SSE Events for Context Status

### 6.1 `context_status` Event

After each LLM response, emit token usage:

```python
yield f"data: {json.dumps({'type': 'context_status', 'tokens_used': total_tokens, 'tokens_max': 200000, 'pct': round(total_tokens / 200000 * 100, 1)})}\n\n"
```

### 6.2 `summary_occurred` Event

When compression fires:

```python
yield f"data: {json.dumps({'type': 'summary_occurred', 'exchanges_compressed': N, 'tokens_before': X, 'tokens_after': Y})}\n\n"
```

---

## 7. Frontend Requirements

### 7.1 Context Gauge — Both `mcp-agent.html` and `admin.html`

Add the context gauge to the header of **both** HTML files. It replaces (or extends) the existing token counter.

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
    background: #4ade80;
    transition: width 0.5s ease, background 0.3s ease;
}
#context-gauge-fill.warn     { background: #facc15; }  /* 60–90% */
#context-gauge-fill.critical { background: #f87171; }  /* >90%   */
```

```javascript
function updateContextGauge(tokensUsed, tokensMax) {
    var pct = Math.min(100, Math.round(tokensUsed / tokensMax * 100));
    var fill = $('context-gauge-fill');
    var label = $('context-gauge-label');
    fill.style.width = pct + '%';
    fill.className = pct >= 90 ? 'critical' : pct >= 60 ? 'warn' : '';
    label.textContent = pct + '%';
    $('token-display').textContent = formatTokens(tokensUsed) + ' tok';
}

// In SSE handler:
else if (type === 'context_status') {
    updateContextGauge(evt.tokens_used, evt.tokens_max);
}
```

### 7.2 Summary Notice in Chat (Permanent System Message)

When a `summary_occurred` SSE event is received, insert a permanent inline notice — **not dismissable, not a banner**, styled like Claude Code's "Context compacted" notice. It sits in the thread as part of the conversation history:

```javascript
else if (type === 'summary_occurred') {
    var notice = document.createElement('div');
    notice.className = 'summary-notice';
    notice.innerHTML =
        '<span class="summary-icon">⬡</span>' +
        '<span class="summary-text">Context compacted — ' +
            evt.exchanges_compressed + ' earlier exchanges compressed. ' +
            'Context reset from ' +
            Math.round(evt.tokens_before / 2000) + '% to ' +
            Math.round(evt.tokens_after / 2000) + '%.' +
        '</span>';
    $('chat-messages').appendChild(notice);
    // Scroll into view
    notice.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
```

```css
.summary-notice {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    margin: 6px 0;
    background: rgba(74, 222, 128, 0.04);
    border-left: 2px solid rgba(74, 222, 128, 0.3);
    font-size: 11.5px;
    color: #6b7280;
    font-style: italic;
    user-select: none;
}
.summary-icon {
    font-size: 11px;
    color: #4ade80;
    opacity: 0.7;
}
```

### 7.3 Context Warning at >90%

When the gauge hits >90%, add a subtle warning line above the chat input (dismissable):

```javascript
function showContextWarning() {
    if ($('context-warning-banner')) return;
    var banner = document.createElement('div');
    banner.id = 'context-warning-banner';
    banner.className = 'context-warning';
    banner.innerHTML =
        'Context nearing limit — will auto-compress on next message. ' +
        '<button onclick="this.parentNode.remove()" class="dismiss-btn">✕</button>';
    $('chat-input-area').prepend(banner);
}
```

---

## 8. Environment Configuration

```bash
# Summarization Engine
CONTEXT_MAX_TOKENS=200000
CONTEXT_TRIGGER_TOKENS=180000         # Trigger at 180k (90% of window)
CONTEXT_TARGET_PCT=0.18               # Compress to ≤18%
CONTEXT_TAIL_MESSAGES=6               # Verbatim tail exchange units
CONTEXT_MIN_EXCHANGES_BETWEEN_SUMMARIES=20

# Persistence
CHECKPOINT_BACKEND=sqlite
CHECKPOINT_DB_PATH=./sajhamcpserver/data/checkpoints.db
THREAD_RETENTION_DAYS=30

# Token counting
USE_TIKTOKEN=true
```

`checkpoints.db` is added to `.gitignore` — it is a runtime file, not committed to git.

---

## 9. Interaction with Existing Components

### 9.1 MessageTrimmer (Hard Fallback)

`MessageTrimmer` in `agent/agent.py` remains as a **last-resort fallback** only. Change its character limit from `200_000` to `800_000` (200k tokens × 4 chars) to avoid premature triggering. It must only fire if the summarizer failed or a single message exceeds the budget.

### 9.2 Agent Server Token Injection

After each agent run, emit context status:

```python
final_state = await agent.aget_state(config)
if final_state and final_state.values:
    total_tokens = count_tokens_accurate(final_state.values.get('messages', []))
    yield f"data: {json.dumps({'type': 'context_status', 'tokens_used': total_tokens, 'tokens_max': 200000, 'pct': round(total_tokens / 200000 * 100, 1)})}\n\n"
```

---

## 10. Testing Plan

| Test ID | Scenario | Expected Result |
|---|---|---|
| SUM-TEST-001 | Send 5 short messages | No compression triggered |
| SUM-TEST-002 | Messages totalling >180k tokens | Compression triggered; summary notice in chat; gauge resets to <20% |
| SUM-TEST-003 | After compression: "what did we discuss earlier?" | Agent references prior summary correctly |
| SUM-TEST-004 | Verify tool pairs not split | After compression, no orphaned `tool_use` messages in state |
| SUM-TEST-005 | Restart server mid-conversation | Conversation resumes with same context (SQLite persistence) |
| SUM-TEST-006 | Message immediately after compression | Second compression does NOT trigger (anti-frequency guard) |
| SUM-TEST-007 | Context gauge accuracy | After each response, gauge % matches actual tokens within ±5% |
| SUM-TEST-008 | >90% context | Warning line appears above chat input |
| SUM-TEST-009 | Admin.html gauge | Gauge visible and updating in admin panel header |

---

## 11. Acceptance Criteria

- [ ] Summarization triggers at ≥180k tokens, not before
- [ ] After summarization, context usage is ≤20% (~40k tokens)
- [ ] Tool use / tool result pairs are never split
- [ ] Compression fires at most once per 20 exchanges (anti-frequency guard)
- [ ] Permanent summary notice appears in chat thread — styled like Claude Code, not dismissable
- [ ] Context gauge in `mcp-agent.html` header: accurate %, green/yellow/red
- [ ] Context gauge in `admin.html` header: accurate %, same styling
- [ ] Conversation persists across server restarts (SQLite in `sajhamcpserver/data/`)
- [ ] `context_status` SSE event emitted after every LLM response
- [ ] `summary_occurred` SSE event emitted after each compression
- [ ] `checkpoints.db` added to `.gitignore`
- [ ] SUM-TEST-001 through SUM-TEST-009 all pass

---

## 12. Out of Scope

- Multi-session context sharing
- User-initiated "Archive & Continue"
- Hierarchical multi-level summaries
- Per-user summary storage in cloud (covered by REQ-07)
