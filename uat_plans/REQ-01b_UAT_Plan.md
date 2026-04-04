# REQ-01b File Tree Phase 2 — UAT Plan

**Date:** 2026-04-04
**Feature:** File Tree Phase 2 — size display, search, quota, copy, batch-delete

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
**Status:** PENDING RESTART — Endpoint added to agent_server.py at line 1248 (before `/api/fs/{section}/tree` to avoid FastAPI path conflict). Requires server restart to activate.

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
**Status:** PENDING RESTART — Endpoint added to agent_server.py. Returned 405 Method Not Allowed on current server (old code). Requires server restart.

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
**Status:** PENDING RESTART — Endpoint added to agent_server.py. Returned 405 Method Not Allowed on current server (old code). Requires server restart.

---

## Browser Tests (PENDING — user to complete)

All browser tests require a server restart and browser reload after confirming all endpoints pass.

### BT-01 — File size shown in tree rows
- [ ] Open My Data tab in mcp-agent.html
- [ ] Verify each file row shows a size badge (e.g. "5 KB", "102 MB")
- [ ] Verify the `ft-row-meta` span is visible and right-aligned
- [ ] Expected: size appears for files, not for folders

### BT-02 — Search filters tree
- [ ] Call `tree.search('goldman')` from browser console
- [ ] Verify only files/folders matching "goldman" are shown
- [ ] Call `tree.clearSearch()` — verify full tree restored
- [ ] Expected: folders with no matching descendants are hidden; matching descendants keep parent folders visible

### BT-03 — Quota bar renders
- [ ] Call `tree.loadQuota('quota-container-id')` on a My Data BPulseFileTree instance
- [ ] Verify quota bar appears with green/amber/red color based on usage
- [ ] Verify "X KB used" label is shown
- [ ] Expected: bar width matches used_pct from `/api/fs/quota`

### BT-04 — Copy endpoint (if UI wired)
- [ ] Right-click a file → Copy (if UI exposes this)
- [ ] Or call `POST /api/fs/uploads/copy` via curl after restart
- [ ] Expected: file appears in destination section

### BT-05 — Batch delete endpoint (if UI wired)
- [ ] Enter bulk mode on My Data tree
- [ ] Select 2+ files → Delete Selected
- [ ] Alternatively call `POST /api/fs/uploads/batch-delete` via curl after restart
- [ ] Expected: `{"deleted": [...], "errors": []}` with all selected files removed

---

## Notes

- BE-FS-001 required no backend change — data was already in `fs_index.py`.
- Quota endpoint path `/api/fs/quota` must be defined BEFORE `/api/fs/{section}/tree` to prevent FastAPI matching "quota" as a section parameter. This ordering is correctly implemented.
- Server is currently running without `--reload`. Restart required: `uvicorn agent_server:app --port 8000 --reload`
