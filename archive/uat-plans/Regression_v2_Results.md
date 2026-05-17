# Regression v2 — Playwright UAT Results

**Date:** 2026-04-05  
**Tester:** Automated Playwright (headless Chrome 146)  
**Script:** `uat_plans/run_regression_v2_tests.mjs`  
**Server:** `uvicorn agent_server:app --port 8000` + SAJHA MCP on port 3002  
**Auth:** `risk_agent` / `RiskAgent2025!` (role: super_admin)

---

## Summary

| Status | Count |
|--------|-------|
| ✅ PASS | 14 |
| ❌ FAIL | 0 |
| ⚠️ SKIP | 0 |
| **Total** | **14** |

All 14 tests pass. This suite covers the gaps identified after the v1 UI Audit regression — areas that were either logged as open bugs, marked INFO/not-automatable, or simply never had test coverage.

---

## Scope — What This Suite Adds

| Area | Prior Status | v2 Coverage |
|------|-------------|-------------|
| Python sandbox timeout | FAIL (dylib bug) | ✅ Fixed + verified |
| Sidebar upload toast | FAIL (BUG-010) | ✅ Already fixed; confirmed |
| Chat file attach | INFO / not automatable | ✅ Automated via `setInputFiles()` |
| User CRUD (create/edit/delete) | Buttons confirmed present only | ✅ Full end-to-end API roundtrip |
| Worker create | Grid confirmed, no create test | ✅ Modal → grid → API verify → cleanup |
| Conversation delete/rename | Buttons confirmed present only | ✅ Function-level + state verified |
| CSV sheet preview | Not tested | ✅ sheet-viewer-panel + SheetJS table |
| XLSX admin preview | Not tested | ✅ `_adminPreviewExcel` renders table |
| Page error check | Separate suite | ✅ Covered in both suites |

---

## Test Results

### PY-007 — Python Sandbox Timeout

| Test | Status | Evidence |
|------|--------|----------|
| PY-007 | ✅ PASS | `timed_out=true`, `elapsed=2.01s` (2s timeout on 10s `time.sleep`) |

**Root cause of prior failure:** `libmpdec.4.dylib` was missing from Homebrew after a Homebrew upgrade removed the old `mpdecimal` version. The Python 3.13 sandbox venv links `_decimal.cpython-313-darwin.so` against this library, causing any Python subprocess to crash at startup.

**Resolution:** `mpdecimal` was reinstalled (`libmpdec.4.dylib` now present at `/opt/homebrew/opt/mpdecimal/lib/`). No code change required.

**Test method:** Direct call to `_run_sandboxed('import time; time.sleep(10)', tmpdir, timeout=2)` via `python3 -c` subprocess from Node.js `execSync`. Confirms the timeout mechanism works end-to-end without an LLM call.

---

### BUG-010 — Sidebar Upload Toast

| Test | Status | Evidence |
|------|--------|----------|
| BUG-010 | ✅ PASS | Toast: `"Uploaded uat_toast_test.txt"` |

**Prior status:** Logged as BUG in `Functional_Test_Results.md` (B-113). The original test was run before BPulseFileTree's `onToast` callback was fully wired up.

**Resolution:** No code fix needed. `BPulseFileTree.upload()` calls `self._toast('Uploaded ' + filename, 'success')` → `_onToast()` → `_bpftToast()` → `showToast()`. The toast fires correctly when `onToast: _bpftToast` is passed in the constructor (already implemented in the mcp-agent.html BPulseFileTree init block).

**Test method:** `page.locator('#ftUploadInput-uploads').setInputFiles(tmpFile)` — Playwright injects a real file into the hidden file input, which triggers `ftUploadFiles('uploads', '', input)` → `_bpftInstB['uploads'].upload()` → XHR upload → toast on success.

---

### B-088 — Chat File Attach End-to-End

| Test | Status | Evidence |
|------|--------|----------|
| B-088 | ✅ PASS | Upload banner fired ✓, system notice: `"📎 File uploaded: uat_chat_attach.csv — you can now ask me to analyse it."` |

**Prior status:** Marked INFO / not-automatable (required OS file picker). Playwright's `setInputFiles()` bypasses the native picker.

**Flow verified:**
1. `page.locator('#fileInput').setInputFiles(csvFile)` triggers the `change` event listener
2. `showUploadBanner('Uploading filename...', 'info')` fires immediately
3. `fetch('/api/files/upload', { method: 'POST', body: formData })` uploads to the server
4. On success: `showUploadBanner('✅ filename uploaded', 'success')` + `addSystemNotice('📎 File uploaded...')` injects a system notice into `#chat-inner`
5. `.msg-system-notice` element confirmed present with correct text

---

### User CRUD — Create, Edit, Delete

| Test | Status | Evidence |
|------|--------|----------|
| USER-001 | ✅ PASS | Row in table ✓, toast: `"User created: UAT V2 Test User"` |
| USER-002 | ✅ PASS | Edited — new name `"UAT V2 Edited User"`, toast: `"User updated"` |
| USER-003 | ✅ PASS | Not in table ✓ after delete, toast: `"User deleted"` |

**Test user:** `uat_v2_test_user` / `UAT V2 Test User` — created and deleted within the test run. Pre-run cleanup via `DELETE /api/super/users/uat_v2_test_user` guards against leftover state from a prior run.

**Key finding — table rendering:** The `#users-tbody` rows render `display_name` (not `user_id`) as visible text. The `user_id` appears only in `onclick` attributes (`openEditUserModal('user_id')`, `deleteUser('user_id', ...)`). Test selectors use `r.innerHTML.includes(uid)` to match via attribute content.

**Endpoints exercised:**
- `POST /api/super/users` — create
- `PUT /api/super/users/{user_id}` — edit
- `DELETE /api/super/users/{user_id}` — delete

**Notable:** `deleteUser()` in admin.html uses `window.confirm()`. Test stubs this with `window.confirm = () => true` before clicking the delete button.

---

### Worker Create + API Verification

| Test | Status | Evidence |
|------|--------|----------|
| WRK-001 | ✅ PASS | Card `"UAT Regression v2 Worker"` in grid ✓, toast: `"Worker created: UAT Regression v2 Worker"` |
| WRK-002 | ✅ PASS | Verified via API: `id="w-28006b01"`, `name="UAT Regression v2 Worker"` |
| WRK-002-CLEANUP | ✅ PASS | Worker `w-28006b01` deleted via API |

**Flow:** `openCreateWorkerModal()` → fill name + description → `submitCreateWorker()` → `POST /api/super/workers` → worker card appears in `#workers-grid` → `GET /api/super/workers` confirms it exists → `DELETE /api/super/workers/{id}` with body `{"confirm_name": "..."}` cleans up.

**Key finding — worker delete API:** `DELETE /api/super/workers/{worker_id}` requires a JSON request body with `{"confirm_name": "<exact worker name>"}`. Without this body, the endpoint returns `HTTP 422 Unprocessable Entity`. The admin.html UI does **not** expose a delete button for workers (only create + configure). Worker deletion is backend-only.

---

### Conversation Delete and Rename

| Test | Status | Evidence |
|------|--------|----------|
| CONV-003 | ✅ PASS | `deleteConversation()` removed conv — 1 conversation remains in `_conversations` |
| CONV-004 | ✅ PASS | `renameConversation()` set title to `"UAT Renamed Conversation"` ✓ |

**Note:** Conversations are stored in `localStorage` (`mcp_conversations` key). The test creates two fresh conversations via `newConversation()`, then deletes the first and renames the second. State is verified against the `_conversations` array directly.

**`deleteConversation(id)` behaviour:** Removes from `_conversations`, re-renders sidebar. If the deleted conversation was active, it switches to the most recently updated remaining conversation (or shows welcome screen if none remain).

**`renameConversation(id, newTitle)` behaviour:** Updates `conv.title` in-place, calls `saveConversations()` (persists to localStorage), then re-renders sidebar.

---

### SHEET-001 — CSV Sheet Preview

| Test | Status | Evidence |
|------|--------|----------|
| SHEET-001 | ✅ PASS | `"risk_agent_file.csv"` opened in `#sheet-viewer-panel` ✓ — 2 table rows, 1 sheet tab |

**Flow:** Click CSV row in uploads tree → `onFileClick` → `ftPreviewFile('uploads', path, 'risk_agent_file.csv')` → detects `.csv` extension → shows `#sheet-viewer-panel` → calls `ftLoadSheet('uploads', path, 'csv')` → fetches file content → `XLSX.read(content, { type: 'string' })` → `XLSX.utils.sheet_to_html()` → renders `<table>` in `#sheet-table-container`.

**No XLSX files in uploads** (only CSV files available in the test worker). CSV and XLSX use the same `ftLoadSheet()` code path and `sheet-viewer-panel`. SheetJS handles both formats.

---

### XLSX-ADMIN-001 — Admin Panel Excel Preview

| Test | Status | Evidence |
|------|--------|----------|
| XLSX-ADMIN-001 | ✅ PASS | `_adminPreviewExcel` renders table (3 rows) — verified via direct function call |

**Method:** Since the admin panel file tree context was empty for the test worker, the test:
1. Generates a 2-sheet XLSX in-browser via SheetJS (`XLSX.utils.book_new()`, `aoa_to_sheet`)
2. Uploads it to `uploads/uat_test_v2.xlsx` via `POST /api/fs/uploads/upload`
3. Fetches it back via `GET /api/fs/uploads/file?path=uat_test_v2.xlsx`
4. Calls `_adminPreviewExcel(blob, container)` directly in the browser
5. Verifies `container.querySelector('table')` exists with rows
6. Cleans up: deletes `uat_test_v2.xlsx`

**Result:** Table rendered with 3 rows (header + 2 data rows from `[['Name','Value'],['Row1',100],['Row2',200]]`).

---

### PE-CHECK — Page Error Monitor

| Test | Status | Evidence |
|------|--------|----------|
| PE-CHECK | ✅ PASS | No null-property page errors during v2 test session |

Zero `Cannot read properties of null` errors across both `admin.html` and `mcp-agent.html` pages during the full v2 test run. The two null-guard fixes from v1 (`if (_user)` at sidebar init and `if (_user) initWorkerContext()`) remain effective.

---

## Bug Status Updates

| Bug ID | Previous Status | v2 Finding |
|--------|----------------|------------|
| BUG-010 | FAIL (B-113) | ✅ **Already fixed** — toast fires via `_bpftToast` callback |
| BUG-04a-BT-PY-007 | FAIL (libmpdec dylib) | ✅ **Resolved** — `mpdecimal` reinstalled; timeout confirmed working |
| B-088 | INFO / not-automatable | ✅ **Verified working** — upload banner + system notice confirmed |
| BUG-NEW-001-004 | Admin write routes untested | ✅ **Verified** — create/edit/delete user all work end-to-end |

---

## Remaining Open Gaps (Connector-related — deferred)

The following gaps were **explicitly excluded** from this suite (connector dependencies):

| Gap | Blocker |
|-----|---------|
| `teams_send_message` | MS Graph `ChannelMessage.Send` doesn't exist as Application permission |
| `outlook_send_email` / `outlook_read_email` | No Exchange Online license on `SaadAhmed@DeepLearnHQ.onmicrosoft.com` |
| Multi-worker connector scope isolation | Requires connector credentials + two live workers |
| BUG-013 — `testConnectorFromModal()` validates nothing | Requires real connector credentials |
| REQ-03 Listener Workflows | No UAT plan written yet |

---

## Test Infrastructure

- **Playwright version:** 1.59.1
- **Browser:** Google Chrome 146 (headless)
- **Auth method:** JWT fetched via Node.js `fetch()`, injected into `sessionStorage` via `page.evaluate()` before second navigation
- **File injection:** Playwright `locator.setInputFiles()` for upload inputs (bypasses native OS file picker)
- **window.confirm stub:** `window.confirm = () => true` applied before any operation that calls native dialog
- **Cleanup:** Test user and test worker deleted at end of run; XLSX file deleted after preview test
- **Script location:** `uat_plans/run_regression_v2_tests.mjs`
- **Run command:** `node uat_plans/run_regression_v2_tests.mjs` (from repo root)

---

## Combined Coverage — v1 + v2

| Feature | v1 (UI Audit) | v2 (Regression) | Status |
|---------|--------------|-----------------|--------|
| All 21 UI audit fixes | ✅ 37 tests | — | PASS |
| Python sandbox timeout | — | ✅ PY-007 | PASS |
| Sidebar upload toast | — | ✅ BUG-010 | PASS |
| Chat file attach | — | ✅ B-088 | PASS |
| User create/edit/delete | — | ✅ USER-001-003 | PASS |
| Worker create + verify | — | ✅ WRK-001-002 | PASS |
| Conversation delete/rename | — | ✅ CONV-003-004 | PASS |
| CSV/XLSX sheet preview | — | ✅ SHEET-001, XLSX-ADMIN-001 | PASS |
| Null page error guard | ✅ BUG-PE-001 | ✅ PE-CHECK | PASS |
| Connector send/receive | — | — | DEFERRED |
| Listener workflows (REQ-03) | — | — | NO PLAN YET |

**Total automated tests across both suites: 54 PASS, 0 FAIL, 3 SKIP (environment-only)**
