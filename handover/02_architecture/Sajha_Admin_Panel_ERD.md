# SAJHA MCP INTELLIGENCE AGENT

> **Source:** Converted from `Sajha_Admin_Panel_ERD.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**SAJHA MCP INTELLIGENCE AGENT**

**Admin Panel**

Engineering Requirements Document

Version 1.0 \| April 2026

> **1. Overview**

The Admin Panel is a new top-level navigation tab in mcp-agent.html, positioned above the existing Settings tab. It provides privileged users with a dedicated interface to manage shared, curated data assets — Domain Data and Verified Workflows — that are surfaced to all users of the intelligence agent.

The Chat UI file tree panel (My Data, My Workflows) remains unchanged and is governed by individual users. The Admin Panel governs the shared layers only. This two-tier governance model ensures that domain reference data and production-grade workflows can be maintained independently of per-user uploads.

| **Aspect** | **Detail** |
|:---|:---|
| **Scope** | Domain Data (shared) + Verified Workflows (shared) |
| **Governed by Chat UI** | My Data + My Workflows (unchanged) |
| **Access control** | is_admin role flag on JWT — hidden tab for non-admins |
| **File size limit** | 20 MB per file |
| **Batch upload limit** | Up to 200 files per upload session |
| **Supported file types** | CSV, PDF, XLSX, DOCX, JSON, MD, TXT, PNG, JPG |
| **No preview required** | Admin panel is operational only — no file preview pane |
| **Backend data root** | Existing sajhamcpserver/data/ folder — no migration needed |

> **2. Navigation & Tab Placement**

The left sidebar of mcp-agent.html currently contains: Chat (top), Settings (bottom). The Admin Panel tab is inserted between them — above Settings, below any future chat history or workspace items.

**2.1 Tab Visibility**

The admin tab icon renders only when the decoded JWT contains "is_admin": true. For non-admin users the tab does not appear in the DOM — it is not merely hidden via CSS. This prevents tab discovery via browser devtools inspection.

**2.2 Tab Icon & Label**

Use a shield or database icon (matching the existing icon set) with the label "Admin". On hover a tooltip reads "Admin Panel". The active state matches the existing tab highlight style.

**2.3 Tab Layout**

The Admin Panel occupies the full main content area when active — same container used by the chat view. It replaces the chat thread completely while open, and returns to the last chat state when the user switches back to the Chat tab.

> **3. Role-Based Access Control**

**3.1 is_admin JWT Claim**

The SAJHA MCP server user authentication (login endpoint) must include an "is_admin" boolean field in the JWT payload. The agent server currently validates the AGENT_API_KEYS env var; admin role checking applies to the SAJHA server JWT path used for file system operations.

**3.2 Default Admin User**

The existing default user risk_agent / RiskAgent2025! is granted is_admin: true. No new accounts need to be created. The user record in the auth store (or hardcoded user config) adds a single "is_admin": true field.

**3.3 Middleware Guard**

All admin REST endpoints (Section 8) check the is_admin claim before executing. A non-admin JWT calling an admin endpoint receives HTTP 403 Forbidden with body {"error": "Admin access required"}. The check is a middleware decorator, not inline per-handler.

**3.4 Frontend Guard**

On page load, after JWT decode, the frontend stores isAdmin = payload.is_admin \|\| false. This flag gates: (1) tab rendering, (2) all admin API calls. If the flag is absent or false the admin tab never renders and admin API calls are never made.

> **NOTE** Role escalation (promoting a user to admin) is out of scope for this ERD. The single admin user model is sufficient for the current deployment.
>
> **4. Admin Panel Layout**

The Admin Panel is a two-section vertical split. The left panel is a file tree (same VS Code-style component as the Chat UI file tree, reused). The right panel is the upload and action zone. There is no preview pane.

**4.1 Left Panel — File Tree (400px fixed width)**

The file tree renders two collapsible root sections:

- Domain Data — maps to sajhamcpserver/data/domain_data/

- Verified Workflows — maps to sajhamcpserver/data/workflows/verified/

Each section behaves identically to the Chat UI file tree sections: chevron expand/collapse, folder icons, file type icons, context menu on right-click. Sections cannot be collapsed to zero height — each maintains a minimum 120px visible area.

**4.2 Right Panel — Upload & Actions Zone (remaining width)**

The right panel contains: a section header showing which folder is currently selected in the file tree, a drag-and-drop upload target area, a file queue list with per-file progress bars, and an action toolbar (New Folder, Delete Selected, Move).

When no folder is selected in the file tree the right panel shows an instructional placeholder: "Select a folder in the tree to upload files or manage contents."

**4.3 Toolbar Actions**

| **Action** | **Location** | **Behaviour** |
|:---|:---|:---|
| **New Folder** | Toolbar + right-click context menu | Prompts inline text input in the tree, creates folder on Enter, cancels on Escape |
| **Rename** | Right-click context menu only | Inline text input on the item, commits on Enter/blur |
| **Delete** | Toolbar + right-click context menu | Confirmation modal before deletion. Non-empty folders show item count warning. |
| **Move** | Toolbar (after selection) | Opens a folder picker modal showing the tree; user selects destination within same section |
| **Upload Files** | Upload zone + toolbar button | Opens OS file picker; also accepts drag-and-drop onto zone or onto a folder in the tree |
| **New MD File** | Right-click context menu (Verified Workflows only) | Creates empty .md file with YAML frontmatter stub, opens name input |

> **5. Domain Data Management**

Domain Data is the shared reference data layer used by agent tools (IRIS CCR, OSFI, counterparties, DuckDB databases, etc.). It maps to sajhamcpserver/data/domain_data/ on disk.

**5.1 Folder Structure**

Admin can create arbitrary sub-folder hierarchies within Domain Data. The folder tree supports unlimited depth. Example structure:

> domain_data/
>
> iris/
>
> iris_combined.csv
>
> osfi/
>
> B-20.pdf
>
> B-10.pdf
>
> counterparties/
>
> counterparty_master.csv
>
> duckdb/
>
> risk_warehouse.duckdb
>
> uploads/
>
> ad_hoc_report.xlsx

**5.2 Accepted File Types**

Domain Data accepts: CSV, XLSX, PDF, DOCX, JSON, TXT, DuckDB (.duckdb), PNG, JPG. Files with unsupported extensions are rejected at upload time with an inline error in the queue item: "Unsupported file type: .\<ext\>".

**5.3 Drag-and-Drop Within Section**

Files and folders can be dragged to any folder within Domain Data. Drag-and-drop across to Verified Workflows is blocked — a visual indicator (red border on drop target) appears if the user attempts a cross-section drop, and the drop is cancelled with a toast: "Cannot move between sections."

**5.4 application.properties Paths**

Existing data path keys in application.properties (IRIS_CCR_PATH, OSFI_PATH, DUCKDB_PATH, UPLOADS_PATH) continue to point to their current absolute paths. The admin file tree does not auto-update these keys when folders are moved. If an admin reorganises folder paths that are referenced by application.properties, the properties file must be updated manually. A NOTE is shown in the UI when deleting or renaming a top-level folder.

> **NOTE** The admin panel does not auto-update application.properties when folders are moved or renamed. This is intentional — path key management stays under developer control.
>
> **6. Verified Workflows Management**

Verified Workflows are production-grade, admin-curated MD workflow files used by the workflow_list and workflow_get MCP tools. They map to sajhamcpserver/data/workflows/verified/ on disk.

**6.1 Accepted File Types**

Verified Workflows accepts .md files only. Uploading any other file type is blocked at the frontend before the request is made. Error message: "Verified Workflows only accepts .md files."

**6.2 YAML Frontmatter Requirement**

Every MD file in Verified Workflows must contain a valid YAML frontmatter block with at minimum: name, description, inputs. The admin panel does not enforce this at upload time (the file may be edited after upload) but the file tree decorates any MD file missing frontmatter with a warning icon and tooltip: "Missing required frontmatter (name, description, inputs)."

The frontmatter validation check runs client-side: after upload the file content is fetched and the --- block is parsed in the browser. Files that pass validation show a green check icon next to their name in the tree.

**6.3 Sub-folder Support**

Admin can create sub-folders within Verified Workflows. The workflow_list MCP tool already supports recursive scanning of verified/ — sub-folders are picked up automatically at the next scan cycle (no server restart required, hot-reload within 5 minutes).

**6.4 New MD File Stub**

When admin selects New MD File from the context menu, the created file is pre-populated with a YAML frontmatter stub:

> ---
>
> name:
>
> description:
>
> inputs:
>
> tags: \[\]
>
> version: "1.0"
>
> ---
>
> \## Step 1

The file name is set by the admin via the inline input. The stub is written server-side when the file is created so it is immediately present on disk.

> **7. File Upload Specification**

**7.1 Upload Mechanism**

Files are uploaded via multipart/form-data POST to the admin upload endpoint. Each file is uploaded individually in a sequential queue — not all at once — to avoid overwhelming the server. The queue processes one file at a time with a per-file progress bar driven by XHR upload progress events.

**7.2 Limits**

| **Constraint** | **Value** | **Enforcement** |
|:---|:---|:---|
| **Max file size** | 20 MB | Client-side check before queue entry; server-side 413 rejection as backstop |
| **Max files per session** | 200 | Client-side check on file picker selection; excess files are dropped with a count toast |
| **Accepted types — Domain Data** | CSV, XLSX, PDF, DOCX, JSON, TXT, .duckdb, PNG, JPG | Client-side MIME + extension check; server-side extension check as backstop |
| **Accepted types — Verified Workflows** | .md only | Client-side extension check; server rejects non-.md with 415 |
| **Concurrent uploads** | 1 at a time (sequential queue) | Prevents server overload; progress is visible per file |

**7.3 Upload Queue UI**

The upload queue renders below the drag-and-drop zone. Each queue item shows: file name, file size, a horizontal progress bar, and a status badge (Queued / Uploading / Done / Error). Completed items fade out after 3 seconds. Failed items remain with a red error badge and a retry button.

A summary line above the queue reads: "X of Y files uploaded" and updates in real time. A Cancel All button appears while uploads are in progress, which aborts remaining queued files (already-uploaded files are not rolled back).

**7.4 Drag-and-Drop Upload**

Files can be dragged from the OS onto: (a) the upload zone in the right panel, or (b) directly onto a folder node in the left file tree. When dragging onto a folder node, the folder highlights with a blue border and the files are uploaded into that folder. Both single files and multi-file selections are supported.

**7.5 Duplicate File Handling**

If a file with the same name exists in the target folder the server returns HTTP 409 Conflict. The queue item shows the error badge with message "File already exists." A Replace button triggers a re-upload with an overwrite flag (?overwrite=true) appended to the request.

> **8. REST API Endpoints**

All admin endpoints are served by agent_server.py (FastAPI, port 8000) under the /api/admin/ prefix. Every endpoint verifies is_admin: true in the Bearer JWT before executing. Non-admin requests receive 403.

The existing /api/fs/ endpoints used by the Chat UI file tree remain unchanged. Admin endpoints operate on the domain_data/ and workflows/verified/ roots only; the Chat UI /api/fs/ endpoints operate on uploads/ and workflows/my/ roots only.

| **Method** | **Endpoint** | **Description** |
|:---|:---|:---|
| **GET** | /api/admin/tree/{section} | Returns full recursive index JSON for section. section = domain_data \| verified_workflows |
| **POST** | /api/admin/upload | Upload a single file. Body: multipart/form-data with fields: file (binary), path (relative target folder), overwrite (bool, default false). Returns {path, size_bytes, modified_at} |
| **POST** | /api/admin/folder | Create a new folder. Body: {section, path}. Returns {created: true, path} |
| **DELETE** | /api/admin/item | Delete file or folder. Body: {section, path, recursive (bool)}. Non-empty folder without recursive=true returns 409. |
| **PATCH** | /api/admin/rename | Rename file or folder in place. Body: {section, path, new_name}. Returns {new_path} |
| **POST** | /api/admin/move | Move file or folder within same section. Body: {section, src_path, dest_folder}. Cross-section moves return 400. |
| **POST** | /api/admin/file | Create new empty file with stub content. Body: {section, folder, filename}. Returns {path}. Used for New MD File action. |
| **GET** | /api/admin/validate/{section}/{path} | Parse frontmatter from an MD file and return validation result. Returns {valid: bool, missing: \[field,...\]} |

> **NOTE** Cross-section moves (e.g., from domain_data/ to verified/) are explicitly blocked server-side. The move endpoint returns 400 Bad Request with {"error": "Cross-section moves are not permitted."} if src and dest resolve to different section roots.
>
> **9. Backend Integration**

**9.1 Folder Mapping**

The two admin sections map directly to existing sub-directories under sajhamcpserver/data/:

> Admin section → Disk path
>
> ─────────────────────────────────────────────────────────
>
> Domain Data → sajhamcpserver/data/domain_data/
>
> Verified Workflows → sajhamcpserver/data/workflows/verified/

No new top-level directories are created. If domain_data/ does not yet exist it is created on first admin panel load by the /api/admin/tree/domain_data call (server auto-creates if missing).

**9.2 Index Rebuilding**

The fs_index.py build_index() function (specified in the Data & Workflows FileTree ERD) already supports recursive scanning. After every admin mutation (upload, delete, rename, move, folder create) the server triggers an async index rebuild for the affected section root. The rebuild is non-blocking — it runs in a background thread and writes the updated .index.json file when complete. Admin tree GET calls return the last-built index; they do not block on rebuild.

**9.3 workflow_list Hot-Reload**

The workflow_list MCP tool scans verified/ on each invocation (not cached). New or moved MD files in Verified Workflows are therefore visible to the agent within the next tool call — no server restart needed.

**9.4 File Size Enforcement**

FastAPI upload endpoint sets a max content length of 20 MB (20 \* 1024 \* 1024 bytes). Files exceeding this limit return HTTP 413 Request Entity Too Large. The client-side check runs first, so the server-side 413 is only a backstop.

> **10. UX Details**

**10.1 Toast Notifications**

| **Event** | **Toast message** | **Colour** |
|:---|:---|:---|
| **Upload complete (single)** | "{filename}" uploaded successfully | Green |
| **Upload complete (batch)** | "{n} files uploaded to {folder}" | Green |
| **Upload error** | "{filename}" failed: {error message} | Red |
| **File too large** | "{filename}" exceeds 20 MB limit — skipped | Amber |
| **Wrong file type** | "{filename}" is not a supported file type — skipped | Amber |
| **Folder created** | Folder "{name}" created | Green |
| **Delete confirmed** | "{name}" deleted | Green |
| **Cross-section drag blocked** | Cannot move between sections | Red |
| **Rename complete** | Renamed to "{new_name}" | Green |
| **Move complete** | Moved to "{dest_folder}" | Green |
| **Duplicate file** | "{filename}" already exists — use Replace to overwrite | Amber |

**10.2 Confirmation Modals**

Delete operations always require confirmation. The modal text depends on the target type:

- File: "Delete {filename}? This cannot be undone."

- Empty folder: "Delete empty folder {name}?"

- Non-empty folder: "Delete {name} and all {n} items inside? This cannot be undone."

Modal has two buttons: Cancel (default focus) and Delete (red). Enter key on the modal does not confirm — the user must click Delete explicitly to prevent accidental keyboard-triggered deletion.

**10.3 Loading States**

The file tree shows a spinner overlay during index fetch on initial load and after any mutation. Tree nodes are not interactive while a mutation is in flight. The toolbar buttons are disabled (greyed out) during upload queue processing.

> **11. Acceptance Criteria**

| **ID** | **Criterion** | **Verification** |
|:---|:---|:---|
| **AC-01** | Admin tab hidden for non-admin | Log in as a user without is_admin flag. Admin tab does not appear in sidebar DOM. |
| **AC-02** | Admin tab visible for admin | Log in as risk_agent. Admin tab appears above Settings tab. |
| **AC-03** | is_admin claim in JWT | Decode risk_agent JWT. Payload contains "is_admin": true. |
| **AC-04** | 403 on admin endpoint without admin role | Call GET /api/admin/tree/domain_data with a non-admin token → 403 Forbidden. |
| **AC-05** | Domain Data tree loads | Open Admin Panel as admin. Domain Data section expands and shows existing folder structure under data/domain_data/. |
| **AC-06** | Verified Workflows tree loads | Verified Workflows section shows contents of data/workflows/verified/ including existing .md files. |
| **AC-07** | Upload single file | Select a folder in Domain Data, drag a 1 MB CSV onto the upload zone. File appears in tree after upload and exists on disk. |
| **AC-08** | Upload 10 files in queue | Select 10 files via file picker. Queue shows all 10 items, processes sequentially, all reach Done status. |
| **AC-09** | 20 MB file size enforcement | Attempt to upload a 25 MB file. Client rejects before request with amber toast. File is not added to queue. |
| **AC-10** | Non-.md blocked in Verified Workflows | Drag a .csv onto a Verified Workflows folder. Error toast: "Verified Workflows only accepts .md files." |
| **AC-11** | Create sub-folder in Domain Data | Click New Folder in toolbar while a Domain Data folder is selected. Enter name, press Enter. Folder appears in tree and on disk. |
| **AC-12** | Rename file | Right-click a file, select Rename, enter new name, press Enter. File renamed on disk and reflected in tree. |
| **AC-13** | Delete file with confirmation | Right-click a file, select Delete. Confirmation modal appears. Click Delete. File removed from disk and tree. |
| **AC-14** | Delete non-empty folder blocked without recursive flag | Right-click a non-empty folder, select Delete. Modal warns "Delete {name} and all {n} items?". Cancel leaves folder intact. |
| **AC-15** | Move within section | Select a file, click Move in toolbar, pick a different folder in same section. File moves on disk. |
| **AC-16** | Cross-section drag blocked | Drag a file from Domain Data onto a Verified Workflows folder. Red border appears, drop is cancelled, toast fires. |
| **AC-17** | Cross-section move API blocked | POST /api/admin/move with src in domain_data and dest in verified_workflows → 400 with cross-section error. |
| **AC-18** | Duplicate file handling | Upload a file whose name already exists in target folder. Queue item shows error badge "File already exists." with Replace button. |
| **AC-19** | New MD File stub | Right-click a Verified Workflows folder, select New MD File, enter name. Created file on disk contains YAML frontmatter stub. |
| **AC-20** | Frontmatter validation icon | Upload an MD file without frontmatter to Verified Workflows. File tree shows warning icon. Upload MD with valid frontmatter — green check icon appears. |
| **AC-21** | workflow_list picks up new verified workflow | Upload a valid MD file with frontmatter to Verified Workflows. Call workflow_list from the agent. New workflow appears in results within next tool call — no restart. |
| **AC-22** | Index rebuilt after mutation | Upload a file, then call GET /api/admin/tree/domain_data. Response reflects the newly uploaded file. |

> **12. Out of Scope**

- File preview in the Admin Panel (no preview pane)

- In-browser MD editing in the Admin Panel (edit is a Chat UI / My Workflows feature only)

- User management UI — promoting/demoting admin role is a backend config change

- Multi-admin concurrent conflict resolution — last write wins

- Version history or undo for deleted files

- Auto-updating application.properties when admin moves a referenced folder

- Chunked resumable upload (20 MB max makes standard multipart sufficient)

- Admin access to My Data or My Workflows (user-governed sections remain exclusive to Chat UI)
