# UI Audit Fixes — QA Retest Plan

> **Status: SUPERSEDED** — This manual retest plan has been replaced by the automated Playwright suite.  
> **Automated results:** [UI_Audit_Playwright_Results.md](UI_Audit_Playwright_Results.md) (37 PASS / 0 FAIL / 3 SKIP)  
> **Master index:** [UAT_Master_Index.md](UAT_Master_Index.md)

**Date:** 2026-04-04
**Scope:** All 21 issues from UI_Audit_UAT_Plan.md
**Files changed:** `public/admin.html`, `public/mcp-agent.html`, `public/js/file-tree.js`
**Prerequisite:** Agent server running on port 8000. Log in as `super_admin` role for all admin.html tests unless stated otherwise.

---

## How to Run

1. Start servers:
   ```
   cd sajhamcpserver && ../venv/bin/python run_server.py
   uvicorn agent_server:app --port 8000 --reload
   ```
2. Open `http://localhost:8000/admin.html` (for admin tests)
3. Open `http://localhost:8000/mcp-agent.html` (for agent tests)
4. Hard refresh both pages after any server restart: **Cmd+Shift+R**

---

## admin.html Tests

### RETEST-ADMIN-001 — Dashboard stat cards populate (was: UI-ADMIN-001)

**Fix:** `fetchUsers()` function added — calls `GET /api/super/users` (super_admin) or `GET /api/admin/worker/users` (admin).

**Steps:**
1. Log in as super_admin, navigate to `admin.html`
2. Wait 2 seconds for dashboard to load

**Expected:**
- "Assigned Users" card shows a number (not "—")
- "Enabled Tools" card shows "All" or a number
- "Workflows" and "Domain Files" cards show counts

**Pass criteria:** All 4 stat cards show values other than "—"

---

### RETEST-ADMIN-002 — Pluralization on worker cards (was: UI-ADMIN-002)

**Fix:** `renderWorkersGrid()` now uses ternary: `1 admin` vs `2 admins`, `1 user` vs `2 users`.

**Steps:**
1. On Dashboard, find a worker card that has exactly 1 admin or 1 user

**Expected:** Card shows "1 admin" (not "1 admins"), "1 user" (not "1 users")

**Pass criteria:** Counts ≥2 show plural; count of 1 shows singular

---

### RETEST-ADMIN-003 — Users section loads (was: UI-ADMIN-003)

**Fix:** `loadUsers()` defined — fetches users, renders table rows with Edit / Reset PW / Delete actions.

**Steps:**
1. Click "Users" in sidebar nav
2. Wait for table to populate

**Expected:**
- No JS ReferenceError in console
- `#users-tbody` populated with user rows
- Each row shows: name, role pill, worker name, status pill, action buttons
- If no users: "No users found." message

**Pass criteria:** Table renders without JS error; rows visible

---

### RETEST-ADMIN-004 — "+ Create User" modal opens (was: UI-ADMIN-004)

**Fix:** `openCreateUserModal()` + `closeModal()` + `closeModalFn()` defined.

**Steps:**
1. Navigate to Users section
2. Click "+ Create User" button
3. Verify modal opens with form fields
4. Fill in: User ID = `test_qa`, Display Name = `QA Test`, Password = `Test1234!`, Role = `user`
5. Click "Create User"
6. Click backdrop (outside modal) — modal should close

**Expected:**
- Modal opens with fields: User ID, Display Name, Email, Password, Role dropdown, Worker dropdown
- On submit: user appears in users table, toast "User created: QA Test" shown
- Backdrop click closes modal (no ReferenceError)

**Pass criteria:** Modal opens, form submits, user created, modal closes on backdrop

**Cleanup:** Delete `test_qa` user via Delete button in Users table

---

### RETEST-ADMIN-005 — Manage Workers section loads (was: UI-ADMIN-005)

**Fix:** `loadWorkers()` defined — calls `renderWorkersGrid(_allWorkers, 'workers-grid')` and refreshes from API.

**Steps:**
1. Click "Manage Workers" in sidebar (Super Admin section)

**Expected:**
- No JS ReferenceError
- `#workers-grid` populated with worker cards matching the Dashboard grid
- Cards show worker name, status badge, user/admin counts

**Pass criteria:** Grid renders without error

---

### RETEST-ADMIN-006 — "+ New Worker" modal opens (was: UI-ADMIN-006)

**Fix:** `openCreateWorkerModal()` defined with form: Name, Description, System Prompt, Clone From dropdown.

**Steps:**
1. Navigate to Manage Workers
2. Click "+ New Worker"
3. Enter Name = `QA Test Worker`, Description = `For QA testing only`
4. Click "Create Worker"

**Expected:**
- Modal opens with Name, Description, System Prompt, Clone From fields
- On submit: new worker card appears in grid, toast "Worker created: QA Test Worker"
- Worker also appears in Dashboard workers grid

**Pass criteria:** Modal opens, worker created, grids refresh

**Cleanup:** Navigate to the new worker in Worker Config and disable/delete it

---

### RETEST-ADMIN-007 — Danger buttons are red (was: UI-ADMIN-007)

**Fix:** `.btn-danger` CSS changed to `background: rgba(220,38,38,0.10); border: rgba(220,38,38,0.30); color: #f87171`.

**Steps:**
1. Navigate to Domain Data — inspect "Delete" button
2. Navigate to Worker Config — inspect "Disable Worker" button
3. Navigate to Workflows — inspect "Delete" button

**Expected:** All three buttons have a **red tint** and red text — visually distinct from grey secondary buttons

**Pass criteria:** Delete/Disable buttons are red, not grey

---

### RETEST-ADMIN-008 — Delete button disabled until items selected (was: UI-ADMIN-008)

**Fix:** Delete buttons start `disabled`. Select button onclick now also toggles `disabled` on Delete.

**Steps:**
1. Navigate to Domain Data
2. Verify "Delete" button is greyed out / disabled on page load
3. Click "Select" button — Delete should become enabled
4. Click "Cancel" — Delete should become disabled again

**Expected:**
- Delete button disabled when not in bulk mode
- Delete button enabled when bulk mode is active (after clicking Select)
- Delete button re-disabled after clicking Cancel

**Pass criteria:** Delete button disabled state tracks bulk mode

---

### RETEST-ADMIN-009 — Filename and size separated (was: UI-ADMIN-009)

**Fix:** Space text node added before `<span class="ft-row-meta">` in `file-tree.js`. CSS `.ft-row-meta { margin-left: auto; }` added to both pages.

**Steps:**
1. Navigate to Domain Data — find a file with a size badge
2. Open browser console and run:
   ```js
   document.querySelector('.ft-row-meta').parentElement.innerText
   ```

**Expected:** Result contains a visible space or separator between filename and size: e.g. `"myfile.md 14 KB"` not `"myfile.md14 KB"`

**Pass criteria:** `innerText` has whitespace between filename and size; size badge is visually right-aligned

---

### RETEST-ADMIN-010 — Row action buttons have aria-label (was: UI-ADMIN-010)

**Fix:** All `ft-action-btn` elements now have `aria-label` matching their `title`.

**Steps:**
1. Navigate to Domain Data
2. Hover over a file row to reveal action buttons
3. Open browser console:
   ```js
   Array.from(document.querySelectorAll('.ft-action-btn')).map(b => b.getAttribute('aria-label'))
   ```

**Expected:** Array contains non-null labels like `["Delete myfile.md"]`, `["New file in myfolder"]`, `["Delete folder myfolder"]`

**Pass criteria:** No null values in the aria-label array for visible action buttons

---

### RETEST-ADMIN-011 — Tools search filter works (was: UI-ADMIN-011)

**Note:** This was already implemented prior to this fix session (`filterTools()` and search input present at line 577). Verify it still works.

**Steps:**
1. Navigate to Tools
2. Type `chart` in the search input

**Expected:** Only tools with "chart" in name or description remain visible

**Pass criteria:** Filtering reduces visible tools (already working — confirm not broken)

---

### RETEST-ADMIN-012 — Tool checkboxes accessible by label click (was: UI-ADMIN-012)

**Note:** Toggle switches use wrapping `<label>` pattern which already works. No change made here — existing implementation uses `<label class="toggle-switch">` wrapping the input. Verify clicking the label toggles the switch.

**Steps:**
1. Navigate to Tools
2. Click directly on a tool name text (not the toggle)

**Pass criteria:** If toggle switches, label click works. If not, this remains open.

---

### RETEST-ADMIN-013 — Audit Log loads (was: UI-ADMIN-013)

**Fix:** `loadAudit()`, `filterAuditTable()`, `auditPagePrev()`, `auditPageNext()` all defined. Calls `GET /api/super/audit?limit=50&offset=0`.

**Steps:**
1. Click "Audit Log" in sidebar (Super Admin section)
2. Wait for table to populate
3. Type a worker ID in the "Filter by worker…" input
4. Click "← Prev" and "Next →" if pagination bar appears

**Expected:**
- No ReferenceError on navigation
- Table rows appear with: Time, Worker, User, Tool, Status (green/red pill), Duration
- Filter inputs narrow results with ~350ms debounce
- Pagination shows "1–50 of N" when > 50 entries; Prev disabled on first page

**Pass criteria:** All 4 functions execute without ReferenceError; data renders

---

### RETEST-ADMIN-014 — Worker Mapping shows hint (was: UI-ADMIN-014)

**Fix:** Added hint text "Select a worker above to configure its connector scope." that hides when a worker is selected.

**Steps:**
1. Navigate to Connectors → Worker Mapping tab
2. Verify hint text is visible with no worker selected
3. Select a worker from the dropdown

**Expected:**
- Hint "Select a worker above to configure its connector scope." visible before selection
- Hint disappears and scope form appears after selecting a worker

**Pass criteria:** Hint visible → hidden transition on worker select

---

### RETEST-ADMIN-015 — Excel sheet tabs work (was: UI-ADMIN-015)

**Fix:** `switchSheet(tabEl, sheetName, wb)` defined — updates active tab class and calls `renderSheet(wb, sheetName, pb)`.

**Steps:**
1. Navigate to Domain Data
2. Upload or find an `.xlsx` file with 2+ sheets (or use an existing multi-sheet file)
3. Click on it to preview
4. Click the second sheet tab

**Expected:**
- No ReferenceError on tab click
- Preview updates to show the second sheet's data
- Active tab styling updates (white background on active tab)

**Pass criteria:** Sheet switching works without error

---

### RETEST-ADMIN-016 — Modal backdrop closes modal (was: UI-ADMIN-016)

**Fix:** `closeModal(event)` defined — delegates to `closeModalFn()` on backdrop click.

**Covered by:** RETEST-ADMIN-004 step 6 (backdrop click test)

**Pass criteria:** Clicking the dark overlay outside the modal box closes the modal

---

## mcp-agent.html Tests

### RETEST-AGENT-001 — Admin Panel button visible to admins (was: UI-AGENT-001)

**Fix:** Login handler now adds `.visible` class to `#admin-tab-btn` when `role === 'admin' || role === 'super_admin'`.

**Steps:**
1. Open `mcp-agent.html`, log in as `risk_agent` (user role)
2. Check bottom of sidebar — Admin button should NOT be visible
3. Log out, log in as a super_admin user
4. Check bottom of sidebar — Admin button SHOULD be visible

**Expected:**
- `user` role: Admin button hidden (no change from before)
- `admin` or `super_admin` role: Admin Panel button visible in sidebar bottom
- Clicking it opens the admin panel (toggleAdminPanel still works)

**Pass criteria:** Button visible for admin/super_admin, hidden for user

---

### RETEST-AGENT-002 — File count badges update after load (was: UI-AGENT-002)

**Fix:** `_bpftInstB` instances now receive `onLoad` callback. After XHR completes, `_ftTrees[section]` is set and `ftUpdateBadge(section)` is called.

**Steps:**
1. Open `mcp-agent.html`, log in
2. Open browser console, run:
   ```js
   document.querySelectorAll('.ft-count-badge')
   ```
3. Wait 3 seconds for trees to load, then run the query again
4. Or expand a sidebar section (Uploads, My Workflows etc.) and check the badge

**Expected:**
- Badges show actual file counts (not 0) once trees have loaded
- e.g. `#ft-badge-uploads` shows `3` if uploads section has 3 files

**Pass criteria:** At least one badge shows a non-zero count after tree loads

---

### RETEST-AGENT-003 — Open Chart button shown for python_execute (was: UI-AGENT-003)

**Fix:** `onToolEnd()` already checks both `output._chart_ready && output.html_file` (generate_chart) AND `output._python_ready && output.figures` (python_execute). Confirmed in code at line 4183-4209.

**Steps:**
1. Send message: `run a GARCH(1,1) on returns [0.5, -0.3, 1.1, -0.9, 0.4] and plot the result`
2. Wait for agent to call python_execute and produce a chart

**Expected:**
- Tool card for python_execute shows an "Open Chart" button in the header
- Clicking "Open Chart" opens the canvas panel with the Plotly chart
- Chart also renders inline in the message (📊 Python Chart with Hide/Show)

**Pass criteria:** "Open Chart" button visible on python_execute tool card; canvas opens

---

### RETEST-AGENT-004 — Welcome screen shows worker name (was: UI-AGENT-004)

**Fix:** Login handler now updates `.welcome-title` textContent from `u.worker_name`.

**Steps:**
1. Open `mcp-agent.html`, ensure no conversations (or click New Conversation)
2. Log in — welcome screen should be visible before any message is sent

**Expected:** Welcome screen title reads the actual worker name (e.g. "Market Risk Worker") not the hardcoded "Market Risk Digital Worker"

**Note:** If `worker_name` from JWT matches the hardcoded string exactly, both will look the same — verify by inspecting `u.worker_name` in the login response or temporarily rename the worker.

**Pass criteria:** `.welcome-title` element text matches the `worker_name` field from the JWT

---

### RETEST-AGENT-005 — Sidebar drag handle has aria-label (was: UI-AGENT-005)

**Fix:** `#sidebar-drag` now has `aria-label="Resize sidebar"` and `role="separator"`.

**Steps:**
1. Open browser console on mcp-agent.html
2. Run: `document.getElementById('sidebar-drag').getAttribute('aria-label')`

**Expected:** Returns `"Resize sidebar"`

**Pass criteria:** `aria-label` is not null

---

## Cross-page Tests (file-tree.js)

These affect both `admin.html` (Impl A, Impl C) and `mcp-agent.html` (Impl B):

| Test | Covers | Check |
|------|--------|-------|
| Filename/size separated | UI-ADMIN-009 | `document.querySelector('.ft-row-meta').parentElement.innerText` has space before size |
| Action button aria-labels | UI-ADMIN-010 | `.ft-action-btn` elements have non-null `aria-label` attributes |
| Badge updates after load | UI-AGENT-002 | Badges non-zero after load |

---

## Acceptance Criteria Summary

| Issue | Description | Expected Status |
|-------|-------------|-----------------|
| UI-ADMIN-001 | Dashboard stat cards populate | PASS |
| UI-ADMIN-002 | "1 admin" pluralization | PASS |
| UI-ADMIN-003 | Users section loads | PASS |
| UI-ADMIN-004 | "+ Create User" modal | PASS |
| UI-ADMIN-005 | Manage Workers section loads | PASS |
| UI-ADMIN-006 | "+ New Worker" modal | PASS |
| UI-ADMIN-007 | btn-danger is red | PASS |
| UI-ADMIN-008 | Delete disabled until selection | PASS |
| UI-ADMIN-009 | Filename/size not concatenated | PASS |
| UI-ADMIN-010 | Action button aria-labels | PASS |
| UI-ADMIN-011 | Tools search (pre-existing) | PASS |
| UI-ADMIN-012 | Toggle label click | VERIFY |
| UI-ADMIN-013 | Audit Log all 4 functions | PASS |
| UI-ADMIN-014 | Worker Mapping hint text | PASS |
| UI-ADMIN-015 | Excel sheet tab switching | PASS |
| UI-ADMIN-016 | Modal backdrop closes modal | PASS (covered by 004) |
| UI-AGENT-001 | Admin Panel button visible | PASS |
| UI-AGENT-002 | File count badges | PASS |
| UI-AGENT-003 | Open Chart for python_execute | PASS |
| UI-AGENT-004 | Welcome screen worker name | PASS |
| UI-AGENT-005 | Sidebar drag aria-label | PASS |

---

## Files Changed

| File | Changes |
|------|---------|
| `public/js/file-tree.js` | Added `onLoad` callback param; `aria-label` on all action buttons; space before `.ft-row-meta` span |
| `public/admin.html` | `btn-danger` CSS red; `.ft-row-meta` CSS; Delete buttons start disabled; Worker Mapping hint; pluralization fix; `fetchUsers`, `loadUsers`, `openCreateUserModal`, `closeModal`, `closeModalFn`, `openEditUserModal`, `submitCreateUser`, `submitEditUser`, `deleteUser`, `resetUserPassword`, `loadWorkers`, `openCreateWorkerModal`, `submitCreateWorker`, `loadAudit`, `filterAuditTable`, `auditPagePrev`, `auditPageNext`, `switchSheet` all defined; Select button now toggles Delete disabled state |
| `public/mcp-agent.html` | Admin Panel button shown on admin login; welcome-title updated from worker_name; `aria-label`/`role` on sidebar-drag; `.ft-row-meta` CSS; `onLoad` callback wired to `ftUpdateBadge` |

---

## Known Remaining Items

- **BUG-04a-BT-PY-007-001** — `libmpdec.4.dylib` missing for timeout test: environment issue, no code change needed. Fix: `brew install mpdecimal` in terminal.
- **UI-ADMIN-012** — Tool toggle switches already use wrapping `<label>` and work; clicking tool name text may not toggle. Low priority — not fixed in this pass.
