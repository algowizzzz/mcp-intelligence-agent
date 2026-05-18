# SAJHA Intelligence Platform

> **Source:** Converted from `REQ-14_Middleware_Phase2_Persistent_Memory.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

SAJHA Intelligence Platform

**REQ-14: Middleware Hardening Phase 2 & Persistent Memory**

**Status:** Partial — verified 2026-05-17

> **Verification (2026-05-17):**
> - **MemoryMiddleware** — class exists in `agent/middlewares/` but is **not** added to the default stack by `create_agent_for_worker` in `agent/agent.py:114-124`. Available as opt-in via `extra_middleware`.
> - **HumanInTheLoopMiddleware (HITL)** — same situation: coded, not wired by default.
> - **RetryMiddleware, TokenBudgetMiddleware, AuditMiddleware** — coded, not wired by default. This is the root cause of "audit `success: None`" complained about in `requirements/pending/REQ-14_Bug_Fixes_SubAgent_Audit_EDGAR.md`.
> - **Persistent memory backend** — Postgres is now wired via `AsyncPostgresSaver` (REQ-07 complete), but the agent still defaults to `AsyncSqliteSaver`. To activate Postgres-backed memory, set `DATABASE_URL` and accept the Phase 2 wiring.
> - **Naming collision warning:** there is a separate file `requirements/pending/REQ-14_Bug_Fixes_SubAgent_Audit_EDGAR.md` that also uses the REQ-14 number for a different scope (bug fixes). Consider renumbering one of them.

**Version:** 1.0 — Initial

**Date:** 2026-04-05

**Branch:** feature/middleware-phase2 (off main, after REQ-13 merges)

**Depends On:** REQ-13 (middleware chain), REQ-07 (PostgreSQL)

**Author:** SAJHA Engineering

Five middlewares deferred from REQ-13 DeerFlow analysis, implemented as Phase 2.

**1. Background**

**1.1 What REQ-13 Delivered**

REQ-13 built four middlewares and the full multi-agent execution framework. The middleware chain after REQ-13:

> mw = \[
>
> DanglingToolCallMiddleware(), \# fix orphaned tool_calls
>
> SummarisationMiddleware(), \# compress long conversations
>
> MessageTrimmer(), \# hard char-limit fallback
>
> \# ← position 4: reserved for MemoryMiddleware (this REQ)
>
> LoopDetectionMiddleware(), \# detect repeated tool calls
>
> ToolErrorHandlingMiddleware(), \# catch tool exceptions
>
> \]

**1.2 Five Gaps Identified**

During the DeerFlow 2.0 analysis for REQ-13, five additional middleware patterns were identified but deferred to keep REQ-13 scope tight:

|  |  |  |
|----|----|----|
| **Middleware** | **Gap It Fills** | **Hook** |
| **MemoryMiddleware** | Agent has no memory between sessions — every query starts cold | wrap_model_call |
| **RetryMiddleware** | Transient SAJHA failures (429, 503) kill the run permanently | wrap_tool_call |
| **TokenBudgetMiddleware** | No proactive cost control — agent burns tokens until Summarisation reacts | wrap_model_call |
| **HumanInTheLoopMiddleware** | LangGraph's GraphBubbleUp is re-raised but no admin-configurable trigger or UI | after_model |
| **AuditMiddleware** | No persistent record of tool calls, model responses, or errors for compliance | all hooks |

**1.3 Updated Middleware Chain After REQ-14**

> mw = \[
>
> DanglingToolCallMiddleware(), \# REQ-13: fix orphaned tool_calls
>
> SummarisationMiddleware(), \# existing: compress long conversations
>
> MessageTrimmer(), \# existing: hard char-limit fallback
>
> MemoryMiddleware(), \# REQ-14: inject cross-session memories
>
> TokenBudgetMiddleware(), \# REQ-14: proactive cost control
>
> RetryMiddleware(), \# REQ-14: retry transient tool failures
>
> LoopDetectionMiddleware(), \# REQ-13: detect repeated tool calls
>
> ToolErrorHandlingMiddleware(), \# REQ-13: catch non-retryable errors
>
> HumanInTheLoopMiddleware(), \# REQ-14: pause for admin-configured approvals
>
> AuditMiddleware(), \# REQ-14: log all events to PostgreSQL
>
> \]

RetryMiddleware sits before ToolErrorHandlingMiddleware intentionally — it retries transient failures first; ToolErrorHandlingMiddleware catches what remains after retries are exhausted.

**2. Component 1 — MemoryMiddleware (Persistent Cross-Session Memory)**

The largest and most impactful component. Gives the agent a persistent memory of past conversations scoped per user per worker — so users don't repeat context every session.

**2.1 Storage Schema**

**Database:** PostgreSQL (REQ-07). **Extension required:** pgvector

> CREATE TABLE memory_entries (
>
> id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
>
> worker_id TEXT NOT NULL,
>
> user_id TEXT NOT NULL,
>
> session_id TEXT NOT NULL,
>
> content TEXT NOT NULL, -- extracted memory fact
>
> embedding vector(1536), -- OpenAI/Anthropic embedding
>
> importance FLOAT DEFAULT 0.5, -- 0.0–1.0, set by extraction LLM
>
> created_at TIMESTAMPTZ DEFAULT now(),
>
> last_accessed TIMESTAMPTZ DEFAULT now(),
>
> expires_at TIMESTAMPTZ, -- NULL = no expiry
>
> source_summary TEXT -- brief context of origin query
>
> );
>
> CREATE INDEX ON memory_entries USING ivfflat (embedding vector_cosine_ops);
>
> CREATE INDEX ON memory_entries (worker_id, user_id, expires_at);

**2.2 Memory Extraction (Post-Conversation)**

At the end of each conversation, a background task makes a single LLM call (not part of the agent run) to extract worth-remembering facts. This is the DeerFlow-inspired pattern — the LLM itself decides what is worth storing.

Extraction prompt template:

> Given this conversation, extract 0–5 facts worth remembering for future sessions.
>
> Return JSON array. Each item: {"content": "...", "importance": 0.0–1.0}.
>
> Only extract facts that would change how you respond to this user in future queries.
>
> Examples worth storing:
>
> \- User prefers tables over prose for risk summaries
>
> \- Goldman Sachs CCR exposure was \$2.1B as of 2026-Q1
>
> \- User is focused on OSFI B-20 compliance for 2026 submissions
>
> Examples NOT worth storing:
>
> \- User said hello
>
> \- You listed 6 tools
>
> \- A query returned no results

Extracted facts are embedded (text-embedding-3-small) and stored in memory_entries. Triggered as a FastAPI BackgroundTask at conversation end — does not block the SSE response.

**2.3 Memory Retrieval (Pre-Model-Call)**

**Hook:** wrap_model_call / awrap_model_call

Before each LLM call, MemoryMiddleware retrieves top-K most relevant memories for the current query using cosine similarity on the query embedding. Retrieved memories are prepended to the system prompt:

> === MEMORIES FROM PAST SESSIONS ===
>
> (Recalled based on relevance to this query)
>
> \- \[2026-03-15\] Goldman Sachs CCR net MTM was \$2.1B, limit util 87%
>
> \- \[2026-02-20\] User prefers structured tables with limit utilisation %
>
> \- \[2026-01-10\] User is tracking OSFI B-20 compliance deadline Q3 2026
>
> Use these memories as context. Do not repeat them unless directly relevant.
>
> === END MEMORIES ===

Retrieval parameters (configurable per worker):

- max_memories_per_query — default 5, max 10

- min_similarity — cosine similarity threshold, default 0.75

- memory_ttl_days — default 90. Memories older than TTL are excluded from retrieval and cleaned up nightly

**2.4 Sub-Agent Memory Access**

- Sub-agents can READ memories (same worker_id + user_id scope)

- Sub-agents cannot WRITE memories — only the lead agent's conversation triggers extraction

- This prevents sub-agent ephemeral reasoning from polluting long-term memory

**2.5 Worker Config Extension**

**File:** agent_server.py — WorkerUpdateRequest

> enable_memory: Optional\[bool\] = False \# opt-in per worker
>
> memory_ttl_days: Optional\[int\] = 90
>
> max_memories_per_query: Optional\[int\] = 5
>
> min_memory_similarity: Optional\[float\] = 0.75

**2.6 Admin UI**

New collapsible "Memory" section in Worker Config panel (admin.html), shown only when enable_memory is toggled on. Fields: TTL (days), Max memories per query, Similarity threshold. Memory can be cleared per-user or all-users via an admin action button.

**3. Component 2 — RetryMiddleware**

**File:** agent/middlewares/retry.py (~90 lines) Hook: wrap_tool_call / awrap_tool_call

**3.1 Problem**

SAJHA MCP tools make HTTP calls that fail transiently — rate limits (429), service restarts (503), brief network drops. Currently ToolErrorHandlingMiddleware catches these and returns an error ToolMessage immediately, which the agent treats as a real failure and changes its reasoning accordingly. These failures are recoverable in seconds.

**3.2 Fix**

Wrap every tool call with exponential backoff retry before the error reaches ToolErrorHandlingMiddleware:

> Attempt 1 → fail (HTTP 429)
>
> Wait 1s
>
> Attempt 2 → fail (HTTP 503)
>
> Wait 2s
>
> Attempt 3 → success ← most transient failures recover here
>
> or → fail → raise to ToolErrorHandlingMiddleware

Retry conditions:

- **Retryable:** HTTP 429, 503, 502, network timeout, connection reset

- **Not retryable:** HTTP 4xx client errors, GraphBubbleUp (HITL interrupt), tool validation errors

- **Max attempts:** 3 (configurable per worker via max_tool_retries)

- **Backoff:** 1s, 2s, 4s (exponential, jitter ±200ms)

On final failure after all retries: re-raises the exception for ToolErrorHandlingMiddleware to catch and convert to an error ToolMessage as before. From the agent's perspective, tool failure handling is unchanged — it just happens less often.

**4. Component 3 — TokenBudgetMiddleware**

**File:** agent/middlewares/token_budget.py (~120 lines) Hook: wrap_model_call / awrap_model_call

**4.1 Problem**

Currently the platform reacts to token usage — Summarisation fires at 180K, MessageTrimmer at 800K. There is no per-query budget ceiling and no early warning. A runaway agent can consume tens of thousands of tokens before any intervention.

**4.2 Fix**

Proactive per-query token budget enforced before each LLM call:

> \# Before each model call, check running token count for this query
>
> if tokens_used \>= budget:
>
> \# Force terminate — return synthetic AIMessage with graceful summary
>
> raise BudgetExceededError(used=tokens_used, budget=budget)
>
> elif tokens_used \>= budget \* 0.80:
>
> \# Warn — embed notice in the upcoming model call
>
> system_prompt += f"\n\[BUDGET WARNING: {tokens_remaining} tokens remaining. Wrap up soon.\]"

Token counting uses the Anthropic usage fields returned in each model response (input_tokens + output_tokens, accumulated per query in thread-local storage). No external tokeniser dependency.

Worker config fields:

- max_tokens_per_query — default None (no limit). Admin sets a ceiling per worker

- token_budget_warn_pct — default 0.80 (80%). Warning threshold as fraction of budget

When budget is exceeded: the agent run ends gracefully. The lead agent receives a BudgetExceeded ToolMessage instructing it to synthesise with whatever context it has. The SSE stream emits a budget_exceeded event for the frontend to display a notice.

**5. Component 4 — HumanInTheLoopMiddleware**

**File:** agent/middlewares/hitl.py (~160 lines) Hook: after_model / aafter_model

**5.1 Problem**

LangGraph's GraphBubbleUp signal is already re-raised by ToolErrorHandlingMiddleware, but there is no admin-configurable trigger system, no frontend confirmation UI, and no timeout handling. HITL requires end-to-end wiring.

**5.2 Trigger Configuration**

Admin configures HITL triggers per worker in workers.json as a list of tool name patterns. When the model response includes a tool_call matching a trigger pattern, the run pauses before the tool executes:

> // workers.json — new field
>
> {
>
> "hitl_triggers": \[
>
> "execute_trade\_\*",
>
> "send_email\_\*",
>
> "delete\_\*",
>
> "submit_regulatory\_\*"
>
> \],
>
> "hitl_timeout_seconds": 300
>
> }

Patterns use fnmatch glob matching (same as task() tool filters). Empty list = HITL disabled.

**5.3 Flow**

> 1\. Model responds with tool_call matching a hitl_trigger pattern
>
> 2\. HumanInTheLoopMiddleware intercepts in after_model hook
>
> 3\. Emit SSE event: {"type": "hitl_required", "tool": "execute_trade_gsib",
>
> "args": {...}, "hitl_id": "abc123", "timeout": 300}
>
> 4\. Agent run PAUSES — stored in hitl_pending_registry\[hitl_id\]
>
> 5\. Frontend shows approval dialog with tool name + args preview
>
> 6a. User approves → POST /api/chat/hitl-response {hitl_id, approved: true}
>
> → agent resumes, tool executes normally
>
> 6b. User rejects → POST /api/chat/hitl-response {hitl_id, approved: false}
>
> → tool_call stripped from AIMessage, agent receives rejection ToolMessage
>
> 6c. Timeout → auto-reject after hitl_timeout_seconds
>
> → same as user rejection + SSE event: {"type": "hitl_timed_out", ...}

**5.4 Frontend**

New modal dialog in mcp-agent.html triggered by hitl_required SSE event. Shows: tool name, formatted args, Approve and Reject buttons, countdown timer. Submits to POST /api/chat/hitl-response. The chat input is disabled while HITL is pending.

**5.5 WorkerUpdateRequest Extension**

> hitl_triggers: Optional\[list\[str\]\] = None \# glob patterns, empty = disabled
>
> hitl_timeout_seconds: Optional\[int\] = 300

**6. Component 5 — AuditMiddleware**

**File:** agent/middlewares/audit.py (~140 lines) Hook: all hooks (wrap_model_call, after_model, wrap_tool_call)

**6.1 Problem**

There is no persistent record of what the agent did — which tools it called, what arguments it used, what the model responded, or what errors occurred. For a financial platform this is a compliance gap. Debugging is log-only with no queryable history.

**6.2 Storage Schema**

> CREATE TABLE audit_log (
>
> id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
>
> session_id TEXT NOT NULL,
>
> worker_id TEXT NOT NULL,
>
> user_id TEXT NOT NULL,
>
> event_type TEXT NOT NULL, -- model_call, tool_call, tool_result, error
>
> event_seq INT NOT NULL, -- ordering within session
>
> tool_name TEXT, -- populated for tool_call / tool_result
>
> tool_args JSONB,
>
> tool_result TEXT, -- truncated to 2000 chars
>
> model_tokens INT, -- input + output tokens for model_call events
>
> error_msg TEXT,
>
> duration_ms INT, -- tool execution time
>
> created_at TIMESTAMPTZ DEFAULT now()
>
> );
>
> CREATE INDEX ON audit_log (worker_id, user_id, created_at);
>
> CREATE INDEX ON audit_log (session_id);

**6.3 What Gets Logged**

|  |  |  |
|----|----|----|
| **Event Type** | **Logged Fields** | **Hook** |
| **model_call** | input token count, message count, memory_injected flag | wrap_model_call (before) |
| **model_response** | output tokens, tool_calls count, loop_warning flag | after_model |
| **tool_call** | tool_name, args (redacted if sensitive), duration_ms | wrap_tool_call (before) |
| **tool_result** | result truncated to 2000 chars, success/error status | wrap_tool_call (after) |
| **tool_retry** | tool_name, attempt number, error that caused retry | RetryMiddleware callback |
| **hitl_triggered** | tool_name, args, hitl_id, outcome (approved/rejected/timeout) | HumanInTheLoopMiddleware |
| **budget_exceeded** | tokens_used, budget, pct_used | TokenBudgetMiddleware |

Sensitive tool args (passwords, API keys, PII patterns) are redacted before storage using a configurable regex list in application.properties.

**6.4 Retention and Cleanup**

- audit_retention_days — configurable per worker, default 365. Nightly cleanup job deletes expired rows.

- Admin can manually purge a specific session or user's audit trail via the admin panel.

**6.5 Admin Audit Log Viewer**

New tab "Audit Log" in admin.html. Filterable by worker, user, date range, event type. Shows paginated table with session drill-down. Read-only. Exportable to CSV.

**7. Implementation Stories**

**Phase 0 — Branch**

|  |  |
|----|----|
| **ID** | **Description** |
| **S0** | Create feature/middleware-phase2 branch off main (after REQ-13 merges) |

**Phase 1 — MemoryMiddleware**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S1** | PostgreSQL schema: memory_entries table + pgvector index | Small |
| **S2** | Post-conversation memory extraction background task (LLM-powered) | Medium |
| **S3** | Embedding + pgvector similarity search for retrieval | Medium |
| **S4** | MemoryMiddleware: retrieve top-K and prepend to system prompt | Medium |
| **S5** | Worker config fields: enable_memory, ttl_days, max_memories, similarity | Small |
| **S6** | WorkerUpdateRequest extension for memory config | Small |
| **S7** | Admin UI: Memory section in Worker Config panel + clear action | Medium |
| **S8** | Sub-agent read-only memory access (no write) | Small |
| **S9** | Nightly TTL cleanup job | Small |
| **S10** | Unit tests: extraction, storage, retrieval, TTL expiry | QA |

**Phase 2 — RetryMiddleware**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S11** | RetryMiddleware with exponential backoff (1s, 2s, 4s, max 3 attempts) | Small |
| **S12** | Retryable vs non-retryable error classification | Small |
| **S13** | Audit hook: log tool_retry events | Small |
| **S14** | Unit tests: retry on 429, 503; no retry on 4xx; respects GraphBubbleUp | QA |

**Phase 3 — TokenBudgetMiddleware**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S15** | TokenBudgetMiddleware: thread-local token accumulator, warn at 80%, hard stop at 100% | Medium |
| **S16** | budget_exceeded SSE event + graceful synthesis prompt | Small |
| **S17** | Worker config: max_tokens_per_query, token_budget_warn_pct | Small |
| **S18** | Admin UI: token budget fields in Worker Config panel | Small |
| **S19** | Unit tests: warn threshold, hard stop, no-limit mode | QA |

**Phase 4 — HumanInTheLoopMiddleware**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S20** | HumanInTheLoopMiddleware: intercept matching tool_calls in after_model hook | Medium |
| **S21** | hitl_pending_registry + pause/resume mechanism | Medium |
| **S22** | POST /api/chat/hitl-response endpoint | Small |
| **S23** | hitl_timeout_seconds auto-reject background task | Small |
| **S24** | SSE events: hitl_required, hitl_approved, hitl_rejected, hitl_timed_out | Small |
| **S25** | Frontend: HITL modal dialog + countdown timer in mcp-agent.html | Medium |
| **S26** | Worker config: hitl_triggers, hitl_timeout_seconds + admin UI | Small |
| **S27** | Audit hook: log hitl_triggered events | Small |
| **S28** | Unit tests: trigger match, approve, reject, timeout | QA |

**Phase 5 — AuditMiddleware**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S29** | PostgreSQL schema: audit_log table + indexes | Small |
| **S30** | AuditMiddleware: log all hooks (model_call, model_response, tool_call, tool_result) | Medium |
| **S31** | Sensitive arg redaction (configurable regex in application.properties) | Small |
| **S32** | Nightly retention cleanup job | Small |
| **S33** | Admin UI: Audit Log tab with filters, pagination, session drill-down, CSV export | Large |
| **S34** | Worker config: audit_retention_days + admin UI | Small |
| **S35** | Unit tests: all event types logged, redaction, retention cleanup | QA |

**Phase 6 — Integration & UAT**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S36** | Integrate all 5 middlewares into create_agent_for_worker() in correct chain order | Medium |
| **S37** | Full regression: all existing UAT Phase 1–4 tests pass on feature branch | QA |
| **S38** | REQ-14 UAT suite (MEM-\*, RET-\*, BDG-\*, HIT-\*, AUD-\* tests) | QA |
| **S39** | Performance: confirm memory retrieval \<100ms p95 per query | QA |
| **S40** | PR to main with squash merge | DevOps |

**8. QA Test Plan**

**8.1 Memory Tests**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **MEM-01** | Conversation ends — memory extraction runs | BackgroundTask fires; LLM extracts facts; stored in memory_entries |
| **MEM-02** | Conversation with nothing memorable | Empty array returned; no rows inserted |
| **MEM-03** | Next query — relevant memory retrieved | Top-K memories prepended to system prompt before model call |
| **MEM-04** | Next query — irrelevant topic | No memories retrieved (below similarity threshold) |
| **MEM-05** | Memory TTL expired | Excluded from retrieval; deleted by nightly cleanup |
| **MEM-06** | Sub-agent reads memory | Retrieves correctly using same worker_id + user_id |
| **MEM-07** | Sub-agent write attempt | No extraction triggered; memory_entries unchanged after sub-agent run |
| **MEM-08** | Worker memory disabled (enable_memory=false) | MemoryMiddleware is a no-op; no DB calls; no prompt injection |
| **MEM-09** | Admin clears all memories for user | All rows for that user_id + worker_id deleted; confirmed via audit log |
| **MEM-10** | max_memories_per_query=3 | At most 3 memories injected regardless of similarity results |

**8.2 Retry Tests**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **RET-01** | Tool returns HTTP 429 | RetryMiddleware retries up to 3× with backoff; succeeds on retry |
| **RET-02** | Tool returns HTTP 503 all 3 attempts | After max retries, raises to ToolErrorHandlingMiddleware; error ToolMessage returned |
| **RET-03** | Tool returns HTTP 404 | No retry; immediately raises to ToolErrorHandlingMiddleware |
| **RET-04** | Tool raises GraphBubbleUp | Not retried; re-raised immediately |
| **RET-05** | Retry succeeds on attempt 2 | tool_retry audit event logged for attempt 1; tool_result logged for attempt 2 |
| **RET-06** | max_tool_retries=1 | Only 1 retry before escalating to ToolErrorHandlingMiddleware |

**8.3 Token Budget Tests**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **BDG-01** | Query uses 85% of budget | Warning injected into next model call system prompt |
| **BDG-02** | Query exceeds 100% of budget | Agent run terminated; synthesis prompt sent; budget_exceeded SSE event emitted |
| **BDG-03** | max_tokens_per_query=None (default) | TokenBudgetMiddleware is a no-op; no token tracking |
| **BDG-04** | Multi-agent worker: sub-agent token counts | Sub-agent tokens are separate from lead agent budget; lead budget tracks only lead |
| **BDG-05** | Budget exceeded on turn 3 of 10 | Agent wraps up gracefully with available context; does not hard-crash |

**8.4 Human-in-the-Loop Tests**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **HIT-01** | Tool matches hitl_triggers pattern | hitl_required SSE event emitted; agent pauses; frontend dialog appears |
| **HIT-02** | User approves HITL | POST hitl-response {approved: true}; tool executes; agent continues |
| **HIT-03** | User rejects HITL | POST hitl-response {approved: false}; rejection ToolMessage sent; agent continues without tool |
| **HIT-04** | HITL timeout | Auto-rejects after hitl_timeout_seconds; hitl_timed_out SSE event; agent continues |
| **HIT-05** | Tool does not match any trigger | No HITL; tool executes immediately |
| **HIT-06** | hitl_triggers empty (default) | HumanInTheLoopMiddleware is a no-op |
| **HIT-07** | Multiple HITL tools in one model response | Each is processed sequentially; separate hitl_id per tool |

**8.5 Audit Tests**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **AUD-01** | Normal query completes | model_call, model_response, tool_call, tool_result rows in audit_log |
| **AUD-02** | Tool fails with error | tool_result row with error_msg; duration_ms recorded |
| **AUD-03** | Tool retried | tool_retry row logged for failed attempt; tool_result for successful attempt |
| **AUD-04** | HITL triggered and approved | hitl_triggered row with outcome=approved |
| **AUD-05** | Budget exceeded | budget_exceeded row with tokens_used, budget, pct_used |
| **AUD-06** | Sensitive args in tool call | Redacted before storage; original not recoverable from audit_log |
| **AUD-07** | audit_retention_days=30 | Nightly cleanup deletes rows older than 30 days |
| **AUD-08** | Admin audit log viewer: filter by user | Returns only rows for that user_id across all sessions |
| **AUD-09** | Admin exports CSV | Downloaded CSV matches filtered table rows exactly |

**8.6 Regression**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **REG-01** | All REQ-13 UAT tests pass | Zero regressions from new middleware chain positions |
| **REG-02** | All existing UAT Phase 1–4 tests pass | Platform behaviour unchanged for single-agent workers with all defaults |
| **REG-03** | Memory disabled worker — identical to REQ-13 behaviour | No DB calls, no prompt modification, no performance impact |
| **REG-04** | No audit_log growth on memory-only queries (no tools called) | model_call and model_response events only; no spurious tool rows |

**9. Performance Considerations**

**9.1 MemoryMiddleware Latency**

Memory retrieval adds a pgvector cosine similarity query per model call. With a properly indexed table and \<= 100K rows per worker/user pair, p95 retrieval latency should be under 100ms. The embedding of the query (to compute similarity) uses the same model as the main agent — this is the dominant cost.

Mitigation: cache the query embedding for the duration of a session (same query embedding reused across multiple model calls in the same turn). Extraction runs as a BackgroundTask — zero impact on response latency.

**9.2 AuditMiddleware Throughput**

Audit writes are async fire-and-forget (FastAPI BackgroundTask). They do not block the SSE stream. At 10 tool calls per query with 50 concurrent users = 500 writes/min, well within PostgreSQL capacity.

**9.3 pgvector Dependency**

pgvector is a PostgreSQL extension, not a new service. It installs via: CREATE EXTENSION vector. No additional infrastructure required beyond the REQ-07 PostgreSQL instance.

**9.4 Storage Estimates**

|  |  |  |
|----|----|----|
| **Table** | **Row Size** | **Estimate @ 50 users, 365 days** |
| **memory_entries** | ~6.5 KB (1536-dim vector + text) | ~50K rows (~325 MB) |
| **audit_log** | ~1 KB per event | ~5M rows (~5 GB/year) |

Audit table will dominate storage. Partition by month and use retention cleanup to keep it bounded. 5 GB/year at 50 users is manageable on standard PostgreSQL. Re-evaluate at 500+ users.

**10. File Summary**

|  |  |  |  |
|----|----|----|----|
| **File** | **Status** | **Lines** | **Component** |
| agent/middlewares/memory.py | New | ~200 | MemoryMiddleware |
| agent/middlewares/retry.py | New | ~90 | RetryMiddleware |
| agent/middlewares/token_budget.py | New | ~120 | TokenBudgetMiddleware |
| agent/middlewares/hitl.py | New | ~160 | HumanInTheLoopMiddleware |
| agent/middlewares/audit.py | New | ~140 | AuditMiddleware |
| agent/memory_extractor.py | New | ~120 | Post-conversation extraction |
| db/migrations/014_memory.sql | New | ~30 | memory_entries schema |
| db/migrations/014_audit.sql | New | ~25 | audit_log schema |
| agent/agent.py | Modified | +15 | Chain integration |
| agent_server.py | Modified | +60 | HITL endpoint, config fields, SSE events |
| public/admin.html | Modified | +180 | Memory UI, budget UI, HITL config, Audit Log tab |
| public/mcp-agent.html | Modified | +90 | HITL modal dialog + SSE handlers |
| **Total new lines** |  | **~885** |  |
| **Total modified lines** |  | **~345** | pgvector only new infrastructure dep |

**11. Out of Scope**

- Cross-worker memory sharing — memory is scoped per worker per user; sharing across workers is a separate privacy and access control decision

- Real-time memory updates during a session — memories are extracted post-conversation only; no mid-session updates

- User-facing memory management UI — users cannot view or delete their own memories in this REQ; admin-only for now

- Memory search as an explicit tool — the agent cannot call a "search_my_memories" tool; injection is automatic and invisible

- HITL for sub-agents — only the lead agent's tool calls are checked against hitl_triggers; sub-agent tool calls are not paused

- Audit log query API — no public REST API for audit log; admin UI only in this REQ

- Distributed audit log (Kafka, etc.) — PostgreSQL is sufficient at current scale; streaming architecture deferred

**12. Dependencies on Other REQs**

|  |  |
|----|----|
| **REQ** | **Relationship** |
| **REQ-13 (Multi-Agent)** | Must merge first. REQ-14 adds to the middleware chain established in REQ-13. MemoryMiddleware slot was reserved at position 4. |
| **REQ-07 (PostgreSQL)** | Both memory_entries and audit_log tables require the PostgreSQL instance from REQ-07. pgvector extension must be enabled on that instance. |
| **REQ-12 (S3 / Multi-pod)** | hitl_pending_registry is in-memory. At multi-pod scale it needs Redis (same as REQ-13 task registry). Single-pod is sufficient for now. |
| **REQ-08 (Iceberg / S3)** | No dependency in this REQ. Audit log may eventually be mirrored to Iceberg for long-term analytics, but that is a future enhancement. |
