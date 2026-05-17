# REQ-01b — File Tree: Phase 2 Backend Changes & Additional Features
**Status:** Pending Implementation (after REQ-01a is complete and stable)
**Version:** 1.0 (2026-04-04)
**Scope:** Backend additions and enhanced features for the shared file tree library. Do not start this until REQ-01a acceptance criteria are fully met.

---

## Prerequisite

REQ-01a must be complete:
- `BPulseFileTree` shared library is live in production
- All three old implementations replaced and deleted
- All smoke tests passing
- BUG-FS-001, BUG-FS-002, BUG-FS-003 fixed

---

## Phase 2 — Backend Changes

### BE-FS-001 — File Size and Modified Date in Tree Response

**File:** `agent_server.py` — `GET /api/fs/{section}/tree` handler

Add `size_bytes` and `modified_at` to each file node in the tree JSON response:

```json
{
  "name": "report.csv",
  "type": "file",
  "path": "reports/report.csv",
  "size_bytes": 48210,
  "modified_at": "2026-04-03T14:22:11Z"
}
```

Same change for admin and super_admin tree endpoints.

**Frontend:** `BPulseFileTree` displays size (formatted: KB/MB) and modified date in each file row. Visible on hover or as a persistent secondary line.

### BE-FS-002 — Copy File Between Sections

**New endpoint:**
```
POST /api/fs/{section}/copy
Body: { "src_path": "reports/report.csv", "dest_section": "my_data", "dest_path": "reports/report.csv" }
```

Copy a file from one section to another within the same worker. Returns 200 on success, 409 if dest already exists, 400 if cross-worker (not supported).

**Frontend:** Context menu → "Copy to…" → modal with section picker and destination folder browser → calls copy endpoint → refreshes both sections.

### BE-FS-003 — Batch Delete

**New endpoint:**
```
POST /api/fs/{section}/batch-delete
Body: { "paths": ["file1.csv", "folder/file2.md"], "include_dirs": false }
```

Delete multiple files in one request. Returns `{ "deleted": [...], "errors": [...] }`.

**Frontend:** Bulk select mode → select items → "Delete Selected" → single API call → tree refreshes. Replaces the current loop-based approach in `adminBulkDelete`.

### BE-FS-004 — Storage Quota Check

**New endpoint:**
```
GET /api/fs/quota
Response: { "used_bytes": 104857600, "limit_bytes": 5368709120, "used_pct": 1.9 }
```

Quota is per-user `my_data` directory. Limit configurable via `application.properties` key `data.my_data_quota_bytes` (default 5 GB).

**Frontend:** Displayed in the My Data section header as a small usage bar. Warning at 80%, error at 95%.

---

## Phase 3 — Additional Features

### F-SEARCH-01 — File Search / Filter Within Tree

Client-side filter using the already-loaded tree data. No new API call.

- Search input appears at top of each section panel
- Filters tree nodes by filename (case-insensitive, partial match)
- Matching nodes shown; non-matching nodes hidden
- Parent folders of matching files kept visible
- Clear button restores full tree
- Keyboard shortcut: `Ctrl+F` / `Cmd+F` when sidebar is focused

### F-META-01 — File Metadata Overlay

Clicking a file's info icon (from BE-FS-001 data) shows a popover:
- Full path, size, last modified, file type
- If `.md`: word count, frontmatter keys detected

### F-COPY-01 — Copy File Between Sections UI

Described in BE-FS-002 above. Context menu entry: "Copy to…"

### F-VERSION-01 — File Version History (Low Priority)

On write operations (rename, overwrite upload), backend preserves the previous version in a `.versions/{filename}/{timestamp}` path. Max 5 versions per file.

Frontend: "History" context menu item → side panel listing versions → click to preview or restore.

**Backend change:** Modify upload and rename handlers to call `_save_version(path)` before overwriting.

---

## Acceptance Criteria

**Phase 2:**
- [ ] Tree API response includes `size_bytes` and `modified_at` for all file nodes
- [ ] Copy endpoint implemented, tested with files across all section combinations
- [ ] Batch delete endpoint implemented, returns correct `deleted`/`errors` breakdown
- [ ] Quota endpoint returns correct `used_bytes` for `my_data/{user_id}/`
- [ ] Frontend: file size visible in tree rows
- [ ] Frontend: quota bar shows in My Data section header

**Phase 3:**
- [ ] Search/filter works client-side with no API call for filtering
- [ ] `Ctrl+F` focuses search input when sidebar open
- [ ] Copy UI allows selecting destination section + folder
- [ ] Version history UI shows up to 5 versions per file (if F-VERSION-01 implemented)

---

## Out of Scope

- Real-time collaborative editing
- Git-based version control integration
- Full-text content search (inside file contents)
- S3 or cloud storage backend (see REQ-08)
- Cross-worker file sharing
