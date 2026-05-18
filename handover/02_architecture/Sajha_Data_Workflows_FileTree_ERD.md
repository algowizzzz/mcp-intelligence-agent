# ENGINEERING REQUIREMENTS

> **Source:** Converted from `Sajha_Data_Workflows_FileTree_ERD.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**ENGINEERING REQUIREMENTS**

**Data & Workflow File Tree Panel**

*Domain Data · My Data · Verified Workflows · My Workflows · File Preview · Multi-folder indexing*

Version 1.0 · April 2026

> **1. Overview**

This document specifies a replacement of the flat file list in the Workspace & Workflows drawer with a VS Code / Cursor-style file tree panel. The panel gains four top-level sections, each supporting nested sub-folders, drag-and-drop reorganisation, inline file creation, and a file preview panel that renders in the canvas area.

| **Section** | **Folder (server)** | **Who adds files** | **Edit capable** |
|----|----|----|----|
| Domain Data | data/domain_data/ | Admin / provisioned at setup. Read-only for end users. | No — read only |
| My Data | data/uploads/ | Any user — drag-drop, upload button, or from chat attachment. | No — read only |
| Verified Workflows | data/workflows/verified/ | Admin / engineering. End users cannot modify. | No — read only |
| My Workflows | data/workflows/my/ | Any user — upload .md or create new .md inline. | Yes — .md files only |

> **NOTE** Preview is available for all file types in all four sections. Editing is intentionally limited to .md files in My Workflows only. Editing Word, Excel, or PDF inside the browser is prohibitively complex and out of scope.
>
> **2. Folder Structure**

**2.1 Directory Layout**

The following physical folder structure replaces the current flat data/uploads/ and data/workflows/ layout. Create these directories on the server. Existing files in data/uploads/ migrate to data/uploads/ (My Data root — no change to path). Existing MD files in data/workflows/ migrate to data/workflows/verified/ for the two official workflows and data/workflows/my/ for user-created ones.

> data/
>
> ├── domain_data/ ← Domain Data section root
>
> │ ├── .index.json ← auto-generated index (see Section 7)
>
> │ └── \[subfolders and files...\]
>
> │
>
> ├── uploads/ ← My Data section root (existing path unchanged)
>
> │ ├── .index.json
>
> │ └── \[subfolders and files...\]
>
> │
>
> └── workflows/
>
> ├── verified/ ← Verified Workflows section root
>
> │ ├── .index.json
>
> │ └── \[subfolders and .md files...\]
>
> └── my/ ← My Workflows section root
>
> ├── .index.json
>
> └── \[subfolders and .md files...\]

**2.2 Migration of Existing Files**

| **Current location** | **Migrates to** | **Action** |
|----|----|----|
| data/uploads/\*.\* (flat) | data/uploads/ (same root) | No move needed — already correct path. |
| data/workflows/counterparty_intelligence.md | data/workflows/verified/ | Move file. |
| data/workflows/op_risk_controls.md | data/workflows/verified/ | Move file. |
| data/workflows/market_credit_risk_intelligence_brief.md | data/workflows/my/ | Move file — user-created workflow. |
| data/workflows/.metadata.json | Replaced by .index.json per folder | See Section 7. |

> **3. File Tree UI Component**

A single reusable FileTree component is used in all four sections. It renders identically to VS Code / Cursor: indented folder rows with chevron toggles, file rows with type icons, and an action toolbar. The component is parameterised by root path, edit permissions, and accepted file types.

**3.1 Tree Row Types**

| **Row type** | **Icon** | **Indent** | **Interactions** |
|----|----|----|----|
| Folder (collapsed) | ▶ folder icon | depth × 16px left padding | Click chevron to expand. Click label to expand + select. Right-click → context menu. |
| Folder (expanded) | ▼ open folder icon | depth × 16px | Click chevron to collapse. |
| File | Type icon (see 3.2) | (depth+1) × 16px | Click to open preview. Right-click → context menu. Drag to move. |
| New item row | \+ icon, text input | Injected inline at target level | Enter to confirm, Escape to cancel. |

**3.2 File Type Icons**

| **Extension** | **Icon colour** | **Preview renderer** |
|----|----|----|
| .md | Blue | Markdown — rendered HTML via marked.js (already used in canvas) |
| .pdf | Red | PDF.js — embedded viewer, page navigation |
| .docx | Blue | mammoth.js — converts to HTML client-side, read-only |
| .xlsx / .csv | Green | SheetJS (xlsx) — renders first sheet as scrollable HTML table |
| .json | Yellow | Syntax-highlighted \<pre\> block via highlight.js |
| .txt | Gray | Plain text in \<pre\> block |
| Other | Gray | "Preview not available" message with download link |

**3.3 Context Menu (Right-click)**

| **Target** | **Menu items** | **Editable section only** |
|----|----|----|
| Folder | Rename, New File, New Folder, Delete Folder (if empty) | New File and New Folder available in all sections for admin; My sections only for users. |
| File | Rename, Move to…, Download, Delete | Rename and Delete restricted to My sections. |
| .md file (My Workflows) | All above + Edit | Edit opens the file in the canvas panel in edit mode. |

**3.4 Toolbar (Section Header)**

Each section header bar contains:

- Section name + collapse chevron (left)

- File count badge — total files in all subfolders

- \+ New Folder button (My sections only)

- \+ New File / Upload button (My sections and Domain Data for admin)

- Collapse All / Expand All toggle icon (right)

**3.5 Drag and Drop**

| **Interaction** | **Behaviour** |
|----|----|
| Drag file onto folder | Moves file into that folder. POST /api/fs/move with {src, dst}. |
| Drag file onto another file | Moves file into the same folder as the target (sibling). |
| Drag folder onto folder | Moves entire folder and its contents recursively. |
| Drag from My Data to My Workflows | Blocked — cross-section moves not permitted. |
| Drag from Verified / Domain sections | Blocked — read-only sections cannot be reorganised by users. |
| Drop external file onto section | Triggers upload into the folder currently being hovered. Same as clicking Upload. |
| Visual feedback | Dragged item shows ghost at 70% opacity. Drop target folder highlights with blue border. |

> **4. Data Sections**

**4.1 Domain Data**

| **Property** | **Specification** |
|----|----|
| Root | data/domain_data/ |
| Purpose | Curated reference data: market data feeds, counterparty master files, regulatory reference tables. Provisioned by admin or engineering. End users browse and use in queries but cannot upload or delete. |
| User permissions | Read + preview only. Upload and delete buttons hidden. |
| Admin permissions | Full CRUD via a separate admin flag in the session token. |
| Accepted file types | All types. No restriction on domain data. |
| Context attachment | Clicking a file selects it for the context bar (blue tag) — same as current behaviour. Multiple files selectable. |

**4.2 My Data**

| **Property** | **Specification** |
|----|----|
| Root | data/uploads/ |
| Purpose | User-uploaded working files: reports, exposures, counterparty lists, spreadsheets. Replaces the current flat upload folder. |
| User permissions | Full CRUD — upload, rename, delete, create subfolders, move files. |
| Accepted file types | PDF, DOCX, XLSX, CSV, TXT, JSON, MD. Others rejected with inline error. |
| Max file size | 50MB per file (from application.properties data.uploads_max_size_mb). |
| Upload methods | Drag-drop onto section or subfolder, Upload button in toolbar, chat attachment (continues to land in root of data/uploads/). |
| Context attachment | Same as Domain Data — click to add blue tag to context bar. |

> **5. Workflow Sections**

**5.1 Verified Workflows**

| **Property** | **Specification** |
|----|----|
| Root | data/workflows/verified/ |
| Purpose | Official, reviewed workflow playbooks. Curated by the team. End users cannot modify. |
| User permissions | Read + preview only. No upload, rename, or delete. |
| File types | MD only. |
| Selection | Click row → opens MD preview in canvas. Separate "Select" action adds to context bar (purple tag). |
| Subfolders | Supported — e.g. verified/ccr/, verified/op_risk/ for organisation. |

**5.2 My Workflows**

| **Property** | **Specification** |
|----|----|
| Root | data/workflows/my/ |
| Purpose | User-created and personal workflow playbooks. Full CRUD. |
| User permissions | Upload .md, create new .md inline, rename, delete, create subfolders, move files. |
| File types | MD only. Non-MD uploads rejected with inline error: "Workflows must be .md files". |
| Create new workflow | "+ New Workflow" button in toolbar → inline filename input → creates empty .md → opens in canvas edit mode. |
| Edit | Click .md file → canvas opens in edit mode (textarea + live preview split). See Section 6.3. |
| Selection | Same as Verified — click → preview, "Select" button → context bar. |

> **6. File Preview Panel**

**6.1 Trigger & Location**

Clicking any file in any section opens the preview panel in the canvas area (right side of the screen). The preview panel replaces the canvas content when triggered, or stacks as a tab alongside an active canvas if one exists. The panel header shows the filename, file type badge, and a close (×) button.

**6.2 Renderer Specifications by File Type**

| **Type** | **Library** | **Render method** | **Editable** | **Complexity** |
|----|----|----|----|----|
| .md | marked.js (already used in canvas) | Rendered HTML in a scrollable div. Same CSS as canvas markdown renderer. | Yes — My Workflows only. Toggle button switches between Preview and Edit modes. | Low — already exists |
| .json | highlight.js | Syntax-highlighted \<pre\> block with line numbers. Colour theme matches dark UI. | No | Low |
| .txt | (none) | Plain \<pre\> block, monospace font, line wrap. | No | Low |
| .pdf | PDF.js (cdnjs hosted) | Embedded canvas renderer. Page navigation: prev/next buttons + page counter. Zoom in/out buttons. | No | Medium — PDF.js well documented |
| .xlsx / .csv | SheetJS (xlsx.js, cdnjs hosted) | Parse client-side, render first sheet as scrollable HTML table. Sheet tab selector for multi-sheet workbooks. | No | Medium — SheetJS well documented |
| .docx | mammoth.js (cdnjs hosted) | Fetch file as ArrayBuffer, convert to HTML client-side, render in sandboxed div. Styles stripped, structure preserved. | No | Medium — mammoth well documented |
| Other | (none) | Grey placeholder: "Preview not available for this file type." with a Download button. | No | None |

**6.3 MD Edit Mode (My Workflows Only)**

When a .md file in My Workflows is opened, the canvas panel shows a split view: left pane is a plain textarea (monospace, line numbers via CSS), right pane is live-rendered preview updating on keystroke with 300ms debounce.

| **Element** | **Specification** |
|----|----|
| Split ratio | 50/50 by default. Draggable divider to resize panes. |
| Save | Auto-save on 2-second idle after last keystroke. PATCH /api/fs/file with {path, content}. "Saved" indicator fades in top-right. |
| Discard | Close (×) button shows "Unsaved changes — Save or Discard?" dialog if dirty. |
| Syntax hint | Toolbar above textarea: H1 H2 H3 Bold Italic Code Block Table — inserts MD syntax at cursor. |
| Read-only sections | Edit mode button does NOT appear for Verified Workflows or Domain Data files. |

**6.4 Preview Panel State**

| **State** | **Behaviour** |
|----|----|
| No file selected | Canvas shows default state (current canvas content or empty). |
| File clicked — preview opens | Canvas switches to preview mode. If canvas had active content, a tab bar appears: \[Canvas\] \[filename.pdf\]. |
| Canvas tab clicked | Returns to previous canvas content. Preview tab stays accessible. |
| Preview closed (×) | Tab removed. Canvas returns to previous content. |
| Different file clicked while preview open | Preview updates to new file in same panel. No new tab. |

> **7. Indexing Mechanism**

**7.1 Design**

Each root folder (domain_data/, uploads/, workflows/verified/, workflows/my/) maintains a .index.json sidecar file. The index stores the full recursive tree: paths, sizes, types, and last-modified timestamps. It is rebuilt automatically on any file system mutation.

> **NOTE** This replaces .metadata.json from the previous flat spec. The index covers the full folder tree, not just top-level files.

**7.2 Index Schema**

> {
>
> "root": "data/uploads",
>
> "built_at": "2026-04-02T14:00:00Z",
>
> "tree": \[
>
> {
>
> "type": "folder",
>
> "name": "Q1 Reports",
>
> "path": "Q1 Reports",
>
> "children": \[
>
> {
>
> "type": "file",
>
> "name": "exposure_Q1.xlsx",
>
> "path": "Q1 Reports/exposure_Q1.xlsx",
>
> "size_bytes": 48200,
>
> "modified_at": "2026-03-15T10:22:00Z",
>
> "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
>
> "last_used": null
>
> }
>
> \]
>
> }
>
> \]
>
> }

**7.3 Rebuild Triggers**

| **Event** | **Action** |
|----|----|
| File uploaded | Rebuild index for that root folder after write completes. |
| File deleted | Rebuild index. |
| File / folder renamed | Rebuild index. |
| File moved (drag-drop) | Rebuild both source and destination root indexes. |
| GET /api/fs/tree request | If index is older than 60 seconds, rebuild before returning. Otherwise return cached index. |
| Server startup | Rebuild all 4 indexes. |

**7.4 Index Builder (Python)**

Add a helper function build_index(root_path) in a new file: sajhamcpserver/sajha/tools/impl/fs_index.py. Call it from all write endpoints after mutation.

> \# sajhamcpserver/sajha/tools/impl/fs_index.py
>
> import os, json, mimetypes
>
> from datetime import datetime, timezone
>
> def build_tree(base, rel=""):
>
> entries = \[\]
>
> full = os.path.join(base, rel) if rel else base
>
> for name in sorted(os.listdir(full)):
>
> if name.startswith("."): continue
>
> item_rel = os.path.join(rel, name) if rel else name
>
> item_full = os.path.join(base, item_rel)
>
> if os.path.isdir(item_full):
>
> entries.append({
>
> "type": "folder", "name": name, "path": item_rel,
>
> "children": build_tree(base, item_rel)
>
> })
>
> else:
>
> stat = os.stat(item_full)
>
> mime, \_ = mimetypes.guess_type(item_full)
>
> entries.append({
>
> "type": "file", "name": name, "path": item_rel,
>
> "size_bytes": stat.st_size,
>
> "modified_at": datetime.fromtimestamp(
>
> stat.st_mtime, tz=timezone.utc).isoformat(),
>
> "mime": mime or "application/octet-stream",
>
> })
>
> return entries
>
> def build_index(root_path):
>
> index = {
>
> "root": root_path,
>
> "built_at": datetime.now(timezone.utc).isoformat(),
>
> "tree": build_tree(root_path)
>
> }
>
> index_path = os.path.join(root_path, ".index.json")
>
> with open(index_path, "w") as f:
>
> json.dump(index, f, indent=2)
>
> return index
>
> **8. Updated Workflow Tools for Multi-folder Structure**

workflow_list and workflow_get (specified in Sajha_Workflow_MD_Migration_Implementation.docx) must be updated to support multi-folder recursive scanning of both verified/ and my/ sub-roots.

**8.1 workflow_list — Changes**

Update WorkflowListTool.execute() to scan both data/workflows/verified/ and data/workflows/my/ recursively. Return a "source" field per workflow indicating which root it came from.

> \# Updated execute() logic:
>
> def execute(self, arguments):
>
> base = \_workflows_base() \# e.g. ./data/workflows
>
> roots = {
>
> "verified": os.path.join(base, "verified"),
>
> "my": os.path.join(base, "my"),
>
> }
>
> workflows = \[\]
>
> for source, root in roots.items():
>
> if not os.path.exists(root): continue
>
> for dirpath, \_, files in os.walk(root):
>
> for fname in sorted(files):
>
> if not fname.endswith(".md") or fname.startswith("."): continue
>
> full_path = os.path.join(dirpath, fname)
>
> rel_path = os.path.relpath(full_path, base) \# e.g. verified/ccr/counterparty.md
>
> with open(full_path) as f:
>
> content = f.read()
>
> name, desc, inputs = \_parse_workflow_meta(fname, content)
>
> workflows.append({
>
> "filename": rel_path, \# full relative path from workflows base
>
> "name": name,
>
> "description": desc,
>
> "inputs": inputs,
>
> "source": source, \# "verified" or "my"
>
> })
>
> return {"workflows": workflows, "count": len(workflows)}

**8.2 workflow_get — Changes**

Accept filename as a relative path from the workflows base (e.g. "verified/counterparty_intelligence.md" or "my/ccr/custom.md"). Update path traversal guard accordingly.

> \# Updated execute() — key change: accept relative subpath
>
> def execute(self, arguments):
>
> filename = arguments.get("filename", "")
>
> base = \_workflows_base()
>
> \# Normalise: strip leading slash, ensure .md
>
> filename = filename.lstrip("/").lstrip("./")
>
> if not filename.endswith(".md"):
>
> filename += ".md"
>
> \# Safety: resolve and confirm it stays inside base
>
> full_path = os.path.realpath(os.path.join(base, filename))
>
> if not full_path.startswith(os.path.realpath(base)):
>
> return {"error": "Access denied"}
>
> if not os.path.exists(full_path):
>
> return {"error": f"Workflow not found: {filename}"}
>
> with open(full_path) as f:
>
> content = f.read()
>
> fname = os.path.basename(full_path)
>
> name, desc, inputs = \_parse_workflow_meta(fname, content)
>
> return {"filename": filename, "name": name,
>
> "description": desc, "inputs": inputs, "content": content}
>
> **9. REST Endpoints (agent_server.py)**

All endpoints operate relative to the section root. The {section} path parameter maps to: domain_data → data/domain_data/, uploads → data/uploads/, verified → data/workflows/verified/, my_workflows → data/workflows/my/.

| **Method** | **Path** | **Description** | **Sections** |
|----|----|----|----|
| GET | /api/fs/{section}/tree | Return full .index.json tree. Rebuild if stale (\>60s). | All 4 |
| GET | /api/fs/{section}/file?path={relpath} | Return file content as base64 (binary) or UTF-8 text. | All 4 |
| POST | /api/fs/{section}/upload?path={folder} | Upload file into specified subfolder. Rebuild index. | uploads, my_workflows |
| PATCH | /api/fs/{section}/file | Update file content. Body: {path, content}. Rebuild index. | my_workflows (.md only) |
| POST | /api/fs/{section}/folder | Create new empty folder. Body: {path}. Rebuild index. | uploads, my_workflows |
| POST | /api/fs/{section}/move | Move file or folder. Body: {src, dst}. Rebuild both indexes if cross-root. | uploads, my_workflows |
| DELETE | /api/fs/{section}/file?path={relpath} | Delete file. Rebuild index. | uploads, my_workflows |
| DELETE | /api/fs/{section}/folder?path={relpath} | Delete folder (must be empty). Rebuild index. | uploads, my_workflows |
| POST | /api/fs/{section}/rename | Rename file or folder. Body: {path, new_name}. Rebuild index. | uploads, my_workflows |

> **NOTE** domain_data and verified are read-only for non-admin users. The server checks the session role before allowing POST/PATCH/DELETE. GET is available to all authenticated users.
>
> **10. Frontend State**

Extend panelState to support the 4-section tree structure:

> const panelState = {
>
> // Drawer
>
> drawerOpen: false,
>
> // Section expand/collapse
>
> domainDataExpanded: false,
>
> myDataExpanded: false,
>
> verifiedWorkflowsExpanded: false,
>
> myWorkflowsExpanded: false,
>
> // File trees (loaded from GET /api/fs/{section}/tree)
>
> domainDataTree: null,
>
> myDataTree: null,
>
> verifiedWorkflowsTree: null,
>
> myWorkflowsTree: null,
>
> // Expanded folders per section (set of relative paths)
>
> expandedFolders: { domainData:new Set(), myData:new Set(),
>
> verified:new Set(), myWorkflows:new Set() },
>
> // Context bar selections
>
> selectedDocs: \[\], // \[{section, path, name}\]
>
> selectedWorkflow: null, // {section, path, name, content} or null
>
> // Preview panel
>
> previewFile: null, // {section, path, name, type} or null
>
> previewMode: "preview", // "preview" \| "edit" (edit: my_workflows .md only)
>
> previewDirty: false,
>
> // Drag state
>
> dragItem: null, // {section, path, type:"file"\|"folder"}
>
> dragOverFolder: null,
>
> };
>
> **11. Acceptance Criteria**

| **\#** | **Criterion** | **Pass condition** |
|----|----|----|
| AC-01 | 4 sections visible | Drawer shows Domain Data, My Data, Verified Workflows, My Workflows — each independently collapsible with file count badge. |
| AC-02 | File tree renders | Expanding My Data shows recursive folder tree matching data/uploads/ structure. Folders have chevron toggle. Files show correct type icon. |
| AC-03 | Index builds on startup | All 4 .index.json files exist and are populated after server start. |
| AC-04 | Index rebuilds on upload | Upload a file to My Data → .index.json updated → tree re-fetched → new file appears without page reload. |
| AC-05 | Subfolder creation | Click "+ New Folder" in My Data → inline input → Enter → folder appears in tree. |
| AC-06 | Drag-drop file move | Drag a file from My Data root onto a subfolder → file moves → index rebuilds → tree reflects new location. |
| AC-07 | Cross-section drag blocked | Dragging a file from My Data onto My Workflows shows a "not allowed" cursor. No move occurs. |
| AC-08 | MD preview | Click a .md file → canvas opens with rendered markdown. Correct headings, code blocks, tables. |
| AC-09 | PDF preview | Click a .pdf file → PDF.js renders first page. Next/prev page navigation works. |
| AC-10 | Excel preview | Click a .xlsx file → SheetJS renders first sheet as HTML table. Sheet tabs shown for multi-sheet files. |
| AC-11 | Word preview | Click a .docx file → mammoth.js converts and renders document structure as HTML. Styles stripped, headings/tables preserved. |
| AC-12 | JSON preview | Click a .json file → syntax-highlighted display with line numbers. |
| AC-13 | MD edit mode | Click .md file in My Workflows → canvas shows split view: textarea left, rendered preview right. Edit in textarea → preview updates within 300ms. |
| AC-14 | MD auto-save | Edit .md file, pause 2 seconds → "Saved" indicator appears. File content updated on server. |
| AC-15 | Edit blocked in Verified | Click .md in Verified Workflows → canvas shows preview only. No edit button, no textarea. |
| AC-16 | workflow_list returns multi-folder | Call workflow_list → returns workflows from both verified/ and my/ sub-trees with correct "source" and relative "filename" paths. |
| AC-17 | workflow_get with subpath | Call workflow_get with filename="verified/counterparty_intelligence.md" → returns correct content. |
| AC-18 | Path traversal blocked | GET /api/fs/uploads/file?path=../../etc/passwd → 403 response, no file content returned. |
| AC-19 | Context bar from tree | Click file in Domain Data → blue tag appears in context bar with filename. Sending message composes \[Context Documents: filename\]. |
| AC-20 | Workflow select from tree | Click workflow in Verified Workflows → preview opens. Click "Select this Workflow" button → purple tag in context bar. |
