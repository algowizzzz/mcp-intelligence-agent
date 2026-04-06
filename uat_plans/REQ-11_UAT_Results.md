# REQ-11 UAT Results — Multi-File Parallel Upload Engine

**Status:** ✅ 14/14 CI PASS  
**Date:** 2026-04-05  
**Tester:** Automated (direct API + async httpx)  
**Environment:** agent_server :8000 · auth via JWT  

---

## Test Execution Summary

| Test | Description | Result | Notes |
|------|-------------|--------|-------|
| UP-01 | Single upload without batch_id → reindex triggered | ✅ PASS | 200, `size_bytes=33` |
| UP-02 | Single upload with batch_id → reindex skipped | ✅ PASS | 200, no automatic reindex |
| UP-03 | POST /reindex after batch → rebuilds index | ✅ PASS | `indexed_files=49`, `elapsed_ms=1.6` |
| UP-04 | 51 MB upload → 413, no leftover partial file | ✅ PASS | 413, `bigfile-qa.bin` not present after |
| UP-05 | Upload to nonexistent worker → 404 | ✅ PASS | 404 |
| UP-06 | Path traversal in upload path → 400 | ✅ PASS | `?path=../../config` → 400 |
| UP-07 | 5 concurrent uploads (httpx async) all 200 | ✅ PASS | All 200, reindex → 54 files |
| UP-08 | 0-byte file upload → 200 | ✅ PASS | 200 |
| UP-09 | overwrite=true on existing file → 200 | ✅ PASS | 200 |
| UP-10 | overwrite=false on existing file → 409 | ✅ PASS | 409 |
| UP-11 | User endpoint (`/api/fs/uploads/upload`) with batch_id → 200 | ✅ PASS | 200 |
| UP-12 | BAC 10K (1.3 MB) streamed via aiofiles | ✅ PASS | `size_bytes=1358117` |
| UP-13 | Admin reindex endpoint (`/api/admin/worker/files/domain_data/reindex`) | ✅ PASS | `indexed_files=56` |
| UP-14 | Freshness — upload common file → BM25 detects it on next search | ✅ PASS | `rebuilt=True`, unique token found |

---

## Key Verifications

### Streaming (aiofiles)
- 64 KB chunked write via `_stream_upload()` helper
- 50 MB limit enforced mid-stream; partial file cleaned up on overflow
- Verified with 1.3 MB BAC 10-K markdown (well under 50 MB, confirms end-to-end streaming path)

### Batch ID / Deferred Reindex
- `?batch_id=<id>` parameter skips per-file `build_index()` call
- Explicit `POST .../reindex` triggers a single rebuild (elapsed ~1–2 ms for typical domain_data size)
- Both super (`/api/super/workers/{id}/files/{section}/reindex`) and admin (`/api/admin/worker/files/{section}/reindex`) reindex endpoints operational

### Concurrent Uploads
- 5 simultaneous `httpx.AsyncClient` uploads via `asyncio.gather` — all return 200
- File system handles concurrent writes to distinct filenames without collision

### Error cases
- `413` on >50 MB — streamer checks byte count mid-write, raises `HTTPException`, cleans up via `dest.unlink(missing_ok=True)`
- `404` on unknown worker — worker lookup fails before path resolution
- `400` on path traversal — `_resolve_admin_path_for_worker` detects `..` in path
- `409` on duplicate without `overwrite=true`

---

## Browser Tests (BT) — Pending

| ID | Scenario | Status |
|----|----------|--------|
| UP-UI-01 | Select 10 files → upload → queue shows 10 items, 4 simultaneous progress bars | ⏳ Pending |
| UP-UI-02 | Multi-file upload → batch progress bar with files/MB counter | ⏳ Pending |
| UP-UI-03 | Upload 10 files → tree refreshes exactly ONCE after all complete | ⏳ Pending |
| UP-UI-04 | Oversized file (>50 MB) in picker → toast, not queued | ⏳ Pending |
| UP-UI-05 | Upload 3 files → one fails → retry | ⏳ Pending |
| UP-UI-06 | Cancel during batch → XHRs aborted, completed kept, tree refreshes | ⏳ Pending |

Browser tests require live Playwright environment — deferred pending test window.

---

## Notes

- All test filenames include a per-run UUID suffix (`RUN = uuid.uuid4().hex[:8]`) — fully idempotent, safe to re-run
- SAJHA BM25 `_INDEX_CACHE` uses 3-part key `domain|my_data|common` — fingerprint detects newly uploaded common files without TTL wait
- `aiofiles` added to `requirements.txt` (>=23.0)
