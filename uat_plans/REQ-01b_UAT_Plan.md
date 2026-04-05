# REQ-01b File Tree Phase 2 — UAT Plan

**Date:** 2026-04-04
**Feature:** File Tree Phase 2 — size display, search, quota, copy, batch-delete
**Test Execution Date:** 2026-04-05

---

## Scope

| ID | Change | Layer |
|----|--------|-------|
| BE-FS-001 | `size_bytes` + `modified_at` in tree response | Backend (pre-existing in fs_index.py) |
| BE-FS-002 | `POST /api/fs/{section}/copy` endpoint | Backend |
| BE-FS-003 | `POST /api/fs/{section}/batch-delete` endpoint | Backend |
| BE-FS-004 | `GET /api/fs/quota` endpoint | Backend |
| FE-SIZE | File size display in tree rows (`ft-row-meta` span) | Frontend |
| FE-SEARCH | `search(query)` / `clearSearch()` methods (F-SEARCH-01) | Frontend |
| FE-QUOTA | `loadQuota(containerId)` method | Frontend |

---

## Backend Tests

### BE-FS-001 — Tree returns size_bytes and modified_at

**Test:** `GET /api/fs/uploads/tree` — verify file nodes include both fields.

**Command:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"risk_agent","password":"RiskAgent2025!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/fs/uploads/tree \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tree'][0])"
```

**Expected:** File node contains `size_bytes` (integer) and `modified_at` (ISO timestamp).
**Status:** PASS — Confirmed size_bytes and modified_at present on all file nodes (data already provided by fs_index.py).

---

### BE-FS-004 — Quota endpoint

**Test:** `GET /api/fs/quota` — returns used_bytes, limit_bytes, used_pct.

**Command:**
```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/fs/quota
```

**Expected:** `{"used_bytes": <int>, "limit_bytes": 5368709120, "used_pct": <float>}`
**Status:** PASS — Returns `{"used_bytes":3514212,"limit_bytes":5368709120,"used_pct":0.07}`. Endpoint active at `/api/fs/quota` (defined before `/{section}/tree` in agent_server.py to avoid FastAPI path conflict).

---

### BE-FS-002 — Copy endpoint

**Test:** `POST /api/fs/uploads/copy` — copy a file cross-section.

**Command:**
```bash
# Create source file
curl -s -X PATCH http://localhost:8000/api/fs/uploads/file \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path":"uat_copy_test.txt","content":"copy test"}'

# Copy to my_workflows
curl -s -X POST http://localhost:8000/api/fs/uploads/copy \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"src_path":"uat_copy_test.txt","dest_section":"my_workflows","dest_path":"uat_copy_test.txt"}'
```

**Expected:** `{"ok": true, "dest_path": "uat_copy_test.txt"}`
**Status:** PASS — Endpoint active. Returns `{"ok":true,"dest_path":"uat_copy_test.txt"}`. Tested via browser JS console against live server.

---

### BE-FS-003 — Batch delete endpoint

**Test:** `POST /api/fs/uploads/batch-delete` — delete multiple files at once.

**Command:**
```bash
curl -s -X POST http://localhost:8000/api/fs/uploads/batch-delete \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"paths":["uat_batch_del_1.txt","uat_batch_del_2.txt"]}'
```

**Expected:** `{"deleted": ["uat_batch_del_1.txt", "uat_batch_del_2.txt"], "errors": []}`
**Status:** PASS — Endpoint active. Returns expected structure with all paths deleted and empty errors array.

---

## Browser Tests

Tested via `mcp-agent.html` (agent server port 8000) using browser JS console against `_bpftInstB` (user sidebar BPulseFileTree instances). All tests performed 2026-04-05.

### BT-01 — File size shown in tree rows

**Steps:**
- Opened My Data tab in mcp-agent.html (uploads section)
- Inspected `.ft-row-meta` spans on file rows

**Result:** PASS
- `document.querySelectorAll('#ft-uploads .ft-row-meta')` returned multiple elements
- File rows display human-readable sizes (e.g. "3.3 KB", "8.5 KB")
- Folder rows do not show size badges
- `.ft-row-meta` span is right-aligned within each row

---

### BT-02 — Search filters tree

**Steps:**
- Called `_bpftInstB.uploads.search('uat')` from browser console
- Verified only matching rows remain visible
- Called `_bpftInstB.uploads.clearSearch()` — verified full tree restored

**Result:** PASS
- `search('uat')` hides non-matching rows; folders containing matches remain visible
- `clearSearch()` restores all rows
- DOM class toggling works correctly — hidden rows have `display:none` style

---

### BT-03 — Quota bar renders

**Steps:**
- Called `instance.loadQuota('quota-test-div')` on a BPulseFileTree instance
- Verified quota bar HTML written to container
- Verified label and bar

**Result:** PASS (after bug fix)

**Bug found and fixed — BUG-01b-BT03-001:**
- **Root cause:** `loadQuota` used `this._prefix.replace(/\/[^\/]+$/, '')` to strip the section from the prefix. Since `_prefix` is `http://localhost:8000/api/fs` (already without section), this regex stripped `/fs` yielding `http://localhost:8000/api`. The function then fetched `/api/quota` → 404.
- **Correct endpoint:** `GET /api/fs/quota` (200, returns `{"used_bytes":3514212,"limit_bytes":5368709120,"used_pct":0.07}`)
- **Fix applied:** `file-tree.js` line 1057 — changed `var base = this._prefix.replace(/\/[^\/]+$/, '')` to `var base = this._prefix`
- **Verified:** With fix applied, loadQuota fetches `/api/fs/quota`, gets 200, renders `"3.4 MB used"` label + green progress bar (2 children in container). `used_pct=0.07` → green color (`#22c55e`).

---

### BT-04 — Copy endpoint (browser)

**Steps:**
- Called `POST /api/fs/uploads/copy` via browser XMLHttpRequest with `src_path:"uat_bt04_src.txt"`, `dest_section:"my_workflows"`, `dest_path:"uat_bt04_dest.txt"`
- Verified file appears in my_workflows tree via GET /api/fs/my_workflows/tree

**Result:** PASS
- Response: `{"ok":true,"dest_path":"uat_bt04_dest.txt"}`
- File `uat_bt04_dest.txt` confirmed present in my_workflows tree after copy

---

### BT-05 — Batch delete endpoint (browser)

**Steps:**
- Created test files `uat_bd_1.txt` and `uat_bd_2.txt` in uploads
- Called `POST /api/fs/uploads/batch-delete` with `paths:["uat_bd_1.txt","uat_bd_2.txt"]` via browser XHR
- Verified response and that files are removed from tree

**Result:** PASS
- Response: `{"deleted":["uat_bd_1.txt","uat_bd_2.txt"],"errors":[]}`
- Files no longer present in subsequent tree refresh

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| BE-FS-001: size_bytes + modified_at in tree response | **PASS** |
| BE-FS-002: Copy endpoint active and returns ok:true | **PASS** |
| BE-FS-003: Batch-delete endpoint active, returns deleted list | **PASS** |
| BE-FS-004: Quota endpoint returns used_bytes/limit_bytes/used_pct | **PASS** |
| BT-01: File size shown in tree rows | **PASS** |
| BT-02: Search filters + clearSearch restores | **PASS** |
| BT-03: Quota bar renders with label and color bar | **PASS (after fix)** |
| BT-04: Cross-section copy via browser | **PASS** |
| BT-05: Batch delete via browser | **PASS** |

---

## Bugs Found

### BUG-01b-BT03-001 — loadQuota fetches wrong URL (FIXED)

**File:** `public/js/file-tree.js`
**Line:** 1057 (original)
**Symptom:** `loadQuota()` shows nothing; quota bar is empty.
**Root cause:** Regex `this._prefix.replace(/\/[^\/]+$/, '')` incorrectly strips the last path segment `/fs` from the prefix `http://localhost:8000/api/fs`, yielding the base URL `http://localhost:8000/api`. Fetch hits `/api/quota` (404).
**Fix:** Replace `var base = this._prefix.replace(/\/[^\/]+$/, '')` with `var base = this._prefix`. The `_prefix` is already the FS base (`/api/fs`); quota is at `_prefix + '/quota'`.
**Status:** FIXED — committed to `public/js/file-tree.js`.

---

## Notes

- BE-FS-001 required no backend change — data was already in `fs_index.py`.
- Quota endpoint path `/api/fs/quota` must be defined BEFORE `/api/fs/{section}/tree` in agent_server.py to prevent FastAPI matching "quota" as a section parameter. This ordering is correctly implemented.
- Server was running without `--reload`; all endpoints confirmed active without restart (endpoints were already live from a prior restart).
