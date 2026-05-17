# RiskGPT Connector Admin UI — Test Report

**Date:** 2026-04-03
**Tester:** Claude Code
**Servers:** Agent (localhost:8000) + SAJHA MCP (localhost:3002) — both running

---

## Part 1: Implementation Summary

### Files Modified

| File | Change |
|------|--------|
| `/Users/saadahmed/Desktop/react_agent/public/admin.html` | Added Connectors nav item + section panel + JS |
| `/Users/saadahmed/Desktop/react_agent/agent_server.py` | Added 6 new API endpoints for connectors |

### New API Endpoints Added to agent_server.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/super/connectors` | super_admin | List all connectors with status (credentials redacted) |
| PUT | `/api/super/connectors/{type}` | super_admin | Create/update connector credentials |
| POST | `/api/super/connectors/{type}/test` | super_admin | Test connector reachability |
| GET | `/api/super/workers/{id}/connector-scope` | super_admin | Get worker connector scope |
| PUT | `/api/super/workers/{id}/connector-scope/{type}` | super_admin | Set worker connector scope |
| GET | `/api/admin/tools` | admin | List all SAJHA tools (proxied from SAJHA `/api/tools/list`) |

### Admin UI Changes (admin.html)

- **Nav item:** "Connectors" added to Super Admin nav section with link icon
- **Section panel** `#section-connectors` with 3 sub-tabs:
  - **Overview** — connector cards grid (Microsoft 365, Atlassian) with status badges, Configure + Test buttons
  - **Tool Library** — 36 connector tools (24 Microsoft + 12 Atlassian) with Read/Write badges, searchable
  - **Worker Mapping** — worker selector + scope form fields (Teams ID, SharePoint URL/SiteID, Power BI workspace, Outlook email, Confluence space, Jira project)
- **Configure modal** — Bootstrap-style slide-in overlay for each connector (Microsoft and Atlassian have different field sets)
- Auth pattern: reuses existing `authHeaders()` function and `_token` sessionStorage variable exactly as other sections do

---

## Part 2: Endpoint Test Results

### Authentication

| Test | Result | Notes |
|------|--------|-------|
| Login (risk_agent / RiskAgent2025!) | PASS | Returns JWT with super_admin role |
| Auth Me | PASS | Returns correct user metadata |
| Unauthenticated request to `/api/super/connectors` | PASS (401) | Returns `{"detail": "Missing token"}` |
| Rate limit on login | PASS (429-style) | 60s lockout after multiple attempts |

### Connector Endpoints

| Test | Result | Response |
|------|--------|----------|
| GET `/api/super/connectors` (empty state) | PASS | Returns both connectors as `not_configured` with correct tool counts (24, 12) |
| PUT `/api/super/connectors/microsoft_azure` | PASS | Saves credentials, returns `status: disconnected`, `has_credentials: true` |
| POST `/api/super/connectors/microsoft_azure/test` | PASS (expected fail) | Reaches MS login endpoint, returns HTTP 400 (invalid test tenant). Network reachability confirmed. |
| POST `/api/super/connectors/atlassian/test` (unconfigured) | PASS | Returns `{"ok": false, "message": "Connector not configured. Save credentials first."}` |
| GET `/api/super/connectors` (after save) | PASS | microsoft_azure shows `disconnected` + `has_credentials: true`; atlassian still `not_configured` |
| PUT invalid connector type | PASS (400) | Returns `{"detail": "Unknown connector type: ..."}` |

### Worker Connector Scope Endpoints

| Test | Result | Response |
|------|--------|----------|
| GET `/api/super/workers/w-market-risk/connector-scope` (empty) | PASS | Returns `{"connector_scope": {}}` |
| PUT microsoft_azure scope | PASS | Persisted `teams_team_id`, `sharepoint_site_url`, `powerbi_workspace_id`, `outlook_user_email` |
| GET scope after save | PASS | All 4 fields correctly returned |
| PUT atlassian scope | PASS | Persisted `confluence_space_key: "RISK"`, `jira_project_key: "CCR"` |
| GET unknown worker | PASS (404) | Returns `{"detail": "Worker not found"}` |

### File System Endpoints

| Test | Result | Notes |
|------|--------|-------|
| GET `/api/fs/uploads/tree` | PASS | Returns tree rooted at `data/workers/w-market-risk/my_data/risk_agent` (correct user scoping) |
| GET `/api/workspace/files` | PASS | Returns user's own files (same directory) |
| POST `/api/files/upload` | PASS | File uploaded to `data/workers/w-market-risk/my_data/risk_agent/test_upload_20260403_234347.txt` |
| Verify uploaded file in tree | PASS | `test_upload.txt` and timestamped version both visible in `/api/fs/uploads/tree` |

### Workflow Endpoints

| Test | Result | Notes |
|------|--------|-------|
| GET `/api/workflows` | PASS | Returns 3+ workflows (counterparty_intelligence.md, op_risk_controls.md, etc.) |
| POST `/api/workflows` (create) | PASS | `{"filename": "test_connector_workflow.md", "ok": true}` |
| DELETE `/api/workflows/test_connector_workflow.md` | PASS | `{"ok": true}` |

### Worker / User Admin Endpoints

| Test | Result | Notes |
|------|--------|-------|
| GET `/api/super/workers` | PASS | Returns 4 workers (w-market-risk, w-e74b5836, w-bb745fb7, w-d2acce9c) |
| GET `/api/super/users` | PASS | Returns all users with hashed passwords (risk_agent, admin, etc.) |
| GET `/api/admin/worker` | PASS | Returns current worker for authenticated user |

### Tool Endpoints

| Test | Result | Notes |
|------|--------|-------|
| GET `/api/mcp/tools` | PASS | Returns 121 tools from SAJHA |
| GET `/api/admin/tools` (initial — wrong path) | FAIL (404) | Initial implementation used `/api/tools` instead of `/api/tools/list` |
| GET `/api/admin/tools` (after fix) | PASS | Returns 121 tools via SAJHA `/api/tools/list` proxy |

---

## Part 3: Issues Found and Fixed

### Bug 1: `/api/admin/tools` wrong SAJHA path
- **Root cause:** Implementation used `/api/tools` but SAJHA exposes the list at `/api/tools/list`
- **Fix:** Updated `agent_server.py` line 2204 to use `/api/tools/list`
- **Status:** FIXED

### Note: Microsoft connector test returns HTTP 400
- **Expected behavior:** Test used a dummy tenant ID `test-tenant-123`
- **Actual behavior:** MS `https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration` returns 400 for invalid tenant UUIDs
- **Status:** Correct behavior — with a real tenant UUID this would return 200

---

## Part 4: UI Patterns Verified

The implementation follows the exact patterns in the existing `admin.html`:

- **Auth:** Uses `authHeaders()` (reuses `_token` from sessionStorage) — same as all other fetch calls
- **Toast notifications:** Uses `showToast(msg, type)` with `success`/`error` types — identical to other sections
- **Modal:** Uses same `modal-overlay hidden` pattern but with a dedicated `conn-modal-overlay` to avoid interfering with the existing shared modal used by Create User / Create Worker
- **CSS:** No new CSS classes introduced; reuses `form-row`, `form-input`, `form-label`, `btn`, `btn-primary`, `btn-secondary`, `section-header`, `section-title`, `section-sub`, `stat-card`, `nav-item` — all defined in the `<style>` block
- **Nav section label:** Added under "Super Admin" section (only visible to super_admin role via `super-nav` div)
- **Section registration:** `showSection('connectors')` handler added to the switch statement in `showSection()` function

---

## Summary

| Category | Passed | Failed |
|----------|--------|--------|
| Authentication | 4/4 | 0 |
| Connector endpoints | 6/6 | 0 |
| Worker scope endpoints | 5/5 | 0 |
| File system | 4/4 | 0 |
| Workflows | 3/3 | 0 |
| Workers/Users | 3/3 | 0 |
| Tools (after fix) | 2/2 | 0 |
| **Total** | **27/27** | **0** |

All endpoints passed. One bug found and fixed during testing (wrong SAJHA tools path).
