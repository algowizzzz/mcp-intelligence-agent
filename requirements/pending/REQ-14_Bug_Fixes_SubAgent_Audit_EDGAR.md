# REQ-14 — Bug Fixes: Sub-Agent Reliability, Audit Integrity, EDGAR Canadian Coverage
**Status:** Pending
**Version:** 1.0 (2026-04-11)
**Branch:** `feature/req-07-08a-postgres-s3` (add to same branch, no new branch needed)
**Discovered:** Live run — "Get me the full picture on Royal Bank of Canada" query, 2026-04-11
**Priority:** High (Issues 1 and 3 affect every multi-agent query; Issue 2 corrupts the audit log)

---

## Background

Four bugs were identified during a live multi-agent RBC research query. Three sub-agents were
spawned (RBC Financial Metrics, RBC SEC Filings, RBC Recent News). The financial metrics
sub-agent timed out, one sub-agent was silently dropped without user visibility, all tool
calls were recorded as `success: None` in the audit log, and EDGAR tools returned empty
results for a Canadian company without explanation.

---

## Bug 1 — Sub-agent timeout too short, not configurable per-worker

**Severity:** High
**File:** `agent_server.py` line 2168, `agent/sub_agent_tool.py` line 110

### Problem
`create_task_tool()` is called in `agent_server.py` without passing `timeout_seconds`,
so every sub-agent uses the hardcoded default of **120 seconds**:

```python
# agent_server.py line 2168 — timeout_seconds never passed
task_tool = create_task_tool(
    parent_tools=tools,
    parent_worker_ctx={**worker, 'user_id': payload['user_id']},
    llm=_ag.llm,
    create_agent_fn=create_agent_for_worker,
)
```

A sub-agent doing 6+ sequential tool calls (EDGAR lookup → metric fetch × 4 → news search →
company brief) easily exceeds 120s. The financial metrics sub-agent timed out for exactly
this reason.

The `workers.json` has no `subagent_timeout_seconds` key, so there is no way to tune this
per-worker without a code change.

### Fix
1. Add `subagent_timeout_seconds` to worker config (default 180)
2. Read it in `agent_server.py` and pass to `create_task_tool`
3. Document in CLAUDE.md worker configuration options table

```python
# agent_server.py — pass worker-configured timeout
task_tool = create_task_tool(
    parent_tools=tools,
    parent_worker_ctx={**worker, 'user_id': payload['user_id']},
    llm=_ag.llm,
    create_agent_fn=create_agent_for_worker,
    timeout_seconds=worker.get('subagent_timeout_seconds', 180),
)
```

---

## Bug 2 — Dropped sub-agent not surfaced to user

**Severity:** Medium
**File:** `agent/middlewares/subagent_limit.py`, `agent_server.py` SSE layer

### Problem
When the LLM spawns more `task()` calls than `max_concurrent_subagents` (default 3), excess
calls are **silently dropped**. The log shows:

```
SubagentLimitMiddleware: dropped 1 task() call(s) (limit=3).
```

This drop is logged server-side but **never surfaced to the user** via SSE. The user sees the
lead agent say "I've initiated three sub-tasks" — the 4th was silently discarded. The final
response says "I don't have financial metrics data" with no explanation that a task was dropped.

### Fix
1. Emit a `task_dropped` SSE event when a task is dropped, matching the existing `task_*` SSE protocol
2. Include in the event: `{tasks_dropped: N, reason: "concurrency_limit", limit: 3}`
3. The lead agent's injected note about dropped tasks (already present) should be formatted
   clearly enough for the LLM to include it in the response

---

## Bug 3 — Audit log records `success: None` for all tool calls

**Severity:** High
**File:** `agent/tools.py` — `_log_audit()` function

### Problem
Every tool call in the RBC run is stored in both the JSONL and PostgreSQL `audit_events`
table with `tool_result_ok = NULL` / `success: None`:

```
Tool: edgar_find_filing  | Success: None | Error: (empty)
Tool: edgar_get_metric   | Success: None | Error: (empty)
Tool: tavily_news_search | Success: None | Error: (empty)
```

The SAJHA server logs confirm these tools **executed successfully** — the audit write path
is not correctly serialising the result boolean. The `tool_result_ok` column is useless
for any success-rate reporting or alerting.

### Root cause to investigate
`_log_audit()` in `agent/tools.py` receives tool result from LangChain's tool execution
layer. The success flag determination may be looking at the wrong field in the result dict,
or the JSONL serialisation is coercing a truthy value to `None` before it reaches the DB
upsert.

### Fix
1. Trace the `success` value through `_log_audit()` → JSONL write → DB insert
2. Ensure `tool_result_ok` is set to `True` when no exception was raised, `False` on exception
3. Add a test to `test_req07_postgres.py`: verify `tool_result_ok` is `True` for a successful
   tool call logged via `_log_audit()`

---

## Bug 4 — EDGAR tools silently return empty results for Canadian companies

**Severity:** Medium
**File:** `sajhamcpserver/sajha/tools/impl/edgar_tavily_tools.py`,
          `sajhamcpserver/sajha/tools/impl/edgar_metric_tools.py`

### Problem
RBC (Royal Bank of Canada) is a foreign private issuer that files `40-F` and `6-K` with
the SEC — not `10-K` or `10-Q`. The EDGAR tools query for 10-K/10-Q filing types and return
empty results for Canadian banks (RBC, TD, BMO, BNS, CM) without any explanation in the
tool output. The sub-agent then spent multiple retries and eventually gave up, blaming
"server errors."

The `CLAUDE.md` documents this limitation for BMO but it is not enforced at the tool level.

### Fix
1. In `edgar_find_filing` and `edgar_company_brief`: detect when the company CIK maps to a
   foreign filer (check `40-F` or `20-F` existence) and return a structured error message:
   ```json
   {
     "error": "foreign_filer",
     "message": "RBC is a foreign private issuer — files 40-F/6-K, not 10-K/10-Q. Use ir_get_documents or tavily_research_search for Canadian banks.",
     "suggestion": "Try ir_get_documents with company='Royal Bank of Canada' or tavily_research_search."
   }
   ```
2. Do not silently return `{}` or raise an unrelated HTTP error
3. Add to agent system prompt: explicit note that Canadian banks (RBC, TD, BMO, BNS, CM, NA)
   require `ir_get_documents` or `tavily_research_search` — not EDGAR tools

---

## Acceptance Criteria

- [ ] Sub-agent timeout configurable per-worker via `subagent_timeout_seconds` in `workers.json`
- [ ] Default timeout increased from 120s → 180s
- [ ] `task_dropped` SSE event emitted when SubagentLimitMiddleware drops a task
- [ ] `audit_events.tool_result_ok` is `True`/`False` (never NULL) for tool calls where result is known
- [ ] EDGAR tools return `foreign_filer` structured error for Canadian companies instead of silent empty
- [ ] All fixes covered by tests

---

## Related
- CLAUDE.md: "BMO and other Canadian banks file 6-K (not 10-Q)" — expand to all 6 Big Six banks
- REQ-07: `audit_events` table — `tool_result_ok` boolean integrity depends on Bug 3 fix
- `max_concurrent_subagents` worker config: already supported, just needs timeout equivalent
