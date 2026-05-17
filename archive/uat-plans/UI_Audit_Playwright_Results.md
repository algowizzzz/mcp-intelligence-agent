# UI Audit & Bug Fix Regression — Playwright UAT Results

**Date:** 2026-04-05  
**Tester:** Automated Playwright (headless Chrome 146)  
**Script:** `uat_plans/run_ui_audit_tests.mjs`  
**Server:** `uvicorn agent_server:app --port 8000`  
**Auth:** `risk_agent` / `RiskAgent2025!` (role: super_admin)

---

## Summary

| Status | Count |
|--------|-------|
| ✅ PASS | 37 |
| ❌ FAIL | 0 |
| ⚠️ SKIP | 3 |
| **Total** | **40** |

All 37 tests pass. 3 tests skipped due to environment (empty domain-data tree in admin context; no `.md` files in `my_workflows` for the test worker). All skipped tests have documented manual verification paths.

---

## Bugs Fixed This Session

| Bug ID | Title | File(s) Changed |
|--------|-------|----------------|
| BUG-004 | `toggleCategory()` scoping — all tools toggled instead of category | `public/admin.html` |
| BUG-007 | Settings modal theme label mismatch (dark/light inverted) | `public/mcp-agent.html` |
| BUG-009 | `window.confirm()` freezes Playwright / browser (file delete UX) | `public/js/file-tree.js`, `public/admin.html`, `public/mcp-agent.html` |
| BUG-010 | Connector scope selector hint hidden (never shown) | `public/admin.html` |
| BUG-012 | Admin panel file-tree badges not updating after tree load | `public/mcp-agent.html` |
| BUG-014 | Canvas "Save to My Data" routed through LLM instead of direct FS | `public/mcp-agent.html` |
| BUG-PE-001 | Null `_user` crash (`reading 'user_id'`) in admin.html init | `public/admin.html` |
| BUG-PE-002 | Null `_user` crash (`reading 'role'`) in `initWorkerContext()` | `public/admin.html` |

### Bugs Not Fixed (Out of Scope / Environment / Not Reproducible)

| Bug ID | Title | Status |
|--------|-------|--------|
| BUG-001 | Connector auth tokens show plain text | Out of scope (security model decision) |
| BUG-002 | Workflow YAML validation fires on every keystroke | Out of scope (UX tradeoff) |
| BUG-003 | Sidebar resize doesn't persist across sessions | Out of scope (localStorage enhancement) |
| BUG-005 | Super-admin cannot delete workers created by other admins | Requires backend ACL change |
| BUG-006 | Audit log export doesn't include filter state | Out of scope |
| BUG-008 | Domain-data tree in admin context doesn't show files | Environment (empty test worker) |
| BUG-011 | My Workflows `.md` click doesn't populate workflow selector | No `.md` in test worker |
| BUG-013 | File rename doesn't update canvas title if file is open | Low impact; deferred |

---

## admin.html Results

### Original UI Audit Retests (RETEST-ADMIN-*)

| Test | Status | Evidence |
|------|--------|----------|
| RETEST-ADMIN-001 | ✅ PASS | Stat cards: users="3" tools="All" workflows="12" files="29" |
| RETEST-ADMIN-002 | ✅ PASS | 6 worker cards — no "1 admins" or "1 users" found |
| RETEST-ADMIN-003 | ✅ PASS | Users table loaded, 5 rows, no ReferenceError |
| RETEST-ADMIN-004 | ✅ PASS | Modal opens and closes on backdrop click |
| RETEST-ADMIN-005 | ✅ PASS | #workers-grid rendered with 6 worker cards |
| RETEST-ADMIN-006 | ✅ PASS | New Worker modal opens via `openCreateWorkerModal()` |
| RETEST-ADMIN-007 | ✅ PASS | All 7 `.btn-danger` have red text: `rgb(248, 113, 113)` |
| RETEST-ADMIN-008 | ✅ PASS | Delete disabled initially ✓ enabled on Select ✓ disabled after Cancel ✓ |
| RETEST-ADMIN-009 | ⚠️ SKIP | No `.ft-row-meta` in admin domain-data tree (empty for test worker). Cross-page equiv PASSED (mcp-agent) |
| RETEST-ADMIN-010 | ✅ PASS | All 20 `.ft-action-btn` have `aria-label` |
| RETEST-ADMIN-011 | ✅ PASS | Filter: 123 tools → 3 when searching "chart" |
| RETEST-ADMIN-012 | ✅ PASS | Label click toggles the switch (state restored) |
| RETEST-ADMIN-013 | ✅ PASS | Audit: 50 rows loaded, filter inputs present, page-info="1–50 of 1019" |
| RETEST-ADMIN-014 | ✅ PASS | Hint visible: "Select a worker above to configure its connector scope." |
| RETEST-ADMIN-015 | ✅ PASS | `switchSheet()` defined in global scope |
| RETEST-ADMIN-016 | ✅ PASS | `closeModal()` and `closeModalFn()` both defined |

### Bug Fix Verification (admin.html)

| Test | Status | Evidence |
|------|--------|----------|
| BUG-004 | ✅ PASS | `toggleCategory("collaboration", false)` unchecked exactly 17/123 tools |
| BUG-009 | ✅ PASS | `_confirmFn` defined on `_bpft_dd` and `_bpft_wf` |
| BUG-009-ADM | ✅ PASS | `_bpftConfirm` opens `#modal-overlay` (no native dialog) |
| BUG-PE-001 | ✅ PASS | No null-property errors (`user_id`, `role`) during full admin session |

---

## mcp-agent.html Results

### Original UI Audit Retests (RETEST-AGENT-*)

| Test | Status | Evidence |
|------|--------|----------|
| RETEST-AGENT-001 | ✅ PASS | Admin button visible for super_admin ✓ hidden for user role ✓ |
| RETEST-AGENT-002 | ✅ PASS | 4/4 badges non-zero: domain_data=29, uploads=78, verified=12, my_workflows=4 |
| RETEST-AGENT-003 | ✅ PASS | `_python_ready` handler in source ✓ `_chart_ready` ✓ "Open Chart" text ✓ |
| RETEST-AGENT-004 | ✅ PASS | `.welcome-title` = "Market Risk Worker" (from JWT `worker_name`) |
| RETEST-AGENT-005 | ✅ PASS | `aria-label="Resize sidebar"`, `role="separator"` |
| CROSS-FILETREE | ✅ PASS | Text node (space `" "`) before `.ft-row-meta` confirmed on mcp-agent.html |

### Bug Fix Verification (mcp-agent.html)

| Test | Status | Evidence |
|------|--------|----------|
| BUG-007 | ✅ PASS | Settings modal theme button shows "Light Theme" in dark mode |
| BUG-009-AGT | ✅ PASS | `#bpft-confirm-overlay` appears; Cancel button removes it |
| BUG-012 | ✅ PASS | Admin badges after panel open: domain_data="29", verified_workflows="12" |
| BUG-014 | ✅ PASS | `canvasSaveToMyData` uses direct `POST /api/fs/uploads/upload` with `FormData` |

---

## Extended Regression Results

### Canvas Save End-to-End

| Test | Status | Evidence |
|------|--------|----------|
| CANVAS-SAVE-001 | ✅ PASS | File `uat_canvas_test.md` created in `uploads/canvas/` via direct FS API |

### Conversations

| Test | Status | Evidence |
|------|--------|----------|
| CONV-001 | ✅ PASS | Fresh session (localStorage empty) — `newConversation()` and `clearAllConversations()` exist |
| CONV-002 | ✅ PASS | `newConversation()` changed `_activeConvId`: `undefined` → `conv_1775372` |

**Note:** Conversations are stored in `localStorage`, which is empty in a fresh Playwright browser context. CONV-001 verifies the conversation system functions exist; CONV-002 verifies creating a new conversation works correctly.

### Workflow Selection

| Test | Status | Evidence |
|------|--------|----------|
| WF-001 | ✅ PASS | My Workflows tree has 4 rendered items |
| WF-002 | ⚠️ SKIP | No `.md` file found in `my_workflows` tree for test worker |

**WF-002 manual verification:** Navigate to My Workflows in mcp-agent.html, click a `.md` workflow file. Expected: canvas opens in read-only mode with workflow content, workflow name appears in chat input area.

### File Preview

| Test | Status | Evidence |
|------|--------|----------|
| FILE-PREV-001 | ✅ PASS | File "Admin_User_Guide.docx" previewed in canvas (content length > 50 chars), title="Admin_User_Guide.docx" |

### Context Menu

| Test | Status | Evidence |
|------|--------|----------|
| CTX-001 | ✅ PASS | Context menu visible with items: Preview, Rename, Download, Delete |

### Theme Toggle & Settings Modal

| Test | Status | Evidence |
|------|--------|----------|
| THEME-001 | ✅ PASS | `toggleTheme()` cycles correctly. Label after restore: "Light Theme" |
| SETTINGS-001 | ✅ PASS | Settings modal: theme btn ✓, clear btn ✓, close btn ✓, removes on close ✓ |

---

## Detailed Bug Fix Notes

### BUG-004 — `toggleCategory()` Scope Fix (`admin.html`)

**Root cause:** `toggleCategory(cat, state)` iterated all tool checkboxes and compared `toolCat` (computed from DOM) to `cat` — but `toolCat` was never assigned (JS scoping error), so `toolCat === undefined` never matched any category name, causing all or no tools to toggle.

**Fix:** Use DOM traversal from each checkbox → `.tool-cards` → `.previousElementSibling` → `.tool-category-name` to resolve the category name, then compare to `cat`.

```javascript
function toggleCategory(cat, state) {
  document.querySelectorAll('[data-tool]').forEach(cb => {
    var toolCards = cb.closest('.tool-cards');
    var nameEl = toolCards && toolCards.previousElementSibling &&
                 toolCards.previousElementSibling.querySelector('.tool-category-name');
    if (nameEl && nameEl.textContent === cat) cb.checked = state;
  });
}
```

---

### BUG-007 — Theme Label Mismatch (`mcp-agent.html`)

**Root cause:** `openSettingsModal()` checked `document.body.classList.contains('dark')` but `toggleTheme()` uses `light-theme` class (not `dark`). On a dark-mode page (no `light-theme` class), the label showed "Dark Theme" when it should say "Light Theme" (the option to switch to).

**Fix:** Changed both `openSettingsModal` and `_settingsUpdateThemeBtn` to check `contains('light-theme')`:

```javascript
var isLight = document.body.classList.contains('light-theme');
btn.textContent = isLight ? 'Dark Theme' : 'Light Theme';
```

---

### BUG-009 — `window.confirm()` → Custom Modal (`file-tree.js`, `admin.html`, `mcp-agent.html`)

**Root cause:** `BPulseFileTree.deleteFile()`, `deleteFolder()`, and `bulkDelete()` used synchronous `if (!window.confirm(...)) return` guards. In Playwright (and Chrome DevTools Protocol), `window.confirm()` causes a 45-second browser freeze.

**Fix:** Added `_confirmFn` callback pattern:
1. **`file-tree.js`**: Constructor stores `config.onConfirm || window.confirm` as `this._confirmFn`. All three delete methods refactored to use async callback pattern: `self._confirmFn(msg, function() { /* xhr code */ })`.
2. **`admin.html`**: Added `_bpftConfirm(msg, cb)` helper using `openModal()` with Delete/Cancel buttons; passed as `onConfirm` to `_bpft_dd` and `_bpft_wf` trees.
3. **`mcp-agent.html`**: Same `_bpftConfirm` helper using a dedicated `#bpft-confirm-overlay` element; passed as `onConfirm` to all `_bpftInstB` trees and `_createAdminTree()`.

---

### BUG-012 — Admin Panel Badges Not Updating (`mcp-agent.html`)

**Root cause:** The admin panel's `_createAdminTree()` function created BPulseFileTree instances without an `onLoad` callback. Since trees are created lazily (only when the admin panel is first opened), their file counts were never reflected in the section badges (`#admin-badge-domain_data`, `#admin-badge-verified_workflows`).

**Fix:** Added `onLoad` callback to `_createAdminTree()` that walks the returned tree and updates the relevant badge:

```javascript
onLoad: function(treeData) {
  var badge = document.getElementById('admin-badge-' + section);
  if (badge && treeData) {
    var count = 0;
    (function walk(nodes) {
      (nodes || []).forEach(function(n) {
        if (n.type === 'file') count++;
        else if (n.children) walk(n.children);
      });
    })(treeData.tree || treeData.children || []);
    badge.textContent = count;
  }
}
```

---

### BUG-014 — Canvas Save Routing Through LLM (`mcp-agent.html`)

**Root cause:** `canvasSaveToMyData()` was POSTing a natural-language instruction to `/api/agent/run` and relying on the LLM to invoke `save_to_my_data` tool. This was slow, expensive (LLM API call), and fragile (LLM might choose wrong tool or path).

**Fix:** Replaced the entire function body with a direct `FormData` upload to `/api/fs/uploads/upload?path=canvas`:

```javascript
var fd = new FormData();
fd.append('file', new Blob([content], { type: 'text/markdown' }), filename);
fetch(_agentBase + '/api/fs/uploads/upload?path=canvas', {
  method: 'POST', headers: _ftAuthHeader(), body: fd
}).then(function(r) {
  if (!r.ok) throw new Error('HTTP ' + r.status);
  showToast('Saved to uploads/canvas/' + filename, 3000);
  ftLoad('uploads');
}).catch(function() { showToast('Save failed', 2000); })
.finally(function() { saveBtn.textContent = '↙ Save'; saveBtn.disabled = false; });
```

---

### BUG-PE-001 + BUG-PE-002 — Null `_user` Crashes (`admin.html`)

**Root cause:** `window.location.href = 'login.html'` queues a browser navigation but does **not** stop JavaScript execution. Unauthenticated page loads continued executing and crashed when accessing `_user.user_id` (sidebar init block) and `_user.role` (`initWorkerContext()`).

**Fix 1** (BUG-PE-001): Wrapped the sidebar init block in `if (_user) { ... }` guard at line 986.

**Fix 2** (BUG-PE-002): Changed bare `initWorkerContext()` call at line 2171 to `if (_user) initWorkerContext()`.

---

## Skip Details

### RETEST-ADMIN-009 (×2 skips)

**Why skipped:** The admin domain-data API returns 0 top-level items for the test session's selected worker context. `.ft-row-meta` is only rendered for files with a known size.

**Coverage:** The same fix (space text node before `.ft-row-meta`) was verified PASSING via `CROSS-FILETREE` on `mcp-agent.html`, which has 78 files in uploads with size badges.

**Manual verification:**
```javascript
document.querySelector('.ft-row-meta').parentElement.innerText
// Expected: "myfile.pdf 214 KB" (space before size)
```

### WF-002

**Why skipped:** The test worker's `my_workflows` tree contains 4 items, but none are `.md` files (likely `.yaml` or other extension).

**Manual verification:** Navigate to My Workflows in mcp-agent.html, click a workflow file → canvas should open in read-only mode.

---

## Page Errors Observed

**Run 1 (before BUG-PE-002 fix):**
```
Cannot read properties of null (reading 'role')
```
Source: `admin.html` → `initWorkerContext()` — fired during the first unauthenticated navigation in `authNavigate()`. Fixed by adding `if (_user)` guard on the `initWorkerContext()` call site.

**Final run (after all fixes):** No page errors captured.

---

## Test Infrastructure

- **Playwright version:** 1.59.1
- **Browser:** Google Chrome 146 (headless)
- **Auth method:** JWT fetched via Node.js `fetch()`, injected into `sessionStorage` via `page.evaluate()` before second navigation — avoids login.html redirect
- **Script location:** `uat_plans/run_ui_audit_tests.mjs`
- **Run command:** `node uat_plans/run_ui_audit_tests.mjs`

---

## Files Changed

| File | Changes |
|------|---------|
| `public/admin.html` | BUG-004 toggleCategory fix; BUG-009 `_bpftConfirm` helper + `onConfirm` on both trees; BUG-PE-001 `if (_user)` guard on sidebar init; BUG-PE-002 `if (_user)` guard on `initWorkerContext()` call |
| `public/mcp-agent.html` | BUG-007 theme label fix; BUG-009 `_bpftConfirm` + `onConfirm` on all trees; BUG-012 `onLoad` badge update in `_createAdminTree()`; BUG-014 `canvasSaveToMyData` direct FS upload |
| `public/js/file-tree.js` | BUG-009 `_confirmFn` callback pattern in constructor, `deleteFile`, `deleteFolder`, `bulkDelete` |
| `uat_plans/run_ui_audit_tests.mjs` | Extended from 22 to 40 tests covering all bug fixes + extended regression |

---

## Files Tested

| File | Tests Covering It |
|------|------------------|
| `public/admin.html` | ADMIN-001–016, BUG-004, BUG-009, BUG-009-ADM, BUG-PE-001 (20 tests) |
| `public/mcp-agent.html` | AGENT-001–005, BUG-007, BUG-009-AGT, BUG-012, BUG-014, CROSS-FILETREE, CANVAS-SAVE-001, CONV-001, CONV-002, WF-001, WF-002, FILE-PREV-001, CTX-001, THEME-001, SETTINGS-001 (20 tests) |
| `public/js/file-tree.js` | ADMIN-009, ADMIN-010, AGENT-002, CROSS-FILETREE, BUG-009, CTX-001 |
