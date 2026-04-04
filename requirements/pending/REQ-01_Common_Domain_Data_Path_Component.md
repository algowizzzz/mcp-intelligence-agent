# REQ-01 — Common Domain Data Path Component
**Status:** Pending Implementation
**Version:** 1.0
**Date:** 2026-04-04
**Scope:** File tree, file operations, and preview subsystem across admin.html and mcp-agent.html

---

## 1. Background & Current State

The platform currently ships three separate implementations of nearly identical file tree and file operation logic:

| Implementation | File | Used By |
|---|---|---|
| Admin file tree | `public/admin.html` lines 586–2100 | super_admin and admin roles in admin console |
| User file tree | `public/mcp-agent.html` lines 2820–5696 | End-user (role=user) in chat interface |
| Admin panel in chat | `public/mcp-agent.html` lines 3110–6520 | super_admin viewing worker files from chat UI |

All three share the same conceptual model: a JSON tree, CRUD operations against `/api/fs/`, `/api/super/workers/{id}/files/`, or `/api/admin/worker/files/` endpoints, file preview, and upload. Code duplication is high — tree rendering, file type detection, preview, delete confirmation, rename, and upload are each implemented 2–3 times independently. This creates maintenance risk and inconsistent UX across roles.

### 1.1 What Is Already Built

The following capabilities are implemented and working:

**Tree operations (all 3 implementations):**
- `GET /{prefix}/files/{section}` → render tree (folder expand/collapse, icons by extension)
- `POST /{prefix}/files/{section}/folder` → create folder
- `POST /{prefix}/files/{section}/rename` → rename file or folder
- `POST /{prefix}/files/{section}/move` → move file or folder within section
- `DELETE /{prefix}/files/{section}/file` → delete file (with confirm)
- `DELETE /{prefix}/files/{section}/folder` → delete folder (with confirm)
- `PATCH /{prefix}/files/{section}/file` → create new `.md` file
- `POST /{prefix}/files/{section}/upload` → multipart upload

**Preview (all 3 implementations):**
- Plain text (.txt, .csv, .json, .md rendered as markdown)
- PDF via iframe embed
- DOCX via mammoth.js client-side decode
- XLSX via SheetJS client-side decode

**Additional (admin.html and mcp-agent.html admin panel):**
- Drag-drop internal moves (within section)
- Bulk select + bulk delete
- Context menu (right-click) with preview, rename, download, delete
- Inline rename on double-click
- External drag-drop from OS file manager

**Additional (mcp-agent.html user panel):**
- Workflow selection → chat input chip (single active workflow)
- File attachment → chat context chips (multiple files)
- Section read-only enforcement (`domain_data`, `verified` are read-only for users)
- Canvas preview panel (rich preview with PDF.js, SheetJS, markdown renderer)
- Upload to My Data section

### 1.2 Backend Endpoints (All Implemented)

```
# User-scoped (role=user)
GET    /api/fs/{section}/tree
GET    /api/fs/{section}/file
POST   /api/fs/{section}/upload
PATCH  /api/fs/{section}/file
POST   /api/fs/{section}/folder
POST   /api/fs/{section}/move
POST   /api/fs/{section}/rename
PATCH  /api/fs/{section}/file/used        ← returns 405 (NOT IMPLEMENTED, BUG)
DELETE /api/fs/{section}/file
DELETE /api/fs/{section}/folder

# Admin own-worker (role=admin)
GET    /api/admin/worker/files/{section}
POST   /api/admin/worker/files/{section}/upload
GET    /api/admin/worker/files/{section}/file
PATCH  /api/admin/worker/files/{section}/file
DELETE /api/admin/worker/files/{section}/file
DELETE /api/admin/worker/files/{section}/folder
POST   /api/admin/worker/files/{section}/folder
POST   /api/admin/worker/files/{section}/rename
POST   /api/admin/worker/files/{section}/move

# Super admin worker-scoped (role=super_admin)
GET    /api/super/workers/{id}/files/{section}
POST   /api/super/workers/{id}/files/{section}/upload
GET    /api/super/workers/{id}/files/{section}/file
PATCH  /api/super/workers/{id}/files/{section}/file
DELETE /api/super/workers/{id}/files/{section}/file
DELETE /api/super/workers/{id}/files/{section}/folder
POST   /api/super/workers/{id}/files/{section}/folder
POST   /api/super/workers/{id}/files/{section}/rename
POST   /api/super/workers/{id}/files/{section}/move
```

---

## 2. Problem Statement & Goals

### 2.1 Problems to Solve

**P1 — Code Duplication:** Tree rendering, file preview, upload, and delete logic exist in 2–3 copies. Any bug fix or feature change must be applied in multiple places, and they have already diverged (e.g. admin panel lacks XLSX preview, user panel lacks bulk select).

**P2 — Feature Parity Gaps:** Capabilities are not consistent across roles/views. See section 1.3 below.

**P3 — Known Bugs:**
- `PATCH /api/fs/{section}/file/used` → 405 (endpoint not wired on server)
- Inline rename editor does not clear existing value — concatenates old+new name
- No upload progress bar or feedback

**P4 — Missing Features:** Copy, file search/filter, version history, storage quotas, batch server operations.

### 1.3 Feature Parity Matrix (Current State)

| Feature | admin.html | mcp-agent user panel | mcp-agent admin panel |
|---|---|---|---|
| Tree render | ✅ | ✅ | ✅ |
| Upload file | ✅ | ✅ | ✅ |
| Create folder | ✅ | ✅ | ✅ |
| Create .md file | ✅ | ✅ | ✅ |
| Rename | ✅ (bug: concat) | ✅ (bug: concat) | ✅ |
| Delete file | ✅ | ✅ | ✅ |
| Delete folder | ✅ | ✅ | ✅ |
| Move (within section) | ✅ | ⚠️ partial | ✅ |
| Copy file | ❌ | ❌ | ❌ |
| Drag-drop (internal) | ✅ | ⚠️ partial | ✅ |
| Drag-drop (external OS) | ✅ | ❌ | ❌ |
| Bulk select + delete | ✅ | ❌ | ✅ |
| Bulk move/rename | ❌ | ❌ | ❌ |
| Preview: text/MD | ✅ | ✅ | ✅ |
| Preview: PDF | ✅ | ✅ | ✅ |
| Preview: XLSX | ✅ | ✅ | ❌ |
| Preview: DOCX | ✅ | ✅ | ❌ |
| Edit MD (in canvas) | ❌ | ✅ | ❌ |
| Preview: Python (.py) | ❌ | ❌ | ❌ |
| Context menu | ✅ | ✅ | ✅ |
| File search/filter | ❌ | ❌ | ❌ |
| Upload progress bar | ❌ | ❌ | ❌ |
| File size in tree | ❌ | ❌ | ❌ |
| Last modified in tree | ❌ | ❌ | ❌ |
| Version history | ❌ | ❌ | ❌ |
| Storage quota display | ❌ | ❌ | ❌ |

---

## 3. Requirements

### 3.1 BUG FIXES (Must-Do Before Feature Work)

**BUG-FS-001 — Inline rename clears field on focus**
- When the user activates inline rename, the input field must be pre-populated with the current name AND the text must be fully selected so the user can begin typing immediately to replace it.
- Current behaviour: value is set but cursor is appended, causing old+new concatenation.
- Fix location: `startInlineRename()` in admin.html and `ftCtxMenu()` rename handler in mcp-agent.html.
- Fix: After setting `input.value = currentName`, call `input.select()`.

**BUG-FS-002 — `PATCH /api/fs/{section}/file/used` returns 405**
- The backend endpoint is not implemented. The frontend calls it every time a message is sent with an active workflow.
- Fix: Implement the endpoint in `agent_server.py` to record the file path + timestamp in an audit JSONL (same as tool_calls.jsonl pattern).
- Schema: `{user_id, worker_id, section, path, used_at}` appended to `data/audit/file_used.jsonl`.
- The `.catch(() => {})` in mcp-agent.html line 4827 should remain to keep the call non-blocking, but the 405 must be eliminated.

**BUG-FS-003 — Upload gives no feedback**
- After selecting files, there is no spinner, progress bar, or success/error notification.
- Fix: Add a simple progress indicator (could be a determinate bar for single file, spinner for multi-file queue).

### 3.2 REFACTOR — Shared File Tree Library

Extract a shared JavaScript module `public/js/file-tree.js` (or inline shared IIFE) containing:

**F-LIB-01 — `FileTree` class / module**

```javascript
// Conceptual interface:
const tree = new FileTree({
  containerId: 'tree-domain_data',
  section: 'domain_data',
  apiPrefix: '/api/fs',           // or /api/super/workers/{id}/files, /api/admin/worker/files
  writable: false,
  workflowSection: false,
  onFileClick: function(section, path, name) {},
  onWorkflowSelect: function(section, path, name) {},
  token: () => localStorage.getItem('jwt'),
});
tree.load();   // fetches and renders tree
tree.refresh(); // re-fetches after mutation
```

**F-LIB-02 — Shared operations API**

All tree operations must route through one implementation:

| Operation | Method |
|---|---|
| Load tree | `tree.load(section)` |
| Create folder | `tree.mkdir(path)` |
| Rename item | `tree.rename(path, newName, isDir)` |
| Move item | `tree.move(src, destFolder)` |
| Delete file | `tree.deleteFile(path)` |
| Delete folder | `tree.deleteFolder(path)` |
| Upload files | `tree.upload(files, destFolder)` |
| Create .md file | `tree.createFile(path, name)` |
| Download file | `tree.download(path)` |

**F-LIB-03 — Shared file preview**

Extract `FilePreview` class:

```javascript
const preview = new FilePreview({ containerId: 'preview-panel' });
preview.render(section, path, name, content);  // detects extension, renders appropriately
```

Supported extensions and renderers:

| Extension | Renderer |
|---|---|
| .md | marked.js + DOMPurify |
| .txt, .json, .csv | Syntax-highlighted `<pre>` |
| .pdf | PDF.js iframe embed |
| .xlsx, .xls | SheetJS table render |
| .docx | mammoth.js decode → HTML |
| .py | Syntax-highlighted `<pre>` with Python highlighting (see REQ-04) |
| .html | Sandboxed iframe (srcdoc) |
| unknown | Raw text or binary size notice |

**F-LIB-04 — Shared drag-drop**

Single drag-drop implementation supporting:
- Internal moves (item → folder within same section)
- External OS drop (files from OS file manager → triggers upload)
- Visual drop target highlighting
- Folder expansion during hover (300ms hover → auto-expand)

### 3.3 FEATURE GAPS — Remaining Work

**F-COPY-01 — Copy file between sections (UI + Backend)**

Frontend: Context menu item "Copy to…" → modal listing destination sections (for admin: domain_data ↔ verified_workflows; for user: domain_data → my_data, verified → my_workflows).

Backend: New endpoint:
```
POST /api/fs/{section}/copy
POST /api/admin/worker/files/{section}/copy
POST /api/super/workers/{id}/files/{section}/copy
Body: { path: "folder/file.md", dest_section: "my_workflows", dest_folder: "" }
```
Implementation: `shutil.copy2()` then return new path.

**F-SEARCH-01 — File search / filter within tree**

A search box above each section panel. Typing filters the visible tree nodes client-side (no new API call needed — the full tree is already loaded). Matching nodes highlight in yellow. Parent folders of matching nodes remain expanded. Clear button resets.

Search must be case-insensitive and match partial names (substring). No regex required.

**F-META-01 — File metadata in tree rows**

The tree API should return size and mtime per node. The tree row displays:
- File size (human-readable: KB, MB) in a muted secondary column
- Last modified date (relative: "2 days ago") on hover tooltip

Backend change: `_build_tree()` function in `agent_server.py` must include `size_bytes` and `modified_at` (ISO8601) for file nodes. Folders show total children count instead of size.

**F-UPLOAD-01 — Upload progress indicator**

During file upload:
- Progress bar in the upload button area showing 0–100% (use `XMLHttpRequest` with `upload.onprogress` instead of `fetch`, which does not support upload progress)
- For multi-file uploads: "Uploading 2 of 5…" counter
- On completion: green checkmark for 2 seconds then auto-dismiss
- On error: red error message with filename and error detail

**F-BULK-01 — Bulk select for user panel (mcp-agent.html user view)**

Add bulk select mode to the user's My Data and My Workflows sections (currently only exists in admin views):
- Checkbox appears on hover per file row
- "Select All" button in section header
- Bulk delete button appears when >0 items selected
- Confirmation modal shows count and filenames

**F-BULK-02 — Bulk move (admin views)**

Extend existing bulk select (admin.html and mcp-agent.html admin panel) to include:
- "Move selected…" button → destination folder picker modal
- Moves all selected files in parallel (Promise.all)
- Reports partial failures (e.g. "3 of 5 moved — 2 failed: [names]")

**F-PREVIEW-PARITY — Admin panel preview parity**

The admin panel in mcp-agent.html currently lacks XLSX, DOCX, and edit-MD preview. After F-LIB-03 is implemented (shared FilePreview class), apply it uniformly so all three views have identical preview capability.

**F-EDITABLE-01 — In-canvas editor for My Workflows**

Users can currently preview My Workflow `.md` files in the canvas panel (read-only). Extend this to allow editing:
- Canvas preview panel for `.md` files in `my_workflows` section shows an "Edit" button
- Clicking Edit switches preview from rendered HTML to a `<textarea>` with the raw Markdown
- "Save" button calls `PATCH /api/fs/my_workflows/file` with `{path, content}` to persist changes
- "Cancel" discards changes and returns to rendered view
- Dirty state indicator (asterisk in panel title when unsaved changes exist)

**F-QUOTA-01 — Storage quota display (Phase 2, lower priority)**

Show used/total storage per section in the section header:
```
My Data   [████░░░░]  42 MB / 200 MB
```
Backend: New endpoint `GET /api/fs/{section}/quota` returns `{used_bytes, limit_bytes}`. Limit is configured per-worker in `workers.json`.

**F-VERSION-01 — File version history (Phase 2, lower priority)**

On write operations (upload, PATCH file content), the backend preserves the previous version in a hidden `.versions/` subdirectory alongside the file. Maximum 5 versions retained. A "History" context menu item shows a modal listing versions with timestamps and "Restore" button.

---

## 4. Non-Functional Requirements

**NFR-FS-01 — Path traversal prevention**
All path parameters must be validated server-side: `resolved_path.startswith(section_root)`. Reject any path containing `..`. This is already implemented — ensure all new endpoints follow the same pattern.

**NFR-FS-02 — Section access control**
The `domain_data` and `verified_workflows` sections must remain read-only for `role=user`. Any write operation attempt (upload, create, rename, delete) must return 403. Enforce in backend, not just frontend.

**NFR-FS-03 — File size limits**
Upload endpoint must enforce a maximum file size. Recommended: 50 MB per file, configurable via `UPLOAD_MAX_SIZE_MB` environment variable. Return 413 with a human-readable error on violation.

**NFR-FS-04 — Allowed file types**
Allow list enforced server-side. Blocked: `.exe`, `.sh`, `.bat`, `.cmd`, `.dll`, `.so`. All other types permitted. Return 415 with specific error for blocked types.

**NFR-FS-05 — Concurrent upload safety**
Uploads to the same destination path must be serialised (file lock). Concurrent uploads to different paths are permitted. Use `filelock` library or a per-path asyncio Lock.

**NFR-FS-06 — Empty folder delete safety**
`DELETE /api/fs/{section}/folder` must fail with 409 if the folder contains any files or subfolders, unless `?recursive=true` is passed (admin-only). User UI must show the folder's child count in the confirmation modal.

---

## 5. Backend Changes Summary

| Change | Endpoint | Priority |
|---|---|---|
| Fix file/used 405 | `PATCH /api/fs/{section}/file/used` | Critical |
| Add `size_bytes` + `modified_at` to tree | `GET /api/fs/{section}/tree` | High |
| Copy endpoint | `POST /api/fs/{section}/copy` | High |
| Quota endpoint | `GET /api/fs/{section}/quota` | Medium |
| File version write | Internal, triggered on PATCH/upload | Low |
| Batch delete | `POST /api/fs/{section}/batch-delete` | Medium |

---

## 6. Acceptance Criteria

- [ ] BUG-FS-001: Rename input pre-selects existing name; typing replaces it cleanly
- [ ] BUG-FS-002: `PATCH /api/fs/{section}/file/used` returns 200 (not 405)
- [ ] BUG-FS-003: Upload shows progress bar; success/error state shown after completion
- [ ] F-LIB-01/02/03: A single `FileTree` and `FilePreview` implementation is used by all three views (no duplicate rendering code)
- [ ] F-COPY-01: Files can be copied from Domain Data to My Data via context menu
- [ ] F-SEARCH-01: Typing in the section search box filters visible nodes in real time
- [ ] F-META-01: File rows show size and last modified in tree
- [ ] F-BULK-01: Users can bulk-select and delete files in My Data and My Workflows
- [ ] F-PREVIEW-PARITY: Admin panel previews XLSX and DOCX correctly
- [ ] F-EDITABLE-01: Users can edit and save My Workflow `.md` files from canvas panel
- [ ] All backend endpoints return correct HTTP status codes; path traversal attempts return 400

---

## 7. Out of Scope

- Real-time collaborative editing (multi-user simultaneous edit)
- Git-based version control integration
- Full-text content search (search inside file contents, not just filenames)
- S3 or cloud storage backend (addressed in REQ-08)
