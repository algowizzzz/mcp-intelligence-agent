# Archive Index

This folder holds **historical artifacts** that are not part of the live runtime, the live test suite, or the active documentation set. Nothing here is referenced by code, CI, or other docs. Everything was moved here on **2026-05-17** as part of a tiered repo cleanup; full history is preserved via `git log --follow <path>`.

If you need something from here, copy it back to its original location and remove from archive — do not edit in place.

---

## Layout

```
archive/
├── INDEX.md                       ← you are here
├── poc-edgar/                     ← POC code superseded by production tools
├── uat-tests/                     ← root-level UAT test scripts (not the live test suite)
├── data-ingestion-scripts/        ← one-off data-download scripts
├── uat-results/                   ← raw test output artifacts (was UAT_RESULTS/)
├── uat-plans/                     ← test plans for completed UAT phases (was uat_plans/)
├── legacy-docs/                   ← Word docs + duplicate markdown (was Documentation/)
├── completed-requirements/        ← shipped REQ specs + duplicate ERDs (was requirements/completed/)
└── handover-stale-snapshot/       ← stale April 2026 snapshot of handover/03_requirements/pending/
```

---

## `poc-edgar/` (3 files)

EDGAR + Tavily proof-of-concept scripts that predated the production tool implementations.

| File | Purpose |
|---|---|
| `poc_edgar_find_filing.py` | Early Tavily-based SEC filing finder |
| `poc_edgar_extract_section.py` | Section extraction from filing HTML |
| `poc_edgar_get_metric.py` | XBRL financial metric retrieval |

**Replaced by:** `sajhamcpserver/sajha/tools/impl/edgar_tavily_tools.py`, `edgar_metric_tools.py`.

---

## `uat-tests/` (9 files)

Root-level UAT test files. These were ad-hoc phase tests, **not** part of the pytest suite in `tests/` (which is still live and contains `test_api.py`, `test_tools.py`, `test_req07_postgres.py`, `test_req08a_s3.py`).

| File | Phase / scope |
|---|---|
| `test_uat_phase1.py` (37 KB) | UAT Phase 1 regression scenarios |
| `test_uat_phase2.py` (41 KB) | UAT Phase 2 regression scenarios |
| `test_uat_phase3.py` (9 KB) | UAT Phase 3 regression scenarios |
| `test_uat_module9.py` (44 KB) | Module 9 (worker-path / UI) end-to-end |
| `test_admin_api.py` (14 KB) | Admin API exercise (workers, users, files) |
| `test_connectors.py` (3 KB) | Connector smoke tests |
| `test_multiworker_platform.py` (47 KB) | Multi-worker isolation end-to-end |
| `test_platform_complete.py` (15 KB) | Platform completeness smoke run |
| `uat_framework.py` (13 KB) | Shared helpers used by the UAT scripts above |

**To re-run any of these**, copy the file (and `uat_framework.py`) back to the repo root and invoke directly — they're standalone scripts, not pytest collections. CI does not reference them.

---

## `data-ingestion-scripts/` (6 files)

One-time data-pull scripts used to populate `bank_filings/`, `regulatory_downloads/`, `regulatory_md/` (all gitignored). Not run by any cron, CI, or runtime path.

| File | What it fetched |
|---|---|
| `download_bank_filings.py` (20 KB) | SEC bank 10-K / 10-Q filings |
| `download_ca_ir.py` (11 KB) | Canadian bank Investor Relations packets |
| `download_regulatory_data.py` (21 KB) | OSFI / Basel regulatory documents (primary) |
| `download_regulatory_browser.py` (10 KB) | Browser-driver variant for JS-rendered sites |
| `download_regulatory_retry.py` (15 KB) | Retry orchestrator for the above |
| `convert_regulatory_to_md.py` (3 KB) | PDF / DOCX → Markdown post-processor |

**To refresh data**, copy the relevant script back, install any extra deps, and run. Output dirs are still gitignored — that has not changed.

---

## `uat-results/` (72 files, was `UAT_RESULTS/`)

Raw test-run output artifacts (`LATEST_phase*.{json,md}`, `MODULE9_*.md`, run logs). Kept for audit traceability of what was tested and when. Not consumed by the live app.

Useful for: regression diffing, validating that a specific UAT scenario was previously run and passed.

---

## `uat-plans/` (31 files, was `uat_plans/`)

UAT plans authored before each test phase: `Enhanced_Regression_Plan.md`, `PLATFORM_UAT_Plan.md`, `GAP_Fixes_UAT_Plan.md`, `Functional_Test_Results.md`, etc.

Useful for: understanding what was in-scope for each completed phase, designing future regression runs.

**Note:** Live planning has moved to `requirements/PLAN.md`, `requirements/NEXT_STEPS.md`, etc. — those are still at the repo root.

---

## `legacy-docs/` (16 entries, was `Documentation/`)

Mix of `.docx` reference manuals and freestanding markdown decks. Topically overlaps with the structured handover package in `handover/`, which is the maintained source.

| File | Topic |
|---|---|
| `Admin_User_Guide.docx` | Admin panel walkthrough (Word) |
| `Connectors_Guide.docx` | Microsoft / Atlassian connector setup |
| `Deployment_Guide.docx` | Production deployment (Docker / Hetzner) |
| `End_User_Guide_Market_Risk.docx` + `.md` | Market-risk worker user guide |
| `QA_Results_Summary.docx` | QA report snapshot |
| `Super_Admin_Guide.docx` | Super-admin tasks |
| `Technical_Documentation.docx` | Technical reference manual |
| `AWS_Enterprise_Deployment_Guide.md` | AWS-specific deployment notes |
| `AWS_Migration_Guide.md` | On-prem → AWS migration playbook |
| `Changelog_Apr10_Apr13_2026.md` | 4-day changelog (April 2026) |
| `Exec_Briefing_Copilot_vs_BPulse.md` | Exec-level positioning vs Copilot |
| `Exec_Briefing_Digital_Workers.md` | Exec-level digital-workers framing |
| `Infra_Agnostic_Strategy.md` | Infra-agnostic deployment strategy |
| `Product_Comparison_Copilot_vs_BPulse.md` | Feature comparison matrix |
| `screenshots/` | UI screenshots referenced by some of the above |

**Use `handover/` for current docs.** If a topic above has no equivalent in `handover/`, promote it back into `handover/` rather than editing here.

---

## `completed-requirements/` (42 files, was `requirements/completed/` + 5 stragglers from `requirements/pending/`)

Specs for requirements that have been verified implemented in code as of 2026-05-17. Moved here so `requirements/` only contains genuinely in-flight work.

Includes the 7 ERD / TRD `.docx` files that previously duplicated copies under `handover/02_architecture/` — the handover copies remain canonical.

| File pattern | Topic |
|---|---|
| `REQ-01a_Shared_FileTree_Library_Build_and_Swap.md` | Shared file-tree library — build and swap-in |
| `REQ-01b_FileTree_Phase2_Backend_and_Features.md` | File-tree Phase 2: size, search, quota, copy, bulk delete |
| `REQ-02a_Connector_External_Setup_Guide.md` | Microsoft / Atlassian connector setup walkthrough |
| `REQ-02b_Connector_MR_Worker_Integration_Testing.md` | Market-risk worker connector integration UAT plan |
| `REQ-03_Visualization_Tool_Debug_and_Rendering.md` | Visualisation tool fixes and chart rendering |
| `REQ-04a_Python_Execution_Tool_Basic.md` | Sandboxed Python execution — base implementation |
| `REQ-04b_Python_Execution_Tool_Heavy_Quant_Libraries.md` | Python sandbox with arch / riskfolio / sklearn etc. |
| `REQ-05_Summarization_Engine.md` | Context summarisation middleware |
| `REQ-07_PostgreSQL_Database_Migration.md` | Postgres-backed workers / users / checkpoints |
| `REQ-08_DevOps_Cloud_Deployment_Guide.md` | Docker / supervisord / nginx / GH Actions deployment |
| `REQ-08a_S3_Object_Storage_Integration.md` | `S3StorageBackend` + `STORAGE_BACKEND=s3` switch |
| `REQ-10_Common_Data_Path.md` | Read-only `common/` data layer across workers |
| `REQ-11_Multi_File_Parallel_Upload.md` | Batched parallel uploads + SSE completion events |
| `RiskGPT_*_ERD.docx` (5 files) | Platform / Connector / MultiWorker / Admin Panel / Data-Workflows ERDs (handover/02_architecture/ has the canonical copies) |
| `mcp-agent-trd-final.docx` | Technical Requirements Document (handover/02_architecture/ has the canonical copy) |
| `*.docx` etc. | Additional Word/PRD/Test-plan artifacts associated with the above |

**To revive a completed REQ for re-work**, copy the spec back to `requirements/pending/` (or `requirements/drafts/`) and link it from `handover/00_START_HERE.md`.

---

## `handover-stale-snapshot/2026-04_pending/` (13 files)

A frozen April-2026 copy of what was then `handover/03_requirements/pending/`. Most of the requirements in it are now actually completed (Phase 0 code reconnaissance verified). The directory was relocated wholesale because (a) it contradicted the live state in `requirements/pending/`, and (b) handover should reflect current reality, not a moment in time.

Useful only for: "what did the team think was pending on April 5, 2026."

The live in-flight backlog now lives in `requirements/pending/` (5 files: REQ-06, 08b, 14, 15, 16) and is summarised in `handover/00_START_HERE.md`.

---

## Restoring something

```bash
git mv archive/<subdir>/<file>  <original_path>
git commit -m "restore: bring <file> back from archive"
```

To see when a file was archived and the prior history:
```bash
git log --follow archive/<subdir>/<file>
```
