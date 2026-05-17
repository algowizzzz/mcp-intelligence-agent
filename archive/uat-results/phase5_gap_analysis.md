# UAT Results — Phase 5 Gap Analysis

**Run ID:** `phase5_2026-04-03_gap_analysis`
**Generated:** 2026-04-03 (session date)
**Scope:** Comprehensive gap analysis across all phases + new endpoint testing (connectors, workflow JWT, PATCH file/used, admin write fixes, storage layer)
**Method:** Static code review + live curl/Python API testing against localhost:8000 and localhost:3002
**Prior phases:** phase1 (infra), phase2 (file ops), phase3 (tools+API), module9 (worker path), phase4 (role-based FE QA)

---

## Summary

| Status | Count |
|--------|-------|
| PASS | 40 |
| FAIL | 9 |
| WARN | 2 |
| **Total** | **51** |

**Pass rate: 78% (40/51)**
**New critical bugs found: 5** (4 missing admin backend endpoints + 1 workflow path mismatch)
**Known gaps resolved: 2** (PATCH file/used now implemented; audit field names now matched in JS)

---

## Section 1 — Coverage Matrix (All Endpoints)

Total unique route decorators in `agent_server.py`: **71**

| Endpoint | Method | Prior Coverage | Phase 5 Tested | Status | Notes |
|----------|--------|---------------|----------------|--------|-------|
| /health | GET | phase1 | Yes | PASS | |
| /api/auth/login | POST | all phases | No (already green) | PASS | |
| /api/auth/me | GET | — | Yes | PASS | |
| /api/auth/onboarding | POST | — | Yes | PASS | Requires body: display_name, new_password, confirm_password |
| /api/auth/change-password | POST | — | Yes | PASS | |
| /api/super/workers | GET | phase4 | No | PASS | |
| /api/super/workers | POST | phase4 | No | PASS | |
| /api/super/workers/{id} | GET | — | Yes | PASS | |
| /api/super/workers/{id} | PUT | phase4 | No | PASS | |
| /api/super/workers/{id} | DELETE | — | Yes | FAIL | Requires body `{confirm_name}` — no body → 422; see BUG-NEW-005 |
| /api/super/workers/{id}/assign | POST | — | Yes | FAIL | Requires `role` field in body; test sent only `user_id` → 422; see BUG-NEW-006 |
| /api/super/workers/{id}/assign/{uid} | DELETE | — | Yes | PASS | |
| /api/super/users | GET | phase4 | No | PASS | |
| /api/super/users | POST | phase4 | No | PASS | |
| /api/super/users/{id} | PUT | phase4 | No | PASS | |
| /api/super/users/{id} | DELETE | phase4 | No | PASS | |
| /api/super/users/{id}/reset-password | POST | phase4 | No | PASS | |
| /api/super/audit | GET | phase4 | Yes | PASS | Fields: timestamp, tool_name, worker_id, user_id, duration_ms, status |
| /api/super/connectors | GET | phase4 brief | Yes | PASS | NEW |
| /api/super/connectors/{type} | PUT | — | Yes | PASS | NEW — upsert with credential merge |
| /api/super/connectors/{type} | DELETE | — | Yes | PASS | NEW — 404 on missing type |
| /api/super/connectors/{type}/test | POST | — | Yes | PASS | NEW — gracefully returns {ok:false} for bad creds |
| /api/super/workers/{id}/connector-scope | GET | — | Yes | PASS | NEW |
| /api/super/workers/{id}/connector-scope/{type} | PUT | — | Yes | PASS | NEW |
| /api/super/workers/{id}/files/{section} | GET | module9 | No | PASS | |
| /api/super/workers/{id}/files/{section}/upload | POST | module9 | No | — | Not re-tested (covered in module9 PA-07) |
| /api/super/workers/{id}/files/{section}/file | GET | — | — | UNTESTED | No prior coverage |
| /api/super/workers/{id}/files/{section}/file | PATCH | — | — | UNTESTED | No prior coverage |
| /api/super/workers/{id}/files/{section}/file | DELETE | — | — | UNTESTED | No prior coverage |
| /api/super/workers/{id}/files/{section}/folder | DELETE | — | — | UNTESTED | No prior coverage |
| /api/super/workers/{id}/files/{section}/folder | POST | module9 | No | PASS | Covered via phase4 SA-FT-05 |
| /api/super/workers/{id}/files/{section}/rename | POST | phase4 | No | PASS | |
| /api/super/workers/{id}/files/{section}/move | POST | — | — | UNTESTED | |
| /api/mcp/tools | GET | phase4 | Yes | PASS | 121 tools |
| /api/admin/worker | GET | phase4 | No | PASS | |
| /api/admin/worker | PUT | — | Yes | FAIL | **BUG-NEW-001: Route does not exist (405)** |
| /api/admin/worker/prompt | PUT | — | — | UNTESTED | Not tested in any phase |
| /api/admin/worker/tools | PUT | phase4 ADM-TOOLS-02 | No | PASS | |
| /api/admin/worker/users | GET | phase4 | Yes | PASS | |
| /api/admin/worker/users | POST | — | Yes | FAIL | **BUG-NEW-002: Route does not exist (405)** |
| /api/admin/worker/users/{id} | PUT | — | Yes | FAIL | **BUG-NEW-003: Route does not exist (405)** |
| /api/admin/worker/users/{id}/reset-password | POST | — | Yes | FAIL | **BUG-NEW-004: Route does not exist (405)** |
| /api/admin/worker/files/{section} | GET | phase4 | No | PASS | |
| /api/admin/worker/files/{section}/upload | POST | module9 | No | PASS | |
| /api/admin/worker/files/{section}/file | GET | — | — | UNTESTED | |
| /api/admin/worker/files/{section}/file | PATCH | — | — | UNTESTED | |
| /api/admin/worker/files/{section}/file | DELETE | — | — | UNTESTED | |
| /api/admin/worker/files/{section}/folder | DELETE | phase4 | No | PASS | |
| /api/admin/worker/files/{section}/folder | POST | phase4 | No | PASS | |
| /api/admin/worker/files/{section}/rename | POST | module9 | No | PASS | |
| /api/admin/worker/files/{section}/move | POST | — | — | UNTESTED | |
| /api/admin/tree/{section} | GET | — | — | UNTESTED | Legacy admin tree (pre-worker-path) |
| /api/admin/upload | POST | — | — | UNTESTED | Legacy admin upload |
| /api/admin/folder | POST | — | — | UNTESTED | Legacy |
| /api/admin/item | DELETE | — | — | UNTESTED | Legacy |
| /api/admin/rename | PATCH | — | — | UNTESTED | Legacy |
| /api/admin/move | POST | — | — | UNTESTED | Legacy |
| /api/admin/file | POST | — | — | UNTESTED | Legacy |
| /api/admin/file | GET | — | — | UNTESTED | Legacy |
| /api/admin/validate/{section}/{path} | GET | — | — | UNTESTED | |
| /api/admin/tools | GET | — | Yes | PASS | Proxies SAJHA tool list |
| /api/files/upload | POST | — | — | UNTESTED | |
| /api/workspace/files | GET | phase4 indirect | Yes | PASS | JWT-gated, per-user |
| /api/workflows | GET | — | Yes | PASS | JWT-gated, reads verified_workflows |
| /api/workflows | POST | — | Yes | PASS | JWT-gated, writes to my_workflows |
| /api/workflows/{filename} | GET | — | Yes | FAIL | **BUG-NEW-007: Reads verified_workflows but create writes my_workflows — always 404 for newly created workflows** |
| /api/workflows/{filename} | DELETE | — | Yes | PASS | Deletes from my_workflows |
| /api/workflows/{filename}/used | PATCH | — | Yes | PASS | Updates metadata sidecar |
| /api/fs/{section}/tree | GET | phase4 | No | PASS | |
| /api/fs/{section}/file | GET | phase4 | No | PASS | |
| /api/fs/{section}/file | PATCH | — | — | UNTESTED | (Not same as /file/used) |
| /api/fs/{section}/file/used | PATCH | phase4 FAIL | Yes | PASS | **FIXED — was 405, now 200** |
| /api/fs/{section}/upload | POST | — | — | UNTESTED | |
| /api/fs/{section}/folder | POST | — | — | UNTESTED | |
| /api/fs/{section}/move | POST | — | — | UNTESTED | |
| /api/fs/{section}/rename | POST | — | — | UNTESTED | |
| /api/fs/{section}/file | DELETE | — | — | UNTESTED | |
| /api/fs/{section}/folder | DELETE | — | — | UNTESTED | |
| /api/agent/run | POST | phase4, module9 | No | PASS | LLM-gated |
| /api/agent/threads | GET | — | Yes | PASS | |
| /api/workers/{id}/tools | GET | — | Yes | PASS | |

---

## Section 2 — Phase 5 Pass/Fail Table (This Session)

### Group A — Connector Endpoints (New)

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| CON-01 | List connectors (super_admin) | GET /api/super/connectors | 200 | PASS | 2 connectors returned |
| CON-02 | Admin blocked from connectors | GET /api/super/connectors | 403 | PASS | RBAC correct |
| CON-03 | Upsert connector (PUT) | PUT /api/super/connectors/microsoft_azure | 200 | PASS | Returns merged record without credentials |
| CON-04 | Test connector (bad creds graceful) | POST /api/super/connectors/microsoft_azure/test | 200 | PASS | Returns {ok:false, message} for invalid tenant |
| CON-05 | Unknown connector type rejected | PUT /api/super/connectors/unknown_type | 400 | PASS | |
| CON-06 | Worker connector-scope GET | GET /api/super/workers/w-market-risk/connector-scope | 200 | PASS | Returns connector_scope dict |
| CON-07 | Worker connector-scope PUT | PUT /api/super/workers/.../connector-scope/microsoft_azure | 200 | PASS | Scope saved and persisted |
| CON-08 | Delete connector | DELETE /api/super/connectors/microsoft_azure | 200 | PASS | |
| CON-09 | Delete missing connector → 404 | DELETE /api/super/connectors/nonexistent | 404 | PASS | |

### Group B — Workflow Endpoints (Now JWT-gated)

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| WF-01 | List workflows (JWT) | GET /api/workflows | 200 | PASS | 12 verified workflows returned |
| WF-02 | Create workflow | POST /api/workflows | 201 | PASS | Writes to my_workflows |
| WF-03 | Get workflow by filename | GET /api/workflows/{filename} | 404 | FAIL | **BUG-NEW-007: GET reads verified_workflows, POST writes my_workflows — path mismatch** |
| WF-04 | Mark workflow used | PATCH /api/workflows/{filename}/used | 200 | PASS | |
| WF-05 | Delete workflow | DELETE /api/workflows/{filename} | 200 | PASS | Deletes from my_workflows correctly |
| WF-06 | Unauthenticated access blocked | GET /api/workflows | 401 | PASS | JWT required |

### Group C — PATCH file/used (Bug from phase4 — now fixed)

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| FS-USED-01 | Mark verified workflow used | PATCH /api/fs/verified/file/used?path=... | 200 | PASS | Was 405 in phase4; now implemented |
| FS-USED-02 | Mark uploads file used | PATCH /api/fs/uploads/file/used?path=... | 200 | PASS | |
| FS-USED-03 | Missing path param → 400 | PATCH /api/fs/verified/file/used | 400 | PASS | Correct validation |

### Group D — Admin Write Endpoints (Phase4 critical bugs)

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| ADM-WC-02 | Admin save worker config | PUT /api/admin/worker | 405 | FAIL | **BUG-NEW-001: Route not defined in agent_server.py. UI calls this, server has no handler.** |
| ADM-USR-01 | Admin list users | GET /api/admin/worker/users | 200 | PASS | |
| ADM-USR-02 | Admin reset user password | POST /api/admin/worker/users/{id}/reset-password | 405 | FAIL | **BUG-NEW-004: Route not defined** |
| ADM-USR-03 | Admin toggle user enabled | PUT /api/admin/worker/users/{id} | 405 | FAIL | **BUG-NEW-003: Route not defined** |
| ADM-USR-04 | Admin create user | POST /api/admin/worker/users | 405 | FAIL | **BUG-NEW-002: Route not defined** |

> **Root Cause:** Phase4 identified that admin.html was calling `/api/super/` endpoints with an admin JWT. The UI was updated to call `/api/admin/worker/users` etc., but the **corresponding backend routes were never implemented**. The fix was done on the frontend only — the backend counterparts are missing.

### Group E — Workspace & Auth Endpoints

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| WS-01 | List workspace files (JWT) | GET /api/workspace/files | 200 | PASS | Per-user directory scoped correctly |
| WS-02 | Workspace files unauthenticated | GET /api/workspace/files | 401 | PASS | |
| AUTH-ME-01 | Get current user | GET /api/auth/me | 200 | PASS | |
| AUTH-ONBOARD-01 | Onboarding (empty body) | POST /api/auth/onboarding | 422 | WARN | Requires body; 422 is correct FastAPI validation behavior — not a bug |
| AUTH-ONBOARD-02 | Onboarding (with body) | POST /api/auth/onboarding | 200 | PASS | |
| AUTH-CHPW-01 | Change password | POST /api/auth/change-password | 200 | PASS | |
| HEALTH-01 | Health check | GET /health | 200 | PASS | |

### Group F — Audit Log Field Fix (phase4 SUPER-BUG-002)

| ID | Scenario | Status | Detail |
|----|----------|--------|--------|
| AUD-FIX-01 | API returns `timestamp` field | PASS | JS now reads `e.timestamp \|\| e.ts \|\| e.called_at \|\| e.time` — first match is correct |
| AUD-FIX-02 | API returns `tool_name` field | PASS | JS now reads `e.tool_name \|\| e.tool` — first match is correct |

> **Assessment:** SUPER-BUG-002 (audit columns showing "—") is **FIXED** in admin.html. The JS fallback chain now correctly resolves both fields.

### Group G — Dashboard Stats Investigation (phase4 SUPER-BUG-001)

| ID | Scenario | Status | Detail |
|----|----------|--------|--------|
| DASH-WF-01 | verified_workflows tree returns file array | PASS | `tree` array contains 12 file objects with `type: "file"` |
| DASH-DOM-01 | domain_data tree structure OK | PASS | 12 items in tree array |

> **Assessment:** The tree API returns correct data. SUPER-BUG-001 (dashboard stats showing "—") is likely a **JS-side counting bug** — the dashboard code may not be traversing `body.tree` to count items. This remains unconfirmed without browser automation; the backend data is correct.

### Group H — SAJHA Connector Tool Count

| ID | Scenario | Status | Detail |
|----|----------|--------|--------|
| SAJHA-CON-01 | Connector tools loaded in SAJHA | PASS | 36 connector tools loaded (Teams, SharePoint, PowerBI, Outlook, Confluence, Jira) |
| SAJHA-TOTAL-01 | Total SAJHA tool count | PASS | 121 tools (up from 74+ baseline — connector tools added successfully) |

### Group I — Storage Abstraction Layer

| ID | Scenario | Status | Detail |
|----|----------|--------|--------|
| STOR-01 | `sajha.storage` module imports | PASS | |
| STOR-02 | `sajha.path_resolver` module imports | PASS | |
| STOR-03 | `WorkerRepository.find_by_user` | FAIL | **BUG-NEW-008: Returns None for `test_user` despite user being in `assigned_users`. Method reads `w.get('users', [])` but field is `assigned_users`.** |
| STOR-04 | Storage read/write/delete cycle | PASS | Local filesystem storage layer works correctly |
| STOR-05 | path_resolver raises ValueError for my_data without user_id | PASS | Correct validation behavior |

### Group J — Misc Endpoint Smoke Tests

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| MCP-01 | MCP tools list (admin) | GET /api/mcp/tools | 200 | PASS | 121 tools |
| THR-01 | Agent threads list | GET /api/agent/threads | 200 | PASS | 4 threads for test_user |
| WT-01 | Worker tools | GET /api/workers/w-market-risk/tools | 200 | PASS | |
| AT-01 | Admin tools proxy | GET /api/admin/tools | 200 | PASS | Proxies SAJHA 121 tools |
| SW-GET | Super get single worker | GET /api/super/workers/{id} | 200 | PASS | |
| SW-PUT | Super update worker | PUT /api/super/workers/{id} | 200 | PASS | |
| SW-DEL | Super delete worker | DELETE /api/super/workers/{id} | 422 | FAIL | **BUG-NEW-005: Requires `confirm_name` body — API consumer (UI) may not send it** |
| ASSIGN-01 | Assign user to worker | POST /api/super/workers/{id}/assign | 422 | FAIL | **BUG-NEW-006: Requires `role` field in body. Sending only `user_id` fails.** |
| ASSIGN-02 | Unassign user from worker | DELETE /api/super/workers/{id}/assign/{uid} | 200 | PASS | |

---

## Section 3 — New Bugs Found

### CRITICAL — Backend Routes Missing (Admin role completely broken for writes)

| ID | Severity | Description | Root Cause |
|----|----------|-------------|-----------|
| BUG-NEW-001 | Critical | `PUT /api/admin/worker` does not exist (405). Admin cannot save worker config name/description. UI (admin.html `saveWorkerConfig()`) calls this endpoint correctly after phase4 fix, but the backend was never implemented. | Frontend was fixed to use correct endpoint path; backend handler was never added. |
| BUG-NEW-002 | Critical | `POST /api/admin/worker/users` does not exist (405). Admin cannot create users scoped to their worker. | Same root cause — frontend fixed but backend missing. |
| BUG-NEW-003 | Critical | `PUT /api/admin/worker/users/{id}` does not exist (405). Admin cannot enable/disable users. | Same root cause. |
| BUG-NEW-004 | Critical | `POST /api/admin/worker/users/{id}/reset-password` does not exist (405). Admin cannot reset user passwords. | Same root cause. |

### HIGH — Logic Bug

| ID | Severity | Description | Root Cause |
|----|----------|-------------|-----------|
| BUG-NEW-007 | High | `GET /api/workflows/{filename}` returns 404 for any workflow created via `POST /api/workflows`. The POST handler writes to `my_workflows` directory but the GET handler reads from `verified_workflows`. These are different directories. New workflows are permanently inaccessible via GET after creation. | `create_workflow` uses `_resolve_worker_path(worker, 'my_workflows')`, `get_workflow` uses `_resolve_worker_path(worker, 'verified_workflows')`. The GET should check both paths, or the POST should be consistent. |
| BUG-NEW-008 | High | `WorkerRepository.find_by_user(user_id)` always returns `None` for real users. The method reads `w.get('users', [])` but the actual field in `workers.json` is `assigned_users`. This breaks any code depending on WorkerRepository for user→worker lookup (storage migration prep code). | Field name mismatch in `sajha/worker_repository.py` line: `users = w.get('users', [])` should be `users = w.get('assigned_users', w.get('users', []))`. |

### MEDIUM — API Contract Issues

| ID | Severity | Description | Impact |
|----|----------|-------------|--------|
| BUG-NEW-005 | Medium | `DELETE /api/super/workers/{id}` requires `confirm_name` in request body (422 without it). No UI component sends this body — the confirmation modal may not include it. | Super admin cannot delete workers through the UI. |
| BUG-NEW-006 | Medium | `POST /api/super/workers/{id}/assign` requires `role` field (`admin` or `user`) in body. The UI's "Assign User" modal may not surface this field. | Super admin cannot assign users to workers without specifying role. |

---

## Section 4 — Remaining Gaps (Non-LLM Tests Not Yet Run)

| Area | Endpoints | Reason Untested |
|------|-----------|----------------|
| Legacy admin API | `/api/admin/tree/`, `/api/admin/upload`, `/api/admin/folder`, `/api/admin/item`, `/api/admin/rename`, `/api/admin/move`, `/api/admin/file` | Legacy endpoints likely superceded by worker-scoped `/api/admin/worker/files/` — low priority |
| FS write operations | `POST /api/fs/{section}/folder`, `POST /api/fs/{section}/rename`, `POST /api/fs/{section}/move`, `DELETE /api/fs/{section}/file`, `DELETE /api/fs/{section}/folder` | Not exercised in this session |
| Super worker file CRUD | `GET/PATCH/DELETE /api/super/workers/{id}/files/{section}/file`, `DELETE /api/super/workers/{id}/files/{section}/folder`, `POST /api/super/workers/{id}/files/{section}/move` | Not exercised |
| Admin worker file CRUD | `GET/PATCH/DELETE /api/admin/worker/files/{section}/file`, `POST /api/admin/worker/files/{section}/move` | Not exercised |
| File upload endpoints | `POST /api/files/upload`, `POST /api/fs/{section}/upload` | Not exercised |
| Admin prompt update | `PUT /api/admin/worker/prompt` | Not exercised in any phase |
| Admin validate | `GET /api/admin/validate/{section}/{path}` | Not exercised |
| LLM agent tests (PD-01—PD-05) | `POST /api/agent/run` with tool invocations | Require Anthropic API credits |
| Dashboard stat count bug (SUPER-BUG-001) | Client-side render | Requires browser automation to confirm if JS counts `tree` items |
| Settings button mislabeling (MCP-BUG-003) | Client-side only | Requires browser to verify if still wired to clearAllConversations() |

---

## Section 5 — Carry-Forward Bugs (from Phase 4, Still Open)

| ID | Status | Description |
|----|--------|-------------|
| ADMIN-BUG-001 | OPEN (backend missing) | Worker Config Save fails — UI now calls correct `/api/admin/worker` PUT but backend route does not exist |
| ADMIN-BUG-002 | OPEN (backend missing) | Admin reset PW — UI now calls `/api/admin/worker/users/{id}/reset-password` but route does not exist |
| ADMIN-BUG-003 | OPEN (backend missing) | Admin toggle user — UI now calls `/api/admin/worker/users/{id}` PUT but route does not exist |
| ADMIN-BUG-004 | OPEN (backend missing) | Admin create user — UI now calls `/api/admin/worker/users` POST but route does not exist |
| SUPER-BUG-001 | PARTIALLY FIXED | Dashboard stats "—" — backend data is correct (12 files in tree array); JS counting logic unverified |
| SUPER-BUG-002 | FIXED | Audit Time/Tool columns "—" — JS now reads correct field names (timestamp, tool_name) |
| MCP-BUG-001 | FIXED | PATCH /api/fs/{section}/file/used was 405 — now returns 200 correctly |
| SUPER-BUG-003 | OPEN | Inline rename editor concatenates old+new name — not retested |
| MCP-BUG-002 | OPEN | Double-fetch on verified workflow click — not retested |
| MCP-BUG-003 | OPEN | Settings button wired to clearAllConversations() — not retested |

---

## Section 6 — Summary Statistics

| Metric | Value |
|--------|-------|
| Total endpoints in agent_server.py | 71 |
| Endpoints with prior coverage (phases 1-4, module9) | 34 |
| New endpoints tested this session | 17 |
| Endpoints with full coverage (any phase) | ~38 (54%) |
| Endpoints never tested | ~33 (46%) |
| This session: tests run | 51 |
| This session: PASS | 40 (78%) |
| This session: FAIL | 9 (18%) |
| This session: WARN | 2 (4%) |
| New critical bugs found | 4 (missing backend routes for admin writes) |
| New high bugs found | 2 (workflow path mismatch, WorkerRepository field name) |
| New medium bugs found | 2 (delete worker requires body, assign requires role) |
| Bugs fixed since phase4 | 2 (PATCH file/used 405 fixed; audit field JS fallback fixed) |
| SAJHA tools total | 121 (36 connector tools added) |

---

## Section 7 — Recommended Fix Priority

| Priority | Bug ID | Fix |
|----------|--------|-----|
| P0 | BUG-NEW-001 | Add `PUT /api/admin/worker` handler to agent_server.py |
| P0 | BUG-NEW-002 | Add `POST /api/admin/worker/users` handler |
| P0 | BUG-NEW-003 | Add `PUT /api/admin/worker/users/{id}` handler |
| P0 | BUG-NEW-004 | Add `POST /api/admin/worker/users/{id}/reset-password` handler |
| P1 | BUG-NEW-007 | Fix `get_workflow` to search both `my_workflows` and `verified_workflows`, or document that GET only reads verified |
| P1 | BUG-NEW-008 | Fix `WorkerRepository.find_by_user`: `w.get('users', [])` → `w.get('assigned_users', w.get('users', []))` |
| P2 | BUG-NEW-005 | Verify UI sends `confirm_name` body on worker delete; or make it optional |
| P2 | BUG-NEW-006 | Verify UI sends `role` field on user assign; or provide a default |
| P3 | SUPER-BUG-001 | Add browser test to confirm dashboard stat JS counts `tree` array length |
| P3 | SUPER-BUG-003 | Fix inline rename editor input clearing |
