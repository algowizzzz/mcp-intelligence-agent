# UI Audit — UAT Plan

> **Status: COMPLETE** — All 21 issues identified here have been fixed and verified.  
> **Results:** [UI_Audit_Playwright_Results.md](UI_Audit_Playwright_Results.md) (37 PASS / 0 FAIL / 3 SKIP)  
> **Master index:** [UAT_Master_Index.md](UAT_Master_Index.md)

**Date:** 2026-04-04
**Method:** Code inspection (grep + file read) + prior browser DOM verification — no LLM calls
**Scope:** `public/admin.html` (all sections) and `public/mcp-agent.html` (sidebar, chat, admin panel)
**Round 2 (button audit):** All `onclick`/`onchange` handlers enumerated and cross-checked against function definitions.

---

## Issue Severity Key

| Severity | Meaning |
|----------|---------|
| Critical | Functionality is completely broken — feature unavailable or throws JS error on use |
| High | Feature works but is significantly misleading, inaccessible, or incorrect |
| Medium | Visual defect or partial functionality gap |
| Low | Minor UX/accessibility concern |

---

## admin.html — Dashboard

### UI-ADMIN-001 — Dashboard stat cards always show "—"

**Severity:** Critical
**Page:** admin.html → Dashboard
**Root cause:** `loadDashboard()` (line 995) calls `fetchUsers()` at line 1003 to populate the Users stat card. `fetchUsers` is not defined anywhere in `admin.html`. The call throws `ReferenceError: fetchUsers is not defined` on every dashboard load.
**Symptom:** All 4 stat cards (Users, Tools, Workflows, Files) display "—" and never update. Workflows and Files counts are fetched in a separate `try` block that succeeds — but because `fetchUsers()` throws first, the function exits before reaching them in some JS engines.
**Code reference:** Line 1003: `var users = await fetchUsers();`

---

### UI-ADMIN-002 — "1 admins" — incorrect pluralization on worker cards

**Severity:** Medium
**Page:** admin.html → Dashboard → Worker cards
**Root cause:** Line 1058: `<span>${w.admin_count || 0} admins</span>` — always uses plural form.
**Symptom:** A worker with exactly 1 admin displays "1 admins" instead of "1 admin".
**Code reference:** Line 1058 in `renderWorkersGrid()`.

---

## admin.html — Users

### UI-ADMIN-003 — Users section always empty; `loadUsers()` not defined

**Severity:** Critical
**Page:** admin.html → Users (nav item)
**Root cause:** `showSection('users')` at line 947 calls `loadUsers()`. `loadUsers` is not defined anywhere in `admin.html` (grep confirms zero definitions).
**Symptom:** Navigating to Users throws `ReferenceError: loadUsers is not defined` in the browser console. The Users table `<tbody id="users-tbody">` remains empty. No error state or empty message is shown to the user — the page appears to have loaded normally but shows a blank table.
**Secondary issue:** `<tbody id="users-tbody">` has no initial placeholder row — if `loadUsers` were fixed and returned zero results, no empty-state message would appear.
**Code reference:** Line 947 (call), no definition found.

---

### UI-ADMIN-004 — "+ Create User" button throws ReferenceError

**Severity:** Critical
**Page:** admin.html → Users
**Root cause:** `onclick="openCreateUserModal()"` at line 665. `openCreateUserModal` is not defined anywhere in `admin.html`.
**Symptom:** Clicking "+ Create User" throws `ReferenceError: openCreateUserModal is not defined`. No modal opens.
**Code reference:** Line 665.

---

## admin.html — Manage Workers

### UI-ADMIN-005 — Manage Workers section always empty; `loadWorkers()` not defined

**Severity:** Critical
**Page:** admin.html → Manage Workers (nav item, super admin only)
**Root cause:** `showSection('workers')` at line 948 calls `loadWorkers()`. `loadWorkers` is not defined anywhere in `admin.html`. Note: `renderWorkersGrid()` IS defined (line 1048) and IS called from `loadDashboard()` — but `loadWorkers()`, which should call it when navigating to the section, does not exist.
**Symptom:** Navigating to Manage Workers throws `ReferenceError: loadWorkers is not defined`. `<div class="workers-grid" id="workers-grid">` stays empty.
**Code reference:** Line 948 (call), no definition found.

---

### UI-ADMIN-006 — "+ New Worker" button throws ReferenceError

**Severity:** Critical
**Page:** admin.html → Manage Workers
**Root cause:** `onclick="openCreateWorkerModal()"` at line 689. `openCreateWorkerModal` is not defined anywhere in `admin.html`.
**Symptom:** Clicking "+ New Worker" throws `ReferenceError: openCreateWorkerModal is not defined`. No modal opens.
**Code reference:** Line 689.

---

## admin.html — Worker Configuration

### UI-ADMIN-007 — `btn-danger` styled grey, not red — destructive actions not visually distinct

**Severity:** High
**Page:** admin.html — Worker Configuration (Disable Worker button), Domain Data toolbar (Delete button), Workflows toolbar (Delete button)
**Root cause:** CSS at lines 199–200:
```css
background: rgba(200,200,200,0.08);
border: 1px solid rgba(200,200,200,0.18);
color: #aaaaaa;
```
This renders `btn-danger` identically to `btn-secondary` — both appear as dim grey buttons.
**Symptom:** The "Disable Worker" and "Delete" (bulk delete) buttons look identical to non-destructive secondary buttons. No visual cue communicates destructive intent.
**Affected elements:** `#worker-enable-toggle` (line 1082), `#dd-bulk-delete-btn` (line 600), `#wf-bulk-delete-btn` (line 636).

---

## admin.html — Domain Data & Workflows

### UI-ADMIN-008 — Delete toolbar buttons always enabled regardless of selection state

**Severity:** High
**Page:** admin.html → Domain Data, admin.html → Workflows
**Root cause:** `#dd-bulk-delete-btn` (line 600) and `#wf-bulk-delete-btn` (line 636) are rendered always enabled in HTML. There is no JS that toggles `disabled` based on checkbox selection count in bulk mode.
**Symptom:** The Delete button appears clickable at all times, including when no files are selected. Clicking it with nothing selected calls `bulkDelete()` with an empty selection, which silently does nothing but gives the user no feedback.
**Affected elements:** Lines 600, 636.

---

### UI-ADMIN-009 — Filename and file size text concatenated in file tree rows

**Severity:** Medium
**Page:** admin.html → Domain Data, admin.html → Workflows, mcp-agent.html (all file tree sections)
**Root cause:** Within each `.ft-row`, the `.ft-row-name` span (filename) and `.ft-row-meta` span (size badge, e.g. "14 KB") are direct DOM siblings with no intervening text node and no CSS `gap` or `margin-left`. When a user selects text across both spans, or when assistive technology reads the row, the two strings are concatenated.
**Symptom:** Rendered text reads as `"test_results_2026-04-03.md14 KB"` — the filename and size run together with no space.
**Browser verification:** Confirmed via browser console: `document.querySelector('.ft-row').innerText` returns `"test_results_2026-04-03.md14 KB"`.
**Affects:** All three BPulseFileTree implementations (Impl A admin.html, Impl B and C mcp-agent.html).

---

### UI-ADMIN-010 — Row action buttons are SVG-only with no `aria-label`

**Severity:** Medium
**Page:** admin.html → Domain Data, admin.html → Workflows, mcp-agent.html (all file tree sections)
**Root cause:** File tree row action buttons (New File, Delete folder, Delete file, etc.) contain only an SVG icon. They have a `title` attribute (e.g. `"Delete folder"`) but no `aria-label`. `textContent` is an empty string.
**Symptom:** Screen readers announce the button as unlabelled. The `title` tooltip only appears on mouse hover — keyboard and touch users receive no label. `button.textContent === ""` confirmed via browser console.
**Affects:** All three BPulseFileTree implementations.

---

## admin.html — Tools

### UI-ADMIN-011 — No search/filter input on Tools page

**Severity:** Low
**Page:** admin.html → Tools
**Root cause:** The Tools page renders all 123 tool checkboxes in a scrollable list with no filtering mechanism. The Connectors → Tool Library sub-tab has a search input (`<input placeholder="Search tools…">` at line 761), but the main Tools section (for enabling tools per worker) does not.
**Symptom:** Finding a specific tool in a list of 123 requires manual scrolling. No search, no category filter, no sort.

---

### UI-ADMIN-012 — Tool checkboxes have no `id` attribute and no `<label for="">` association

**Severity:** Low
**Page:** admin.html → Tools
**Root cause:** Tool checkboxes are rendered programmatically (via `loadTools()`) without assigning an `id` attribute and without wrapping the label text in a `<label for="...">` element.
**Symptom:** Clicking the tool name text next to a checkbox does not toggle the checkbox. Accessibility: the label is not programmatically associated with its control. Confirmed: 123 tool checkbox `<input>` elements have no `id`.

---

## admin.html — Audit Log

### UI-ADMIN-013 — Audit Log permanently stuck at "Loading…"; `loadAudit()` not defined

**Severity:** Critical
**Page:** admin.html → Audit Log (nav item, super admin only)
**Root cause:** `showSection('audit')` at line 950 calls `loadAudit()`. `loadAudit` is not defined anywhere in `admin.html`.
**Additional undefined functions called from Audit Log DOM:**
- `filterAuditTable()` — called from `oninput` on worker/user filter inputs (lines 702–703)
- `auditPagePrev()` — called from Prev button (line 708)
- `auditPageNext()` — called from Next button (line 710)
**Symptom:** Navigating to Audit Log throws `ReferenceError: loadAudit is not defined`. The audit `<tbody>` shows the static initial row: `"Loading…"` — it never clears. Filter inputs and pagination buttons also throw ReferenceErrors on interaction.
**Code reference:** Line 950 (call), no definition found.

---

## admin.html — Domain Data & Workflows (File Preview)

### UI-ADMIN-015 — Excel multi-sheet file preview: sheet tab clicks throw ReferenceError

**Severity:** High
**Page:** admin.html → Domain Data (file preview panel), admin.html → Workflows (file preview panel)
**Root cause:** When an Excel file (`.xlsx`/`.xls`) with multiple sheets is previewed, `previewFile()` generates sheet tab elements with `onclick="switchSheet(this,'SheetName',...)"`. The function `switchSheet` is not defined anywhere in `admin.html`. Only `renderSheet` (line 1361) and `b64ToAb` (line 1306) are defined.
**Symptom:** Clicking any sheet tab other than the first (which renders automatically via `renderSheet(wb, sheetNames[0], pb)`) throws `ReferenceError: switchSheet is not defined`. The preview stays on the first sheet with no feedback.
**Code reference:** Line 1349 (tab onclick); no `switchSheet` definition found.

---

## admin.html — Connectors

*Connectors section is the only section without critical undefined-function bugs. `loadConnectors()`, `switchConnectorTab()`, `loadConnectorTools()`, `loadWorkerMappingTab()`, `loadWorkerConnectorScope()`, `saveConnectorScope()`, and `testConnector()` are all defined and implemented.*

### UI-ADMIN-016 — Generic modal backdrop close (`closeModal`) not defined

**Severity:** Low (secondary — modal never opens)
**Page:** admin.html — modal overlay (`#modal-overlay`)
**Root cause:** Line 851: `<div class="modal-overlay hidden" id="modal-overlay" onclick="closeModal(event)">`. The function `closeModal` is not defined. This modal is populated and opened by `openCreateUserModal()` and `openCreateWorkerModal()`, both of which are also undefined (UI-ADMIN-004, UI-ADMIN-006). As a result the backdrop click handler is currently unreachable, but if the modal functions are ever implemented, backdrop-click-to-close will throw `ReferenceError`.
**Code reference:** Line 851 (onclick); no `closeModal` definition found.

---

### UI-ADMIN-014 — Connectors Worker Mapping: no feedback when worker select is empty

**Severity:** Low
**Page:** admin.html → Connectors → Worker Mapping tab
**Root cause:** When the Worker Mapping tab loads, `cw-scope-form` is hidden until a worker is selected from the dropdown. If no workers are available or the dropdown fails to populate, the user sees an empty select and a blank area with no explanation.
**Symptom:** No placeholder text explains that a worker must be selected before scope can be configured. The empty state is visually ambiguous.

---

## mcp-agent.html — Sidebar & Admin Panel

### UI-AGENT-001 — Admin Panel sidebar button never shown to any user

**Severity:** Critical
**Page:** mcp-agent.html — sidebar bottom
**Root cause:** `#admin-tab-btn` has CSS `display: none` at line 2445:
```css
#admin-tab-btn { display: none; /* shown only for admins via JS */ }
#admin-tab-btn.visible { display: flex; }
```
The `.visible` class is defined in CSS but is never added by any JavaScript — grep confirms zero occurrences of `admin-tab-btn` being given the `visible` class.
**Symptom:** The Admin Panel button is invisible for all users including super admins. The admin panel can only be opened via browser console: `toggleAdminPanel()`. No in-app path to the Admin Panel exists.
**Code reference:** CSS line 2445 (`display: none`), line 2447 (`.visible` class — never applied).

---

### UI-AGENT-002 — File section count badges always show 0

**Severity:** High
**Page:** mcp-agent.html — sidebar file tree section headers
**Root cause:** Race condition in `ftUpdateBadge(section)` (lines 5254–5258):
```js
function ftUpdateBadge(section) {
  var badge = $('ft-badge-' + section);
  if (!badge) return;
  var tree = _ftTrees[section];
  badge.textContent = tree ? ftCountFiles(tree.tree) : 0;
}
```
`ftLoad()` calls `_bpftInstB[section].load()` then immediately calls `ftUpdateBadge(section)`. Since `.load()` is async (XHR), `_ftTrees[section]` is not yet populated when `ftUpdateBadge` runs — it always evaluates the falsy branch and sets `0`.
**Symptom:** All four sidebar badges — `#ft-badge-domain_data`, `#ft-badge-uploads`, `#ft-badge-verified`, `#ft-badge-my_workflows` — are hardcoded `0` in HTML and remain `0` after tree load. Users cannot see how many files are in each section without expanding it.
**Fix direction:** BPulseFileTree needs an `onLoad` callback that fires after tree data arrives; `ftUpdateBadge` should be called from that callback.

---

## mcp-agent.html — Chat UI

### UI-AGENT-003 — "Open Chart" button missing for `python_execute` chart results; canvas does not auto-open

**Severity:** High
**Page:** mcp-agent.html — chat tool result cards
**Root cause:** `onToolEnd()` at line 4144 checks `output._chart_ready && output.html_file` before rendering the "Open Chart" button. `python_execute` sets `_chart_ready: true` and populates `figures: [{filename, type, url}]` — but does NOT set `html_file`. The `html_file` field is only set by the `generate_chart` tool. The same condition exists in `agent_server.py` line 1870 for the `canvas` SSE event.
**Symptom:** When the agent uses `python_execute` to produce a Plotly chart, no "Open Chart" button appears in the tool card, and the canvas panel does not auto-open. The chart URL is available in the raw figures array but is inaccessible from the UI. Verified in UAT REQ-03 VIZ-TEST-001 (PARTIAL PASS).
**Affected code:** `mcp-agent.html` line 4144; `agent_server.py` line 1870.

---

### UI-AGENT-004 — Welcome screen worker name hardcoded

**Severity:** Low
**Page:** mcp-agent.html — welcome screen (shown before first message)
**Root cause:** Line 3071: `<div class="welcome-title">Market Risk Digital Worker</div>` is a static string. The header (`#header-worker-name`, line 3035) and `<title>` (line 6674) are correctly updated from the authenticated user's `worker_name` field, but `welcome-title` is never touched by JS.
**Symptom:** If deployed for a different worker (e.g. "Credit Risk Digital Worker"), the welcome screen still reads "Market Risk Digital Worker". The mismatch is visible before the user sends any message.

---

### UI-AGENT-006 — mcp-agent.html button audit: all other handlers confirmed defined

**Severity:** N/A (pass)
**Page:** mcp-agent.html — all pages
**Finding:** Full enumeration of all `onclick`/`onchange` attributes in `mcp-agent.html` cross-checked against function definitions. All handlers are implemented:

| Button / Element | Handler | Status |
|------------------|---------|--------|
| Sidebar toggle | `toggleSidebar()` | ✓ Defined (line 3486) |
| Chats / Data & Workflows tabs | `switchSidebarTab()` | ✓ Defined (line 3636) |
| New conversation | `newConversation()` | ✓ Defined (line 3685) |
| Upload Files (sidebar) | `ftUploadFiles()` / `onchange` | ✓ Defined (line 5641) |
| New Folder (sidebar uploads) | `ftNewFolder()` | ✓ Defined (line 5633) |
| New Workflow (sidebar) | `ftNewFile()` | ✓ Defined (line 5637) |
| Refresh (Domain Data / Verified) | `ftLoad()` | ✓ Defined (line 5210) |
| Section expand/collapse headers | `ftToggle()` | ✓ Defined (line 5227) |
| Theme toggle | `toggleTheme()` | ✓ Defined (line 7033) |
| Settings | `openSettingsModal()` | ✓ Defined (line 3855) |
| Settings: Clear All Conversations | `clearAllConversations()` | ✓ Defined (line 3821) |
| Send message | `runAgent()` | ✓ Defined (line 4991) |
| Stop generating | `cancelRun()` | ✓ Defined (line 5071) |
| Attach file (input) | `document.getElementById('fileInput').click()` | ✓ Input present |
| Canvas Save to My Data | `canvasSaveToMyData()` | ✓ Defined (line 5797) |
| Canvas Export as Word | `exportCanvasAsWord()` | ✓ Defined (line 7050) |
| Canvas Close | `closeCanvas()` | ✓ Defined (line 7006) |
| Canvas Select from Workflows | `selectFromCanvas()` | ✓ Defined (line 5828) |
| Markdown toolbar (H1,H2, Bold…) | `mdInsert()` | ✓ Defined (line 5590) |
| PDF Prev/Next/Zoom | `pdfNav()` / `pdfZoom()` | ✓ Defined (lines 5515, 5521) |
| Admin panel tree: New Folder | `adminNewFolder()` | ✓ Defined (line 6067) |
| Admin panel tree: Bulk Select | `adminToggleBulkSelect()` | ✓ Defined (line 6303) |
| Admin panel tree: Upload | `adminSelectFolder()` + `adminQueueFiles()` | ✓ Both defined |
| Admin panel: Bulk Delete bar | `adminBulkDelete()` | ✓ Defined (line 6344) |
| Admin panel: Cancel Bulk | `adminCancelBulkSelect()` | ✓ Defined (line 6318) |
| Admin panel: Cancel All queue | `adminCancelQueue()` | ✓ Defined (line 6596) |
| Admin panel: Preview close | `adminClosePreview()` | ✓ Defined (line 6199) |
| Admin panel: Retry upload | `adminRetry()` / `adminRetryOverwrite()` | ✓ Both defined |
| Copy message MD | `copyCurrentMD()` | ✓ Defined (line 4610) |
| Retry last | `retryLast()` | ✓ Defined (line 4643) |
| Tool card expand | `toggleToolCard()` | ✓ Defined (line 4212) |
| Copy code block | `copyCodeBlock()` | ✓ Defined (line 4497) |
| HITL option select | `selectHitlOption()` | ✓ Defined (line 4546) |
| HITL submit | `submitHitl()` | ✓ Defined (line 4554) |
| Worker switcher (super admin) | `switchChatWorker()` | ✓ Defined (line 6703) |
| Reasoning toggle | `toggleReasoning()` | ✓ Defined (line 4017) |
| View restored canvas | `openRestoredCanvas()` | ✓ Defined (line 7028) |
| Excel sheet tabs | `sheetShowTab()` | ✓ Defined (line 5550) |
| Remove workflow chip | `clearWorkflow()` | ✓ Defined (line 5858) |
| Remove file chip | `deselectFile()` | ✓ Defined (line 5864) |
| Logout | `doLogout()` | ✓ Defined (line 6642) |
| Admin Panel toggle | `toggleAdminPanel()` | ✓ Defined (line 5934) — but button never shown (UI-AGENT-001) |

**No additional undefined button handlers found in mcp-agent.html.**

---

### UI-AGENT-005 — Sidebar icon-only buttons have no `aria-label`

**Severity:** Low
**Page:** mcp-agent.html — sidebar bottom buttons
**Root cause:** Theme toggle, Settings, and Admin Panel buttons in the sidebar bottom (`<div class="sidebar-bottom">`) use SVG icons with a visible text label beneath them — so `textContent` is non-empty (e.g. "Admin", "Settings", "Light Theme"). This is better than the file-tree row buttons. However, the `id="sidebar-drag"` resize handle (line 3016) has only a `title` attribute and no `aria-label`. File upload trigger buttons (`ftUploadInput-*`) are hidden inputs triggered by toolbar buttons that have no visible label text.
**Symptom:** Minor accessibility gap on drag handle and upload trigger buttons.

---

## admin.html — Full Button Audit Summary

All `onclick`/`onchange` handlers enumerated and cross-checked:

| Button / Element | Handler | Status |
|------------------|---------|--------|
| Nav: Dashboard | `showSection('dashboard')` | ✓ |
| Nav: Worker Config | `showSection('worker-config')` | ✓ |
| Nav: Tools | `showSection('tools')` | ✓ |
| Nav: Domain Data | `showSection('domain-data')` | ✓ |
| Nav: Workflows | `showSection('workflows')` | ✓ |
| Nav: Users | `showSection('users')` → `loadUsers()` | ✗ `loadUsers` undefined |
| Nav: Manage Workers | `showSection('workers')` → `loadWorkers()` | ✗ `loadWorkers` undefined |
| Nav: Connectors | `showSection('connectors')` → `switchConnectorTab()` | ✓ |
| Nav: Audit Log | `showSection('audit')` → `loadAudit()` | ✗ `loadAudit` undefined |
| Nav: Go to Chat | `goToChat()` | ✓ |
| Nav: Logout | `logout()` | ✓ |
| Worker switcher dropdown | `switchWorker()` | ✓ |
| Dashboard: + New Worker shortcut | `showSection('workers')` | ✓ (navigates, but section is empty) |
| Manage Workers: + New Worker | `openCreateWorkerModal()` | ✗ Undefined |
| Worker Config: Disable/Enable Worker | `toggleWorkerEnabled()` | ✓ |
| Worker Config: Save Changes | `saveWorkerConfig()` | ✓ |
| Tools: All on / All off | `toggleCategory()` | ✓ |
| Tools: Save Tools | `saveTools()` | ✓ |
| Domain Data: ↑ Upload | triggers `bpft-upload-input-dd` → `window._bpft_dd.upload()` | ✓ (wired at line 1784) |
| Domain Data: + Folder | `window._bpft_dd.mkdir()` | ✓ |
| Domain Data: Select | `window._bpft_dd.toggleBulkMode()` | ✓ |
| Domain Data: Delete (bulk) | `window._bpft_dd.bulkDelete()` | ✓ (but always enabled — UI-ADMIN-008) |
| Domain Data: Preview close ×  | `closePreview()` | ✓ |
| Domain Data: Excel sheet tabs | `switchSheet()` | ✗ Undefined (UI-ADMIN-015) |
| Workflows: ↑ Upload .md | triggers `bpft-upload-input-wf` → `window._bpft_wf.upload()` | ✓ (wired at line 1786) |
| Workflows: + New | `window._bpft_wf.createMd()` | ✓ |
| Workflows: Select | `window._bpft_wf.toggleBulkMode()` | ✓ |
| Workflows: Delete (bulk) | `window._bpft_wf.bulkDelete()` | ✓ (but always enabled — UI-ADMIN-008) |
| Workflows: Preview close × | `closePreview('wf')` | ✓ |
| Users: + Create User | `openCreateUserModal()` | ✗ Undefined (UI-ADMIN-004) |
| Audit: Refresh | `loadAudit(0)` | ✗ Undefined |
| Audit: filter inputs | `filterAuditTable()` | ✗ Undefined |
| Audit: ← Prev / Next → | `auditPagePrev()` / `auditPageNext()` | ✗ Both undefined |
| Connectors: Refresh | `loadConnectors()` | ✓ |
| Connectors tabs (Overview/Tools/Workers) | `switchConnectorTab()` | ✓ |
| Connectors: Configure | `openConnectorModal()` | ✓ |
| Connectors: Test (card) | `testConnector()` | ✓ |
| Connectors modal: Cancel | `closeConnModalFn()` | ✓ |
| Connectors modal: Test Connection | `testConnectorFromModal()` | ✓ |
| Connectors modal: Save | `saveConnector()` | ✓ |
| Connectors modal: overlay backdrop | `closeConnModal(event)` | ✓ |
| Worker Mapping: worker select | `loadWorkerConnectorScope()` | ✓ |
| Worker Mapping: Save MS365 Scope | `saveConnectorScope('microsoft_azure')` | ✓ |
| Worker Mapping: Save Atlassian Scope | `saveConnectorScope('atlassian')` | ✓ |
| General modal overlay backdrop | `closeModal(event)` | ✗ Undefined (UI-ADMIN-016) |

**Summary: 9 handlers undefined/broken in admin.html.**

---

## Acceptance Criteria Summary

| Issue ID | Page | Severity | Description | Status |
|----------|------|----------|-------------|--------|
| UI-ADMIN-001 | admin.html / Dashboard | Critical | `fetchUsers()` undefined → stat cards show "—" | OPEN |
| UI-ADMIN-002 | admin.html / Dashboard | Medium | "1 admins" grammar | OPEN |
| UI-ADMIN-003 | admin.html / Users | Critical | `loadUsers()` undefined → Users table always empty | OPEN |
| UI-ADMIN-004 | admin.html / Users | Critical | `openCreateUserModal()` undefined → ReferenceError on "+ Create User" click | OPEN |
| UI-ADMIN-005 | admin.html / Manage Workers | Critical | `loadWorkers()` undefined → section always empty | OPEN |
| UI-ADMIN-006 | admin.html / Manage Workers | Critical | `openCreateWorkerModal()` undefined → ReferenceError on "+ New Worker" click | OPEN |
| UI-ADMIN-007 | admin.html / Worker Config, file trees | High | `btn-danger` CSS is grey, not red — destructive buttons indistinguishable | OPEN |
| UI-ADMIN-008 | admin.html / Domain Data, Workflows | High | Delete toolbar button always enabled regardless of selection | OPEN |
| UI-ADMIN-009 | admin.html + mcp-agent.html / file trees | Medium | Filename + size text concatenated with no separator | OPEN |
| UI-ADMIN-010 | admin.html + mcp-agent.html / file trees | Medium | Row action buttons SVG-only, no `aria-label` | OPEN |
| UI-ADMIN-011 | admin.html / Tools | Low | No search/filter on 123-entry Tools page | OPEN |
| UI-ADMIN-012 | admin.html / Tools | Low | Tool checkboxes not associated with `<label>` elements | OPEN |
| UI-ADMIN-013 | admin.html / Audit Log | Critical | `loadAudit()`, `filterAuditTable()`, `auditPagePrev()`, `auditPageNext()` all undefined → Audit Log permanently "Loading…" | OPEN |
| UI-ADMIN-014 | admin.html / Connectors | Low | Worker Mapping tab: no empty-state guidance when no worker selected | OPEN |
| UI-ADMIN-015 | admin.html / Domain Data, Workflows | High | `switchSheet()` undefined → Excel multi-sheet file preview: sheet tab clicks throw ReferenceError | OPEN |
| UI-ADMIN-016 | admin.html / Modals | Low | `closeModal()` undefined → generic modal backdrop click will throw when modal is eventually opened | OPEN |
| UI-AGENT-001 | mcp-agent.html / Sidebar | Critical | Admin Panel button never shown — `.visible` CSS class defined but never applied by JS | OPEN |
| UI-AGENT-002 | mcp-agent.html / Sidebar | High | File count badges always 0 — async race condition in `ftUpdateBadge()` | OPEN |
| UI-AGENT-003 | mcp-agent.html / Chat | High | "Open Chart" button missing for `python_execute` chart results; canvas does not auto-open | OPEN |
| UI-AGENT-004 | mcp-agent.html / Welcome screen | Low | Welcome screen worker name hardcoded to "Market Risk Digital Worker" | OPEN |
| UI-AGENT-005 | mcp-agent.html / Sidebar | Low | Sidebar drag handle and file upload trigger buttons missing `aria-label` | OPEN |

**Critical issues: 7** (UI-ADMIN-001, 003, 004, 005, 006, 013, UI-AGENT-001)
**High issues: 5** (UI-ADMIN-007, 008, 015, UI-AGENT-002, UI-AGENT-003)
**Medium issues: 3** (UI-ADMIN-002, 009, 010)
**Low issues: 6** (UI-ADMIN-011, 012, 014, 016, UI-AGENT-004, 005)
**Total: 21 issues**

### Buttons confirmed working (admin.html)
Worker Config save, enable/disable toggle, file tree upload (Domain Data + Workflows), + Folder (mkdir), + New .md (createMd), Select/bulk-mode toggle, preview close, all Connectors page functions (Configure, Test, Save, Worker Mapping save).

### Buttons confirmed working (mcp-agent.html)
All 40+ button handlers verified defined — see full table above. No undefined handlers found except the Admin Panel button which is intentionally hidden but handler itself (`toggleAdminPanel`) is defined.

---

## Files Inspected

| File | Method |
|------|--------|
| `public/admin.html` | grep + Read (code inspection) + prior browser DOM verification |
| `public/mcp-agent.html` | grep + Read (code inspection) + prior browser DOM verification |
| `public/js/file-tree.js` | Read (class methods and DOM structure) |
| `agent_server.py` | grep (canvas SSE condition) |
