# REQ-17 — Holistic Regression Test Suite

**Purpose:** Pre-migration baseline + post-migration validation for the upstream SAJHA cutover (REQ-17). Ensures nothing breaks when our embedded SAJHA fork is replaced by upstream `ajsinha/sajhamcpserver` v5.0.0 + our tools-pack overlay.

**Status:** Pending — to be run before any migration code lands
**Date:** 2026-05-17
**Owner:** Saad Ahmed
**Source for coverage analysis:** `handover/04_uat_and_testing/*` + `tests/` + UAT plans in `archive/uat-plans/`
**Companion docs:** [REQ-17 technical reqs](REQ-17_SAJHA_Upstream_Sync.md) · [PM brief](REQ-17_PM_Brief.md) · [Jr dev stories](REQ-17_Jr_Dev_Stories.md)

---

## How to use this suite

### Phase 1 — Pre-migration baseline (run BEFORE any migration commit)
Run every test below. For each PASS, record evidence (curl output, screenshot, JSON snapshot) into `/tmp/baseline/`. This becomes our "known good" reference.

### Phase 2 — During migration
Re-run **smoke subset** (P0 tests only) after each story commit. Stops the bleed early.

### Phase 3 — Post-migration validation (gate before merge)
Run every test again. Compare to baseline. **Merge is gated on:** all P0 tests pass, no P1 regression vs baseline, P2 deltas documented.

### Phase 4 — Production smoke (48 hr after cutover)
Run a smoke subset every 6 hr against production for 48 hr. Any P0 fail rolls back.

### Priority codes
- **P0** — blocks merge. Core functionality. Must pass before and after.
- **P1** — blocks merge. Important but recoverable. Must pass after.
- **P2** — informational. Track regression but doesn't block.

### Test ID convention
`<SuiteLetter>-<NN>` e.g. `A-01` = Auth suite, test 01.

---

## Test environment setup

```
Hardware:    Mac/Linux dev machine, 16 GB RAM, ports 3002 + 8000 free
Browser:     Chrome / Edge with DevTools console available
SAJHA:       127.0.0.1:3002   (pre-migration: embedded fork; post-migration: upstream)
Agent:       127.0.0.1:8000   (FastAPI, unchanged scope)
Postgres:    OFF (DATABASE_URL unset, per LOCAL_DEV_SETUP.md)
LLM:         xAI Grok configured in .env (XAI_API_KEY required)
```

### Required env vars
- `XAI_API_KEY` (or ANTHROPIC_API_KEY) — for `H-*` and `I-*` tool/chat tests
- `TAVILY_API_KEY` — for `H-Tavily-*` and `H-EDGAR-*` tests (optional; mark blocked if absent)
- `SAJHA_API_KEY` — defaults to `sja_full_access_admin`
- `JWT_SECRET` — must be unchanged between pre/post baseline

### Test fixtures to seed
- Three workers: `w-market-risk`, `w-test-isolation-a`, `w-test-isolation-b`
- Three users (one per role):
  - `risk_agent` / `RiskAgent2025!` (super_admin → w-market-risk)
  - `admin` / set during baseline (admin → w-market-risk)
  - `test_user` / `TestUser123!` (user → w-market-risk)
- One sample file in each of: `w-market-risk/my_data/risk_agent/`, `w-market-risk/domain_data/`, `w-market-risk/templates/`
- One verified workflow: `w-market-risk/workflows/verified/sample_workflow.md`

---

## A. Authentication & RBAC

| ID | Title | Role | Steps | Expected | Automation | Priority |
|---|---|---|---|---|---|---|
| A-01 | Login — super_admin | super_admin | POST `/api/auth/login` with `risk_agent` / `RiskAgent2025!` | 200, JWT with `role: super_admin`, `worker_id: w-market-risk` | curl | **P0** |
| A-02 | Login — admin | admin | POST `/api/auth/login` with `admin` / password | 200, JWT with `role: admin` | curl | **P0** |
| A-03 | Login — user | user | POST `/api/auth/login` with `test_user` / `TestUser123!` | 200, JWT with `role: user` | curl | **P0** |
| A-04 | Login — wrong password | — | POST `/api/auth/login` with wrong password | 401 | curl | P1 |
| A-05 | Login — rate limit | — | 11 failed logins in 60s for same user_id | 429 on attempt 11 | curl loop | P2 |
| A-06 | `/api/auth/me` returns JWT payload | all | GET with valid JWT | 200, `user_id`, `role`, `worker_id`, `display_name` | curl | **P0** |
| A-07 | `/api/auth/me` rejects no JWT | — | GET without auth header | 401 | curl | **P0** |
| A-08 | `/api/auth/me` rejects expired JWT | — | GET with manually-expired JWT | 401 | curl | P1 |
| A-09 | Onboarding wizard — first login | new user | POST `/api/auth/onboarding` with display_name + password | 200, `onboarding_complete: true` | curl + UI | P1 |
| A-10 | Password change — change as self | user | POST `/api/auth/change-password` with old + new (≥10 chars) | 200 | curl | P1 |
| A-11 | Role gate: user cannot reach `/api/super/*` | user | GET `/api/super/workers` with user JWT | 403 | curl | **P0** |
| A-12 | Role gate: admin cannot reach `/api/super/*` | admin | GET `/api/super/users` with admin JWT | 403 | curl | **P0** |
| A-13 | Role gate: super_admin reaches `/api/super/*` | super_admin | GET `/api/super/workers` | 200 | curl | **P0** |
| A-14 | Role gate: admin reaches `/api/admin/worker` | admin | GET `/api/admin/worker` | 200 | curl | **P0** |
| A-15 | Role gate: user cannot reach `/api/admin/*` | user | GET `/api/admin/worker` | 403 | curl | **P0** |

---

## B. User Management

| ID | Title | Role | Steps | Expected | Automation | Priority |
|---|---|---|---|---|---|---|
| B-01 | List users | super_admin | GET `/api/super/users` | 200, JSON array | curl | **P0** |
| B-02 | Get one user | super_admin | GET `/api/super/users/{user_id}` | 200, single user dict | curl | P1 |
| B-03 | Create user | super_admin | POST `/api/super/users` body `{user_id, role, worker_id, display_name}` | 201, user created | curl | **P0** |
| B-04 | Update user | super_admin | PUT `/api/super/users/{id}` change display_name | 200, change persisted | curl | **P0** |
| B-05 | Reset user password (admin endpoint) | super_admin | POST `/api/super/users/{id}/reset-password` body `{new_password}` | 200, user can log in with new password | curl + login attempt | **P0** |
| B-06 | Delete user | super_admin | DELETE `/api/super/users/{id}` | 200/204, user can no longer log in | curl + login attempt | **P0** |
| B-07 | Cannot create duplicate user_id | super_admin | POST same user twice | 400/409 on second | curl | P1 |
| B-08 | Assign user to worker | super_admin | POST `/api/super/workers/{wid}/assign` body `{user_id}` | 200, user JWT reflects new worker_id | curl | **P0** |
| B-09 | Unassign user from worker | super_admin | DELETE `/api/super/workers/{wid}/assign/{user_id}` | 200, user no longer in worker's user list | curl | P1 |

---

## C. Worker Management

| ID | Title | Role | Steps | Expected | Automation | Priority |
|---|---|---|---|---|---|---|
| C-01 | List workers | super_admin | GET `/api/super/workers` | 200, JSON array (incl `w-market-risk`) | curl | **P0** |
| C-02 | Get one worker | super_admin | GET `/api/super/workers/{wid}` | 200, full worker config | curl | **P0** |
| C-03 | Create worker | super_admin | POST `/api/super/workers` body `{worker_id, name, system_prompt, enabled_tools}` | 201, new worker dir exists at `data/workers/{wid}/` | curl + filesystem | **P0** |
| C-04 | Update worker | super_admin | PUT `/api/super/workers/{wid}` change name | 200, change persisted | curl | **P0** |
| C-05 | Delete worker (no users) | super_admin | DELETE `/api/super/workers/{empty-wid}` | 200/204 | curl | P1 |
| C-06 | Delete worker (has users) | super_admin | DELETE on worker with assigned users | 422 with explanatory error | curl | P1 |
| C-07 | Admin gets own worker | admin | GET `/api/admin/worker` | 200, only own worker | curl | **P0** |
| C-08 | Admin updates system prompt | admin | PUT `/api/admin/worker/prompt` body `{system_prompt}` | 200, change reflected in `/api/admin/worker` | curl | **P0** |
| C-09 | Admin enables/disables tools | admin | PUT `/api/admin/worker/tools` body `{enabled_tools: [...]}` | 200, change reflected; next agent run respects allowlist | curl + agent test | **P0** |
| C-10 | Worker connector scope | super_admin | PUT `/api/super/workers/{wid}/connector-scope/{type}` | 200, scope persisted | curl | P1 |
| C-11 | Worker config: agent_mode toggle | super_admin | PUT worker with `agent_mode: "multi"` | 200, multi-agent enabled | curl | P1 |
| C-12 | Worker config: max_concurrent_subagents | super_admin | PUT worker with `max_concurrent_subagents: 4` | 200, value persisted | curl | P2 |

---

## D. Prompt Management

| ID | Title | Role | Steps | Expected | Automation | Priority |
|---|---|---|---|---|---|---|
| D-01 | Read system prompt | admin | GET `/api/admin/worker` | Returns `system_prompt` field | curl | **P0** |
| D-02 | Update system prompt | admin | PUT `/api/admin/worker/prompt` | 200, takes effect on next chat run | curl + chat | **P0** |
| D-03 | Empty system prompt rejected | admin | PUT with empty prompt | 400 OR accepted (document either way for baseline) | curl | P2 |
| D-04 | Worker-specific prompt isolation | super_admin | Worker A prompt does not leak into Worker B chat | Each worker's chat reflects only its prompt | UI / curl + chat | **P0** |

---

## E. Connector Management

| ID | Title | Role | Steps | Expected | Automation | Priority |
|---|---|---|---|---|---|---|
| E-01 | List connectors | super_admin | GET `/api/super/connectors` | 200, credentials redacted | curl | **P0** |
| E-02 | Add connector — Microsoft 365 | super_admin | POST `/api/super/connectors/microsoft_azure` body with creds | 201 (skip if no real creds — note blocked) | curl | P2 |
| E-03 | Test connector format validation | super_admin | POST `/api/super/connectors/{type}/test` | 200 with `{ok: true}` or 4xx with error | curl | P1 |
| E-04 | Update connector | super_admin | PUT `/api/super/connectors/{type}` | 200 | curl | P1 |
| E-05 | Delete connector | super_admin | DELETE `/api/super/connectors/{type}` | 200 | curl | P1 |
| E-06 | Worker connector scope read | admin | GET `/api/super/workers/{wid}/connector-scope/{type}` | 200, scope JSON | curl | P2 |
| E-07 | Connector-backed tool blocked when scope = none | user | Chat invoking a connector tool, scope set to none | Tool refuses with auth error | UI + chat | P1 |

---

## F. LLM Configuration

| ID | Title | Role | Steps | Expected | Automation | Priority |
|---|---|---|---|---|---|---|
| F-01 | Get LLM config | super_admin | GET `/api/super/llm-config` | 200, current provider + model | curl | **P0** |
| F-02 | Set LLM config — xAI Grok | super_admin | PUT `/api/super/llm-config` body `{provider: "xai", model: "grok-4-1-fast-non-reasoning"}` | 200, persisted | curl | **P0** |
| F-03 | Hot-swap LLM provider takes effect | super_admin | Change provider then issue chat | New provider used (verify via response style or logs) | curl + chat | P1 |
| F-04 | Invalid provider rejected | super_admin | PUT with provider `"invalid"` | 400 | curl | P2 |

---

## G. File Management

For sections: `uploads` (== `my_data` user-scoped), `domain_data`, `common`, `verified` (workflows), `my_workflows`, `templates`.

| ID | Title | Role | Steps | Expected | Automation | Priority |
|---|---|---|---|---|---|---|
| G-01 | Tree — my_data (per user) | user | GET `/api/fs/my_data/tree` | 200, root path matches `data/workers/{wid}/my_data/{uid}/` | curl | **P0** |
| G-02 | Tree — domain_data (worker-scoped) | user | GET `/api/fs/domain_data/tree` | 200, root matches worker domain_data | curl | **P0** |
| G-03 | Tree — common (shared) | user | GET `/api/fs/common/tree` | 200, common shared dir | curl | P1 |
| G-04 | Tree — verified workflows | user | GET `/api/fs/verified/tree` | 200 | curl | **P0** |
| G-05 | Upload to my_data | user | POST `/api/fs/my_data/upload` with one file | 201, file appears in tree | curl | **P0** |
| G-06 | Upload to domain_data | admin | POST `/api/fs/domain_data/upload` | 201 | curl | **P0** |
| G-07 | User cannot upload to domain_data | user | POST `/api/fs/domain_data/upload` as user | 403 | curl | **P0** |
| G-08 | Read file | user | GET `/api/fs/my_data/file?path=…` | 200, file contents | curl | **P0** |
| G-09 | Storage quota | user | GET `/api/fs/quota` | 200, `{used_bytes, limit_bytes, used_pct}` | curl | P1 |
| G-10 | Copy file | admin | POST `/api/fs/my_data/copy` body `{src, dst}` | 200, dst file exists | curl | P1 |
| G-11 | Rename file | admin | POST `/api/fs/my_data/rename` body `{old, new}` | 200, new path resolves, old does not | curl | P1 |
| G-12 | Batch-delete | admin | POST `/api/fs/my_data/batch-delete` body `{paths: [...]}` | 200, all paths gone | curl | P1 |
| G-13 | Path traversal blocked | any | GET `/api/fs/my_data/file?path=../../config/users.json` | 400 or 403 | curl | **P0** |
| G-14 | URL-encoded traversal blocked | any | path = `..%2F..%2Fconfig%2Fusers.json` | 400 or 403 | curl | **P0** |
| G-15 | Oversize upload rejected | admin | Upload 51 MB file | 413 | curl | P1 |
| G-16 | Empty upload accepted | admin | Upload 0-byte file | 200 | curl | P2 |
| G-17 | **Multi-worker isolation — read** | user A | User in worker A attempts GET `/api/fs/my_data/file?path=…` on worker B path | 403/404; cannot read | curl | **P0 GATE** |
| G-18 | **Multi-worker isolation — list** | user A | User in worker A: tree never shows worker B's data | Tree root is A's only | curl | **P0 GATE** |
| G-19 | **Per-user isolation in my_data** | user X | User X cannot read user Y's `my_data` files in the same worker | 403/404 | curl | **P0 GATE** |
| G-20 | Reindex BM25 index | admin | POST `/api/fs/{section}/reindex` | 200, tree retrieved fresh | curl | P2 |

---

## H. Tools

### H.1 Tool discovery

| ID | Title | Steps | Expected | Priority |
|---|---|---|---|---|
| H-DISC-01 | `tools/list` returns all expected tools | Call `tools/list` on SAJHA | 31 custom tools listed (post-migration: + plus whatever upstream contributes; for baseline: 31) | **P0** |
| H-DISC-02 | Agent discovers SAJHA tools at boot | Restart agent, check `Discovered N additional SAJHA tools` log | N == expected count | **P0** |
| H-DISC-03 | Worker's enabled_tools allowlist enforced | Configure worker with `enabled_tools: ["bm25_search"]`, ask agent to use a non-allowed tool | Agent refuses or never sees it | **P0** |
| H-DISC-04 | Tool config JSON validates | Each `tools-pack/configs/*.json` parses without error at server startup | No load failures in server log | **P0** |

### H.2 Per-tool smoke (one happy-path call per tool)

Each test = call the tool with a known-safe input, expect a non-error response. Mark "creds-blocked" if external secrets needed and not available.

| ID | Tool | Sample input | Expected output | Creds needed | Priority |
|---|---|---|---|---|---|
| H-T-01 | `bm25_search` | `{query: "test", section: "domain_data"}` | result array | none | **P0** |
| H-T-02 | `list_uploaded_files` | `{}` | files JSON | none | **P0** |
| H-T-03 | `file_read` | path of seeded test file | content string | none | **P0** |
| H-T-04 | `pdf_read` | path of seeded PDF | text content | none | **P0** |
| H-T-05 | `parquet_read` | path of seeded parquet | rows | none | P1 |
| H-T-06 | `search_files` | query | matches | none | P1 |
| H-T-07 | `fill_template` | template name + vars | rendered output | none | P1 |
| H-T-08 | `md_to_docx` | sample MD | docx file path | none | P1 |
| H-T-09 | `data_export` | source + format | success | none | P1 |
| H-T-10 | `data_transform` | df ops | dataframe | none | P1 |
| H-T-11 | `generate_chart` | sample data | plotly HTML path + chart SSE | none | **P0** |
| H-T-12 | `python_execute` | `"print('hello')"` | stdout = "hello" | none | **P0** |
| H-T-13 | `python_run_script` | seeded `.py` file path | execution output | none | P1 |
| H-T-14 | `duckdb_list_tables` | — | list of tables | none | **P0** |
| H-T-15 | `duckdb_query` | `"SELECT 1"` | row [[1]] | none | **P0** |
| H-T-16 | `duckdb_describe_table` | sample table | columns | none | P1 |
| H-T-17 | `duckdb_aggregate` | sample table + group | aggregated rows | none | P1 |
| H-T-18 | `duckdb_get_stats` | table | stats | none | P2 |
| H-T-19 | `duckdb_list_files` | — | files in data layer | none | P1 |
| H-T-20 | `duckdb_sql` | safe sql | results | none | P1 |
| H-T-21 | `duckdb_refresh_views` | — | success | none | P2 |
| H-T-22 | `sqlselect_list_sources` | — | source list | none | P1 |
| H-T-23 | `sqlselect_execute_query` | safe select | result | none | P1 |
| H-T-24 | `sqlselect_describe_source` | source name | schema | none | P1 |
| H-T-25 | `sqlselect_get_schema` | source | schema | none | P2 |
| H-T-26 | `sqlselect_sample_data` | source | sample rows | none | P2 |
| H-T-27 | `sqlselect_count_rows` | source | row count | none | P2 |
| H-T-28 | `msdoc_read_word` | seeded `.docx` | text | none | P1 |
| H-T-29 | `msdoc_read_excel` | seeded `.xlsx` | rows | none | P1 |
| H-T-30 | `msdoc_search_word` | query | matches | none | P2 |
| H-T-31 | `msdoc_search_excel` | query | matches | none | P2 |
| H-T-32 | `msdoc_get_word_metadata` | docx | metadata | none | P2 |
| H-T-33 | `msdoc_get_excel_metadata` | xlsx | metadata | none | P2 |
| H-T-34 | `msdoc_extract_text` | doc | text | none | P2 |
| H-T-35 | `msdoc_list_files` | — | files | none | P2 |
| H-T-36 | `msdoc_read_excel_sheet` | xlsx + sheet | rows | none | P2 |
| H-T-37 | `msdoc_get_excel_sheets` | xlsx | sheet names | none | P2 |
| H-T-38 | `msdoc_get_excel_stats` | xlsx | stats | none | P2 |
| H-T-39 | `iris_search_counterparties` | search term | list | none | P1 |
| H-T-40 | `iris_list_dates` | — | dates | none | P1 |
| H-T-41 | `iris_counterparty_dashboard` | counterparty | dashboard data | none | P1 |
| H-T-42 | `iris_exposure_trend` | counterparty + dates | trend | none | P1 |
| H-T-43 | `iris_rating_screen` | rating | counterparties | none | P2 |
| H-T-44 | `iris_limit_lookup` | counterparty | limits | none | P1 |
| H-T-45 | `iris_limit_breach_check` | counterparty | breaches | none | P1 |
| H-T-46 | `iris_multi_counterparty_comparison` | cps[] | comparison | none | P2 |
| H-T-47 | `iris_portfolio_breach_scan` | — | breaches | none | P2 |
| H-T-48 | `get_counterparty_exposure` | counterparty | exposure | none | **P0** |
| H-T-49 | `get_trade_inventory` | counterparty | trades | none | **P0** |
| H-T-50 | `get_credit_limits` | counterparty | limits | none | **P0** |
| H-T-51 | `get_historical_exposure` | counterparty + date | snapshot | none | P1 |
| H-T-52 | `get_var_contribution` | counterparty | VaR | none | P1 |
| H-T-53 | `tavily_web_search` | query | results | **TAVILY_API_KEY** | P1 |
| H-T-54 | `tavily_news_search` | query | results | TAVILY | P2 |
| H-T-55 | `tavily_research_search` | query | results | TAVILY | P2 |
| H-T-56 | `tavily_domain_search` | domain + query | results | TAVILY | P2 |
| H-T-57 | `tavily_yahoo_get_quote` | symbol | quote | TAVILY | P1 |
| H-T-58 | `tavily_yahoo_get_history` | symbol | history | TAVILY | P2 |
| H-T-59 | `tavily_yahoo_search_symbols` | query | symbols | TAVILY | P2 |
| H-T-60 | `edgar_find_filing` | ticker | filings | TAVILY | P1 |
| H-T-61 | `edgar_extract_section` | filing + section | text | TAVILY | P1 |
| H-T-62 | `edgar_company_brief` | ticker | brief | TAVILY | P1 |
| H-T-63 | `edgar_earnings_brief` | ticker | brief | TAVILY | P1 |
| H-T-64 | `edgar_risk_summary` | ticker | risks | TAVILY | P2 |
| H-T-65 | `edgar_segment_analysis` | ticker | segments | TAVILY | P2 |
| H-T-66 | `edgar_get_metric` | ticker + metric | value | TAVILY | P2 |
| H-T-67 | `edgar_get_statements` | ticker | statements | TAVILY | P2 |
| H-T-68 | `edgar_calculate_ratios` | ticker | ratios | TAVILY | P2 |
| H-T-69 | `edgar_peer_comparison` | ticker[] | comparison | TAVILY | P2 |
| H-T-70 | `ir_*` (9 IR tools) | varies | results | TAVILY | P2 |
| H-T-71 | Connector tools — `outlook_*` (6) | — | API error or success | M365 creds | P2 (blocked if no creds) |
| H-T-72 | Connector tools — `teams_*` (6) | — | success/error | M365 creds | P2 (blocked if no creds) |
| H-T-73 | Connector tools — `jira_*` (7) | — | success/error | Atlassian creds | P2 (blocked if no creds) |
| H-T-74 | Connector tools — `confluence_*` (5) | — | success/error | Atlassian creds | P2 (blocked if no creds) |
| H-T-75 | Connector tools — `sharepoint_*` (6) | — | success/error | M365 creds | P2 (blocked if no creds) |
| H-T-76 | Connector tools — `powerbi_*` (6) | — | success/error | M365 creds | P2 (blocked if no creds) |
| H-T-77 | `workflow_list` | — | workflows array | none | **P0** |
| H-T-78 | `workflow_get` | filename | content | none | **P0** |
| H-T-79 | `list_versions` | — | version list | none | P2 |
| H-T-80 | `customer_olap_pivot` | source + dims | pivot | none | P2 |
| H-T-81 | `olap_pivot_table` | source + dims | pivot | none | P2 |
| H-T-82 | `olap_time_series` | source + time col | ts | none | P2 |
| H-T-83 | `document_search` (BM25 alias) | query | matches | none | **P0** |
| H-T-84 | `saad_fib` (demo tool) | n=10 | first 10 fibs | none | P2 |

### H.3 Tool output contract

| ID | Title | Expected | Priority |
|---|---|---|---|
| H-CTR-01 | Tool result is JSON-serializable dict | All H-T-* responses parse as JSON dict | **P0** |
| H-CTR-02 | Tool result respects 12,000 char cap (or per-tool override) | No tool result > limit unless documented exception | P1 |
| H-CTR-03 | HTML-producing tools strip `html` field, set `_chart_ready: true` | `generate_chart` + `python_execute` SSE shape | **P0** |
| H-CTR-04 | Error tool returns `{error: "..."}` not raw exception | Force a tool failure | **P0** |

---

## I. Agent / Chat Flow

| ID | Title | Role | Steps | Expected | Automation | Priority |
|---|---|---|---|---|---|---|
| I-01 | Send chat → SSE stream → response | user | POST `/api/agent/run` with `{query, worker_id, user_id}` and `Accept: text/event-stream` | Stream yields `session`, multiple `text`, final `usage`; ends cleanly | curl + SSE parse | **P0** |
| I-02 | Tool invocation surfaces `tool_start` + `tool_end` | user | Ask the agent something that requires a tool call (e.g. "fibonacci first 10") | SSE includes `tool_start` and `tool_end` events with correct tool name | curl | **P0** |
| I-03 | Canvas event for chart tool | user | "make a chart of the first 10 fibonacci numbers" | SSE includes `canvas` with `chart_url` | curl + browser | **P0** |
| I-04 | Thread persistence | user | Send msg, get `thread_id`, send follow-up with same `thread_id` | Second response references first | curl | **P0** |
| I-05 | Thread list | user | GET `/api/agent/threads?worker_id=...` | 200, includes recent thread | curl | **P0** |
| I-06 | Thread messages | user | GET `/api/agent/threads/{tid}/messages` | 200, full conversation | curl | P1 |
| I-07 | Context summarisation triggers at 180k tokens | user | Build a conversation past 180k tokens, send one more | SSE emits `summary_occurred` event; `tokens_after` < `tokens_before` | curl loop | P1 |
| I-08 | Loop detection at 3 repeats (warning) | user | Send a query that intentionally loops the agent | Agent emits warning text after 3 identical tool calls | curl + crafted prompt | P2 |
| I-09 | Loop detection at 5 repeats (hard stop) | user | Continue I-08 | Agent stops; error event | curl | P1 |
| I-10 | Token budget warning at 80% | user | Set worker `max_tokens_per_query` low; exceed 80% | SSE `context_gauge` shows ≥0.8 | curl | P2 |
| I-11 | Budget exceeded event | user | Continue I-10 until budget hits | SSE `budget_exceeded` event | curl | P2 |
| I-12 | HITL approval gate triggers | user | Configure worker with `hitl_triggers: ["delete_*"]`, request a delete | SSE `hitl` event with `hitl_id`, agent pauses | curl + browser | P1 |
| I-13 | HITL approval flow | user | Submit POST `/api/chat/hitl-response` with `{hitl_id, approved: true}` | Agent resumes; tool runs | curl | P1 |
| I-14 | HITL rejection flow | user | POST with `approved: false` | Agent does not run the tool; emits rejection text | curl | P1 |
| I-15 | Agent SSE handles tool error gracefully | user | Force a tool to error | SSE includes `tool_end` with error result, agent continues or stops with message | curl | **P0** |

---

## J. Workflows

| ID | Title | Role | Steps | Expected | Automation | Priority |
|---|---|---|---|---|---|---|
| J-01 | List workflows | admin | GET `/api/workflows` | 200, array of `{filename, …}` | curl | **P0** |
| J-02 | Read workflow content | admin | GET `/api/workflows/{file}` | 200, MD content | curl | **P0** |
| J-03 | Create workflow | admin | POST `/api/workflows` with `{filename, content}` | 201; file present in verified/my_workflows | curl | **P0** |
| J-04 | Delete workflow | admin | DELETE `/api/workflows/{file}` | 200; file gone | curl | P1 |
| J-05 | Mark workflow used | user | PATCH `/api/workflows/{file}/used` | 200; usage counter incremented | curl | P2 |
| J-06 | Execute single-agent workflow | user | Send a chat that picks a workflow | Agent runs workflow steps; SSE events normal | curl + UI | **P0** |
| J-07 | Execute multi-agent workflow (`agent_mode: multi`) | user | Seed a workflow with multi frontmatter; run it | SSE includes `task_started`, `task_running`, `task_completed` per sub-agent | curl | P1 |
| J-08 | Sub-agent result placeholder `{id.result_summary}` resolves | user | Workflow with sub-agent A referenced by sub-agent B | B receives A's truncated result text | curl | P1 |

---

## K. Frontend UI (Browser)

Run from a real browser, login → exercise. Use Chrome DevTools to assert.

| ID | Title | Role | Steps | Expected | Priority |
|---|---|---|---|---|---|
| K-01 | Login page renders | — | Open `/login.html` | Form visible | **P0** |
| K-02 | Login → redirect to chat | user | Submit valid credentials | Lands on `/mcp-agent.html` | **P0** |
| K-03 | Chat: type + send | user | Type "hello", click send | Message appears, streaming response begins | **P0** |
| K-04 | Chat: tool card renders | user | Ask for a tool-requiring task | Tool card with input/output visible | **P0** |
| K-05 | Chat: canvas opens for chart | user | Ask for a chart | Canvas pane opens, iframe loads | **P0** |
| K-06 | Chat: file attachment | user | Upload file via paperclip | Attachment appears below input, file gets uploaded | **P0** |
| K-07 | Chat: new thread | user | Click "+ New" | Fresh thread, sidebar updated | **P0** |
| K-08 | Chat: switch thread | user | Click an older thread | Messages reload | P1 |
| K-09 | File sidebar — domain data | user | Expand DOMAIN DATA | Files render | **P0** |
| K-10 | File sidebar — my data | user | Expand MY DATA | Files render | **P0** |
| K-11 | File sidebar — search | user | Type in search box | Filters list | P1 |
| K-12 | Admin panel — workers tab | super_admin | `/admin.html` → Workers | Workers grid, can click into one | **P0** |
| K-13 | Admin panel — users tab | super_admin | Users tab | List with CRUD buttons | **P0** |
| K-14 | Admin panel — audit tab | super_admin | Audit tab | Log entries with filters | P1 |
| K-15 | Admin panel — connectors tab | super_admin | Connectors tab | List with add/test | P1 |
| K-16 | Admin panel — LLM config | super_admin | LLM tab | Current provider/model; can change | P1 |
| K-17 | Admin panel — file browser | admin | Worker file browser | Tree across all sections | **P0** |
| K-18 | Onboarding wizard — first login | new user | Login with `onboarding_complete: false` | 3-step form: display_name, password, done | P1 |
| K-19 | Sign-out | user | Click sign out | Redirect to login, JWT cleared | **P0** |
| K-20 | Worker dropdown (super_admin only) | super_admin | Switch worker in chat dropdown | Files panel + chat scope to new worker | **P0** |

---

## L. Audit & Observability

| ID | Title | Steps | Expected | Priority |
|---|---|---|---|---|
| L-01 | Audit log captures tool call | Make any tool call | New row in `data/audit/tool_calls.jsonl` with `user_id`, `worker_id`, `tool_name`, `status`, `duration_ms` | **P0** |
| L-02 | Sensitive args redacted | Call a tool with arg `{api_key: "secret"}` | Audit entry shows `[REDACTED]` for that field | **P0** |
| L-03 | Audit query — by user | GET `/api/super/audit?user_id=test_user` | Only that user's entries | P1 |
| L-04 | Audit query — by worker | GET `/api/super/audit?worker_id=w-market-risk` | Filtered correctly | P1 |
| L-05 | Audit pagination | GET with `limit=10&offset=0` then `offset=10` | Different pages | P2 |
| L-06 | Health endpoint | GET `/health` (both servers) | Both return `{status: "ok"}` (or equivalent) | **P0** |

---

## M. Edge Cases

| ID | Title | Steps | Expected | Priority |
|---|---|---|---|---|
| M-01 | Malformed JSON body | POST `/api/agent/run` with broken JSON | 400, no crash | **P0** |
| M-02 | Missing required field | POST `/api/agent/run` without `query` | 422 | **P0** |
| M-03 | Very long single message | Submit a 100k-char message | Either accepted (truncated/summarised) or 413 | P1 |
| M-04 | Concurrent chat sessions (same user) | Open 2 browser tabs; send simultaneously | Both stream independently | P1 |
| M-05 | LLM provider down | Disable LLM key, send chat | SSE `error` event, no crash | P1 |
| M-06 | SAJHA down | Stop SAJHA, attempt tool call | Agent surfaces error gracefully | P1 |
| M-07 | Tool timeout | Trigger a tool that exceeds its timeout | Tool returns `timeout` status; agent continues | P1 |
| M-08 | Unicode in user input | Submit emoji + non-Latin text | Handled correctly through whole stack | P2 |
| M-09 | Path traversal in upload filename | Upload file named `../../etc/passwd` | Rejected | **P0** |
| M-10 | XSS in workflow content | Workflow with `<script>` tags | Rendered safely (escaped) in UI preview | P1 |

---

## Pre-migration baseline capture script (`scripts/capture_baseline.sh`)

A short script (to be written before Phase 1) that runs ~30 P0 curl tests and dumps results to `/tmp/baseline/<test_id>.json`. Used as the "known good" for post-migration diffing.

Includes:
- `/api/auth/me` snapshots per role
- `/api/super/workers` JSON
- `/api/super/users` JSON
- `/api/mcp/tools` JSON (tool catalog)
- `/api/fs/{section}/tree` per role
- Selected tool invocations (`bm25_search`, `python_execute`, `iris_*`, `duckdb_query`, `workflow_list`)
- A 1-message chat run, capturing the SSE event stream

---

## Post-migration validation script (`scripts/validate_migration.sh`)

Same set as baseline, plus:
- Re-run every test in §A–§M
- Diff captured baseline vs new responses for every P0 test
- **Worker isolation hardened tests** (G-17, G-18, G-19): must pass under the new architecture where worker-context lives in the agent layer + tools-pack helper, not in SAJHA.
- **Tool registration check** (H-DISC-01): verify all 31 custom tools appear in `tools/list` after the plugin pack loads.
- **Upstream-untouched check**: `cd sajhamcpserver-upstream && git status` must show no modifications.

---

## Pass / Fail gate criteria

| Gate | Requirement |
|---|---|
| **Phase 1 baseline** | All P0 tests pass on the current (pre-migration) stack. Any failing P0 is fixed BEFORE we start migration. Failing P1/P2 documented as pre-existing. |
| **Phase 2 smoke (per story commit)** | All P0 tests for the touched area pass. CI green. |
| **Phase 3 final gate (merge)** | Every P0 test passes on the post-migration stack. All P1 tests either pass or have a documented and PM-approved waiver. P2 regressions logged but not blocking. **Worker isolation tests (G-17/18/19) are HARD gate** — no waivers. |
| **Phase 4 production smoke (48h)** | Critical-path tests (A-01..03, A-06, A-11..15, B-01, C-01..04, G-01..06, H-T-01, H-T-11, H-T-12, I-01..03, K-02..04) run every 6 hours. Any P0 fail rolls back. |

---

## Test fixtures (appendix)

### Required fixture files (commit to a separate `tests/fixtures/` if not already there)

| Fixture | Path | Used by |
|---|---|---|
| Sample workflow | `data/workers/w-market-risk/workflows/verified/sample_workflow.md` | J-01..06, K-09..11 |
| Sample PDF | `data/workers/w-market-risk/domain_data/sample.pdf` | H-T-04 |
| Sample parquet | `data/workers/w-market-risk/domain_data/sample.parquet` | H-T-05 |
| Sample CSV | `data/workers/w-market-risk/domain_data/sample.csv` | H-T-14..21 |
| Sample DOCX | `data/workers/w-market-risk/my_data/risk_agent/sample.docx` | H-T-28..38 |
| Sample XLSX | `data/workers/w-market-risk/my_data/risk_agent/sample.xlsx` | H-T-29.. |
| Template | `data/workers/w-market-risk/templates/sample_template.md` | H-T-07 |

### Required test workers

| worker_id | Name | Purpose |
|---|---|---|
| `w-market-risk` | Market Risk Worker | primary functional + workflow tests |
| `w-test-iso-a` | Isolation Test A | G-17, G-18 — read this user's data |
| `w-test-iso-b` | Isolation Test B | G-17, G-18 — the worker this user CANNOT see |

### Required test users

| user_id | password | role | worker_id | Purpose |
|---|---|---|---|---|
| `risk_agent` | `RiskAgent2025!` | super_admin | w-market-risk | A-01, all `/super/*` tests |
| `admin` | (set during baseline) | admin | w-market-risk | A-02, admin scope tests |
| `test_user` | `TestUser123!` | user | w-market-risk | A-03, user scope tests |
| `iso_user_a` | (set) | user | w-test-iso-a | G-17 (perspective: tries to read B) |
| `iso_user_b` | (set) | user | w-test-iso-b | G-19 (other side of isolation) |

---

## Out-of-scope

- Performance / load testing (separate REQ if needed).
- Penetration testing beyond path traversal + XSS already listed.
- Mobile / responsive UI validation.
- Localization / i18n.
- Verifying the 500 upstream tools — per PM decision, ignored for now.

---

## Tracking

Run results captured in `/tmp/baseline/` (pre) and `/tmp/post-migration/` (post). For each test, log:
- ID
- Date / time
- Pass / Fail / Skip / Blocked
- Evidence pointer (file or screenshot)
- Notes

Tally at end of each phase. Anything not green that should be green = stops the merge.
