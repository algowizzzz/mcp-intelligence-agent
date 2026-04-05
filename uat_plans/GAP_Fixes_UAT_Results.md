# GAP Fixes — UAT Results

**Date:** 2026-04-05  
**Plan:** [GAP_Fixes_UAT_Plan.md](GAP_Fixes_UAT_Plan.md)  
**Execution:** Automated — CI via Python ast/grep inspection; BT via live HTTP against port 8000  
**Overall:** ✅ **19 PASS / 0 FAIL / 0 SKIP**

---

## CI Results (Code Inspection)

| ID | Test | Result | Detail |
|----|------|--------|--------|
| CI-GAP-01a | msdoc_tools imports storage, not pathlib.Path | **PASS** | `from sajha.storage import storage` present; `from pathlib import Path` removed |
| CI-GAP-01b | BytesIO used for Word and Excel reads | **PASS** | `storage.read_bytes(file_path)` + `io.BytesIO(raw)` in both `_read_word_document` and `_read_excel_document` |
| CI-GAP-01c | storage.exists() and storage.list_prefix() used | **PASS** | All 4 `file_path.exists()` calls replaced with `storage.exists(file_path)`; `_list_files_by_type` uses `storage.list_prefix` |
| CI-GAP-02a | WorkerRepository imported and instantiated | **PASS** | `from sajha.worker_repository import WorkerRepository as _WorkerRepository`; `_worker_repo = _WorkerRepository(config_path=...)` |
| CI-GAP-02b | _load_workers / _find_worker delegate to repo | **PASS** | `_load_workers()` returns `_worker_repo.list()`; `_find_worker()` returns `_worker_repo.find(worker_id)`; no `json.loads(_SAJHA_WORKERS_FILE` in either function |
| CI-GAP-02c | _save_workers calls reload after write | **PASS** | `_worker_repo.reload()` called after file write in `_save_workers()` |
| CI-GAP-03 | Chart endpoint uses serve_file() | **PASS** | `serve_file(str(chart_path), media_type=...)` used; `FileResponse(str(chart_path)` not present |
| CI-GAP-03b | serve_file accepts media_type parameter | **PASS** | `def serve_file(path: str, media_type: str = None)` — passes through to `FileResponse(path, media_type=media_type)` |
| CI-GAP-04a | _VERIFIED_WF / _MY_WF constants removed | **PASS** | Neither constant appears outside comments in `agent_server.py` |
| CI-GAP-04b | Global workflow directories retired from disk | **PASS** | `sajhamcpserver/data/workflows/verified/` and `.../workflows/my/` do not exist |
| CI-GAP-04c | My-workflow files present in MR worker | **PASS** | `BMO_Market_Credit_Risk_Intelligence_Brief_Workflow.md` and `market_credit_risk_intelligence_brief.md` both present in `data/workers/w-market-risk/workflows/my/` |
| CI-GAP-05a | _DOMAIN_DATA / _MY_DATA constants removed | **PASS** | Neither constant appears outside comments in `agent_server.py` |
| CI-GAP-05b | Global domain_data / uploads dirs retired | **PASS** | `sajhamcpserver/data/domain_data/` and `sajhamcpserver/data/uploads/` do not exist |
| CI-GAP-05c | MR worker domain_data has all migrated subdirs | **PASS** | `osfi/`, `templates/`, `test_ccr/`, `Test/` all present in `data/workers/w-market-risk/domain_data/` |

---

## BT Results (Live API — port 8000)

Auth: `risk_agent` / `RiskAgent2025!` (role: super_admin)

| ID | Test | Result | Detail |
|----|------|--------|--------|
| BT-GAP-02 | Worker listing API returns workers | **PASS** | `GET /api/super/workers` → HTTP 200, `worker_count=8` |
| BT-GAP-02b | Worker file tree lookup works | **PASS** | `GET /api/super/workers/w-market-risk/files/domain_data` → HTTP 200 |
| BT-GAP-03 | Chart file serve works via serve_file() | **PASS** | `GET /api/fs/charts/chart_bar_20260403_201904.html` → HTTP 200, `8637 bytes` returned |
| BT-GAP-04 | MR worker verified workflows accessible | **PASS** | `GET /api/super/workers/w-market-risk/files/verified_workflows` → HTTP 200 |
| BT-GAP-05 | MR worker domain_data contains migrated osfi dir | **PASS** | `GET /api/super/workers/w-market-risk/files/domain_data` → HTTP 200, `osfi` in response tree |

---

## Files Changed

| File | Change |
|------|--------|
| `sajhamcpserver/sajha/tools/impl/msdoc_tools_tool_refactored.py` | Added `storage` import; migrated `_list_files_by_type` to `storage.list_prefix`; migrated `_read_word_document` / `_read_excel_document` / `MsDocGetWordMetadataTool.execute` to `storage.read_bytes` + `io.BytesIO`; replaced all `file_path.exists()` with `storage.exists(file_path)`; removed `from pathlib import Path` |
| `agent_server.py` | Imported `WorkerRepository`; created `_worker_repo` singleton; updated `_load_workers()`, `_find_worker()` to use repo; updated `_save_workers()` to call `_worker_repo.reload()`; updated `serve_file()` to accept `media_type`; fixed chart endpoint to use `serve_file()`; removed `_DOMAIN_DATA`, `_MY_DATA`, `_VERIFIED_WF`, `_MY_WF` constants; set `_ADMIN_SECTION_ROOTS = {}` |
| `sajhamcpserver/data/workers/w-market-risk/workflows/my/` | Added `BMO_Market_Credit_Risk_Intelligence_Brief_Workflow.md`, `market_credit_risk_intelligence_brief.md` (migrated from global `data/workflows/my/`) |
| `sajhamcpserver/data/workers/w-market-risk/domain_data/` | Added `osfi/`, `templates/`, `test_ccr/`, `Test/` subdirectories (migrated from global `data/domain_data/`) |
| `sajhamcpserver/data/workers/w-market-risk/my_data/risk_agent/` | Added `123/` directory (migrated from global `data/uploads/`) |
| `sajhamcpserver/data/domain_data/` | **Deleted** — all content migrated to MR worker |
| `sajhamcpserver/data/uploads/` | **Deleted** — all content migrated to MR worker `my_data/risk_agent/` |
| `sajhamcpserver/data/workflows/verified/` | **Deleted** — content was already duplicated in MR worker |
| `sajhamcpserver/data/workflows/my/` | **Deleted** — content migrated to MR worker |

---

## Gap Analysis Update

All 5 gaps from `requirements/Requirements_Gap_Analysis.md` are now **CLOSED**.

| Gap | Status | Remaining |
|-----|--------|-----------|
| GAP-01 msdoc_tools storage migration | ✅ CLOSED | None |
| GAP-02 WorkerRepository wiring | ✅ CLOSED | None |
| GAP-03 serve_file() adoption | ✅ CLOSED | None — `FileResponse` no longer used directly outside `serve_file()` |
| GAP-04 Global workflow dirs retired | ✅ CLOSED | None |
| GAP-05 Global domain_data/uploads retired | ✅ CLOSED | None |
