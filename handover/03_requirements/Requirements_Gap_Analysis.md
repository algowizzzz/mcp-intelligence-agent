# Requirements Gap Analysis — RiskGPT / B-Pulse Digital Workers

**Date:** 2026-04-05  
**Scope:** All documents in `requirements/completed/` cross-referenced against the live codebase.  
**Analyst:** Claude Code (automated review + manual verification)  
**Overall Status:** REQ-01 through REQ-04 ✅ fully implemented. Six architectural prep requirements partially implemented. Five requirements pending (REQ-05 to REQ-08 + REQ-03 Listener Workflows).

---

## Summary Table

| Requirement | Doc | Status | Gaps |
|-------------|-----|--------|------|
| REQ-01a — BPulseFileTree shared library | completed | ✅ COMPLETE | None |
| REQ-01b — File tree phase 2 (size, search, quota, copy, bulk-delete) | completed | ✅ COMPLETE | None |
| REQ-03 — Visualisation toolkit (chart rendering pipeline) | completed | ✅ COMPLETE | 1 minor (2 FileResponse calls bypass serve_file) |
| REQ-04a — Python sandbox (basic libs + security) | completed | ✅ COMPLETE | None |
| REQ-04b — Python sandbox (extended quant libs) | completed | ✅ COMPLETE | None |
| REQ-PREP-01 — Storage abstraction layer (`storage.py`) | completed | ✅ COMPLETE | None |
| REQ-PREP-02 — Unified path resolver (`path_resolver.py`) | completed | ✅ COMPLETE | None |
| REQ-PREP-03 — Migrate all tools to storage + resolver | completed | ✅ COMPLETE (updated 2026-04-05) | `msdoc_tools` migrated. `duckdb_olap_advanced` config writes and `workflow_tools` infra reads are acceptable — not domain data I/O. See GAP_Fixes_UAT_Results.md |
| REQ-PREP-04 — DuckDB in-memory + worker context routing | completed | ✅ COMPLETE | `duckdb_olap_advanced.py` still has 3 direct `open()` calls |
| REQ-PREP-05 — BytesIO write pattern for output tools | completed | ✅ COMPLETE | None confirmed |
| REQ-PREP-06 — WorkerRepository | completed | ✅ COMPLETE (updated 2026-04-05) | `_worker_repo` singleton wired; `_load_workers` / `_find_worker` delegate to repo; `_save_workers` calls `reload()`. See GAP_Fixes_UAT_Results.md |
| REQ-PREP-07 — File serve abstraction | completed | ✅ COMPLETE (updated 2026-04-05) | `serve_file()` updated with `media_type` param; chart endpoint migrated. `FileResponse` no longer used directly. See GAP_Fixes_UAT_Results.md |
| REQ-WF-01 — Retire global verified workflows directory | completed | ✅ COMPLETE (updated 2026-04-05) | `_VERIFIED_WF` removed; `data/workflows/verified/` deleted. See GAP_Fixes_UAT_Results.md |
| REQ-WF-02 — Unify section key to `verified_workflows` | completed | ✅ COMPLETE | Both `'verified'` and `'verified_workflows'` handled in `_resolve_worker_path()` |
| REQ-WF-03 — Fix super admin file tree endpoint resolver | completed | ✅ COMPLETE | `_resolve_admin_path_for_worker()` used for all super admin file endpoints |
| REQ-WF-04 — Migrate global my-workflows to MR worker | completed | ✅ COMPLETE (updated 2026-04-05) | `_MY_WF` removed; 2 files migrated; `data/workflows/my/` deleted. See GAP_Fixes_UAT_Results.md |
| REQ-WF-05 — CCR worker verified workflows: intentionally empty | completed | ✅ COMPLETE | Documented decision; empty-state handled gracefully |
| REQ-DD-01 — Migrate global domain data to MR worker | completed | ✅ COMPLETE (updated 2026-04-05) | `_DOMAIN_DATA` removed; `data/domain_data/` deleted; all subdirs in MR worker. See GAP_Fixes_UAT_Results.md |
| REQ-DD-02 — Migrate global uploads to user-scoped my_data | completed | ✅ COMPLETE (updated 2026-04-05) | `_MY_DATA` removed; `data/uploads/` deleted; content in `my_data/risk_agent/`. See GAP_Fixes_UAT_Results.md |
| REQ-MD-01 — my_data is per-user, not per-worker | completed | ✅ COMPLETE | `X-Worker-My-Data-Root` includes user_id sub-path at injection time |
| REQ-CD-01 — common_data as formal third category | completed | ✅ COMPLETE | `_COMMON_DATA` constant; `data/common/` on disk; read-only enforced in tools |
| REQ-API-01 — Audit all file endpoints for resolver consistency | completed | ✅ COMPLETE | All super admin endpoints now use `_resolve_admin_path_for_worker()` |
| REQ-API-02 — Audit SAJHA tool context header compliance | completed | ✅ COMPLETE | `operational_tools.py` `_domain_root()` and `_my_data_root()` check worker context first |
| EDGAR / Tavily / IR tools | completed | ✅ COMPLETE | No filesystem dependencies; fully external-API-based |
| Connector suite (Teams, Outlook, Jira, SharePoint) | completed | ✅ IMPLEMENTED | Teams channel send + Outlook email blocked by M365 permissions/licensing (not code defects) |
| Admin Panel Feature Parity | completed | ✅ COMPLETE | All admin panel CRUD functions defined and tested (see Functional_Test_Results.md) |
| Workflow Tool Suite | completed | ✅ COMPLETE | Verified via UAT |
| REQ-05 — Summarization Engine | **pending** | 🔲 NOT STARTED | Pending implementation |
| REQ-06 — B-Pulse Branding | **pending** | 🔲 NOT STARTED | Pending implementation |
| REQ-07 — PostgreSQL Migration | **pending** | 🔲 NOT STARTED | Pending implementation |
| REQ-08 — Apache Iceberg + S3 Data Strategy | **pending** | 🔲 ARCHITECTURE REVIEW | Pending |
| REQ-03 Listener Workflows | **pending** | 🔲 NOT STARTED | `.docx` spec exists, no UAT plan written |

---

## Detailed Findings

### 1. Completed — No Gaps

**REQ-01a, REQ-01b: BPulseFileTree**  
`public/js/file-tree.js` fully implements the shared library. All three inline implementations in `admin.html` (domain_data, verified_workflows) and `mcp-agent.html` (my_data) replaced. Phase 2 features (size display, search filter, quota bar, copy, bulk-delete) all tested via Playwright suite (37 PASS / 0 FAIL).

**REQ-04a, REQ-04b: Python Sandbox**  
`python_executor.py` fully implements sandboxed execution with AST-based blocked import detection, subprocess timeout, and matplotlib/Plotly figure capture. Extended quant libs (arch, riskfolio-lib, QuantLib, networkx, scikit-learn) all present in `python_sandbox_venv` and verified via backend + LLM tests. All 15 acceptance criteria passed.

**REQ-PREP-01: storage.py**  
`sajhamcpserver/sajha/storage.py` implements `LocalStorageBackend` with all 7 interface methods (`read_bytes`, `write_bytes`, `read_text`, `write_text`, `list_prefix`, `exists`, `delete`, `copy`). `S3StorageBackend` stub present but gated. Module-level `storage` singleton exported. Fully compliant.

**REQ-PREP-02: path_resolver.py**  
`sajhamcpserver/sajha/path_resolver.py` implements `resolve(category, worker_ctx, user_id)` for all 6 categories. S3 prefix variant returns `s3://bucket/...` when `STORAGE_BACKEND=s3`. `ValueError` raised for unknown categories and `my_data` without `user_id`. Fully compliant.

**REQ-WF-02: Section key unification**  
`agent_server.py:244–245` — both `'verified'` and `'verified_workflows'` are mapped in `_resolve_worker_path()`. Canonical key `'verified_workflows'` is now used throughout all new code and super admin endpoints.

**REQ-WF-03: Super admin file tree endpoint resolver**  
`agent_server.py:326–338` — `_resolve_admin_path_for_worker()` wraps `_admin_section_roots_for_worker()`. All super admin file endpoints (`GET /api/super/workers/{id}/files/{section}`, upload, read, write, delete, mkdir, rename, move) call this function. REQ-API-01 is satisfied.

**REQ-API-02: Tool context header compliance**  
`operational_tools.py:32–60` — `_domain_root()`, `_my_data_root()`, `_templates_dir()` all check `getattr(_g, 'worker_data_root', None)` / `getattr(_g, 'worker_my_data_root', None)` before any fallback. This is the highest-risk tool confirmed compliant.

---

### 2. Partial Implementation — Code Gaps

#### GAP-01 — REQ-PREP-03: Tools not fully migrated to storage module

**Status:** ⚠️ Partial  
**Spec requirement:** No tool file should use `open()`, `os.walk()`, `os.listdir()`, `pathlib.Path`, or `shutil` for data file access after migration.

**Findings:**

| Tool | Issue | Risk |
|------|-------|------|
| `msdoc_tools_tool_refactored.py` | Uses `from pathlib import Path` and passes path strings to `openpyxl.load_workbook()` and `python-docx` directly. No `storage` import. | Medium — will break on S3 |
| `duckdb_olap_advanced.py` | 3 `with open(config_dir / ...)` calls at lines 1009–1015 writing JSON config files. No `storage` import. | Low — config files, not data files |
| `workflow_tools.py` | Has `storage` import but 2 remaining `with open(...)` calls at lines 28, 47 (reading `application.properties` and metadata). | Low — infra files, not domain data |

**Not a gap:** `python_executor.py`'s 4 `open()` calls are for subprocess stdin/stdout temp files in a tmpdir — these are correct and should NOT use storage abstraction.

---

#### GAP-02 — REQ-PREP-06: WorkerRepository not wired into agent_server.py

**Status:** ⚠️ Partial  
**Spec requirement:** `agent_server.py` should contain no direct `json.load` calls against the workers file; `WorkerRepository` should be the only place that reads `workers.json`.

**Findings:**
- `WorkerRepository` class exists at `sajhamcpserver/sajha/worker_repository.py` with `find()`, `list()`, `find_by_user()`, and `reload()`. `PostgresWorkerRepository` stub present. Class is fully correct.
- `agent_server.py:106` — `_load_workers()` calls `json.loads(_SAJHA_WORKERS_FILE.read_text()).get('workers', [])` directly.
- `agent_server.py:115` — `_find_worker()` is defined and used in 15+ places throughout the file.
- The `WorkerRepository` class is **never imported or instantiated** in `agent_server.py`.

**Impact:** Postgres migration would still require touching `agent_server.py`. The repository pattern is correctly designed but the integration step was not completed.

---

#### GAP-03 — REQ-PREP-07: serve_file() defined but not fully adopted

**Status:** ⚠️ Partial  
**Spec requirement:** All file-serving endpoints should call `serve_file()` instead of `FileResponse` directly.

**Findings:**
- `serve_file()` is defined at `agent_server.py:35`.
- `agent_server.py:1566–1567` — chart file endpoint uses `FileResponse(str(chart_path), ...)` directly (2 calls on the same endpoint, conditional on file extension).
- All other file-serving endpoints appear to use `serve_file()`.

**Impact:** Chart file serving bypasses the abstraction. On S3 migration, chart downloads would need a separate fix.

---

#### GAP-04 — REQ-WF-01 / REQ-WF-04: Global workflow directories not retired from disk or code

**Status:** ⚠️ Partial  
**Spec requirement:** `_VERIFIED_WF` and `_MY_WF` constants removed from code; global `data/workflows/verified/` and `data/workflows/my/` directories deleted from disk after verification.

**Findings:**
- `agent_server.py:191–192` — `_VERIFIED_WF` and `_MY_WF` constants still defined.
- `data/workflows/verified/` — 12 files still present on disk.
- `data/workflows/my/` — directory exists on disk.
- However, these constants are NOT used as active fallbacks in any resolver — they appear to be referenced only in the `_resolve_admin_path` function for the global super admin section mapping (not the worker-scoped ones). Functional impact is low because worker-scoped resolvers are used in all live code paths.

**Risk:** Low for current operation. Medium for future: the constants could be picked up by mistake in new code.

---

#### GAP-05 — REQ-DD-01 / REQ-DD-02: Global domain_data and uploads not retired from disk

**Status:** ⚠️ Partial (code compliant; data migration incomplete)  
**Spec requirement:** `data/domain_data/` and `data/uploads/` emptied and retired; `_MY_DATA` constant removed.

**Findings:**
- `data/domain_data/` — still populated: `counterparties/`, `iris/`, `msdocs/`, `osfi/`, `duckdb/`, `sqlselect/`, `templates/`, `test_ccr/`.
- `data/uploads/` — still populated: `charts/`, `company_briefs/`, `counterparty_briefs/`, `exports/`, `reports/`.
- `agent_server.py:190` — `_MY_DATA` constant still defined as `_DATA_ROOT / 'uploads'`.
- `agent_server.py:201` — `_MY_DATA` is referenced in the global admin section roots mapping.
- Code layer (tool implementations) is worker-context-aware — `operational_tools.py` correctly checks worker context headers first.

**Risk:** Medium. Active workers (MR worker) have their own scoped paths configured and populated in `workers.json`. The global fallback paths remain functional. However, the spec calls for retirement to avoid split-brain confusion.

**Note:** The `data/workers/w-market-risk/domain_data/` directory already contains much of the same content. Both paths coexist.

---

### 3. Pending Requirements (Not Started)

#### REQ-05 — Summarization Engine

**Status:** 🔲 Not started  
**Location:** `requirements/pending/REQ-05_Summarization_Engine.md`  
**Scope:** Rolling context compression engine triggered at 180k tokens. SQLite-backed compression history. Context utilization gauge in both UIs. Permanent system notice when compressed.  
**Current state:** Agent server uses a basic reactive summarization. No compression gauge in UI. No SQLite compression log.

---

#### REQ-06 — B-Pulse Branding

**Status:** 🔲 Not started  
**Location:** `requirements/pending/REQ-06_Branding_BPulse_Digital_Workers.md`  
**Scope:** Rename all user-facing text from "RiskGPT" / "SAJHA MCP Server" / "Market Risk Digital Worker" to "B-Pulse Digital Workers".  
**Current state:** `public/mcp-agent.html` contains hardcoded "Market Risk Digital Worker" strings. `public/admin.html` contains "RiskGPT" references. Config files use `risk_agent` naming.

---

#### REQ-07 — PostgreSQL Database Migration

**Status:** 🔲 Not started  
**Location:** `requirements/pending/REQ-07_PostgreSQL_Database_Migration.md`  
**Scope:** Migrate user config, conversation history, audit logs, worker config from JSON/JSONL flat files to PostgreSQL.  
**Current state:** All config in `sajhamcpserver/config/` JSON files. Conversations in `data/threads.jsonl`. Audit log in `data/audit/tool_calls.jsonl`. `WorkerRepository` stub already provides the abstraction seam for worker config (GAP-02 above is the blocker for workers).

---

#### REQ-08 — Apache Iceberg + S3 Data Strategy

**Status:** 🔲 Architecture review pending  
**Location:** `requirements/pending/REQ-08_Apache_Iceberg_S3_Data_Strategy.md`  
**Scope:** Evaluate Apache Iceberg for analytical data layer; S3-first strategy for domain data and uploads.  
**Current state:** `storage.py` S3 stub is the groundwork. DuckDB in-memory (REQ-PREP-04 complete) removes the persistent file constraint.

---

#### REQ-03 Listener Workflows

**Status:** 🔲 No UAT plan  
**Location:** `REQ-03_Listener_Workflows.docx` (repo root)  
**Scope:** Event-driven workflow execution triggered by external events (Teams messages, scheduled timers, etc.).  
**Current state:** Spec document exists but has not been translated to a UAT plan or implementation. No listener code found in `agent_server.py` or SAJHA server.

---

### 4. External Blockers (Not Code Defects)

| Item | Blocker | Status |
|------|---------|--------|
| `teams_send_message` — channel send | No `ChannelMessage.Send` application permission in MS Graph | Deferred — M365 admin |
| `outlook_send_email` / `outlook_read_email` | `SaadAhmed@DeepLearnHQ.onmicrosoft.com` has no Exchange Online license | Deferred — M365 admin |
| Multi-worker connector scope isolation | Requires live credentials + 2 active workers | Deferred — connector setup |
| `testConnectorFromModal()` | Real credential test requires licensed connectors | Deferred — connector setup |

---

## Implementation Priority for Open Gaps

| Priority | Gap | Effort | Unblocks |
|----------|-----|--------|---------|
| P1 | GAP-02 — Wire WorkerRepository into agent_server.py | Small | REQ-07 (Postgres migration seam) |
| P1 | GAP-01 — Migrate msdoc_tools to storage module | Small | REQ-08 (S3 migration completeness) |
| P2 | GAP-04 — Retire global workflow dirs (disk + constants) | Small | Clean architecture |
| P2 | GAP-05 — Retire global domain_data + uploads (disk migration) | Medium | Clean architecture |
| P3 | GAP-03 — Chart endpoint to use serve_file() | Trivial | REQ-08 completeness |
| P4 | REQ-05 Summarization Engine | Large | User experience |
| P4 | REQ-06 B-Pulse Branding | Medium | Brand compliance |
| P5 | REQ-07 PostgreSQL | Large | Enterprise deployment |
| P5 | REQ-08 Iceberg / S3 | XL | Enterprise scale |

---

## Files Reviewed

| Source | Type | Reviewed |
|--------|------|---------|
| `requirements/completed/` | 4 `.md` + 23 `.docx` files | All .md files read; .docx titles and scope reviewed |
| `sajhamcpserver/sajha/storage.py` | Implementation | Full read |
| `sajhamcpserver/sajha/path_resolver.py` | Implementation | Full read |
| `sajhamcpserver/sajha/worker_repository.py` | Implementation | Full read |
| `agent_server.py` | Implementation | Key sections read (resolvers, WorkerRepository, serve_file, global constants) |
| `sajhamcpserver/sajha/tools/impl/operational_tools.py` | Implementation | Path resolver functions audited |
| `sajhamcpserver/sajha/tools/impl/` (all 38 files) | Audit | Storage module usage vs direct I/O checked via grep |
| `sajhamcpserver/data/` filesystem | Data | Directory listing to verify migration state |
| UAT result docs (all 7) | Test evidence | Cross-referenced for acceptance criteria verification |
