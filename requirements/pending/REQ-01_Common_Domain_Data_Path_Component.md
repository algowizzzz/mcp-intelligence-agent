# REQ-01 — Common Domain Data Path Component
**Status:** Pending Implementation
**Version:** 1.1 (Updated 2026-04-04 — retirement-first approach)
**Scope:** File tree, file operations, and preview subsystem across admin.html and mcp-agent.html

---

## ⚠️ IMPORTANT — READ BEFORE WRITING ANY CODE

**Nothing in this document is built until Phase 0 (code retirement) is complete.**

The platform has three separate, largely duplicate implementations of file-tree logic spread across two files. Before any new shared library is written, every old implementation must be explicitly identified, archived, and removed. Building on top of unretired code risks:
- Silent conflicts between old and new event handlers
- Duplicate global variable names causing runtime errors
- Confusion about which code path is active
- Inability to test the new implementation cleanly

The retirement process is the first deliverable. New code comes after.

---

## Phase 0 — Code Retirement (Must complete before Phase 1)

### 0.1 What Exists Today: Full Inventory

There are **three separate file-tree implementations** totalling approximately **2,590 lines** of JavaScript across two files.

#### Implementation A — `public/admin.html` (~840 lines)

File-tree code runs from roughly line 1239 to line 2079.

| Function | Lines | Description |
|---|---|---|
| `_workerFileTreeUrl` | 1243–1249 | Builds worker-scoped file tree API URL |
| `loadFileTree` | 1251–1263 | Fetches tree from API, triggers render |
| `renderTree` | 1265–1270 | Entry-point for tree render |
| `renderChildren` | 1275–1394 | Recursive node renderer (drag, click, context) |
| `closePreview` | 1399–1407 | Clears preview panel |
| `previewFile` | 1409–1492 | Fetches + renders file (text/CSV/PDF/DOCX/XLSX/MD) |
| `renderSheet` | 1494–1498 | SheetJS XLSX renderer |
| `escHtml` | 1500 | HTML escape utility |
| `adminUpload` | 1505–1510 | Opens file input |
| `_workerUploadUrl` | 1512–1517 | Builds upload endpoint URL |
| `_workerFileOpUrl` | 1519–1525 | Builds file-operation endpoint URL |
| `handleFileUpload` | 1527–1549 | Multipart upload handler |
| `adminNewFolder` | 1551–1562 | Create folder via `prompt()` |
| `adminNewFile` | 1564–1576 | Create .md file via `prompt()` |
| `renameItem` | 1578–1581 | Rename dispatcher |
| `deleteItem` | 1583–1602 | Single delete with confirm |
| `toggleSelectMode` | 1605–1620 | Toggles bulk select mode |
| `bulkDelete` | 1622–1659 | Batch delete |
| `isPathDir` | 1661–1669 | Checks if path is a directory |
| `showContextMenu` | 1996–2030 | Right-click context menu |
| `closeContextMenu` | 2028–2030 | Closes context menu |
| `downloadFile` | 2032–2039 | Blob download |
| `startInlineRename` | 2042–2079 | Inline rename input + API call |
| `handleExternalDragOver` | 1939–1948 | External drag-over handler |
| `handleExternalDragLeave` | 1950–1953 | External drag-leave handler |
| `handleExternalDrop` | 1955–1991 | External drop → upload |

**Global variables used only by Implementation A:**
- `_treesData` (line 1239)
- `_selectedItems` (line 1240)
- `_selectModes` (line 1241)
- `_drag` (line 1273)
- `_ctxMenu` (line 1994)
- `_uploadSection` (line 1503)

**HTML elements used only by Implementation A:**
- `tree-verified_workflows`, `tree-domain_data` (tree containers)
- `preview-body`, `preview-body-wf` (preview panels)
- `preview-file-name`, `preview-file-meta`

**CSS classes introduced by Implementation A:**
- `.tree-item`, `.tree-indent`, `.tree-rename-input`
- `.context-menu`, `.context-menu-item`, `.context-menu-sep`
- `.drop-active`, `.select-mode`

---

#### Implementation B — `public/mcp-agent.html` User Panel (`ft_*` prefix, ~650 lines)

File-tree code runs from roughly line 5041 to line 5716.

| Function | Lines | Description |
|---|---|---|
| `_ftHeaders` | 5053–5058 | Auth headers for `/api/fs/` |
| `_ftAuthHeader` | 5060–5066 | Auth-only header (multipart) |
| `ftLoad` | 5068–5078 | Fetch tree from `/api/fs/{section}/tree` |
| `ftLoadAll` | 5080–5082 | Load all sections in parallel |
| `ftToggle` | 5084–5097 | Section expand/collapse |
| `ftCountFiles` | 5099–5107 | Recursive file count |
| `ftUpdateBadge` | 5109–5114 | File count badge update |
| `ftFileIcon` | 5116–5130 | Extension → SVG icon |
| `ftFolderIcon` | 5132–5137 | Folder SVG icon |
| `ftRenderTree` | 5139–5150 | Full tree render for section |
| `ftRenderNodes` | 5152–5211 | Recursive node render |
| `ftToggleFolder` | 5212–5216 | Folder expand toggle |
| `ftFileClick` | 5218–5230 | File click → preview or select |
| `_ftSelectWorkflowForChat` | 5231–5253 | Fetch workflow → active chip |
| `_ftAddFileToChat` | 5254–5267 | File → context chips |
| `ftToggleFileSelection` | 5268–5271 | Toggle file in `_selectedFiles` |
| `ftPreviewWorkflow` | 5272–5315 | Workflow markdown preview |
| `ftPreviewFile` | 5316–5391 | Full-type file preview (canvas) |
| `ftLoadPdf` | 5392–5437 | PDF.js render |
| `pdfRenderPage` | 5359–5373 | PDF page render |
| `pdfNav` | 5375–5379 | PDF page navigation |
| `pdfZoom` | 5381–5384 | PDF zoom |
| `ftLoadSheet` | 5438–5468 | SheetJS XLSX/CSV render |
| `ftOpenMdEditor` | 5469–5541 | Markdown editor for My Workflows |
| `ftBindDragDrop` | 5542–5596 | Drag-drop binding |
| `ftNewFolder` | 5599–5623 | Create folder inline |
| `ftNewFile` | 5625–5653 | Create .md file inline |
| `ftUploadFiles` | 5655–5669 | Batch upload |
| `ftDeleteFile` | 5671–5686 | Delete file |
| `ftDeleteFolder` | 5688–5696 | Delete folder |
| `ftCtxMenu` | 5699–5716 | Context menu |

**Global variables used only by Implementation B:**
- `_FT_SECTIONS` (5041–5051) — section metadata
- `_ftTrees` (5321)
- `_ftExpanded` (5322)
- `_ftSectionOpen` (5323)

**HTML elements used only by Implementation B:**
- `ft-body-{section}`, `ft-tree-{section}`

**CSS classes introduced by Implementation B:**
- `.ft-row`, `.ft-row-chevron`, `.ft-row-name`, `.ft-row-actions`
- `.ft-icon`, `.ft-indent`, `.ft-action-btn`
- `.ft-inline-input`, `.wf-active`
- `.ctx-chip`, `.ctx-chip-remove`, `.workflow-chip`

---

#### Implementation C — `public/mcp-agent.html` Admin Panel (`admin_*` prefix, ~1,100 lines)

File-tree code runs from roughly line 5900 to line 6777.

| Function | Lines | Description |
|---|---|---|
| `_adminHeaders` | 5920–5925 | Auth headers for admin API |
| `_adminJsonHeaders` | 5927–5931 | JSON + auth headers |
| `_adminFileOpUrl` | 5933–5944 | Worker-scoped admin endpoint builder |
| `_decodeJwt` | 5946–5954 | JWT decode from sessionStorage |
| `adminInit` | 5956–5959 | Token init |
| `toggleAdminPanel` | 5961–5977 | Show/hide admin panel |
| `adminLoadAll` | 5979–5981 | Load all admin sections |
| `adminLoad` | 5983–5995 | Fetch admin section tree |
| `adminFtToggle` | 5997–6010 | Section toggle |
| `adminRenderTree` | 6012–6022 | Tree entry point |
| `adminRenderNodes` | 6024–6098 | Recursive node render |
| `adminValidateMdIcons` | 6099–6123 | MD frontmatter validation icons |
| `adminDragStart` | 6127–6139 | Drag source handler |
| `adminDragOver` | 6141–6151 | Drag-over |
| `adminDragLeave` | 6153–6157 | Drag-leave |
| `adminDrop` | 6159–6170 | Drop → move |
| `adminMoveItem` | 6172–6186 | Move file to dest folder |
| `adminToggleFolder` | 6189–6193 | Folder expand toggle |
| `adminSelectFolder` | 6195–6218 | Select upload dest folder |
| `adminNewFolder` | 6220–6246 | Create folder inline |
| `adminNewFolderActive` | 6248–6251 | Helper: create in selected location |
| `adminDeleteItem` | 6253–6295 | Delete with confirmation modal |
| `adminConfirmClose` | 6297–6301 | Close confirm modal |
| `adminCtxMenu` | 6304–6318 | Context menu |
| `adminPreviewFile` | 6321–6373 | Full-type preview |
| `adminClosePreview` | 6375–6378 | Close preview |
| `_fmtSize` | 6380–6384 | Format bytes → human-readable |
| `_adminPreviewCsv` | 6386–6403 | CSV/TSV table preview |
| `_adminPreviewExcel` | 6405–6416 | SheetJS Excel preview |
| `_adminPreviewDocx` | 6418–6428 | Mammoth DOCX preview |
| `adminRenameItem` | 6431–6473 | Inline rename + API |
| `adminToggleBulkSelect` | 6479–6492 | Enter bulk select mode |
| `adminCancelBulkSelect` | 6494–6504 | Exit bulk select mode |
| `adminBulkToggle` | 6506–6510 | Toggle item in selection |
| `_adminBulkUpdateBar` | 6512–6518 | Update bulk action bar |
| `adminBulkDelete` | 6520–6571 | Batch delete selected |
| `adminQueueFiles` | 6574–6579 | Queue files from input |
| `adminEnqueueFiles` | 6581–6611 | Enqueue with validation |
| `adminUpdateQueueUI` | 6613–6646 | Render upload queue UI |
| `adminProcessQueue` | 6648–6712 | XHR upload queue processing |
| `adminRetry` | 6714–6722 | Retry failed upload |
| `adminRetryOverwrite` | 6724–6770 | Retry with overwrite |
| `adminCancelQueue` | 6772–6777 | Cancel queue |

**Global variables used only by Implementation C:**
- `_adminToken` (5902), `_adminTrees` (5904), `_adminExpanded` (5905)
- `_adminSectionOpen` (5906), `_adminSelectedSection` (5907)
- `_adminSelectedFolder` (5908), `_adminQueue` (5909)
- `_adminUploading` (5910), `_adminXhr` (5911)
- `_adminDrag` (6125), `_adminBulkSection` (6476)
- `_adminBulkSelected` (6477), `_adminConfirmCb` (5913)
- `_ADMIN_SECTIONS` (5915–5918)

**HTML elements used only by Implementation C:**
- `admin-zone`, `admin-body-{section}`, `admin-tree-{section}`
- `admin-preview-panel`, `admin-preview-body`
- `admin-confirm-modal`
- `admin-queue-container`, `admin-queue-list`
- `admin-bulk-bar`

**CSS classes introduced by Implementation C:**
- `.admin-bulk-checkbox`, `.admin-drop-target`
- `.admin-preview-panel`, `.admin-preview-body`
- `.admin-queue-item`, `.admin-queue-badge`, `.admin-progress-bar`
- `.admin-bulk-bar`, `.admin-inline-input`

---

### 0.2 Shared Code (Do NOT Delete)

The following are used by Implementation B and C simultaneously and must not be removed until both are replaced:

- `ft-ctx-menu` HTML element and CSS (shared between user panel and admin panel in mcp-agent.html)
- `_ftHeaders` / `_ftAuthHeader` — may be reused by new shared library
- PDF.js references (shared PDF render logic)

---

### 0.3 Retirement Strategy

**Method: Archive via Git branch, then delete from main**

Do NOT simply comment out code — commented-out code accumulates and causes confusion. The correct approach:

1. **Create an archive branch** before any deletions:
   ```bash
   git checkout -b archive/legacy-file-tree-implementations
   git push origin archive/legacy-file-tree-implementations
   ```
   This branch permanently preserves the full working state of all three implementations with their exact line numbers, so nothing is ever truly lost.

2. **On main/development branch**: Delete the code blocks listed in 0.4 below, in the order specified.

3. **Commit each file separately** with a clear message:
   ```
   chore: retire legacy file tree Implementation A from admin.html
   chore: retire legacy file tree Implementation B (ft_*) from mcp-agent.html
   chore: retire legacy file tree Implementation C (admin_*) from mcp-agent.html
   ```

4. **Smoke-test after each deletion** (see 0.5) before proceeding to next.

---

### 0.4 Exact Deletion Plan

**Step 1 — Delete Implementation A from admin.html**

Remove the following contiguous block from `admin.html`:
- Lines 1239–1669 (global variable declarations + all file-tree functions)
- Lines 1939–1991 (external drag-drop handlers)
- Lines 1994–2079 (context menu + inline rename)

Also remove:
- The HTML elements: `tree-verified_workflows`, `tree-domain_data`, `preview-body`, `preview-body-wf`, `preview-file-name`, `preview-file-meta` and their containing `<div>` wrappers
- CSS class definitions for `.tree-item`, `.tree-indent`, `.tree-rename-input`, `.context-menu`, `.context-menu-item`, `.context-menu-sep`, `.drop-active`, `.select-mode`

**Step 2 — Delete Implementation B from mcp-agent.html**

Remove lines 5041–5716 entirely (the `_FT_SECTIONS` variable declaration through `ftCtxMenu`).

Also remove:
- HTML elements: `ft-body-{section}`, `ft-tree-{section}` containers and their parent wrappers
- CSS class definitions for `.ft-row`, `.ft-row-chevron`, `.ft-row-name`, `.ft-row-actions`, `.ft-icon`, `.ft-indent`, `.ft-action-btn`, `.ft-inline-input`, `.wf-active`, `.ctx-chip`, `.ctx-chip-remove`, `.workflow-chip`

**Step 3 — Delete Implementation C from mcp-agent.html**

Remove lines 5900–6777 (from `_adminToken` variable declaration through `adminCancelQueue`).

Also remove:
- HTML elements: `admin-zone`, `admin-body-{section}`, `admin-tree-{section}`, `admin-preview-panel`, `admin-confirm-modal`, `admin-queue-container`, `admin-bulk-bar`
- CSS: `.admin-bulk-checkbox`, `.admin-drop-target`, `.admin-preview-panel`, `.admin-preview-body`, `.admin-queue-item`, `.admin-queue-badge`, `.admin-progress-bar`, `.admin-bulk-bar`, `.admin-inline-input`

> **Note:** After all three deletions, both files will have placeholder `<div>` containers where the trees used to render. These are intentional and will be filled by the new shared library in Phase 1.

---

### 0.5 Smoke Tests After Each Deletion

Run these checks after deleting each implementation to confirm nothing else broke:

**After deleting Implementation A (admin.html):**
- [ ] Login page still loads correctly
- [ ] Admin console loads without JS errors in console
- [ ] Dashboard stats load (GET /api/super/workers, GET /api/super/users)
- [ ] User management, Connectors, Audit Log tabs still function
- [ ] **Expected failure (intentional):** Domain Data and Workflows tabs show empty/blank panels — this is correct

**After deleting Implementation B (mcp-agent.html ft_* functions):**
- [ ] Chat interface loads without JS errors
- [ ] Message sending still works
- [ ] Token counter still updates
- [ ] Settings/theme toggle still works
- [ ] **Expected failure (intentional):** Left sidebar file tree panels are blank — this is correct

**After deleting Implementation C (mcp-agent.html admin_* functions):**
- [ ] Chat interface still loads (same checks as above)
- [ ] **Expected failure (intentional):** Admin panel inside chat UI is blank — this is correct

---

### 0.6 Definition of Done for Phase 0

Phase 0 is complete when ALL of the following are true:

- [ ] Archive branch `archive/legacy-file-tree-implementations` pushed to remote
- [ ] All three implementations deleted from their respective files
- [ ] Three separate commits made (one per implementation deleted)
- [ ] Both files load in browser with zero JavaScript errors in console (only the expected blank panels)
- [ ] All non-file-tree functionality (auth, chat, audit log, connectors, user management) works as before
- [ ] No commented-out file-tree code remains in either file
- [ ] `grep -n "renderChildren\|ftRenderNodes\|adminRenderNodes" public/admin.html public/mcp-agent.html` returns zero results

Only after 0.6 is fully checked off does Phase 1 begin.

---

## Phase 1 — Shared Library Implementation

### 1.1 Background & Current State (Post-Retirement)

After Phase 0, both files will have empty panel containers where the three implementations used to live. The backend is fully implemented and unchanged — all API endpoints are working (see section 2 below). The work is entirely frontend.

The following capabilities were confirmed working across all three retired implementations and must be preserved in the new shared library:

**Tree operations (all 3 implementations had these):**
- `GET /{prefix}/files/{section}` → render tree (folder expand/collapse, icons by extension)
- `POST /{prefix}/files/{section}/folder` → create folder
- `POST /{prefix}/files/{section}/rename` → rename file or folder
- `POST /{prefix}/files/{section}/move` → move file or folder within section
- `DELETE /{prefix}/files/{section}/file` → delete file (with confirm)
- `DELETE /{prefix}/files/{section}/folder` → delete folder (with confirm)
- `PATCH /{prefix}/files/{section}/file` → create new `.md` file
- `POST /{prefix}/files/{section}/upload` → multipart upload

**Preview (all 3 had these, Implementation A and B had the most complete versions):**
- Plain text, CSV, JSON, MD (rendered as markdown)
- PDF via PDF.js
- DOCX via mammoth.js
- XLSX via SheetJS

**Additional from Implementation C (must carry forward):**
- XHR-based upload with progress bar and queue (this was the best upload implementation)
- Bulk select + bulk delete with count badge
- Drag-drop between sections (domain_data ↔ verified_workflows)

**Additional from Implementation B (must carry forward):**
- Workflow selection → chat input chip (single active workflow)
- File attachment → chat context chips (multiple files)
- Section read-only enforcement (domain_data and verified are read-only for users)
- Canvas preview panel with full PDF.js paging and zoom

---

### 1.2 Backend Endpoints (All Implemented, No Changes Needed)

```
# User-scoped (role=user)
GET    /api/fs/{section}/tree
GET    /api/fs/{section}/file
POST   /api/fs/{section}/upload
PATCH  /api/fs/{section}/file
POST   /api/fs/{section}/folder
POST   /api/fs/{section}/move
POST   /api/fs/{section}/rename
PATCH  /api/fs/{section}/file/used        ← returns 405 — BUG-FS-002 fix required
DELETE /api/fs/{section}/file
DELETE /api/fs/{section}/folder

# Admin own-worker (role=admin)
GET/POST/PATCH/DELETE /api/admin/worker/files/{section}/*

# Super admin worker-scoped (role=super_admin)
GET/POST/PATCH/DELETE /api/super/workers/{id}/files/{section}/*
```

---

### 1.3 New Shared Library: `public/js/file-tree.js`

Create a new file `public/js/file-tree.js` as a single self-contained IIFE (no framework dependencies). Both `admin.html` and `mcp-agent.html` import it via `<script src="/js/file-tree.js"></script>`.

**Configuration object (passed at instantiation):**

```javascript
const tree = new BPulseFileTree({
  containerId: 'ft-tree-domain_data',   // target DOM element id
  section: 'domain_data',
  apiPrefix: '/api/fs',                  // or /api/super/workers/{id}/files, /api/admin/worker/files
  writable: false,                       // read-only sections get no create/rename/delete UI
  workflowSection: false,                // workflow sections get Select/Deselect for chat chip
  token: () => sessionStorage.getItem('bpulse_jwt'),
  onFileClick: null,                     // optional callback(section, path, name, content)
  onWorkflowSelect: null,                // optional callback(section, path, name, content)
  onWorkflowDeselect: null,
  previewContainerId: null,              // optional: canvas preview panel id
});
tree.load();
tree.refresh();
tree.destroy();  // removes event listeners, clears DOM
```

**Core API:**

| Method | Description |
|---|---|
| `tree.load()` | Fetch and render tree |
| `tree.refresh()` | Re-fetch and re-render |
| `tree.mkdir(parentPath)` | Create folder |
| `tree.rename(path, isDir)` | Inline rename |
| `tree.move(srcPath, destFolder)` | Move item |
| `tree.deleteFile(path)` | Delete file |
| `tree.deleteFolder(path)` | Delete folder |
| `tree.upload(files, destFolder)` | XHR upload with progress |
| `tree.createMd(parentPath)` | Create new .md file |
| `tree.download(path)` | Blob download |
| `tree.bulkDelete(paths)` | Batch delete |
| `tree.setReadOnly(bool)` | Toggle write controls at runtime |

**Shared preview class: `BPulseFilePreview`**

```javascript
const preview = new BPulseFilePreview({ containerId: 'canvas-preview-panel' });
preview.render(section, path, name, content, apiPrefix, tokenFn);
preview.clear();
```

Supported extensions:

| Extension | Renderer |
|---|---|
| .md | marked.js + DOMPurify |
| .txt, .json, .csv | Syntax-highlighted `<pre>` |
| .pdf | PDF.js with paging + zoom controls |
| .xlsx, .xls | SheetJS table |
| .docx | mammoth.js → HTML |
| .py | highlight.js Python (see REQ-04) |
| .html | Sandboxed srcdoc iframe |
| other | Raw text or binary size notice |

---

### 1.4 Known Bugs to Fix During Implementation

These bugs existed in all three retired implementations and must NOT be carried forward:

**BUG-FS-001 — Rename concatenates old+new name**
All three had this. Fix: after setting `input.value = currentName`, call `input.select()` immediately so typing replaces rather than appends.

**BUG-FS-002 — `PATCH /api/fs/{section}/file/used` returns 405**
Backend endpoint not implemented. Fix in `agent_server.py`: wire the handler to append `{user_id, worker_id, section, path, used_at}` to `data/audit/file_used.jsonl`.

**BUG-FS-003 — Upload gives no feedback**
Only Implementation C had an XHR queue (the best design). The new library must use XHR (not fetch) for upload to support `upload.onprogress`. Show a progress bar per file and a queue counter for multi-file batches.

---

### 1.5 Feature Parity Requirements (New Library Must Have)

The new implementation must replicate all capabilities from the three retired versions plus fill the gaps:

| Feature | Must Have | Source |
|---|---|---|
| Tree render with icons | ✅ | All three |
| Upload with XHR progress bar | ✅ | Implementation C |
| Create folder (inline, no prompt()) | ✅ | Implementations B and C |
| Create .md file (inline) | ✅ | Implementations B and C |
| Rename (pre-selects existing name) | ✅ | Bug fix required |
| Delete file with confirm | ✅ | All three |
| Delete folder with confirm + child count | ✅ | All three |
| Move within section (drag-drop) | ✅ | All three |
| Copy between sections | ✅ | New — not in any old impl |
| Bulk select + bulk delete | ✅ | Implementations A and C |
| Context menu (right-click) | ✅ | All three |
| External OS drag-drop | ✅ | Implementation A |
| Read-only enforcement | ✅ | Implementation B |
| Workflow select chip | ✅ | Implementation B |
| File attach chip | ✅ | Implementation B |
| Preview: MD, text, JSON, CSV | ✅ | All three |
| Preview: PDF (PDF.js) | ✅ | Implementations B and C |
| Preview: XLSX (SheetJS) | ✅ | All three |
| Preview: DOCX (mammoth.js) | ✅ | Implementations A and B |
| Preview: .py (syntax highlight) | ✅ | New — REQ-04 |
| Edit + save My Workflows .md | ✅ | Implementation B had partial |
| File search/filter (client-side) | ✅ | New |
| File size + modified date in tree | ✅ | New (requires backend change) |
| Drag between sections | ✅ | Implementation C only |
| MD frontmatter validation icons | ✅ | Implementation C only |

---

## Phase 2 — Bug Fixes & Backend Changes

These backend changes are required to support new features in the shared library:

| Change | Endpoint | Priority |
|---|---|---|
| Fix file/used 405 | `PATCH /api/fs/{section}/file/used` | Critical |
| Add `size_bytes` + `modified_at` to tree response | `GET /api/fs/{section}/tree` | High |
| Copy endpoint | `POST /api/fs/{section}/copy` | High |
| Batch delete | `POST /api/fs/{section}/batch-delete` | Medium |
| Quota endpoint | `GET /api/fs/{section}/quota` | Low |

---

## Phase 3 — Additional Features (After Core is Stable)

**F-SEARCH-01 — File search / filter within tree**
Client-side name filter using the already-loaded tree data. No new API call.

**F-META-01 — File size and last modified in tree rows**
Requires `size_bytes` and `modified_at` in tree API response.

**F-COPY-01 — Copy file between sections**
Context menu → "Copy to…" modal → `POST /{prefix}/copy`.

**F-VERSION-01 — File version history** (Phase 3, low priority)
On write, backend preserves previous version in `.versions/` subdirectory. Max 5 versions. "History" context menu item.

---

## Non-Functional Requirements

**NFR-FS-01** — Path traversal prevention: all paths validated server-side, already implemented, must not regress.

**NFR-FS-02** — Section access control: `domain_data` and `verified_workflows` remain read-only for `role=user`. Enforced in backend.

**NFR-FS-03** — Upload max file size: 50 MB per file, configurable via `UPLOAD_MAX_SIZE_MB`. Return 413 on violation.

**NFR-FS-04** — Allowed file types: block `.exe`, `.sh`, `.bat`, `.cmd`, `.dll`, `.so`. Return 415.

**NFR-FS-05** — Concurrent upload safety: per-path filelock.

**NFR-FS-06** — Empty folder delete safety: 409 if folder has children unless `?recursive=true` (admin-only).

---

## Acceptance Criteria (Overall)

**Phase 0:**
- [ ] Archive branch exists and is pushed to remote
- [ ] Zero file-tree functions remain in admin.html and mcp-agent.html (verified by grep)
- [ ] Both pages load in browser with zero JS console errors
- [ ] All non-file-tree functionality unaffected

**Phase 1:**
- [ ] `public/js/file-tree.js` exists and is the single source of truth for all tree rendering
- [ ] admin.html uses `BPulseFileTree` for Domain Data and Workflows sections
- [ ] mcp-agent.html uses `BPulseFileTree` for all four sections (user panel + admin panel)
- [ ] BUG-FS-001, BUG-FS-002, BUG-FS-003 fixed
- [ ] All features from the feature parity table above present and working

**Phase 2+:**
- [ ] New endpoints implemented (copy, batch-delete, quota)
- [ ] File search/filter works client-side
- [ ] File size and modified date visible in tree rows

---

## Out of Scope

- Real-time collaborative editing
- Git-based version control integration
- Full-text content search (search inside file contents)
- S3 or cloud storage backend (see REQ-08)
