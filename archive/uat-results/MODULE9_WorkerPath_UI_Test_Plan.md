# Module 9 — Worker Path Architecture UI Test Plan
**Status:** Ready for execution
**Date:** 2026-04-03
**Scope:** UI validation of all changes in `RiskGPT_Worker_Path_Architecture_Requirements.md`
**Roles covered:** super_admin (`risk_agent`), admin (`admin`), user (`test_user`)
**Servers:** Agent Server :8000 + SAJHA MCP :3002

---

## Summary of Changes Being Tested

| Area | What Changed | REQ |
|------|-------------|-----|
| Section key | `verified_workflows` now recognised in all file endpoints | WF-02 |
| Super admin resolver | All 9 super admin file endpoints now use `_admin_section_roots_for_worker()` — blocks `my_data`, `common` | WF-03, API-01 |
| Admin resolver expanded | `my_workflows` added as third admin-accessible section | WF-03 |
| Clone isolation fix | `ignore_patterns('my_data')` now correctly excludes the full `my_data` tree from clones | MD-01 |
| operational_tools.py | `_domain_root()`, `_my_data_root()`, `_templates_dir()` now worker-context-aware | API-02 |
| Tool header | `X-Worker-My-Data-Root` injects `{my_data_path}/{user_id}` — per-user sub-path | MD-01 |
| Data: domain_data | `osfi/`, `duckdb/`, `sqlselect/`, `Test/`, `templates/` copied to `w-market-risk/domain_data/` | DD-01 |
| Data: my_data | `data/uploads/` content copied to `w-market-risk/my_data/risk_agent/` | DD-02 |
| application.properties | All fallback paths updated to MR worker-scoped directories | DD-01/02 |
| Global directories | `data/workflows/verified/` (12 files) and `data/domain_data/` (original) still exist — to be retired after verification | WF-01 |

---

## Role Matrix

| Feature | super_admin (risk_agent) | admin (admin) | user (test_user) |
|---------|-------------------------|---------------|-----------------|
| Open admin.html | ✓ Full super admin panel | ✓ Own worker panel | ✗ Redirected to chat |
| See "All Workers" grid | ✓ | ✗ | ✗ |
| Worker selector dropdown | ✓ (all workers) | ✗ | ✗ |
| Browse `domain_data` | ✓ any worker | ✓ own worker | ✗ |
| Browse `verified_workflows` | ✓ any worker | ✓ own worker | ✗ |
| Browse `my_data` | ✗ blocked (HTTP 400) | ✗ blocked | ✗ |
| Browse `common_data` | ✗ not exposed in UI | ✗ not exposed | ✗ |
| Upload to `domain_data` | ✓ | ✓ | ✗ |
| Upload to `verified_workflows` | ✓ | ✓ | ✗ |
| Create/delete workers | ✓ | ✗ | ✗ |
| Audit log | ✓ | ✗ | ✗ |

---

## Module 9A — File Tree: Super Admin (risk_agent)

> Open `admin.html`, log in as `risk_agent / RiskAgent2025!`

### PA-01 — MR worker Domain Data tree shows migrated subdirectories

**Steps:**
1. Log in as super_admin → admin.html loads with "Market Risk Worker" badge
2. Navigate to **Domain Data** in left nav
3. Expand the file tree

**Expected:**
- Tree root contains at minimum: `counterparties/`, `duckdb/`, `iris/`, `osfi/`, `sqlselect/`, `analytics/`, `market_data/`, `Test/`
- `duckdb/` folder expands to show `duckdb_analytics.db`, `customers.csv`, `orders.csv`, `products.csv`
- `osfi/` folder expands to show `CAR_2026/`, `LAR_2026/`, `B13_tech_cyber.md`, `README.md`
- `sqlselect/` folder expands to show `customer_data.csv`, `inventory_data.csv`, `sales_data.csv`
- `iris/` folder shows `iris_combined.csv` (critical — tools depend on this)

**Validates:** REQ-DD-01 (migration complete), REQ-WF-03 (correct resolver)

---

### PA-02 — MR worker Verified Workflows tree shows 12 workflows

**Steps:**
1. Navigate to **Workflows** in left nav (MR worker context)
2. View verified_workflows file tree

**Expected:**
- Exactly 12 `.md` files visible:
  - counterparty_exposure_trend.md, counterparty_intelligence.md, cpty_intelligence_new_tools.md, data_file_analysis.md, data_quality_report.md, financial_institution_credit_profile.md, limit_breach_escalation.md, market_credit_intelligence.md, op_risk_controls.md, op_risk_kri_monitoring.md, osfi_regulatory_watch.md, portfolio_concentration_report.md
- No "Error loading tree" or "Unknown admin section" message
- Each file shows correct size and last-modified date

**Validates:** REQ-WF-02 (section key fix), REQ-WF-01 (worker-scoped path used — not global fallback)

---

### PA-03 — Switch to CCR worker — verified_workflows is empty (not MR fallback)

**Steps:**
1. Click worker selector dropdown (top of admin panel) → select **CCR Agent**
2. Navigate to **Workflows**

**Expected:**
- File tree shows "Empty" or shows only index (no `.md` workflow files)
- **Does NOT show the 12 MR workflows** — tree is worker-scoped
- No error message, no loading spinner stuck

**Validates:** REQ-WF-05 (CCR intentionally empty, graceful state), REQ-WF-03 (no cross-worker leakage)

---

### PA-04 — CCR worker Domain Data is isolated from MR domain data

**Steps:**
1. Remain on CCR Agent worker context
2. Navigate to **Domain Data**

**Expected:**
- CCR domain data (`w-e74b5836/domain_data/`) is shown — NOT the MR worker data
- No `iris/iris_combined.csv`, `counterparties/`, `osfi/` etc. visible (CCR domain_data is sparse)
- Switching back to MR worker shows MR data again

**Validates:** REQ-WF-05, REQ-WF-03 (per-worker resolution), REQ-API-01 (no cross-worker file access)

---

### PA-05 — my_data section is NOT accessible via admin panel file tree

**Steps:**
1. In browser DevTools → Network tab
2. Manually trigger `GET /api/super/workers/w-market-risk/files/my_data` (or attempt via URL bar)

**Expected:**
- API returns HTTP 400 `{"detail":"Unknown admin section: my_data. Admin-accessible: domain_data, my_workflows, verified_workflows"}`
- The admin panel nav has **no "My Data" link** or editable file tree entry
- No way to browse `w-market-risk/my_data/risk_agent/` from admin panel

**Validates:** REQ-MD-01 (my_data is user-owned, not admin-editable), REQ-WF-03

---

### PA-06 — common_data NOT exposed as editable file tree in admin panel

**Steps:**
1. Inspect admin.html nav — verify no "Common Data" or "Regulatory" editable section
2. Try API: `GET /api/super/workers/w-market-risk/files/common` (via DevTools)

**Expected:**
- API returns HTTP 400 (not in admin resolver whitelist)
- No nav entry for `common_data` in left sidebar
- `data/common/regulatory/` content not browsable via any admin UI control

**Validates:** REQ-CD-01 (common_data is read-only, platform-managed)

---

### PA-07 — Upload via button to domain_data (MR worker)

**Steps:**
1. MR worker context → **Domain Data**
2. Click **↑ Upload** button
3. Select a test file (e.g. a small `.csv`)

**Expected:**
- File appears in the domain_data tree after upload
- Toast notification: "Uploaded: `filename.csv`"
- File path is under `w-market-risk/domain_data/`, not `data/domain_data/`

**Validates:** REQ-WF-03 (upload uses admin resolver), REQ-DD-01

---

### PA-08 — Upload via drag-drop (external file) to domain_data

**Steps:**
1. MR worker context → **Domain Data** tree pane
2. Drag a file from Finder and drop onto the domain_data tree pane
3. Observe drop-active visual (dashed border highlights the pane)

**Expected:**
- `drop-active` CSS applied while file is held over the pane
- File is uploaded to `w-market-risk/domain_data/`
- Toast shows progress or completion
- Tree refreshes and shows the new file

**Validates:** AP-04 (external drop zone from Phase 3), REQ-WF-03

---

### PA-09 — Upload via drag-drop to verified_workflows

**Steps:**
1. Navigate to **Workflows**
2. Drag a `.md` file from Finder and drop onto the verified_workflows pane

**Expected:**
- File is uploaded to `w-market-risk/workflows/verified/`
- Tree refreshes showing new workflow
- Toast confirms upload

**Validates:** AP-04, REQ-WF-02 (verified_workflows section key works for upload)

---

### PA-10 — File operations (rename, move, delete) on verified_workflows

**Steps:**
1. Upload a test file `_test_wf.md` to verified_workflows
2. Double-click the file name → inline rename input appears (AP-05)
3. Rename to `_test_wf_renamed.md` → Enter
4. Right-click the file → context menu appears (AP-06) → select Rename
5. Rename back to `_test_wf.md`
6. Drag `_test_wf.md` onto the tree root or a subfolder → move works (AP-07)
7. Delete via context menu → confirm in modal (AP-08 style)

**Expected:**
- All operations succeed via `verified_workflows` section key
- No HTTP 400 "Unknown admin section" errors
- Tree refreshes correctly after each operation

**Validates:** REQ-WF-02/03, AP-05/06/07

---

### PA-11 — Audit log shows correct worker-scoped events

**Steps:**
1. Navigate to **Audit Log** (super admin nav)
2. Note total count displayed in pagination (`X–Y of Z`)
3. Filter by worker → select "Market Risk Worker"
4. Click Next → page advances (AP-13)

**Expected:**
- Pagination shows `1–200 of {total}` (hides if total ≤ 200)
- Filter narrows results correctly
- Next/Prev buttons are enabled/disabled based on page position
- Entries reference `w-market-risk` worker_id

**Validates:** AP-12/13 (already passing — regression check), REQ-WF-03 (audit tied to worker context)

---

## Module 9B — File Tree: Admin Role

> Open `admin.html`, log in as `admin / Admin2025!`

### PB-01 — Admin panel loads with own worker (no worker selector)

**Steps:**
1. Log in as `admin` → admin.html
2. Observe header / sidebar

**Expected:**
- "Market Risk Worker" badge shown (admin is assigned to MR worker)
- **No worker selector dropdown** (admin can only see own worker)
- **No "All Workers" grid**
- **No SUPER ADMIN nav section**
- Sidebar shows: Dashboard, Worker Config, Tools, Domain Data, Workflows, Users

**Validates:** AP-01 (admin view), REQ-WF-03 (admin uses own resolver)

---

### PB-02 — Admin Domain Data tree shows migrated data

**Steps:**
1. Admin panel → **Domain Data**

**Expected:**
- Same tree as PA-01 (since admin is on MR worker): `counterparties/`, `duckdb/`, `iris/`, `osfi/`, `sqlselect/`, etc.
- API call goes to `/api/admin/worker/files/domain_data` (not super endpoint)

**Validates:** REQ-DD-01, REQ-WF-03 (admin resolver returns same paths as super admin for their worker)

---

### PB-03 — Admin Verified Workflows shows 12 workflows

**Steps:**
1. Admin panel → **Workflows**

**Expected:**
- All 12 verified workflow files visible
- API call goes to `/api/admin/worker/files/verified_workflows`
- No error messages

**Validates:** REQ-WF-02 (admin endpoint also uses correct section key)

---

### PB-04 — Admin cannot access super-admin endpoints (403 enforcement)

**Steps:**
1. In DevTools Network tab, attempt: `GET /api/super/workers/w-market-risk/files/domain_data` with admin JWT

**Expected:**
- HTTP 403 Forbidden
- Admin panel has no navigation path to super admin per-worker file endpoints

**Validates:** REQ-API-01 (role-based access control), S-10 (already in Phase 1 — regression check)

---

### PB-05 — Admin upload to own worker's domain_data

**Steps:**
1. Admin panel → Domain Data → **↑ Upload** → select a test file

**Expected:**
- File uploaded to `w-market-risk/domain_data/`
- API call: `POST /api/admin/worker/files/domain_data/upload`
- Tree refreshes, file appears

**Validates:** REQ-WF-03 (admin resolver used for mutations), REQ-DD-01

---

### PB-06 — Admin cannot see or upload to my_data or common_data

**Steps:**
1. Inspect admin panel nav — confirm no "My Data" or "Common Data" section
2. Try via DevTools: `GET /api/admin/worker/files/my_data` with admin JWT

**Expected:**
- HTTP 400 (my_data not in `_admin_section_roots_for_worker` for admin endpoints)
- No nav entry in admin panel for these sections

**Validates:** REQ-MD-01, REQ-CD-01

---

## Module 9C — File Tree: User Role

> Open `admin.html`, log in as `test_user / TestUser2025!`

### PC-01 — User is redirected away from admin.html

**Steps:**
1. Navigate to `admin.html` as `test_user`

**Expected:**
- Immediate redirect to `mcp-agent.html` (chat UI)
- No admin panel content shown
- No admin-console-banner visible

**Validates:** AP-14 (already passing — regression check)

---

### PC-02 — User chat with MR worker correctly reads worker-scoped domain data

**Steps:**
1. Open `mcp-agent.html` as `test_user` (MR worker context)
2. Send query: "List the OSFI documents available"
3. Send query: "What DuckDB tables are available?"
4. Send query: "Show me the IRIS counterparty dates"

**Expected:**
- `osfi_list_docs` returns files from `w-market-risk/domain_data/osfi/` (not empty)
- `duckdb_list_tables` reflects tables from `w-market-risk/domain_data/duckdb/duckdb_analytics.db`
- `iris_list_dates` reads from `w-market-risk/domain_data/iris/iris_combined.csv`
- **None of these fall back to global `data/domain_data/` path**

**Validates:** REQ-DD-01 (data migration complete), REQ-API-02 (operational_tools worker-context-aware)

---

### PC-03 — User my_data is isolated per user (REQ-MD-01)

**Steps:**
1. As `test_user`, run an agent query that saves output: "Run a counterparty intelligence analysis for Goldman Sachs and save it"
2. Observe where `md_save` writes the file
3. As `risk_agent`, confirm the file is NOT visible in risk_agent's my_data

**Expected:**
- `md_save` writes to `w-market-risk/my_data/test_user/` (the authenticated user's sub-path)
- `risk_agent`'s my_data (`w-market-risk/my_data/risk_agent/`) is not affected
- `X-Worker-My-Data-Root` header for test_user = `./data/workers/w-market-risk/my_data/test_user`

**Validates:** REQ-MD-01 (per-user isolation), REQ-API-02

---

### PC-04 — User can read their own uploaded files

**Steps:**
1. As `risk_agent`, confirm `list_uploaded_files` shows files in `my_data/risk_agent/`
2. Switch to `test_user`, run `list_uploaded_files`

**Expected:**
- `risk_agent` sees their files in `my_data/risk_agent/` (migrated from data/uploads/)
- `test_user` sees empty list (or only their own files from `my_data/test_user/`)
- Neither can see the other's files

**Validates:** REQ-MD-01, REQ-DD-02

---

## Module 9D — Data Migration Verification (via chat tools)

### PD-01 — OSFI tools read from MR worker domain_data (not global)

**Steps:**
1. As `risk_agent` in chat (MR worker)
2. Query: "What OSFI CAR documents are available? List them."

**Expected:**
- `osfi_list_docs` returns files from `w-market-risk/domain_data/osfi/`
- Response shows: `CAR_2026/CAR_2026_ch2_credit_risk.md`, `CAR_2026/CAR_2026_overview.md`, `LAR_2026/LAR_2026_overview.md`, `B13_tech_cyber.md`
- Source in response: `[src:data/workers/w-market-risk/domain_data/osfi/...]`

**Validates:** REQ-DD-01, REQ-API-02 (osfi_tools uses worker_data_root header)

---

### PD-02 — DuckDB queries target MR worker database

**Steps:**
1. As `risk_agent` in chat (MR worker)
2. Query: "List all tables in the analytics database"
3. Query: "Show the first 5 rows of the customers table"

**Expected:**
- `duckdb_list_tables` returns tables from `w-market-risk/domain_data/duckdb/duckdb_analytics.db`
- Data is correct (customers, orders, products tables)
- Source: `[src:data/workers/w-market-risk/domain_data/duckdb/...]`

**Validates:** REQ-DD-01 (duckdb migrated), application.properties updated

---

### PD-03 — IRIS CCR data reads from MR worker iris path

**Steps:**
1. As `risk_agent` in chat
2. Query: "List available IRIS CCR dates"

**Expected:**
- Returns dates: 2026-02-27, 2026-03-26, 2026-03-27
- Data sourced from `w-market-risk/domain_data/iris/iris_combined.csv`
- Not the legacy `data/domain_data/iris/iris_combined.csv`

**Validates:** REQ-DD-01, iris_ccr_tools worker-context path (already compliant)

---

### PD-04 — Workflow tool reads from MR worker workflows path

**Steps:**
1. As `risk_agent` in chat
2. Query: "List all available verified workflows"

**Expected:**
- `workflow_list` returns 12 workflows from `w-market-risk/workflows/verified/`
- Titles include: Counterparty Exposure Trend, Counterparty Intelligence, etc.
- **NOT from legacy `data/workflows/verified/`**

**Validates:** REQ-WF-01 (legacy path not used), workflow_tools worker-context-aware

---

### PD-05 — md_save writes to user-scoped my_data path

**Steps:**
1. As `risk_agent` in chat
2. Run: "Save a simple test note with today's date to my files"

**Expected:**
- `md_save` writes file to `w-market-risk/my_data/risk_agent/` (with `risk_agent` = authenticated user_id)
- File visible via `list_uploaded_files` tool
- Source path: `data/workers/w-market-risk/my_data/risk_agent/...`

**Validates:** REQ-DD-02, REQ-MD-01, REQ-API-02 (_my_data_root worker-aware)

---

## Module 9E — Worker Clone Isolation

### PE-01 — Cloned worker has empty my_data

**Steps:**
1. Super admin panel → Manage Workers → Create new worker with **Clone from: Market Risk Worker**
2. After creation, inspect the new worker's domain_data and my_data directories

**Expected:**
- New worker `domain_data/` is a copy of MR domain_data (12 subdirs including osfi, duckdb, etc.)
- New worker `my_data/` is **empty** — no `risk_agent/` subdirectory, no files copied
- Worker system prompt is cloned from MR

**Validates:** REQ-MD-01 (my_data is user-owned, not cloned), `_clone_worker_folder` fix

---

### PE-02 — Clone worker domain_data is independent

**Steps:**
1. Using the clone from PE-01
2. Upload a file to clone's `domain_data`
3. Verify the file does NOT appear in MR worker's `domain_data`

**Expected:**
- Clone has its own isolated domain_data tree
- No cross-worker bleed

**Validates:** REQ-WF-03 worker path isolation

---

## Module 9F — Admin Panel Gaps (Phase 3 Extensions)

> These extend the existing Phase 3 Module 8 tests

### PF-01 — File tree shows all 3 verified admin sections (domain_data, verified_workflows)

**Steps:**
1. Admin panel (either role) → check the "Data & Workflows" nav section

**Expected:**
- "Domain Data" nav link → loads domain_data file tree
- "Workflows" nav link → loads verified_workflows file tree
- Both sections load without errors
- There is NO "My Data" or "Common" nav entry

**Validates:** REQ-WF-02/03, REQ-MD-01, REQ-CD-01

---

### PF-02 — File preview works for new domain_data files (osfi .md)

**Steps:**
1. Admin panel → Domain Data → navigate to `osfi/` → click `B13_tech_cyber.md`

**Expected:**
- Preview pane shows rendered markdown (headings, bold, tables via GFM renderer)
- File is loaded from `w-market-risk/domain_data/osfi/B13_tech_cyber.md`

**Validates:** AP-09 (markdown preview), REQ-DD-01 (osfi files accessible in tree)

---

### PF-03 — File preview for .xlsx in domain_data (duckdb or Test folder)

**Steps:**
1. Admin panel → Domain Data → navigate to Test folder → click `test_trades.parquet` (or upload a test .xlsx)

**Expected:**
- If `.xlsx`: preview shows sheet tabs and HTML table (AP-10)
- File path confirms it's in MR domain_data

**Validates:** AP-10, REQ-DD-01

---

### PF-04 — Bulk delete in domain_data works end-to-end

**Steps:**
1. Upload 2–3 test files to domain_data
2. Click **Select** mode → check 3 files
3. Click **Delete 3** → `showModal()` confirmation dialog appears (not `window.confirm`)
4. Confirm → files deleted

**Expected:**
- Custom modal (not browser confirm dialog) — AP-08 fix validated
- All 3 files removed from tree
- Index rebuilt correctly

**Validates:** AP-08 (showModal fix), REQ-WF-03 (delete uses admin resolver)

---

### PF-05 — Inline rename works on both file tree sections

**Steps:**
1. Admin panel → Domain Data → double-click a filename → inline input appears
2. Type new name → Enter → name changes
3. Navigate to Workflows → double-click a workflow file → inline input appears
4. Press Escape → rename cancelled, original name preserved

**Expected:**
- Inline input replaces the name span in both sections
- Enter commits, Escape cancels
- API call uses `verified_workflows` section key for step 3 (not `verified`)

**Validates:** AP-05 (inline rename), REQ-WF-02 (correct section key in rename calls)

---

### PF-06 — Context menu appears on both sections, Delete uses correct section key

**Steps:**
1. Admin panel → Workflows → right-click on a workflow file
2. Context menu shows: Preview, Rename, Download, Delete (danger)
3. Click Delete → modal confirmation
4. Confirm delete

**Expected:**
- Context menu appears (not native browser menu)
- Delete calls `DELETE /api/super/workers/{id}/files/verified_workflows/file` (not `verified`)
- File is removed from tree

**Validates:** AP-06 (context menu), REQ-WF-02 (section key in delete)

---

### PF-07 — External drag-drop to verified_workflows pane

**Steps:**
1. Admin panel → Workflows tree pane visible
2. Drag a `.md` file from Finder onto the workflows pane (not a tree item — the pane itself)

**Expected:**
- `drop-active` CSS highlights the pane (dashed border overlay)
- File is uploaded to `w-market-risk/workflows/verified/`
- Toast confirms upload
- Tree refreshes showing new file

**Validates:** AP-04 (drop zone), REQ-WF-02 (verified_workflows upload works)

---

### PF-08 — Pagination visible when audit log has > 200 entries

**Steps:**
1. Super admin → Audit Log
2. Verify total entry count

**Expected:**
- If total > 200: pagination div visible (`audit-pagination` shown, not `display:none`)
- Shows `1–200 of {total}`
- Next button enabled, Prev button disabled on first page
- Click Next → loads entries 201–400

**Validates:** AP-13 (pagination — already passing, regression check)

---

## Module 9G — Retirement Readiness Check

> These verify the system is ready for global path retirement (not yet executed)

### PG-01 — Legacy global verified_workflows directory can be safely deleted

**Pre-condition:** PA-02 passes (MR worker shows 12 workflows from worker-scoped path)

**Verification (manual, DO NOT EXECUTE yet):**
- Confirm `data/workflows/verified/` has 12 files — all duplicated in `w-market-risk/workflows/verified/`
- Confirm no code path in agent_server.py references `data/workflows/verified/` as default for any worker
- Confirm `_ADMIN_SECTION_ROOTS['verified_workflows']` still points to global (legacy use for old admin endpoint only)
- **Action when ready:** `rm -rf sajhamcpserver/data/workflows/verified/` and `data/workflows/my/`

**Validates:** REQ-WF-01, REQ-WF-04 readiness

---

### PG-02 — Legacy global domain_data directory can be safely deleted

**Pre-condition:** PD-01, PD-02, PD-03 all pass (tools read from MR worker path)

**Verification (manual, DO NOT EXECUTE yet):**
- Confirm `data/domain_data/{osfi,duckdb,sqlselect,iris,counterparties,templates,Test}/` are all present in `w-market-risk/domain_data/`
- Confirm all tools read from worker-scoped path when worker context is active
- Confirm no test or tool references `data/domain_data/` directly when called through the agent server
- **Action when ready:** `rm -rf sajhamcpserver/data/domain_data/`

**Validates:** REQ-DD-01 readiness

---

### PG-03 — Legacy global uploads directory can be safely deleted

**Pre-condition:** PD-05 passes (md_save writes to user-scoped my_data)

**Verification (manual, DO NOT EXECUTE yet):**
- Confirm `data/uploads/{company_briefs,counterparty_briefs,charts,exports,reports}` are in `w-market-risk/my_data/risk_agent/`
- Confirm `list_uploaded_files` returns files from worker-scoped path
- **Action when ready:** `rm -rf sajhamcpserver/data/uploads/`

**Validates:** REQ-DD-02 readiness

---

## Known Remaining Gaps (Not Addressed in This Sprint)

| Gap | Notes | REQ |
|-----|-------|-----|
| `my_workflows` section absent from admin panel UI | API supports it (`_admin_section_roots_for_worker` includes it) but no nav link or file tree pane in admin.html | WF-03 |
| DuckDB / SQLSelect tools not worker-context-aware | These tools read `data_directory` from tool JSON config or properties at startup — not per-request. The `application.properties` fallback was updated to MR worker paths. A deeper fix requires per-request config injection into these tool classes. | API-02 |
| common_data tools (osfi_tools reads from domain_data) | OSFI docs are currently in `w-market-risk/domain_data/osfi/` per REQ-DD-01 note. Future decision: if CCR worker also needs OSFI, move to `data/common/regulatory/osfi/`. | CD-01 |
| `data/common/regulatory/` subdirs are empty | Structure exists but no documents loaded. Platform team decision required. | CD-01 |
| `saad` vs `risk_agent` user_id in my_data | Requirements doc says `my_data/saad/` but actual system user_id is `risk_agent`. Migration used `risk_agent`. If a `saad` user is created in future, their my_data will be at `my_data/saad/`. | MD-01 |
| Global `_ADMIN_SECTION_ROOTS` still points to global `_VERIFIED_WF` | Used only by deprecated `_resolve_admin_path()` (for old global admin endpoint). Will be cleaned up when global directories are retired. | WF-01 |

---

## Execution Checklist

```
[ ] PA-01  MR domain_data tree — migrated subdirs visible
[ ] PA-02  MR verified_workflows — 12 workflows visible
[ ] PA-03  CCR verified_workflows — empty (no MR fallback)
[ ] PA-04  CCR domain_data — isolated from MR
[ ] PA-05  my_data section blocked in admin file endpoints
[ ] PA-06  common_data not exposed in admin panel UI
[ ] PA-07  Upload via button to domain_data
[ ] PA-08  Upload via drag-drop to domain_data
[ ] PA-09  Upload via drag-drop to verified_workflows
[ ] PA-10  File ops (rename, move, delete) on verified_workflows
[ ] PA-11  Audit log pagination (regression)
[ ] PB-01  Admin panel loads (own worker, no super admin nav)
[ ] PB-02  Admin domain_data shows migrated data
[ ] PB-03  Admin verified_workflows shows 12 workflows
[ ] PB-04  Admin cannot access super admin endpoints
[ ] PB-05  Admin upload to own domain_data
[ ] PB-06  Admin cannot access my_data or common_data
[ ] PC-01  User redirected from admin.html
[ ] PC-02  User chat reads worker-scoped domain data (osfi, duckdb, iris)
[ ] PC-03  User my_data is isolated per user
[ ] PC-04  User list_uploaded_files shows their own files only
[ ] PD-01  OSFI tools read from MR worker domain_data
[ ] PD-02  DuckDB queries target MR worker database
[ ] PD-03  IRIS CCR reads from MR worker iris path
[ ] PD-04  workflow_list returns from MR worker verified path
[ ] PD-05  md_save writes to user-scoped my_data
[ ] PE-01  Clone worker has empty my_data
[ ] PE-02  Clone domain_data is independent of source
[ ] PF-01  Nav shows domain_data + verified_workflows only (no my_data/common)
[ ] PF-02  File preview for .md in osfi subfolder
[ ] PF-03  File preview for .xlsx in domain_data
[ ] PF-04  Bulk delete via showModal (not window.confirm)
[ ] PF-05  Inline rename on both sections
[ ] PF-06  Context menu delete uses correct section key
[ ] PF-07  External drag-drop to verified_workflows
[ ] PF-08  Audit log pagination regression check
[ ] PG-01  Retirement readiness: global workflows verified (manual)
[ ] PG-02  Retirement readiness: global domain_data (manual)
[ ] PG-03  Retirement readiness: global uploads (manual)
```

**Total:** 39 test cases — 36 executable now, 3 retirement readiness checks (manual/deferred)

---

*Document generated: 2026-04-03 | Based on RiskGPT_Worker_Path_Architecture_Requirements.md*
