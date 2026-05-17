# REQ-01b Backend Test Results

**Date:** 2026-04-04
**Tester:** Claude (automated curl)
**Server:** http://localhost:8000

---

## Summary

| Test | Endpoint | Status | Result |
|------|----------|--------|--------|
| BE-FS-001 | GET /api/fs/uploads/tree | **PASS** | `size_bytes` + `modified_at` on every file node |
| BE-FS-004 | GET /api/fs/quota | **PASS** | `{"used_bytes":580660,"limit_bytes":5368709120,"used_pct":0.01}` |
| BE-FS-002 | POST /api/fs/{section}/copy | **PASS** | `{"ok":true,"dest_path":"_test_copy_dst.md"}` |
| BE-FS-003 | POST /api/fs/{section}/batch-delete | **PASS** | `{"deleted":["_test_copy_src.md"],"errors":[]}` |

All 4 backend acceptance criteria met. No failures.

---

## Test 1: BE-FS-001 — Tree includes size_bytes and modified_at

**Endpoint:** `GET /api/fs/uploads/tree`

**Result:** PASS — data was already in `fs_index.py`, no backend code change needed.

**Sample file node:**
```json
{
  "type": "file",
  "name": "UAT9D_test_245c1a.md",
  "path": "UAT9D_test_245c1a.md",
  "size_bytes": 19,
  "modified_at": "2026-04-03T22:50:28.361384+00:00",
  "mime": "text/markdown"
}
```

---

## Test 2: BE-FS-004 — Quota endpoint

**Endpoint:** `GET /api/fs/quota`

**Response:**
```json
{
  "used_bytes": 580660,
  "limit_bytes": 5368709120,
  "used_pct": 0.01
}
```

**Notes:**
- Endpoint defined at line 1248 in `agent_server.py`, **before** `/api/fs/{section}/tree` to prevent FastAPI matching "quota" as a `section` parameter — ordering verified.
- Quota calculated from `my_data/{user_id}/` directory (uploads section).
- Default limit: 5 GB (5,368,709,120 bytes).

---

## Test 3: BE-FS-002 — Copy file between sections

**Setup:** Created `_test_copy_src.md` in `uploads` section.

**Request:**
```bash
POST /api/fs/uploads/copy
{"src_path":"_test_copy_src.md","dest_section":"my_workflows","dest_path":"_test_copy_dst.md"}
```

**Response:**
```json
{"ok": true, "dest_path": "_test_copy_dst.md"}
```

**Edge cases covered by implementation:**
- 403 if destination section is read-only (domain_data, verified_workflows)
- 404 if source file does not exist
- 409 if destination already exists

---

## Test 4: BE-FS-003 — Batch delete

**Request:**
```bash
POST /api/fs/uploads/batch-delete
{"paths":["_test_copy_src.md"],"include_dirs":false}
```

**Response:**
```json
{"deleted": ["_test_copy_src.md"], "errors": []}
```

**Notes:**
- `include_dirs: false` guards against accidental directory deletion
- Returns per-path `errors` array — partial success is possible
- Index rebuilt after all deletes

---

## Files Changed

| File | Change |
|------|--------|
| `agent_server.py` | Added `GET /api/fs/quota`, `POST /api/fs/{section}/copy`, `POST /api/fs/{section}/batch-delete` |
| `public/js/file-tree.js` | Added `loadQuota()`, `search()`/`clearSearch()`, file size display in tree rows |
