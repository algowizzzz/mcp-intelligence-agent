# REQ-01a — Shared File Tree Library: Audit, Build & Swap
**Status:** Pending Implementation
**Version:** 2.0 (Updated 2026-04-04 — build-first, swap-then-clean approach)
**Scope:** Build `public/js/file-tree.js` (`BPulseFileTree`) and swap all three active implementations in `admin.html` and `mcp-agent.html` to use it. Delete replaced code only after each swap is verified. Phase 2 backend changes and additional features are tracked in REQ-01b.

---

## ⚠️ CRITICAL — READ BEFORE WRITING ANY CODE

This document covers one of the highest-risk changes in the platform. The file tree is the primary interface for all data management. If this breaks, **the entire platform becomes unusable for data access**.

**Approach: Build → Swap → Verify → Clean (never delete before build)**

1. Build `BPulseFileTree` as a complete shared library first
2. Swap one implementation at a time, testing after each swap
3. Delete the replaced old code only after the swap is verified working
4. Never delete working code before its replacement is proven

There are **three active implementations** across two files. All three are live. The goal is not to delete them upfront, but to replace them one by one.

---

## Phase 0 — Audit (Must complete before Phase 1)

### 0.1 What Exists Today: Three Active Implementations

#### Implementation A — `public/admin.html` (~840 lines, lines 1239–2079)

Admin panel file tree. Used for Domain Data and Workflows sections in the admin console.

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
| `_workerFileTreeUrl` | 1512–1517 | Builds upload endpoint URL |
| `_workerFileOpUrl` | 1519–1525 | Builds file-operation endpoint URL |
| `handleFileUpload` | 1527–1549 | Multipart upload handler |
| `adminNewFolder` | 1551–1562 | Create folder via `prompt()` — to be replaced with inline |
| `adminNewFile` | 1564–1576 | Create .md file via `prompt()` — to be replaced with inline |
| `renameItem` | 1578–1581 | Rename dispatcher |
| `deleteItem` | 1583–1602 | Single delete with confirm |
| `toggleSelectMode` | 1605–1620 | Toggles bulk select mode |
| `bulkDelete` | 1622–1659 | Batch delete |
| `isPathDir` | 1661–1669 | Directory check |
| `showContextMenu` | 1996–2030 | Right-click context menu |
| `closeContextMenu` | 2028–2030 | Closes context menu |
| `downloadFile` | 2032–2039 | Blob download |
| `startInlineRename` | 2042–2079 | Inline rename input + API call |
| `handleExternalDragOver/Leave/Drop` | 1939–1991 | External OS drag-drop → upload |

**Global variables (Implementation A only):**
`_treesData`, `_selectedItems`, `_selectModes`, `_drag`, `_ctxMenu`, `_uploadSection`

**HTML elements (Implementation A only):**
`tree-verified_workflows`, `tree-domain_data`, `preview-body`, `preview-body-wf`, `preview-file-name`, `preview-file-meta`

---

#### Implementation B — `public/mcp-agent.html` User Sidebar (`ft_*` prefix, ~650 lines, lines 5041–5716)

User chat sidebar file tree. Used for My Data, Domain Data, Verified Workflows, My Workflows sections in the chat UI left panel.

| Function | Lines | Description |
|---|---|---|
| `_ftHeaders` | 5053–5058 | Auth headers for `/api/fs/` |
| `_ftAuthHeader` | 5060–5066 | Auth-only header (for multipart uploads) |
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
| `pdfRenderPage`, `pdfNav`, `pdfZoom` | 5359–5384 | PDF controls |
| `ftLoadSheet` | 5438–5468 | SheetJS XLSX/CSV render |
| `ftOpenMdEditor` | 5469–5541 | Markdown editor for My Workflows |
| `ftBindDragDrop` | 5542–5596 | Drag-drop binding |
| `ftNewFolder` | 5599–5623 | Create folder inline |
| `ftNewFile` | 5625–5653 | Create .md file inline |
| `ftUploadFiles` | 5655–5669 | Batch upload |
| `ftDeleteFile` | 5671–5686 | Delete file |
| `ftDeleteFolder` | 5688–5696 | Delete folder |
| `ftCtxMenu` | 5699–5716 | Context menu |

**Global variables (Implementation B only):**
`_FT_SECTIONS`, `_ftTrees`, `_ftExpanded`, `_ftSectionOpen`

**HTML elements (Implementation B only):**
`ft-body-{section}`, `ft-tree-{section}`

---

#### Implementation C — `public/mcp-agent.html` Admin Panel (`admin_*` prefix, ~1,100 lines, lines 5900–6777)

Admin panel embedded inside the chat UI (accessible to admin/super_admin users). Handles Domain Data and Workflows for the current worker.

| Function | Lines | Description |
|---|---|---|
| `_adminHeaders`, `_adminJsonHeaders` | 5920–5931 | Auth headers |
| `_adminFileOpUrl` | 5933–5944 | Worker-scoped admin endpoint builder |
| `adminInit`, `toggleAdminPanel` | 5956–5977 | Panel init + toggle |
| `adminLoadAll`, `adminLoad` | 5979–5995 | Fetch admin section trees |
| `adminFtToggle`, `adminRenderTree`, `adminRenderNodes` | 5997–6098 | Render tree |
| `adminValidateMdIcons` | 6099–6123 | MD frontmatter validation icons |
| `adminDragStart/Over/Leave/Drop`, `adminMoveItem` | 6127–6186 | Drag-drop move |
| `adminToggleFolder`, `adminSelectFolder` | 6189–6218 | Folder toggle + upload destination |
| `adminNewFolder`, `adminNewFolderActive` | 6220–6251 | Create folder inline |
| `adminDeleteItem`, `adminConfirmClose` | 6253–6301 | Delete with confirmation modal |
| `adminCtxMenu` | 6304–6318 | Context menu |
| `adminPreviewFile`, `adminClosePreview` | 6321–6378 | Full-type file preview |
| `_fmtSize`, `_adminPreviewCsv`, `_adminPreviewExcel`, `_adminPreviewDocx` | 6380–6428 | Preview helpers |
| `adminRenameItem` | 6431–6473 | Inline rename + API |
| `adminToggleBulkSelect`, `adminCancelBulkSelect`, `adminBulkToggle`, `_adminBulkUpdateBar`, `adminBulkDelete` | 6479–6571 | Bulk select + delete |
| `adminQueueFiles`, `adminEnqueueFiles`, `adminUpdateQueueUI`, `adminProcessQueue` | 6574–6712 | XHR upload queue (best existing impl) |
| `adminRetry`, `adminRetryOverwrite`, `adminCancelQueue` | 6714–6777 | Upload retry + cancel |

**Global variables (Implementation C only):**
`_adminToken`, `_adminTrees`, `_adminExpanded`, `_adminSectionOpen`, `_adminSelectedSection`, `_adminSelectedFolder`, `_adminQueue`, `_adminUploading`, `_adminXhr`, `_adminDrag`, `_adminBulkSection`, `_adminBulkSelected`, `_adminConfirmCb`, `_ADMIN_SECTIONS`

**HTML elements (Implementation C only):**
`admin-zone`, `admin-body-{section}`, `admin-tree-{section}`, `admin-preview-panel`, `admin-preview-body`, `admin-confirm-modal`, `admin-queue-container`, `admin-queue-list`, `admin-bulk-bar`

---

### 0.2 Known Bugs in All Three Implementations (Must NOT carry forward)

**BUG-FS-001 — Rename concatenates old+new name**
Fix: after setting `input.value = currentName`, immediately call `input.select()` so typing replaces rather than appends.

**BUG-FS-002 — `PATCH /api/fs/{section}/file/used` returns 405**
Endpoint not implemented in `agent_server.py`. Fix: add handler that appends `{user_id, worker_id, section, path, used_at}` to `data/audit/file_used.jsonl`.

**BUG-FS-003 — Upload gives no progress feedback**
Only Implementation C has an XHR queue with progress. The new shared library must use XHR (not `fetch`) for uploads so `upload.onprogress` is available.

---

### 0.3 Best-of-Breed Features to Carry Forward

Take the best implementation of each feature from across all three:

| Feature | Best Source |
|---|---|
| XHR upload with progress bar + retry | Implementation C |
| Inline folder/file creation (no `prompt()`) | Implementations B and C |
| Bulk select + bulk delete | Implementations A and C |
| Workflow → chat chip selection | Implementation B |
| File attachment → context chip | Implementation B |
| PDF.js with paging + zoom | Implementation B |
| DOCX preview via mammoth.js | Implementation A |
| MD frontmatter validation icons | Implementation C |
| Drag-drop between sections | Implementation C |
| Drag-drop from OS (external files) | Implementation A |

---

## Phase 1 — Build Shared Library + Swap

### 1.1 New File: `public/js/file-tree.js`

A single self-contained IIFE. No framework dependencies (vanilla JS only). Imported in both `admin.html` and `mcp-agent.html` via:

```html
<script src="/js/file-tree.js"></script>
```

**Instantiation:**

```javascript
const tree = new BPulseFileTree({
  containerId: 'ft-tree-domain_data',
  section: 'domain_data',
  apiPrefix: '/api/fs',            // or /api/admin/worker/files, /api/super/workers/{id}/files
  writable: false,                 // domain_data and verified_workflows are read-only for users
  workflowSection: false,          // workflow sections show Select/Deselect chip button
  token: () => sessionStorage.getItem('bpulse_jwt'),
  onFileClick: null,               // callback(section, path, name, content)
  onWorkflowSelect: null,          // callback(section, path, name, content)
  onWorkflowDeselect: null,
  previewContainerId: null,        // canvas preview panel element id
});

tree.load();      // fetch + render
tree.refresh();   // re-fetch + re-render
tree.destroy();   // remove event listeners, clear DOM
```

**Core API methods:**

| Method | Description |
|---|---|
| `tree.load()` | Fetch tree from API and render |
| `tree.refresh()` | Re-fetch and re-render |
| `tree.mkdir(parentPath)` | Create folder inline (no `prompt()`) |
| `tree.rename(path, isDir)` | Inline rename (pre-selects existing name) |
| `tree.move(srcPath, destFolder)` | Move item within section |
| `tree.deleteFile(path)` | Delete file with confirmation |
| `tree.deleteFolder(path)` | Delete folder with confirmation + child count |
| `tree.upload(files, destFolder)` | XHR batch upload with per-file progress |
| `tree.createMd(parentPath)` | Create new .md file inline |
| `tree.download(path)` | Blob download |
| `tree.bulkDelete(paths)` | Batch delete selected items |
| `tree.setReadOnly(bool)` | Toggle write controls at runtime |

**Companion class: `BPulseFilePreview`**

```javascript
const preview = new BPulseFilePreview({ containerId: 'canvas-preview-panel' });
preview.render(section, path, name, content, apiPrefix, tokenFn);
preview.clear();
```

Supported file types:

| Extension | Renderer |
|---|---|
| `.md` | marked.js + DOMPurify |
| `.txt`, `.json`, `.csv` | Syntax-highlighted `<pre>` |
| `.pdf` | PDF.js with page controls + zoom |
| `.xlsx`, `.xls` | SheetJS table |
| `.docx` | mammoth.js → HTML |
| `.py` | highlight.js Python (read-only, see REQ-04a) |
| `.html` | Sandboxed `srcdoc` iframe |
| other | Raw text or binary size notice |

---

### 1.2 Feature Parity — New Library Must Have All of These

| Feature | Required | Notes |
|---|---|---|
| Tree render with icons by extension | ✅ | |
| Folder expand/collapse | ✅ | |
| Upload with XHR progress bar per file | ✅ | BUG-FS-003 fix |
| Upload queue (multi-file) with retry | ✅ | From Impl C |
| Create folder inline (no `prompt()`) | ✅ | |
| Create .md file inline | ✅ | |
| Rename inline (pre-selects existing name) | ✅ | BUG-FS-001 fix |
| Delete file with confirm | ✅ | |
| Delete folder with confirm + child count | ✅ | |
| Move within section (drag-drop) | ✅ | |
| Drag-drop from OS (external files) | ✅ | From Impl A |
| Bulk select + bulk delete | ✅ | |
| Context menu (right-click) | ✅ | |
| Download file | ✅ | |
| Read-only enforcement per section/role | ✅ | |
| Workflow select → chat chip | ✅ | From Impl B |
| File attach → context chip | ✅ | From Impl B |
| Preview: MD, text, JSON, CSV | ✅ | |
| Preview: PDF (PDF.js + paging + zoom) | ✅ | |
| Preview: XLSX (SheetJS) | ✅ | |
| Preview: DOCX (mammoth.js) | ✅ | |
| Preview: .py (syntax highlight) | ✅ | REQ-04a dependency |
| Edit + save My Workflows .md | ✅ | |
| MD frontmatter validation icons | ✅ | From Impl C |
| Drag between sections | ✅ | From Impl C |
| Copy between sections | ✅ | New — requires REQ-01b backend endpoint |
| File search/filter (client-side) | ✅ | New |
| File size + modified date in rows | ✅ | New — requires REQ-01b backend change |

---

### 1.3 Backend Endpoints (All Implemented, Ready to Use)

```
# User-scoped (role=user)
GET    /api/fs/{section}/tree
GET    /api/fs/{section}/file
POST   /api/fs/{section}/upload
PATCH  /api/fs/{section}/file              (create new .md)
POST   /api/fs/{section}/folder
POST   /api/fs/{section}/move
POST   /api/fs/{section}/rename
PATCH  /api/fs/{section}/file/used         ← BUG-FS-002: returns 405, fix in agent_server.py
DELETE /api/fs/{section}/file
DELETE /api/fs/{section}/folder

# Admin own-worker (role=admin)
GET/POST/PATCH/DELETE /api/admin/worker/files/{section}/*

# Super admin worker-scoped (role=super_admin)
GET/POST/PATCH/DELETE /api/super/workers/{id}/files/{section}/*
```

---

### 1.4 Swap Order and Test After Each

**Swap 1 — `admin.html` Implementation A**

1. Add `<script src="/js/file-tree.js"></script>` to admin.html
2. Instantiate `BPulseFileTree` for `domain_data` and `verified_workflows` sections
3. Verify the new tree works in admin console
4. Delete lines 1239–2079 (the old Implementation A code)
5. Run smoke tests (see 1.5)

**Swap 2 — `mcp-agent.html` Implementation B (user sidebar)**

1. Instantiate `BPulseFileTree` for all four user sidebar sections
2. Wire `onWorkflowSelect`, `onFileClick` callbacks to existing chat chip logic
3. Verify tree loads and file/workflow operations work
4. Delete lines 5041–5716 (the old Implementation B code)
5. Run smoke tests

**Swap 3 — `mcp-agent.html` Implementation C (admin panel inside chat UI)**

1. Instantiate `BPulseFileTree` for admin panel sections using admin API prefix
2. Wire upload queue, bulk delete, drag-drop between sections
3. Verify admin panel inside chat works for admin/super_admin users
4. Delete lines 5900–6777 (the old Implementation C code)
5. Run smoke tests

---

### 1.5 Smoke Tests After Each Swap

Run the full set after each of the three swaps.

**After Swap 1 (admin.html):**
- [ ] Admin console loads with zero JS errors
- [ ] Domain Data tree renders with correct folders and files
- [ ] Verified Workflows tree renders
- [ ] Upload a file → appears in tree
- [ ] Create folder → appears in tree
- [ ] Rename file → name updates correctly (pre-selects existing name)
- [ ] Delete file → removed from tree
- [ ] Right-click context menu appears with correct options
- [ ] Domain Data is read-only for admin role (no write buttons shown)
- [ ] All other admin console tabs (Users, Connectors, Audit) unaffected

**After Swap 2 (mcp-agent.html user sidebar):**
- [ ] Chat UI loads with zero JS errors
- [ ] All four sections visible (My Data, Domain Data, Verified Workflows, My Workflows)
- [ ] Click a workflow → workflow chip appears in chat input
- [ ] Click a file → file chip appears in chat input
- [ ] Upload file to My Data → appears in tree
- [ ] Create folder in My Workflows → appears
- [ ] Edit a .md workflow → editor opens, save works
- [ ] My Data and My Workflows are writable; Domain Data and Verified Workflows are read-only
- [ ] PDF preview opens with page controls
- [ ] DOCX preview renders via mammoth.js
- [ ] XLSX preview renders as table
- [ ] Chat sending, SSE streaming, canvas panel unaffected

**After Swap 3 (mcp-agent.html admin panel):**
- [ ] Admin panel toggle opens without JS errors (for admin/super_admin)
- [ ] Domain Data and Workflows trees render in admin panel
- [ ] Upload queue works (multi-file, progress bar, retry on failure)
- [ ] Bulk select → select multiple → bulk delete
- [ ] Drag-drop between sections (e.g. My Data → Verified Workflows)
- [ ] Inline rename pre-selects existing name
- [ ] All user-panel functions from Swap 2 still working

---

### 1.6 Definition of Done

Phase 1 is complete when ALL of the following are true:

- [ ] `public/js/file-tree.js` exists and is the single source of truth for all file tree rendering
- [ ] `admin.html` uses `BPulseFileTree` for all file tree sections
- [ ] `mcp-agent.html` user sidebar uses `BPulseFileTree` for all four sections
- [ ] `mcp-agent.html` admin panel uses `BPulseFileTree` for admin sections
- [ ] All old implementation code (Impl A lines 1239–2079, Impl B lines 5041–5716, Impl C lines 5900–6777) has been deleted
- [ ] BUG-FS-001 fixed (rename pre-selects)
- [ ] BUG-FS-002 fixed (`PATCH /api/fs/{section}/file/used` implemented)
- [ ] BUG-FS-003 fixed (XHR upload with progress)
- [ ] All smoke tests in 1.5 pass for all three swaps
- [ ] Zero JavaScript errors in browser console for any role (user, admin, super_admin)
- [ ] `grep -n "renderChildren\|ftRenderNodes\|adminRenderNodes\|loadFileTree\|adminLoad\b" public/admin.html public/mcp-agent.html` returns zero results

---

## Backend: BUG-FS-002 Fix Required

**File:** `agent_server.py`

Add the missing `PATCH /api/fs/{section}/file/used` endpoint:

```python
@app.patch('/api/fs/{section}/file/used')
async def fs_mark_file_used(section: str, body: dict = Body(...), payload: dict = Depends(require_jwt)):
    user_id = payload['sub']
    worker_id = payload.get('worker_id', '')
    path = body.get('path', '')
    entry = {
        'user_id': user_id,
        'worker_id': worker_id,
        'section': section,
        'path': path,
        'used_at': datetime.utcnow().isoformat() + 'Z'
    }
    audit_path = Path('sajhamcpserver/data/audit/file_used.jsonl')
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    return {'ok': True}
```

---

## Non-Functional Requirements

**NFR-FS-01** — Path traversal prevention: all paths validated server-side (already implemented, must not regress).

**NFR-FS-02** — Section access control: `domain_data` and `verified_workflows` read-only for `role=user`. Enforced in both frontend (`writable: false`) and backend.

**NFR-FS-03** — Upload max file size: 50 MB per file. Return 413 on violation.

**NFR-FS-04** — Allowed file types: block `.exe`, `.sh`, `.bat`, `.cmd`, `.dll`, `.so`. Return 415.

**NFR-FS-05** — Concurrent upload safety: per-path filelock.

**NFR-FS-06** — Empty folder delete safety: 409 if folder has children unless `?recursive=true` (admin-only).

---

## Out of Scope (See REQ-01b)

- Backend copy/batch-delete/quota endpoints
- File search/filter UI
- File size and modified date in tree rows
- Drag-drop between sections (backend move endpoint)
- File version history
