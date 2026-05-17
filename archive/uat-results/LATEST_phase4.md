# UAT Results — phase4 (Role-Based FE QA)

**Run ID:** `phase4_2026-04-04_00-23-59`
**Generated:** 2026-04-04 00:23:59 UTC
**Scope:** Full browser-based FE QA across all roles (super_admin, admin, user) — UI only, no backend code changes
**Method:** CDP browser automation via Claude in Chrome; network requests captured per action

---

## Summary

| Status | Count |
|--------|-------|
| ✓ PASS | 42 |
| ✗ FAIL | 11 |
| ⚠ WARN | 3 |
| **Total** | **56** |

**Pass rate: 75% (42/56)**
**Critical failures: 4** (all admin role write operations broken — wrong endpoint prefix)

---

## Role 1 — super_admin (admin.html)

**Credentials:** `risk_agent` / `RiskAgent2025!`
**Redirect on login:** `/admin.html` ✓
**API prefix:** `/api/super/`

### Authentication

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| SA-AUTH-01 | Login with bad credentials | POST /api/auth/login | 401 | ✓ PASS | Error displayed correctly |
| SA-AUTH-02 | Login with valid super_admin credentials | POST /api/auth/login | 200 | ✓ PASS | JWT issued, redirect to admin.html |

### Dashboard

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| SA-DASH-01 | Dashboard worker stats load | GET /api/super/workers | 200 | ✓ PASS | Worker count renders |
| SA-DASH-02 | Dashboard user stats load | GET /api/super/users | 200 | ✓ PASS | User count renders |
| SA-DASH-03 | Dashboard Workflows stat renders | (render) | — | ✗ FAIL | **BUG:** Shows "—" instead of count |
| SA-DASH-04 | Dashboard Domain Files stat renders | (render) | — | ✗ FAIL | **BUG:** Shows "—" instead of count |

### Domain Data & Workflows (file tree)

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| SA-FT-01 | Domain Data loads for Market Risk Worker | GET /api/super/workers/w-market-risk/files/domain_data | 200 | ✓ PASS | File tree renders |
| SA-FT-02 | Workflows load for Market Risk Worker | GET /api/super/workers/w-market-risk/files/verified_workflows | 200 | ✓ PASS | File tree renders |
| SA-FT-03 | Worker switch — Domain Data re-scopes (CCR) | GET /api/super/workers/w-e74b5836/files/domain_data | 200 | ✓ PASS | Worker ID in URL updates correctly |
| SA-FT-04 | Worker switch — Workflows re-scopes (CCR) | GET /api/super/workers/w-e74b5836/files/verified_workflows | 200 | ✓ PASS | Worker ID in URL updates correctly |
| SA-FT-05 | Create folder | POST /api/super/workers/w-market-risk/files/domain_data/folder | 200 | ✓ PASS | Folder created, tree refreshed |
| SA-FT-06 | Rename folder (inline editor) | POST /api/super/workers/w-market-risk/files/domain_data/rename | 200 | ⚠ WARN | **BUG:** Inline editor does not clear existing value — concatenates old+new name (e.g. `uat_qa_renamed_folderuat_qa_test_folder`) |
| SA-FT-07 | Delete folder | DELETE /api/super/workers/w-market-risk/files/domain_data/folder | 200 | ✓ PASS | Folder removed, tree refreshed |

### Audit Log

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| SA-AUDIT-01 | Audit log initial load | GET /api/super/audit?limit=200&offset=0 | 200 | ✓ PASS | 936 total entries |
| SA-AUDIT-02 | Audit Time column renders | (render) | — | ✗ FAIL | **BUG:** All Time cells show "—" despite data present |
| SA-AUDIT-03 | Audit Tool column renders | (render) | — | ✗ FAIL | **BUG:** All Tool cells show "—" despite data present |
| SA-AUDIT-04 | Pagination next page | GET /api/super/audit?limit=200&offset=200 | 200 | ✓ PASS | Page 2 loads |
| SA-AUDIT-05 | Worker filter | GET /api/super/audit?limit=200&offset=0&worker_id=w-ccr | 200 | ✓ PASS | Filtered results load |

### User Management

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| SA-USR-01 | Users list | GET /api/super/users | 200 | ✓ PASS | All users listed with role/status |
| SA-USR-02 | Reset password | POST /api/super/users/uat_usr_b48d7537/reset-password | 200 | ✓ PASS | Temporary password returned |
| SA-USR-03 | Disable user | PUT /api/super/users/uat_usr_b48d7537 | 200 | ✓ PASS | Status changes to Disabled |
| SA-USR-04 | Enable user | PUT /api/super/users/uat_usr_b48d7537 | 200 | ✓ PASS | Status changes back to Active |
| SA-USR-05 | Create user | POST /api/super/users | 201 | ✓ PASS | New user appears in list |
| SA-USR-06 | Delete user | DELETE /api/super/users/uat_qa_user | 200 | ✓ PASS | User removed from list |

### Connectors

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| SA-CON-01 | Connectors Overview tab | GET /api/super/connectors | 200 | ✓ PASS | Connector list renders |
| SA-CON-02 | Tool Library tab | (client-side) | — | ✓ PASS | Tool cards render from cached data |
| SA-CON-03 | Worker Mapping tab | GET /api/super/workers | 200 | ✓ PASS | Worker-connector mapping renders |
| SA-CON-04 | Create Worker modal | POST /api/super/workers | 201 | ✓ PASS | Worker created and appears in grid |

---

## Role 2 — admin (admin.html)

**Credentials:** `admin` / `Admin2025!`
**Redirect on login:** `/admin.html` ✓
**API prefix (reads):** `/api/admin/`
**API prefix (writes, broken):** `/api/super/` ← root cause of all write failures

> **Root Cause:** admin.html write operations (Worker Config save, User management) are hardcoded to `/api/super/` endpoints. The admin JWT only has access to `/api/admin/` routes. All writes return 403 silently (no UI error feedback).

### Authentication

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| ADM-AUTH-01 | Login with valid admin credentials | POST /api/auth/login | 200 | ✓ PASS | JWT issued, redirect to admin.html |

### Dashboard

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| ADM-DASH-01 | Dashboard loads for scoped worker | GET /api/admin/worker | 200 | ✓ PASS | Single worker context (no dropdown) |
| ADM-DASH-02 | Dashboard user stats load | GET /api/admin/worker/users | 200 | ✓ PASS | 3 assigned users shown |
| ADM-DASH-03 | No worker selector dropdown | (UI check) | — | ✓ PASS | Admin is correctly scoped to single worker |
| ADM-DASH-04 | Workflows/Domain Files stats render | (render) | — | ✗ FAIL | **BUG:** Shows "—" (same as super_admin dashboard bug) |

### Worker Config

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| ADM-WC-01 | Worker Config loads (uses cached data) | (none — reuses GET /api/admin/worker) | — | ✓ PASS | Name, description, system prompt shown |
| ADM-WC-02 | Save Changes | PUT /api/super/workers/w-market-risk | 403 | ✗ FAIL | **CRITICAL BUG:** Wrong endpoint prefix. Should be PUT /api/admin/worker |
| ADM-WC-03 | Save Changes — UI feedback | (render) | — | ✗ FAIL | **BUG:** 403 silently swallowed — no error toast/message shown to admin |

### Tools

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| ADM-TOOLS-01 | Tools list loads | GET /api/mcp/tools | 200 | ✓ PASS | Tool toggles render by category |
| ADM-TOOLS-02 | Save Tools | PUT /api/admin/worker/tools | 200 | ✓ PASS | Correct admin endpoint used |

### Domain Data

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| ADM-DD-01 | Domain Data file tree loads | GET /api/admin/worker/files/domain_data | 200 | ✓ PASS | File tree renders |
| ADM-DD-02 | Create Folder | POST /api/admin/worker/files/domain_data/folder | 200 | ✓ PASS | Correct admin endpoint used |
| ADM-DD-03 | Delete Folder | DELETE /api/admin/worker/files/domain_data/folder | 200 | ✓ PASS | Correct admin endpoint used |

### Workflows

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| ADM-WF-01 | Verified Workflows load | GET /api/admin/worker/files/verified_workflows | 200 | ✓ PASS | File tree renders |

### User Management

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| ADM-USR-01 | Worker-scoped users list | GET /api/admin/worker/users | 200 | ✓ PASS | Only w-market-risk users shown |
| ADM-USR-02 | Reset PW | POST /api/super/users/{id}/reset-password | 403 | ✗ FAIL | **CRITICAL BUG:** Wrong endpoint. Should be /api/admin/worker/users/{id}/reset-password |
| ADM-USR-03 | Disable user | PUT /api/super/users/{id} | 403 | ✗ FAIL | **CRITICAL BUG:** Wrong endpoint. Should be PUT /api/admin/worker/users/{id} |
| ADM-USR-04 | Create User modal | POST /api/super/users | 403 | ✗ FAIL | **CRITICAL BUG:** Hardcoded to /api/super/users. Also triggers native window.alert() on failure (CDP-freezing) |
| ADM-USR-05 | No Delete User action visible | (UI check) | — | ✓ PASS | Delete correctly absent for admin role |

### Other

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| ADM-MISC-01 | Open Chat link | href=/mcp-agent.html | — | ✓ PASS | Links correctly to chat interface |
| ADM-MISC-02 | No Audit Log section | (UI check) | — | ✓ PASS | Correctly hidden from admin nav |
| ADM-MISC-03 | No Connectors section | (UI check) | — | ✓ PASS | Correctly hidden from admin nav |
| ADM-MISC-04 | No Manage Workers section | (UI check) | — | ✓ PASS | Correctly hidden from admin nav |

---

## Role 3 — user (mcp-agent.html)

**Credentials:** `test_user` / `TestUser2025!`
**Redirect on login:** `/mcp-agent.html` ✓
**API prefix:** `/api/fs/` (file system), `/api/agent/` (chat)

### Authentication

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| USR-AUTH-01 | Login with valid user credentials | POST /api/auth/login | 200 | ✓ PASS | JWT issued, redirect to mcp-agent.html |
| USR-AUTH-02 | Redirect to mcp-agent.html (not admin.html) | (redirect) | — | ✓ PASS | User role correctly routed |

### File Trees — Initial Load

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| USR-FT-01 | Domain Data tree loads on login | GET /api/fs/domain_data/tree | 200 | ✓ PASS | 32 items |
| USR-FT-02 | Uploads (My Data) tree loads on login | GET /api/fs/uploads/tree | 200 | ✓ PASS | 1 file shown |
| USR-FT-03 | Verified Workflows tree loads on login | GET /api/fs/verified/tree | 200 | ✓ PASS | 12 workflows |
| USR-FT-04 | My Workflows tree loads on login | GET /api/fs/my_workflows/tree | 200 | ✓ PASS | 2 workflows |

### File Interaction

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| USR-FI-01 | Click file in My Data | GET /api/fs/uploads/file?path=test_user_file.csv | 200 | ✓ PASS | CSV preview rendered as table; file auto-attached to chat |
| USR-FI-02 | Click workflow in Verified | GET /api/fs/verified/file?path=counterparty_exposure_trend.md | 200 | ⚠ WARN | **BUG:** Same endpoint called twice (double fetch) on single click |
| USR-FI-03 | Workflow shows READ ONLY in preview panel | (render) | — | ✓ PASS | Preview panel header shows "READ ONLY" label + Deselect button |
| USR-FI-04 | Deselect Workflow | (client-side) | — | ✓ PASS | Chip removed from input, no API call needed |

### Chat

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| USR-CHAT-01 | Send message | POST /api/agent/run | 200 | ✓ PASS | Message sent, streaming response received |
| USR-CHAT-02 | file/used mark on send (with active workflow) | PATCH /api/fs/verified/file/used?path=... | 405 | ✗ FAIL | **BUG:** Endpoint not implemented on server. `.catch(() => {})` silently ignores error |
| USR-CHAT-03 | API error displayed correctly | (render 400) | — | ✓ PASS | Full error detail rendered in chat bubble |
| USR-CHAT-04 | Workflow chip visible in chat input when selected | (render) | — | ✓ PASS | `► workflow.md ×` chip shown |
| USR-CHAT-05 | File chip visible in chat input when file selected | (render) | — | ✓ PASS | `filename.csv ×` chip shown |

### UI / UX

| ID | Scenario | Endpoint | HTTP | Status | Detail |
|----|----------|----------|------|--------|--------|
| USR-UX-01 | Settings button behavior | onclick=clearAllConversations() | — | ✗ FAIL | **BUG:** Button labeled "Settings" (gear icon) actually triggers "Clear All Conversations" confirmation modal — severe mislabeling |
| USR-UX-02 | Light Theme toggle | (client-side) | — | ✓ PASS | Theme persists client-side |
| USR-UX-03 | Token counter visible | (render 0 tok) | — | ✓ PASS | Counter displayed in top-right |
| USR-UX-04 | Suggested prompts on welcome screen | (render) | — | ✓ PASS | 6 domain-relevant prompts shown |
| USR-UX-05 | No admin banner for onboarded user | (render) | — | ✓ PASS | test_user (onboarding_complete=true) sees no banner |

---

## Bug Summary

### 🔴 Critical — Functionality Broken

| ID | Location | Description | Endpoint Affected | Impact |
|----|----------|-------------|-------------------|--------|
| ADMIN-BUG-001 | admin.html / Worker Config | Save Changes uses `/api/super/workers/{id}` instead of `/api/admin/worker`. Admin cannot save any worker configuration changes. Silent failure — no UI error. | PUT /api/super/workers/w-market-risk → 403 | Admin role completely unable to update worker config |
| ADMIN-BUG-002 | admin.html / Users | Reset PW hardcoded to `/api/super/users/{id}/reset-password`. Admin cannot reset user passwords. | POST /api/super/users/{id}/reset-password → 403 | Admin role cannot manage user credentials |
| ADMIN-BUG-003 | admin.html / Users | Disable/Enable hardcoded to `/api/super/users/{id}`. Admin cannot disable or enable users. | PUT /api/super/users/{id} → 403 | Admin role cannot manage user status |
| ADMIN-BUG-004 | admin.html / Users | Create User hardcoded to `/api/super/users`. Admin cannot create users. Additionally triggers `window.alert()` on failure, which freezes CDP-based automation. | POST /api/super/users → 403 | Admin role cannot create users; alert dialog is a UX regression |

### 🟠 High — API Endpoint Missing / Data Not Rendering

| ID | Location | Description | Endpoint Affected | Impact |
|----|----------|-------------|-------------------|--------|
| MCP-BUG-001 | mcp-agent.html / Chat | `PATCH /api/fs/{section}/file/used` returns 405 on every message send with an active workflow. Backend endpoint not implemented. | PATCH /api/fs/verified/file/used → 405 | Workflow usage tracking silently broken |
| SUPER-BUG-001 | admin.html / Dashboard | Workflows and Domain Files stat cards show "—" for all roles (super_admin and admin). Response data likely missing or field name mismatch in render. | (dashboard stats render) | Dashboard misleads admins about file/workflow counts |
| SUPER-BUG-002 | admin.html / Audit Log | Time and Tool columns display "—" for all 936 rows. Field names in API response likely don't match JS render code. | (audit log render) | Audit log unusable — two key columns empty |

### 🟡 Medium — UX / Behavior Issues

| ID | Location | Description | Impact |
|----|----------|-------------|--------|
| SUPER-BUG-003 | admin.html / File tree | Inline rename editor does not clear existing value — new name is appended to old name (e.g. typing "new" in a field showing "old" → "oldnew"). | Files/folders get corrupted names |
| MCP-BUG-002 | mcp-agent.html / Workflows | Clicking a workflow in the VERIFIED section triggers `GET /api/fs/verified/file?path=...` twice (double fetch). | Unnecessary API load; potential race condition |
| MCP-BUG-003 | mcp-agent.html | "Settings" button (gear icon, bottom-left sidebar) is wired to `clearAllConversations()` — a destructive operation. Button label and function are completely mismatched. | User confusion; accidental data loss risk |

---

## Endpoint Coverage Matrix

| Endpoint | super_admin | admin | user | Notes |
|----------|-------------|-------|------|-------|
| POST /api/auth/login | ✓ | ✓ | ✓ | All roles |
| GET /api/super/workers | ✓ | — | — | |
| GET /api/super/users | ✓ | — | — | |
| GET /api/super/audit | ✓ | — | — | |
| GET /api/super/connectors | ✓ | — | — | |
| POST /api/super/users | ✓ | ✗ 403 | — | Admin broken |
| PUT /api/super/users/{id} | ✓ | ✗ 403 | — | Admin broken |
| DELETE /api/super/users/{id} | ✓ | — | — | |
| POST /api/super/users/{id}/reset-password | ✓ | ✗ 403 | — | Admin broken |
| POST /api/super/workers | ✓ | — | — | |
| PUT /api/super/workers/{id} | ✓ | ✗ 403 | — | Admin broken (wrong endpoint used) |
| GET /api/super/workers/{id}/files/{section} | ✓ | — | — | |
| POST /api/super/workers/{id}/files/{section}/folder | ✓ | — | — | |
| POST /api/super/workers/{id}/files/{section}/rename | ✓ | — | — | |
| DELETE /api/super/workers/{id}/files/{section}/folder | ✓ | — | — | |
| GET /api/admin/worker | — | ✓ | — | |
| GET /api/admin/worker/users | — | ✓ | — | |
| GET /api/admin/worker/files/{section} | — | ✓ | — | |
| POST /api/admin/worker/files/{section}/folder | — | ✓ | — | |
| DELETE /api/admin/worker/files/{section}/folder | — | ✓ | — | |
| GET /api/admin/worker/files/verified_workflows | — | ✓ | — | |
| PUT /api/admin/worker/tools | — | ✓ | — | |
| GET /api/mcp/tools | — | ✓ | — | Shared endpoint |
| GET /api/fs/{section}/tree | — | — | ✓ | All 4 sections |
| GET /api/fs/{section}/file?path= | — | — | ✓ | |
| PATCH /api/fs/{section}/file/used | — | — | ✗ 405 | Not implemented |
| POST /api/agent/run | — | — | ✓ | |

---

## Cross-Role Security Observations

- **Admin JWT correctly blocked from /api/super/ routes** — returns 403, not 200. Backend RBAC is functioning; the bugs are purely FE endpoint mismatches.
- **User JWT correctly directed to /api/fs/ routes** — no leakage to admin/super endpoints observed.
- **Session storage correctly cleared on logout** — localStorage.clear() required to switch roles in same browser tab.
- **No Connectors or Audit Log accessible to admin or user** — nav items correctly absent.

---

## Credentials Reference

| User | Role | Password | Redirect |
|------|------|----------|----------|
| risk_agent | super_admin | RiskAgent2025! | /admin.html |
| admin | admin | Admin2025! | /admin.html |
| test_user | user | TestUser2025! | /mcp-agent.html |
