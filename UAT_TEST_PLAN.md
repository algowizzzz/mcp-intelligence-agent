# UAT Test Plan — RiskGPT Multi-Worker Platform

**Version:** 1.0
**Date:** 2026-04-03
**Scope:** End-to-end from login through chat, file ops, tools, workflows, and admin functions across all three user roles.
**Environment:** Local — agent server `http://localhost:8000`, SAJHA MCP `http://localhost:3002`
**Frontend pages:** `login.html`, `mcp-agent.html`, `admin.html`

---

## Test Data Setup (Prerequisites)

| Item | Value |
|------|-------|
| super_admin creds | `risk_agent` / `RiskAgent2025!` |
| admin creds | `admin` / `Admin2025!` |
| user creds | `test_user` / `TestUser2025!` |
| MR worker | `w-market-risk` |
| CCR worker | `w-e74b5836` |
| Test files | 1× `.md`, 1× `.csv`, 1× `.pdf`, 1× `.xlsx` (prepared before run) |

---

## Module 1 — Authentication & Session

| ID | Scenario | Role | Steps | Expected |
|----|----------|------|-------|----------|
| A-01 | Successful login | super_admin | Open `login.html` → enter creds → submit | Redirect to `mcp-agent.html`, JWT in sessionStorage, user badge shows name |
| A-02 | Successful login | admin | Same with admin creds | Redirect, admin panel link visible in header |
| A-03 | Successful login | user | Same with user creds | Redirect, no admin panel link |
| A-04 | Wrong password | any | Enter bad password | Error message, no redirect, attempt count incremented |
| A-05 | Rate limiting | super_admin | Submit wrong password 11× rapidly | 11th attempt returns HTTP 429, UI shows lockout message |
| A-06 | Expired token | any | Manually set expired JWT in sessionStorage, reload page | Redirect back to login |
| A-07 | `/api/auth/me` | super_admin | POST login → GET `/api/auth/me` with token | Returns user_id, role, worker_id |
| A-08 | Logout | any | Click logout button | sessionStorage cleared, redirect to login |
| A-09 | Change password | admin | Login → POST `/api/auth/change-password` with old+new → re-login with new | Success; old password no longer works |
| A-10 | Onboarding flow | new user | POST `/api/auth/onboarding` with first-time token | 200, sets initial password, token invalidated after use |

---

## Module 2 — Worker Management (super_admin only)

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| W-01 | List workers | `GET /api/super/workers` | 200; returns both `w-market-risk` and `w-e74b5836`; each has `data_path`, `common_data_path`, `enabled_tools` |
| W-02 | Create worker | POST with `name`, `description`, `system_prompt`, `enabled_tools: ["*"]` | 201; new worker_id returned; folder created at `data/workers/{id}` with subdirs: `domain_data/`, `workflows/verified/`, `workflows/my/`, `templates/`, `my_data/` |
| W-03 | Worker path isolation | Create two workers; upload different files to each | Each worker only sees its own files via `/api/super/workers/{id}/files/` |
| W-04 | Update worker prompt | `PUT /api/super/workers/{id}` with new `system_prompt` | 200; next agent run uses new prompt |
| W-05 | Update tool allowlist | PUT worker with `enabled_tools: ["iris_search_counterparties","workflow_list"]` | `GET /api/workers/{id}/tools` returns only those 2 tools |
| W-06 | Clone worker | `POST /api/super/workers` with `clone_from: "w-market-risk"` | New worker created; `domain_data/` and `workflows/verified/` copied from source; `my_data/` empty |
| W-07 | Assign user to worker | `POST /api/super/workers/{id}/assign` with `user_id` | 200; user appears in worker's `assigned_users`; `users.json` updated with `worker_id` |
| W-08 | Unassign user | `DELETE /api/super/workers/{id}/assign/{user_id}` | 200; user removed from both files |
| W-09 | Delete worker | `DELETE /api/super/workers/{id}` | 200; worker folder removed from disk; worker absent from list |
| W-10 | Admin cannot manage workers | Admin calls `POST /api/super/workers` | 403 |
| W-11 | User cannot manage workers | User calls `GET /api/super/workers` | 403 |

---

## Module 3 — User Management (super_admin only)

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| U-01 | List users | `GET /api/super/users` | 200; returns all users with role, worker_id |
| U-02 | Create admin user | POST with `role: admin`, `worker_id: w-market-risk` | 201; user appears in `users.json`; can login |
| U-03 | Create regular user | POST with `role: user` | 201; assigned to a worker |
| U-04 | Create super_admin | POST with `role: super_admin` | 201 |
| U-05 | Update user role | PUT user, change role from `user` to `admin` | Role updated in `users.json` and token reflects new role on next login |
| U-06 | Reset password | `POST /api/super/users/{id}/reset-password` | Generates onboarding token; user must set new password via onboarding flow |
| U-07 | Delete user | `DELETE /api/super/users/{id}` | 200; removed from `users.json`; removed from any worker's `assigned_users` |
| U-08 | Duplicate user_id rejected | POST with existing `user_id` | 409 conflict |
| U-09 | assigned_users sync | Assign user via worker endpoint vs user endpoint | Both `workers.json` and `users.json` remain in sync |

---

## Module 4 — File Operations (by Role)

### 4A — Super Admin: Full CRUD on any worker

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| F-01 | Browse domain_data tree | `GET /api/super/workers/w-market-risk/files/domain_data` | 200; tree with iris/, osfi/ subdirs |
| F-02 | Upload .csv to domain_data | POST multipart to `.../files/domain_data/upload` | 201; file appears in tree |
| F-03 | Upload .md to verified workflows | POST to `.../files/verified/upload` | 201 |
| F-04 | Upload duplicate → 409 | Upload same filename twice | 409; UI shows "Replace" button |
| F-05 | Upload duplicate → overwrite | Click Replace | 200; file replaced |
| F-06 | Create folder | POST `.../files/domain_data/folder` with `{path: "test_folder"}` | 200; folder visible in tree |
| F-07 | Create nested folder | POST with `path: "test_folder/sub_folder"` | 200; nested structure in tree |
| F-08 | Create new .md file (blank) | PATCH `.../files/verified/file` with `{path: "new_wf.md", content: ""}` | 200; file appears in tree |
| F-09 | Write content to file | PATCH with non-empty content | 200; content persisted |
| F-10 | Read file content | GET `.../files/domain_data/file?path=...` | 200; `{content, encoding, size_bytes}` |
| F-11 | Preview .md file | In admin.html: click preview on .md | Rendered markdown in preview panel |
| F-12 | Preview .csv file | Click preview on .csv | Table with rows/cols |
| F-13 | Preview .json file | Click preview on .json | Formatted JSON |
| F-14 | Preview .pdf file | Click preview on .pdf | PDF rendered in iframe via base64 decode |
| F-15 | Preview .xlsx file | Click preview on .xlsx | Sheet tabs + table via SheetJS |
| F-16 | Rename file | POST `.../rename` with `{path, new_name}` | 200; old name gone, new name visible |
| F-17 | Rename folder | POST `.../rename` on folder path | 200; all contents moved with it |
| F-18 | Move file to subfolder | POST `.../move` with `{src, dest_folder}` | 200; file appears under dest |
| F-19 | Move via drag-drop (UI) | Drag file onto folder in tree | File moves; tree refreshes |
| F-20 | Delete file | DELETE `.../file?path=...` | 200; file absent from tree |
| F-21 | Delete folder (non-empty) | DELETE `.../folder` with `{recursive: true}` | 200; folder + contents gone |
| F-22 | Delete folder (non-recursive on non-empty) | DELETE `.../folder` with `{recursive: false}` on non-empty folder | 400/409 error |
| F-23 | Bulk delete (UI) | Toggle Select mode, check 3 items, click Delete | Confirmation modal; all 3 deleted |
| F-24 | Cross-worker isolation | Read worker A's file path via worker B's endpoint | 404 scoped to correct root |

### 4B — Admin: Own Worker Only

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| F-25 | Browse own worker tree | `GET /api/admin/worker/files/domain_data` | 200; only own worker's data |
| F-26 | Upload file to own worker | POST to `/api/admin/worker/files/domain_data/upload` | 201 |
| F-27 | Admin cannot access other worker | `GET /api/super/workers/w-market-risk/files/domain_data` with admin token | 403 |
| F-28 | Admin file CRUD | Create folder, write file, read, rename, delete via `/api/admin/worker/files/` | All 200; tree updates |
| F-29 | Admin upload overwrite | Upload same file twice → Replace | 200 |

### 4C — User: No File Management

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| F-30 | User cannot browse files | GET `/api/admin/worker/files/domain_data` with user token | 403 |
| F-31 | User cannot upload | POST to any file upload endpoint | 403 |

---

## Module 5 — Chat / Agent

| ID | Scenario | Role | Steps | Expected |
|----|----------|------|-------|----------|
| C-01 | Simple text query | user | Open `mcp-agent.html`, type "Hello, who are you?", send | SSE streams `session` event then `text` events; response rendered in chat |
| C-02 | SSE streaming visible | any | Long query | Text appears word-by-word; `[DONE]` closes stream |
| C-03 | Tool-calling query | user | Ask "Search for counterparty Goldman Sachs in IRIS" | Agent calls `iris_search_counterparties`, returns results, citations visible |
| C-04 | Multi-step tool chain | any | Ask for a counterparty intelligence brief | Agent calls workflow_list → workflow_get → multiple data tools in sequence |
| C-05 | Thread persistence | user | Send message, copy thread_id, refresh page, resume thread | Prior messages visible; agent has context |
| C-06 | Thread isolation | user A + user B | Both on same worker, different users | `GET /api/agent/threads` each sees only own threads |
| C-07 | Worker switcher (super_admin) | super_admin | Switch worker dropdown in header | Agent uses new worker's system_prompt and tool allowlist |
| C-08 | Tool filtered by worker | admin | Worker has `enabled_tools: ["iris_search_counterparties"]`; ask for EDGAR data | Agent responds it cannot (tool not available) |
| C-09 | System prompt respected | super_admin | Worker A: "You are a market risk expert"; Worker B: "You are a credit analyst" | Each worker's first response reflects its persona |
| C-10 | Abort in-progress run | any | Click stop/cancel during streaming | Stream stops; partial message shown |
| C-11 | Error handling — server down | any | Agent server down → send query | UI shows error toast, no crash |
| C-12 | File upload in chat | any | Upload a CSV via chat upload button | File stored in worker's uploads; agent can reference it |

---

## Module 6 — Tool Testing

### 6A — IRIS CCR Tools

| ID | Query / Tool | Expected |
|----|-------------|----------|
| T-01 | `iris_search_counterparties` — "Find Goldman Sachs" | Returns counterparty rows with name, rating, exposure |
| T-02 | `iris_counterparty_dashboard` — specific cpty | Full dashboard: exposures, limits, VAR |
| T-03 | `iris_exposure_trend` — date range | Chart data points over time |
| T-04 | `iris_limit_lookup` — limit type query | Returns applicable limits |
| T-05 | `iris_limit_breach_check` — portfolio scan | Lists any breaches with severity |
| T-06 | `iris_portfolio_breach_scan` | Returns portfolio-wide summary |
| T-07 | `iris_multi_counterparty_comparison` | Side-by-side comparison table |
| T-08 | `iris_rating_screen` | Filters cptys by rating |
| T-09 | `iris_list_dates` | Returns available date snapshots |

### 6B — OSFI Regulatory Tools

| ID | Query / Tool | Expected |
|----|-------------|----------|
| T-10 | `osfi_list_docs` | Lists available OSFI .md files |
| T-11 | `osfi_search_guidance` — keyword "capital" | Returns matching excerpts with headings |
| T-12 | `osfi_read_document` — CAR_2026 | Returns chunked content |
| T-13 | `osfi_fetch_announcements` — live fetch | Calls Tavily; returns OSFI news content |
| T-14 | Multi-chunk navigation | Read chunk; use `next_char_offset` to page | Subsequent calls return next chunk |

### 6C — EDGAR / SEC Tools

| ID | Query | Expected |
|----|-------|----------|
| T-15 | `edgar_find_filing` — "JPMorgan 10-K 2024" | CIK, accession number, filing URL |
| T-16 | `edgar_extract_section` — MD&A | Extracted text from filing |
| T-17 | `edgar_get_metric` — Revenue | XBRL value with units |
| T-18 | `edgar_get_statements` — Balance Sheet | Structured financial data |
| T-19 | `edgar_earnings_brief` — recent quarter | Earnings summary with EPS, revenue |
| T-20 | `edgar_peer_comparison` — 3 banks | Comparative metrics table |
| T-21 | `edgar_risk_summary` | Key risk factors extracted |
| T-22 | `edgar_segment_analysis` | Business segment breakdown |
| T-23 | `edgar_company_brief` | One-page company summary |
| T-24 | `edgar_calculate_ratios` | ROE, ROA, CET1 etc. |
| T-25 | Canadian bank (BMO) 10-K attempt | Returns "BMO files 6-K, not 10-K" guidance |

### 6D — Tavily / IR / News Tools

| ID | Query | Expected |
|----|-------|----------|
| T-26 | `tavily_news_search` — "bank stress test 2025" | Recent news articles with sources |
| T-27 | `tavily_web_search` — general query | Web results |
| T-28 | `tavily_research_search` — deep research | Extended content |
| T-29 | `tavily_yahoo_get_quote` — "JPM" | Live stock price, P/E, market cap |
| T-30 | `tavily_yahoo_get_history` — "GS" last 30 days | OHLCV price history |
| T-31 | `tavily_yahoo_search_symbols` — "goldman" | Symbol matches |
| T-32 | `ir_list_supported_companies` | List of companies with IR data |
| T-33 | `ir_get_latest_earnings` — "RBC" | Earnings release content |

### 6E — DuckDB / SQL Tools

| ID | Query | Expected |
|----|-------|----------|
| T-34 | `duckdb_list_files` | Lists DuckDB databases in worker dir |
| T-35 | `duckdb_list_tables` — specific DB | Table names |
| T-36 | `duckdb_query` — simple SELECT | Row results |
| T-37 | `duckdb_sql` — aggregation | Aggregated results |
| T-38 | `sqlselect_list_sources` | Lists CSV/Parquet files available |
| T-39 | `sqlselect_execute_query` — SELECT on iris CSV | Returns rows |
| T-40 | `sqlselect_sample_data` — iris CSV | First N rows |
| T-41 | `sqlselect_get_schema` — iris CSV | Column names + types |

### 6F — MS Document Tools

| ID | Query | Expected |
|----|-------|----------|
| T-42 | `msdoc_list_files` | Lists Word/Excel in uploads |
| T-43 | `msdoc_read_word` — uploaded .docx | Extracted text |
| T-44 | `msdoc_read_excel` — uploaded .xlsx | Sheet data |
| T-45 | `msdoc_search_word` — keyword | Matching paragraphs |
| T-46 | `msdoc_search_excel` — value search | Matching cells |

### 6G — Utility Tools

| ID | Query | Expected |
|----|-------|----------|
| T-47 | `list_uploaded_files` | Lists files in worker uploads/ |
| T-48 | `pdf_read` — uploaded PDF | Extracted text pages |
| T-49 | `parquet_read` — uploaded .parquet | Schema + sample rows |
| T-50 | `md_save` — save analysis output | Saves .md to uploads/ |
| T-51 | `md_to_docx` — convert saved .md | .docx created in uploads/ |
| T-52 | `generate_chart` | Chart image or data returned |
| T-53 | `fill_template` — cpty_intel_brief.md | Template filled with placeholders replaced |
| T-54 | `search_files` — keyword in uploads | Returns matching file excerpts |

### 6H — CCR Tools (worker-scoped data)

| ID | Query | Expected |
|----|-------|----------|
| T-55 | `get_counterparty_exposure` | Returns exposure by cpty from iris data |
| T-56 | `get_credit_limits` | Limits table |
| T-57 | `get_trade_inventory` | Trade-level details |
| T-58 | `get_var_contribution` | VaR attribution |
| T-59 | `get_historical_exposure` — date range | Time series |
| T-60 | CCR tool on worker with no iris data | Returns "data not found" gracefully, not 500 |

---

## Module 7 — Workflows

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| WF-01 | List workflows via tool | Ask "What workflows are available?" | Agent calls `workflow_list`; returns 12+ verified workflows with name, description, inputs |
| WF-02 | Get workflow content | Ask agent to fetch `counterparty_intelligence` workflow | Agent calls `workflow_get`, reads steps |
| WF-03 | Execute counterparty_intelligence | "Run counterparty intelligence for Deutsche Bank" | Multi-step: search IRIS → EDGAR → Tavily news → assemble brief; result saved via md_save |
| WF-04 | Execute osfi_regulatory_watch | "Run OSFI regulatory watch" | Calls osfi_list_docs → osfi_search_guidance → osfi_read_document; regulatory summary produced |
| WF-05 | Execute portfolio_concentration_report | "Generate portfolio concentration report" | Calls iris tools → aggregates → generates chart → saves report |
| WF-06 | Execute limit_breach_escalation | "Check for limit breaches and escalate" | Calls iris_limit_breach_check; formats escalation memo |
| WF-07 | Custom workflow creation (admin) | Upload new .md workflow to `verified_workflows/` section | Workflow appears in `workflow_list` immediately (hot-reload, ~5 min) |
| WF-08 | Custom workflow in `my/` folder | Upload to `my/` subdirectory | Also appears in workflow_list with `source: my` |
| WF-09 | Workflow with missing inputs | Run workflow without providing required inputs | Agent asks for missing parameters before proceeding |
| WF-10 | Worker-scoped workflow isolation | Upload workflow to Worker A; query from Worker B | Worker B does not see Worker A's custom workflows |

---

## Module 8 — Admin Panel (admin.html)

| ID | Scenario | Role | Steps | Expected |
|----|----------|------|-------|----------|
| AP-01 | Admin panel loads | admin | Open `admin.html` | Own worker info displayed; domain_data and workflows sections visible |
| AP-02 | Super admin panel | super_admin | Open `admin.html` | Worker selector visible; can switch between workers |
| AP-03 | File tree renders | admin | Navigate to Domain Data tab | Tree shows folders and files with icons |
| AP-04 | Upload queue | admin | Drop multiple files on upload zone | Queue items appear; progress bars animate; success/error per file |
| AP-05 | Inline rename (double-click) | admin | Double-click a filename in tree | Inline input appears; press Enter to commit |
| AP-06 | Context menu | admin | Right-click file in tree | Menu with Preview, Rename, Delete options |
| AP-07 | Drag-and-drop move | admin | Drag file onto folder | File moves; tree refreshes |
| AP-08 | Bulk delete | admin | Enable Select mode, select 3 files, Delete | Confirmation modal; all 3 deleted |
| AP-09 | Preview .md panel | admin | Click .md file | Markdown rendered on right panel |
| AP-10 | Preview .xlsx | admin | Click Excel file | Sheet tabs + table shown |
| AP-11 | Worker tool filtering UI | super_admin | Edit worker, remove a tool from allowlist | Tool absent from `GET /api/workers/{id}/tools` |
| AP-12 | Audit log section | super_admin | Navigate to Audit tab | Recent tool calls shown; filter by worker_id/user_id works |
| AP-13 | Audit pagination | super_admin | Many entries: change offset | Non-overlapping entries; total_matched consistent |
| AP-14 | User cannot see admin panel link | user | Login as user, view header | Admin console link absent |

---

## Module 9 — Security & RBAC

| ID | Scenario | Expected |
|----|----------|----------|
| S-01 | No token on protected endpoint | GET `/api/super/workers` with no Authorization header | 401 |
| S-02 | Invalid token signature | Send tampered JWT | 401 |
| S-03 | User calls super endpoint | User token on `GET /api/super/workers` | 403 |
| S-04 | Admin calls super endpoint | Admin token on `DELETE /api/super/workers/{id}` | 403 |
| S-05 | Thread isolation | GET `/api/agent/threads` as User A | Returns only User A's threads |
| S-06 | User queries wrong worker tools | GET `/api/workers/w-market-risk/tools` with user assigned to different worker | 403 |
| S-07 | Path traversal attempt | GET `.../files/domain_data/file?path=../../config/users.json` | 403 "Access denied" |
| S-08 | Upload oversized file | Upload 51 MB file | 413 error |
| S-09 | Rate limit recovery | Wait 60s after 429 on login | Login succeeds again |
| S-10 | JWT expiry | Let token expire (or set short-lived token) | Next request → 401; frontend redirects to login |

---

## Module 10 — Thread & Session Persistence

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| P-01 | Thread survives restart | Start chat, get thread_id; restart agent server; resume same thread | Prior conversation context available |
| P-02 | Thread registry loaded at startup | Restart server; `GET /api/agent/threads` | Previously created threads still present in registry |
| P-03 | Thread scoped to user+worker | User A and User B on same worker | Each sees only own threads |
| P-04 | Multiple threads | Create 3 separate conversations as same user | All 3 appear in thread list |

---

## Module 11 — G-04 Worker Path Isolation (SAJHA side)

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| G-01 | IRIS data isolated | Worker A has different iris CSV than Worker B; query each | Queries return different data per worker |
| G-02 | OSFI docs via common_data_path | Both workers share `/data/common/regulatory/osfi` | Same OSFI docs accessible to both workers |
| G-03 | Workflow tools isolated | Worker A has custom workflow in `my/`; Worker B does not | `workflow_list` from Worker B does not show Worker A's workflow |
| G-04 | DuckDB isolated | Worker A has DuckDB A, Worker B has DuckDB B | `duckdb_list_files` returns different files per worker |
| G-05 | Header injection verified | Agent sends `X-Worker-Data-Root` to SAJHA on every tool call | SAJHA tools use per-request path; no global data leakage |

---

## Execution Order & Dependencies

```
Module 1 (Auth)           → all other modules depend on valid tokens
Module 2 (Workers)        → Module 3, 4, 5, 11 depend on workers existing
Module 3 (Users)          → Module 9 (RBAC) uses newly created roles
Module 4 (Files)          → Module 6 (Tools) needs data files uploaded first
Module 5 (Chat/Agent)     → Module 6, 7 run through the chat interface
Module 6 (Tools)          → Module 7 (Workflows) composes multiple tools
Module 7 (Workflows)      → can run in parallel with M6 after M4 complete
Module 8 (Admin Panel)    → frontend layer over M2/M4; runs in parallel
Module 9 (Security)       → negative tests; run after all positive tests pass
Module 10 (Persistence)   → requires a deliberate server restart mid-run
Module 11 (G-04)          → requires two workers with distinct data sets
```

---

## Test Execution Strategy

### Phase 1 — Automated API tests (extend `test_multiworker_platform.py`)
Covers: A-01–A-10, W-01–W-11, U-01–U-09, F-01–F-31, S-01–S-10, P-01–P-04, G-01–G-05

### Phase 2 — Tool & workflow coverage (`test_tools_and_workflows.py`)
Fires each tool via `POST /api/agent/run` with targeted natural-language queries.
Asserts: tool was called in SSE stream + non-empty result returned.
Covers: T-01–T-60, WF-01–WF-10

### Phase 3 — Manual UI walkthrough (browser)
Visual/UX validation: streaming animation, drag-drop, preview rendering, bulk select.
Covers: AP-01–AP-14, C-01–C-12

---

## Summary

| Phase | Test IDs | Count | Method |
|-------|----------|-------|--------|
| Auth & Session | A-01–A-10 | 10 | Automated |
| Worker Management | W-01–W-11 | 11 | Automated |
| User Management | U-01–U-09 | 9 | Automated |
| File Operations | F-01–F-31 | 31 | Automated |
| Chat / Agent | C-01–C-12 | 12 | Manual + partial auto |
| Tool Coverage | T-01–T-60 | 60 | Automated (agent run) |
| Workflows | WF-01–WF-10 | 10 | Automated (agent run) |
| Admin Panel UI | AP-01–AP-14 | 14 | Manual |
| Security / RBAC | S-01–S-10 | 10 | Automated |
| Thread Persistence | P-01–P-04 | 4 | Automated |
| G-04 Path Isolation | G-01–G-05 | 5 | Automated |
| **Total** | | **176** | |
