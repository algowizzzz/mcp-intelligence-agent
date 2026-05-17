# GAP Fixes — UAT Plan

**Date:** 2026-04-05  
**Feature:** 5 architectural gap fixes identified in `requirements/Requirements_Gap_Analysis.md`  
**Test method:** Code-inspection (CI) + live API (BT) + direct module import  
**Prerequisites:** Servers NOT required for CI tests. Agent server (`uvicorn agent_server:app --port 8000`) required for BT tests.

---

## Fixes Under Test

| Gap | Fix |
|-----|-----|
| GAP-01 | `msdoc_tools_tool_refactored.py` migrated to `sajha.storage` module |
| GAP-02 | `WorkerRepository` wired into `agent_server.py`; `_load_workers` / `_find_worker` delegate to repo |
| GAP-03 | Chart endpoint uses `serve_file()` instead of `FileResponse` directly |
| GAP-04 | `_VERIFIED_WF` / `_MY_WF` constants removed; global `data/workflows/verified|my/` dirs retired; 2 my-workflow files migrated to MR worker |
| GAP-05 | `_DOMAIN_DATA` / `_MY_DATA` constants removed; `data/domain_data/` and `data/uploads/` migrated to MR worker and retired from disk |

---

## Code-Inspection Tests

### CI-GAP-01a — msdoc_tools imports storage module

**Check:** `msdoc_tools_tool_refactored.py` imports `from sajha.storage import storage` and does NOT import `from pathlib import Path`.

---

### CI-GAP-01b — msdoc_tools uses BytesIO for document reads

**Check:** `_read_word_document` and `_read_excel_document` call `storage.read_bytes(file_path)` and pass `io.BytesIO(raw)` to `Document()` / `load_workbook()`.

---

### CI-GAP-01c — msdoc_tools uses storage.exists() and storage.list_prefix()

**Check:** All `file_path.exists()` calls replaced with `storage.exists(file_path)`. `_list_files_by_type()` calls `storage.list_prefix(self.docs_directory)`.

---

### CI-GAP-02a — WorkerRepository imported and instantiated in agent_server.py

**Check:** `agent_server.py` contains `from sajha.worker_repository import WorkerRepository` and `_worker_repo = _WorkerRepository(...)`.

---

### CI-GAP-02b — _load_workers and _find_worker delegate to repo

**Check:** `_load_workers()` returns `_worker_repo.list()`. `_find_worker()` returns `_worker_repo.find(worker_id)`. No `json.loads(_SAJHA_WORKERS_FILE` call in these functions.

---

### CI-GAP-02c — _save_workers calls reload after write

**Check:** `_save_workers()` calls `_worker_repo.reload()` after writing the file.

---

### CI-GAP-03 — chart endpoint uses serve_file()

**Check:** `agent_server.py` chart serve endpoint calls `serve_file(str(chart_path), media_type=...)` not `FileResponse(str(chart_path), ...)` directly.

---

### CI-GAP-03b — serve_file accepts media_type parameter

**Check:** `serve_file(path, media_type=None)` signature updated to pass `media_type` through to `FileResponse`.

---

### CI-GAP-04a — global workflow constants removed

**Check:** `agent_server.py` does NOT contain `_VERIFIED_WF` or `_MY_WF` as variable assignments.

---

### CI-GAP-04b — global workflow directories do not exist on disk

**Check:** `sajhamcpserver/data/workflows/verified/` and `sajhamcpserver/data/workflows/my/` do not exist.

---

### CI-GAP-04c — migrated my-workflow files present in MR worker

**Check:** `data/workers/w-market-risk/workflows/my/` contains `BMO_Market_Credit_Risk_Intelligence_Brief_Workflow.md` and `market_credit_risk_intelligence_brief.md`.

---

### CI-GAP-05a — global domain constants removed

**Check:** `agent_server.py` does NOT contain `_DOMAIN_DATA` or `_MY_DATA` as variable assignments.

---

### CI-GAP-05b — global data directories do not exist on disk

**Check:** `sajhamcpserver/data/domain_data/` and `sajhamcpserver/data/uploads/` do not exist.

---

### CI-GAP-05c — MR worker domain_data contains all migrated subdirs

**Check:** `data/workers/w-market-risk/domain_data/` contains `osfi/`, `templates/`, `test_ccr/`, `Test/`.

---

## Backend / API Tests (require running servers)

### BT-GAP-02 — worker listing API still works after repo wiring

**Request:** `GET /api/super/workers` (super_admin JWT)  
**Expected:** 200, returns array of workers. WorkerRepository is the source of truth.

---

### BT-GAP-02b — worker lookup works after repo wiring

**Request:** `GET /api/super/workers/w-market-risk/files/domain_data`  
**Expected:** 200, returns file tree. Worker found via `_find_worker()` → repo.

---

### BT-GAP-03 — chart file serve still works

**Request:** `GET /api/fs/charts/<any_existing_chart_file>` with valid JWT  
**Expected:** 200, file served correctly. No regression from serve_file() change.

---

### BT-GAP-04 — MR worker verified workflows still accessible via API

**Request:** `GET /api/super/workers/w-market-risk/files/verified_workflows`  
**Expected:** 200, returns 12 workflow files. Served from MR worker-scoped path.

---

### BT-GAP-05 — MR worker domain_data still accessible via API

**Request:** `GET /api/super/workers/w-market-risk/files/domain_data`  
**Expected:** 200, returns files including osfi/, templates/, test_ccr/ after migration.

---

## Acceptance Criteria Summary

| ID | Criterion | Expected |
|----|-----------|---------|
| CI-GAP-01a | msdoc_tools imports storage, not pathlib.Path | PASS |
| CI-GAP-01b | BytesIO used for Word and Excel reads | PASS |
| CI-GAP-01c | storage.exists() and storage.list_prefix() used | PASS |
| CI-GAP-02a | WorkerRepository imported and instantiated | PASS |
| CI-GAP-02b | _load_workers / _find_worker delegate to repo | PASS |
| CI-GAP-02c | _save_workers calls reload after write | PASS |
| CI-GAP-03 | Chart endpoint uses serve_file() | PASS |
| CI-GAP-03b | serve_file accepts media_type | PASS |
| CI-GAP-04a | _VERIFIED_WF / _MY_WF constants removed | PASS |
| CI-GAP-04b | Global workflow dirs do not exist on disk | PASS |
| CI-GAP-04c | My-workflow files present in MR worker | PASS |
| CI-GAP-05a | _DOMAIN_DATA / _MY_DATA constants removed | PASS |
| CI-GAP-05b | Global domain_data / uploads dirs do not exist | PASS |
| CI-GAP-05c | MR worker domain_data has all migrated subdirs | PASS |
| BT-GAP-02 | Worker listing API works | PASS |
| BT-GAP-02b | Worker lookup works | PASS |
| BT-GAP-03 | Chart file serve works | PASS |
| BT-GAP-04 | Verified workflows accessible | PASS |
| BT-GAP-05 | Domain data accessible after migration | PASS |
