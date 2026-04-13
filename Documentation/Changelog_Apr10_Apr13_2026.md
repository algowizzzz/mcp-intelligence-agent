# B-Pulse Platform — Engineering Changelog
### April 6–13, 2026 (72 commits)

This document covers every commit made to the `main` branch during the 7-day period ending April 13, 2026. Commits are grouped thematically and listed in reverse-chronological order within each group. Each entry describes what changed, which files were modified, and why.

---

## Table of Contents

**April 10–13 (54 commits)**
1. [DuckDB Tool Engine — Subfolder Access & Concurrency Fixes](#1-duckdb-tool-engine)
2. [MsDocs & Python Executor — Subfolder Access Fixes](#2-msdocs--python-executor)
3. [SQLSelect — Auto-Discovery for Unfamiliar Files](#3-sqlselect)
4. [Agent Stability — Recursion, Concurrency, Timeouts](#4-agent-stability)
5. [Production Deployment — CI/CD, Docker, Hetzner](#5-production-deployment)
6. [Storage Layer — PostgreSQL + S3 (REQ-07/08a/15)](#6-storage-layer)
7. [Frontend — Chat History, File Manager, UI Fixes](#7-frontend)
8. [Requirements & Dependencies](#8-requirements--dependencies)
9. [New Workers & Config](#9-new-workers--config)
10. [Documentation & AWS Guides](#10-documentation--aws-guides)
11. [Tool Bug Fixes (Tavily, PDF, EDGAR)](#11-tool-bug-fixes)
12. [April 11 — DB Audit & LLM Factory](#12-april-11--db-audit--llm-factory)

**April 6 (18 commits)**
13. [REQ-12 — Heading Extraction, HuggingFace LLM, Handover Package](#13-april-6--req-12-heading-extraction-huggingface-llm-handover-package)
14. [Tool Additions — file_read, xAI Grok, LLM Config UI](#14-april-6--tool-additions--llm-config-ui)
15. [EDGAR Fixes & New Workflow](#15-april-6--edgar-fixes--sec-filing-workflow)
16. [Worker Path Resolution & Upload Tools](#16-april-6--worker-path-resolution--upload-tools)
17. [Frontend — Auth Guards, Canvas, UI Hardening](#17-april-6--frontend-auth-guards-canvas-ui-hardening)
18. [Sub-Agent Deadlock Fix](#18-april-6--sub-agent-deadlock-fix)

---

## 1. DuckDB Tool Engine

### `0ee10b3` — fix: duckdb_list_files and duckdb_query no longer block eventlet
**Date:** 2026-04-12 | **Files:** `agent/tools.py`, `duckdb_olap_tools_refactored.py`

**Root cause:** `duckdb_list_files.execute()` was calling `_initialize_views_from_files()` before returning results. That method opens a shared DuckDB connection and runs `CREATE VIEW` statements for every CSV/Parquet/JSON file. DuckDB's file I/O is C-level and bypasses eventlet's monkey-patched I/O — it blocks the entire Flask event loop, causing 30-second timeouts on first call.

**Fixes:**
- **`duckdb_list_files`**: Removed `_initialize_views_from_files()` call entirely. The tool only needs a filesystem scan (`_scan_data_files`) to return file names and view names — no DuckDB connection is needed. `view_name` is derived via the same sanitisation logic used by `duckdb_query`, so the agent can use it directly.
- **`duckdb_query`**: Removed `_initialize_views_from_files()` call — it was redundant since the fresh per-request connection already registers views itself inside `execute()` via `_scan_data_files()`.
- **`agent/tools.py`**: Added explicit per-tool HTTP timeouts for all DuckDB tools (60s) and Python execution tools (120s), overriding the 30s default that was causing premature timeouts before the underlying issue was fixed.

---

### `49ca469` — fix: duckdb_list_files now exposes view_name so agent can query subfolder files
**Date:** 2026-04-12 | **Files:** `duckdb_olap_tools_refactored.py`

**Problem:** `duckdb_list_files` was deriving `view_name` from the bare `filename` (e.g. `iris/IRIS_ALL_PROD_UTIL_2026-02-27.csv` → `IRIS_ALL_PROD_UTIL_2026_02_27`). But `duckdb_query` creates views using the `unique_key` (e.g. `iris__IRIS_ALL_PROD_UTIL_2026_02_27`). The mismatch meant `is_loaded` was always `False` and the agent was using the wrong name in SQL.

**Fix:** `view_name` now derived from `unique_key` (not `filename`) using the same sanitisation — strip extension, replace non-alphanumeric with `_`. Added `_usage` hint in the response body: `"Use view_name in SQL: SELECT COUNT(*) FROM <view_name>"`. Updated tool descriptions to instruct the agent to use `view_name` and never call `read_csv_auto()` with raw paths.

---

### `c042c30` — fix: DuckDB and sqlselect performance — stop blocking on every request
**Date:** 2026-04-12 | **Files:** `duckdb_olap_tools_refactored.py`, `sqlselect_tool_refactored.py`

**Problems addressed:**
1. **DuckDB timeout on parallel calls**: `_initialize_views_from_files()` was called on every `duckdb_query` call with `sample_size=-1` (full file read) plus a `SELECT COUNT(*)` verification per view. With 4 parallel duckdb_query calls, each call fully read every data file, blocking the server for 30+ seconds total.
2. **Shared connection crash**: The shared `self.conn` DuckDB connection was accessed concurrently by multiple greenlets. DuckDB's file I/O yields the Python GIL, allowing eventlet to schedule another greenlet — which then hits the same connection → "Server disconnected" crash.
3. **sqlselect blocking on auto-discovered files**: The Pass 2 auto-discovery was using `CREATE TABLE` (eager, reads all data on creation) instead of `CREATE VIEW` (lazy, reads data only at query time).

**Fixes:**
- `duckdb_query.execute()`: Replaced shared `self._get_connection()` with a fresh `duckdb.connect(':memory:')` per request, closed in `finally`. Views registered locally on the fresh connection, used, then discarded.
- `_initialize_views_from_files()`: Changed `sample_size=-1` → `sample_size=100`. Removed `SELECT COUNT(*)` verification after view creation. Added `_worker_init_key()` cache — skips full re-scan if the worker context (data directories) is unchanged since last call.
- `sqlselect auto-discovery`: Changed `CREATE TABLE` → `CREATE OR REPLACE VIEW` for auto-discovered files.

---

### `3f877f0` — fix: domain_data subfolder files now accessible in all 3 tool engines
**Date:** 2026-04-12 | **Files:** `duckdb_olap_tools_refactored.py`, `python_executor.py`, `sqlselect_tool_refactored.py`

**Root cause:** All three tool engines were silently skipping files in subdirectories (e.g. `iris/iris_combined.csv`). The DuckDB scanner had `if os.sep in rel_path: continue`. The msdoc list had the same guard. The sqlselect engine only registered named sources from config — files added to subfolders were invisible.

**Fix — DuckDB (`_scan_data_files`):** Removed subfolder skip. Instead, encodes the subfolder path into the view key: `iris/iris_combined.csv` → `unique_key = iris__iris_combined` → view name `iris__iris_combined`. Uses `storage.list_prefix()` (recursive `rglob`) so all nested files are found.

**Fix — Python executor (`_copy_context_files`):** Added `os.walk` fallback when a bare filename like `iris_combined.csv` is requested — searches recursively through domain_data to find the file regardless of subfolder.

**Fix — sqlselect (`_ensure_worker_sources` Pass 2):** Added auto-discovery via `os.walk(domain_data_dir)`. For any CSV/Parquet/JSON file found in any subfolder, registers a lazy `CREATE OR REPLACE VIEW` using the path-encoded name (`iris/iris_combined.csv` → table `iris__iris_combined`).

---

### `68161c6` — Fix DuckDB worker context: build ctx from g.worker_data_root headers
**Date:** 2026-04-12 | **Files:** `duckdb_olap_tools_refactored.py`

**Problem:** DuckDB tools were not resolving data directories from the Flask request context (`g.worker_data_root`), causing them to fall back to the static default path at startup time.

**Fix:** `_get_worker_ctx()` now reads `worker_data_root`, `worker_my_data_root`, and `worker_common_root` from Flask's `g` object (set by the auth middleware for each request) and builds a dict that `path_resolve()` can use.

---

### `9345f62` — Fix DuckDB tool: add missing time import + re-init per request
**Date:** 2026-04-12 | **Files:** `duckdb_olap_tools_refactored.py`

Added missing `import time` (was causing `NameError: name 'time' is not defined` in execution timing code). Added per-request view re-initialization so data directory changes take effect immediately without restarting the server.

---

### `261bf80` — fix: replace self.db_path with self.data_directory in DuckDB tools
**Date:** 2026-04-12 | **Files:** `duckdb_olap_tools_refactored.py`

Replaced 7 references to the old `self.db_path` attribute (from a previous refactor) with `self.data_directory`. `self.db_path` no longer exists — was causing `AttributeError` on tool calls that referenced it for path resolution.

---

## 2. MsDocs & Python Executor

### `e5047e6` — fix: msdoc tools can now find files in subfolders (e.g. bmo financials/)
**Date:** 2026-04-12 | **Files:** `msdoc_tools_tool_refactored.py`

**Problem:** `_list_files_by_type()` had `if os.sep in rel_path or '/' in rel_path: continue` — this silently dropped every file in a subfolder. `_get_file_path()` only searched the top-level directory. If a Word or Excel file was uploaded into a subfolder (e.g. `bmo/` or `financials/`), it was invisible to all msdoc tools.

**Fix:**
- `_list_files_by_type()`: Removed the subfolder skip guard. Added extension-based filter instead (only include `.docx`, `.xlsx` etc.). Deduplication now uses absolute path rather than filename to avoid false positives.
- `_get_file_path()`: Added `os.walk` recursive fallback when a bare filename is passed. If `bmo_annual_report.docx` is in `domain_data/bmo/`, the tool now finds it by walking all subdirectories.
- `msdoc_list_files.execute()`: Removed hardcoded `msdocs` subfolder restriction. Scans all three data layers (domain_data, my_data, common) recursively.

---

### `b7d75c7` — msdoc tools: search all data folders, not just domain_data/msdocs
**Date:** 2026-04-12 | **Files:** `msdoc_tools_tool_refactored.py`

Extended msdoc tool search scope from the hardcoded `domain_data/msdocs/` subfolder to all three data layers: `domain_data/`, `my_data/{user_id}/`, and `common/`. Files in any of these locations are now discoverable. This was a prerequisite for the subfolder fix above.

---

## 3. SQLSelect

### (covered above in `3f877f0` and `c042c30`)

The sqlselect engine (`sqlselect_tool_refactored.py`) received two changes:
1. **Subfolder auto-discovery** (Pass 2 in `_ensure_worker_sources`): walks `domain_data` recursively, registers any CSV/JSON/Parquet files it finds as lazy views.
2. **Performance fix**: Changed `CREATE TABLE` (eager load) → `CREATE OR REPLACE VIEW` (lazy, schema-only at creation, data read only at query time).

---

## 4. Agent Stability

### `798902a` — feat: raise max_concurrent_subagents ceiling from 4 to 8
**Date:** 2026-04-12 | **Files:** `agent/middlewares/subagent_limit.py`, `agent_server.py`

Raised the ceiling on parallel sub-agents from 4 to 8. The admin API (`PUT /api/admin/worker`) now accepts values in range `[2, 8]`. `SubagentLimitMiddleware` updated accordingly. Needed for complex multi-agent workflows that spawn many parallel data-retrieval agents.

---

### `531e7d4` — fix: raise LangGraph recursion_limit to 100 (was 25 default)
**Date:** 2026-04-12 | **Files:** `agent_server.py`

LangGraph's default `recursion_limit=25` was causing `GraphRecursionError` on longer multi-step workflows (e.g. counterparty intelligence briefs that chain 8+ tool calls). Raised to 100. Configured in the `RunnableConfig` passed to every graph invocation.

---

### `ec74fbb` — fix: retry SAJHA tool discovery at startup to avoid race condition
**Date:** 2026-04-12 | **Files:** `agent/tools.py`

**Problem:** The agent server starts SAJHA tool discovery before SAJHA is fully initialised. In Docker with supervisord, SAJHA (Flask on port 3002) starts a few seconds after the agent (FastAPI on port 8000). If tool discovery ran before SAJHA was ready, the agent started with 0 tools.

**Fix:** `discover_sajha_tools()` now retries up to 10 times with 3-second backoff. Added `_MIN_EXPECTED_TOOLS = 30` threshold — if fewer tools are returned, it's treated as a partial/failed discovery and retried. On repeated failure, logs a warning but does not crash.

---

## 5. Production Deployment

### `d496ca6` — Add CI/CD pipeline and Hetzner production deployment
**Date:** 2026-04-12 | **Files (new):** `.github/workflows/deploy.yml`, `docker-compose.prod.yml`, `scripts/bootstrap-server.sh`, `scripts/init-db.sql`

Set up the full CI/CD pipeline:
- **`deploy.yml`**: GitHub Actions workflow — builds Docker image, pushes to GHCR, SSHes into Hetzner server, pulls and restarts container. Triggered on push to `main`. Includes `/health` check to verify deployment.
- **`docker-compose.prod.yml`**: Production compose file with PostgreSQL 16, EFS-backed data volume, Secrets Manager env var injection, nginx on port 80, supervisord managing 3 processes (SAJHA + agent + nginx).
- **`scripts/bootstrap-server.sh`**: One-shot server provisioning script — installs Docker, pulls the image, sets up volumes, creates `.env` file, starts the stack.
- **`scripts/init-db.sql`**: PostgreSQL schema initialisation — creates `threads`, `audit_log`, `users`, `workers` tables with correct indexes.

---

### `0b29a4d` — fix(deploy): postgres start_period + correct psycopg3 DATABASE_URL
**Date:** 2026-04-12 | **Files:** `docker-compose.prod.yml`

Added `start_period: 30s` to the PostgreSQL healthcheck so the agent container waits for Postgres to be fully ready before connecting. Fixed the `DATABASE_URL` format: psycopg3 requires `postgresql+psycopg://` not `postgresql+psycopg2://` or `postgresql://`.

---

### `fc8cf8f` — fix(docker): add psycopg3 dependency and drop broken nginx sub_filter lines
**Date:** 2026-04-12 | **Files:** `nginx.conf`, `requirements.txt`

Added `psycopg[binary]` to `requirements.txt` (the psycopg3 binary wheel). Removed two broken `sub_filter` directives from `nginx.conf` that were causing nginx to fail on startup — they were leftover from a URL-rewriting attempt that was no longer needed.

---

### `58a25de` — fix(deploy): python-multipart, anthropic llm default, supervisord socket
**Date:** 2026-04-12 | **Files:** `requirements.txt`, `sajhamcpserver/config/llm_config.json`, `supervisord.conf`

- Added `python-multipart` to `requirements.txt` (required by FastAPI for form/file upload parsing — was missing from the prod image, causing 422 errors on uploads).
- Changed `llm_config.json` default provider from `xai` back to `anthropic` for production.
- Added supervisord socket and UNIX socket permissions config to `supervisord.conf` to allow the health-check and reload commands to work correctly inside the container.

---

### `acbe27c` / `b0d9ba2` — CI: force no-cache rebuild, then restore cache
**Date:** 2026-04-12 | **Files:** `.github/workflows/deploy.yml`

`acbe27c`: Temporarily disabled Docker layer cache in GitHub Actions (`--no-cache`) to force a clean reinstall of the sandbox Python venv after adding new packages (`arch`, `riskfolio-lib`, etc.).
`b0d9ba2`: Re-enabled cache once the fresh image was confirmed good, restoring fast build times.

---

### `82c999a` — Revert to local storage on Hetzner (Docker volumes persist)
**Date:** 2026-04-12 | **Files:** `.github/workflows/deploy.yml`, `docker-compose.prod.yml`

After investigating the Hetzner deployment, confirmed that Docker bind-mount volumes at `/opt/sajha/data` survive container rebuilds and restarts. Reverted the S3 storage backend to `local` — Supabase S3 was added as an option but is not needed on Hetzner where volumes are persistent. Removed S3 env vars from the deployment workflow.

---

### `a371ac6` — Remove Railway, switch to Supabase S3 for file storage
**Date:** 2026-04-12 | **Files:** `.github/workflows/deploy.yml`, `CLAUDE.md`, `docker-compose.prod.yml`, `railway.toml` (deleted)

Removed Railway as a deployment target (ephemeral filesystem was causing file loss on redeploy). Deleted `railway.toml`. Added Supabase S3 configuration to the production compose file as the persistent storage backend for that deployment phase (later reverted for Hetzner per the commit above).

---

## 6. Storage Layer

### `2797a32` — REQ-07 + REQ-08a: PostgreSQL DB layer + S3 storage — 41/41 CI tests PASS
**Date:** 2026-04-11 | **Files (many — major feature)**

The largest single commit of the sprint. Introduced the full PostgreSQL database layer and S3 storage abstraction.

**New files:**
- `sajhamcpserver/sajha/db/engine.py` — SQLAlchemy async engine, connection pool, session factory
- `sajhamcpserver/sajha/db/models.py` — ORM models: `Thread`, `AuditLog`, `User`, `Worker`, `WorkerUser`
- `sajhamcpserver/sajha/db/repo.py` — Repository layer: CRUD for all models, audit log writes, thread management
- `sajhamcpserver/sajha/db/migrations/` — Alembic migration scaffolding + initial schema migration
- `sajhamcpserver/alembic.ini` — Alembic config pointing at SAJHA's db
- `scripts/migrate_json_to_pg.py` — One-time migration script to move threads.jsonl + audit JSONL into Postgres
- `tests/test_req07_postgres.py` — 25 tests covering DB read/write, audit logging, thread persistence
- `tests/test_req08a_s3.py` — 16 tests covering S3 storage upload/download/delete/list

**Changes to existing files:**
- `agent_server.py`: Replaced JSONL-based thread and audit storage with async PostgreSQL writes via `repo.py`. All 85 endpoints now write threads and audit events to Postgres.
- `sajhamcpserver/sajha/storage.py`: Added `S3StorageBackend` class (alongside existing `LocalStorageBackend`). Backend selected via `STORAGE_BACKEND` env var. `S3StorageBackend` uses `boto3` with configurable endpoint URL for Supabase/Minio/AWS compatibility.
- `requirements.txt`: Added `sqlalchemy[asyncio]`, `asyncpg`, `psycopg[binary]`, `alembic`, `boto3`.
- `docker-compose.local.yml`: Added PostgreSQL 16 service for local dev.

---

### `d4416bc` — REQ-15 Phase 1-3: Supabase S3 persistent file storage
**Date:** 2026-04-12 | **Files:** `agent_server.py`, `sajhamcpserver/sajha/storage.py`, `sajhamcpserver/sajha/tools/impl/fs_index.py`, `requirements.txt`, `.gitignore`

Implemented S3-backed file operations across all three storage sections (domain_data, my_data, common):
- `agent_server.py`: All file upload, download, move, rename, delete, and tree endpoints now call `storage.upload()`, `storage.download()`, `storage.delete()`, `storage.list_prefix()` — abstracted over local or S3 backend.
- `fs_index.py`: Refactored BM25 index builder to use the storage abstraction instead of direct `pathlib` calls, so indexing works on both local files and S3 objects.
- `storage.py`: `S3StorageBackend.list_prefix()` uses `paginator` to handle buckets with >1000 objects. `upload()` streams in 64KB chunks to avoid loading large files into memory.

---

### `93c709e` — Fix PostgreSQL checkpoint URL: strip postgresql+psycopg:// prefix
**Date:** 2026-04-12 | **Files:** `agent_server.py`

LangGraph's `AsyncSqliteSaver` was being passed a PostgreSQL URL by mistake. Fixed: `CHECKPOINT_DB_PATH` is now correctly used as a SQLite file path. Separately, the PostgreSQL `DATABASE_URL` is passed only to `AsyncEngine` for the repo layer. The URL format `postgresql+psycopg://` is now correctly stripped to the base `postgresql://` when needed by psycopg3 directly.

---

### `0641036` — Fix PostgreSQL audit and thread DB writes (REQ-07)
**Date:** 2026-04-11 | **Files:** `agent/tools.py`, `agent_server.py`, `dev.sh`, `sajhamcpserver/sajha/db/engine.py`

Fixed async database write failures:
- `engine.py`: Added connection retry with exponential backoff. Fixed async session factory to use `expire_on_commit=False` (prevents lazy-load errors on already-committed objects).
- `agent_server.py`: Fixed async context manager usage in audit log writes — was incorrectly using `await` outside async context.
- `dev.sh`: Added `DATABASE_URL` export for local development.
- `agent/tools.py`: Fixed tool audit log serialisation — tool inputs were being double-serialised as JSON strings inside JSON objects.

---

## 7. Frontend

### `d02781e` — Chat history restored on logout/login from DB + LangGraph checkpoints
**Date:** 2026-04-12 | **Files:** `agent_server.py`, `public/mcp-agent.html`

**Backend (`agent_server.py`):** Added `GET /api/agent/threads` endpoint that returns all threads for the current user+worker from PostgreSQL, including the last message content, timestamp, and thread ID. Added `GET /api/agent/threads/{thread_id}/messages` to retrieve the full message history for a specific thread from LangGraph checkpoints.

**Frontend (`mcp-agent.html`):** On login and page refresh, the chat history sidebar now calls `GET /api/agent/threads` and populates the sidebar with previous conversations. Clicking a thread replays the history into the chat canvas from the checkpoint store.

---

### `ec78966` — fix: file manager UX — upload to selected folder, drag-drop target, Move to dialog
**Date:** 2026-04-12 | **Files:** `public/admin.html`, `public/js/file-tree.js`

Three file manager UX fixes:
1. **Upload to selected folder**: File upload now POSTs to the currently selected folder path rather than always uploading to the root. The selected folder is tracked as `currentUploadTarget` in the file tree state.
2. **Drag-and-drop target**: Dragging a file over a folder now visually highlights the folder as the drop target (CSS `drag-over` class). On drop, the file is moved to that folder via the `POST /api/fs/.../move` endpoint.
3. **Move to dialog**: Fixed the "Move to" context menu option — it now opens a modal with a folder picker populated from the current tree, and calls the move API with `dest_folder` (not `dst` which was the old parameter name).

---

### `73c8466` — fix: move API uses dest_folder not dst
**Date:** 2026-04-12 | **Files:** `public/js/file-tree.js`

The file move API (`POST /api/fs/.../move`) expects the parameter `dest_folder`. The frontend was sending `dst`. Fixed parameter name. Also fixed internal drag-drop to use the same parameter consistently.

---

### `cb4762a` — debug: add error tracing to context menu and move dialog
**Date:** 2026-04-12 | **Files:** `public/js/file-tree.js`

Added `console.error` tracing to the context menu action handlers and the move dialog submission to expose API errors in the browser console during debugging (these context menus were silently failing).

---

### `a269a45` — fix: set nginx client_max_body_size to 60M
**Date:** 2026-04-12 | **Files:** `nginx.conf`

nginx's default `client_max_body_size` is 1MB. Uploading any file larger than 1MB was returning a 413 "Request Entity Too Large" before the request even reached FastAPI. Set to `60M` to accommodate large Excel uploads (some clients have 30–40MB `.xlsx` files).

---

### `d13a7b1` — Fix 20 MB upload limit + tool HTTP-500 errors
**Date:** 2026-04-12 | **Files:** `Dockerfile`, `agent_server.py`, `nginx.conf`, `public/js/file-tree.js`, `sajhamcpserver/sajha/tools/base_mcp_tool.py`, `sajhamcpserver/sajha/tools/impl/python_executor.py`

- **`agent_server.py`**: Raised FastAPI's upload limit from 20MB to 50MB via `UploadFile` size limit config.
- **`nginx.conf`**: Set `client_max_body_size 60M` (later refined in `a269a45`).
- **`base_mcp_tool.py`**: Fixed HTTP-500 errors from tool calls — unhandled exceptions inside `execute()` were propagating as 500s. Added top-level exception handler that returns `{"error": str(e), "success": False}` instead.
- **`python_executor.py`**: Added Python version and available library check to sandbox preamble — lets the agent self-diagnose missing packages before attempting to use them.
- **`Dockerfile`**: Added `RUN pip install arch riskfolio-lib scikit-learn networkx xarray` to sandbox venv for financial analytics.

---

### `4b6f559` — fix(frontend): use relative API URLs in production
**Date:** 2026-04-12 | **Files:** `public/mcp-agent.html`

`mcp-agent.html` was using hardcoded `http://localhost:8000/api/...` URLs for 15 API calls. In production (served from the Hetzner server over HTTP), these calls were going to `localhost` on the user's machine and failing. Changed all API calls to relative URLs (`/api/...`) so they route through nginx to the backend correctly.

---

### `7ce9f58` — fix(frontend): syncThreadsFromDB use rg_token not mcp_token
**Date:** 2026-04-12 | **Files:** `public/mcp-agent.html`

The `syncThreadsFromDB()` function was looking for the auth token under the key `mcp_token` in localStorage. The auth system stores it as `rg_token`. Fixed the key name — chat history was not loading on page refresh because the Bearer token was missing from the API call.

---

### `a9b6ede` — fix(frontend): stub updateCostDisplay to fix chat history on refresh
**Date:** 2026-04-12 | **Files:** `public/mcp-agent.html`

`updateCostDisplay()` was called by the thread history loader but the function didn't exist in the production bundle, throwing a `ReferenceError` that interrupted the entire history load. Added a no-op stub.

---

## 8. Requirements & Dependencies

### `9f5fe60` — Fix library gaps: bcrypt + pydantic in requirements, sandbox venv complete
**Date:** 2026-04-12 | **Files:** `Dockerfile`, `requirements.txt`

- Added `bcrypt` to `requirements.txt` (was missing — needed for password hashing in the auth system).
- Added `pydantic[email]` (needed by FastAPI's email validator on user creation endpoints).
- `Dockerfile`: Added explicit `pip install --upgrade pip` before venv creation, and added `greenlet` to the sandbox venv (needed by SQLAlchemy's async mode inside the Python executor sandbox).

---

### `ff0d5f6` — fix: add pandas/plotly to SAJHA requirements + fix rollup_engine f-string syntax
**Date:** 2026-04-12 | **Files:** `sajhamcpserver/requirements.txt`, `sajhamcpserver/sajha/olap/rollup_engine.py`

- Added `pandas` and `plotly` to SAJHA's `requirements.txt`. These were being imported by OLAP tools but not declared as SAJHA dependencies (they existed in the agent requirements but not the SAJHA venv).
- Fixed f-string syntax error in `rollup_engine.py` — a `\n` inside an f-string expression (not allowed before Python 3.12) was causing a `SyntaxError` at import time, preventing rollup tools from loading.

---

### `b5eeb76` — fix: add python-docx and openpyxl to SAJHA requirements
**Date:** 2026-04-12 | **Files:** `sajhamcpserver/requirements.txt`

Added `python-docx` and `openpyxl` to SAJHA's `requirements.txt`. Both were used by the msdoc tools (Word and Excel reading) but were missing from the declared dependencies, causing `ImportError` when msdoc tools were first called after a clean Docker build.

---

## 9. New Workers & Config

### `4a94edb` — feat: add Finance Agent worker and users to repo config
**Date:** 2026-04-12 | **Files:** `sajhamcpserver/config/users.json`, `sajhamcpserver/config/workers.json`

Added a second production worker:
- **Worker ID:** `w-finance-agent`
- **Name:** Finance Agent
- **Users:** `finance_user_1`, `finance_user_2`, `finance_admin` — all with bcrypt-hashed passwords, correct role assignments (`user` / `admin`)
- **Enabled tools:** Full toolset including EDGAR, Tavily, Python execute, DuckDB, msdoc, IR tools
- **Config:** Separate data paths (`data/workers/w-finance-agent/`), its own system prompt, memory disabled by default

---

### `9afeff1` — Init w-finance-agent data directories
**Date:** 2026-04-12 | **Files:** `sajhamcpserver/data/workers/w-finance-agent/domain_data/.index.json`, `.../workflows/verified/.index.json`

Created the initial empty `.index.json` files for the Finance Agent worker's data directories so the BM25 indexer initialises correctly on first run.

---

## 10. Documentation & AWS Guides

### `55c3399` — docs: add executive briefing and product comparison docs
**Date:** 2026-04-12 | **Files (new):** `Documentation/Exec_Briefing_Copilot_vs_BPulse.md`, `Documentation/Exec_Briefing_Digital_Workers.md`, `Documentation/Product_Comparison_Copilot_vs_BPulse.md`

Three new sales/marketing documents:
- **`Exec_Briefing_Digital_Workers.md`**: One-page executive brief on the concept of Digital Workers — specialist per-desk AI agents vs generic assistants. Covers the 4 customisation dimensions, 3 bank use-case scenarios, and the business case framing.
- **`Exec_Briefing_Copilot_vs_BPulse.md`**: Side-by-side comparison of Microsoft Copilot and B-Pulse for a CFO/CRO audience. Includes the VaR query example (Copilot: searches SharePoint; B-Pulse: queries the live risk system). Two-layer architecture diagram.
- **`Product_Comparison_Copilot_vs_BPulse.md`**: Comprehensive feature comparison across 8 tables: Core AI capabilities, Knowledge & data access, Financial services tools, Document & Office tools, M365/collaboration connectors, Agent orchestration, Security/governance, Deployment/infrastructure.

---

### `d71ec39` — docs: add quick reference overview to AWS Enterprise Deployment Guide
**Date:** 2026-04-12 | **Files:** `Documentation/AWS_Enterprise_Deployment_Guide.md`

Added a 4-section Quick Reference at the beginning of the AWS guide: the 4-infra-swap table (Hetzner→AWS equivalents), 9-step checklist, 4 critical gotchas (IAM roles, EFS mount targets, secrets env var format, ALB idle timeout for SSE), and the CDK per-client isolation note.

---

### `be2a3db` — docs: add AWS Enterprise Deployment Guide for team onboarding
**Date:** 2026-04-12 | **Files (new):** `Documentation/AWS_Enterprise_Deployment_Guide.md`

745-line runbook covering the full Hetzner → AWS ECS migration:
- VPC setup (2 AZ, public/private subnets)
- RDS PostgreSQL 16 on private subnet
- EFS for persistent data volume (replaces Docker bind-mount)
- Secrets Manager for all credentials
- ECR repository + GitHub Actions push
- Full ECS task definition JSON (Fargate, 2 vCPU / 8 GB)
- ALB with HTTPS listener, 300s idle timeout for SSE
- GitHub Actions deploy workflow diff vs Hetzner version
- Data migration: `aws s3 cp` + `psql` restore commands
- Multi-client CDK TypeScript pattern (isolated RDS, EFS, secrets per client)
- Hetzner vs AWS operations cheat sheet

---

### `32421a4` — Add infra-agnostic strategy + AWS transition state doc
**Date:** 2026-04-12 | **Files (new):** `Documentation/Infra_Agnostic_Strategy.md`

195-line document explaining the infrastructure-agnostic design decisions baked into the codebase:
- How the 4 infrastructure swaps (Docker volume → EFS, local Postgres → RDS, env vars → Secrets Manager, SSH deploy → ECS rolling update) require zero application code changes
- The storage abstraction (`local` vs `s3` backend via env var)
- The PostgreSQL URL abstraction (same code, different connection string)
- Why single-container supervisord is compatible with ECS Fargate
- Current state audit: what works on Hetzner today vs what needs enabling for enterprise AWS

---

### `a9d7cee` — Add AWS migration guide (current stack, no new features)
**Date:** 2026-04-12 | **Files (new):** `Documentation/AWS_Migration_Guide.md`

252-line guide scoped to migrating the current Hetzner stack to AWS without adding new features. Step-by-step: create ECR repo, push image, create ECS cluster, configure task definition with existing env vars, set up ALB, point DNS. Includes troubleshooting section for the 3 most common failure modes.

---

### `ff5655a` — Docs v3.0: rewrite Technical, Connectors, Deployment guides
**Date:** 2026-04-12 | **Files:** `Documentation/Technical_Documentation.docx`, `Documentation/Connectors_Guide.docx`, `Documentation/Deployment_Guide.docx` (all binary, replaced)

Updated the three primary Word document guides to reflect the production-deployed state:
- **Technical Documentation**: Updated tool count (122 tools, 41 files), added PostgreSQL layer, S3 storage abstraction, middleware stack details, LangGraph checkpoint persistence.
- **Connectors Guide**: Added Microsoft Graph app registration steps for Teams/Outlook/SharePoint; updated Jira/Confluence OAuth flow; added connector scope configuration via admin panel.
- **Deployment Guide**: Replaced old Vercel+Railway instructions with Hetzner Docker deployment; added supervisord architecture diagram; added environment variable reference table.

---

### `33e725f` — REQ-16: Hetzner S3 migration requirements doc
**Date:** 2026-04-12 | **Files (new):** `requirements/pending/REQ-16_Hetzner_S3_Migration.md`

568-line requirements document for migrating Hetzner file storage from Docker bind-mount to an S3-compatible object store. Covers Hetzner Object Storage (S3-compatible endpoint), MinIO self-hosted on the same server as a fallback, and the migration plan (copy existing data, swap env var, verify). Includes audit findings of the 12 file operation functions that need path → key translation.

---

### `52d05e7` — REQ-15: Supabase Persistent Storage — requirements doc
**Date:** 2026-04-12 | **Files (new):** `requirements/pending/REQ-15_Supabase_Persistent_Storage.md`

Requirements doc for using Supabase as a managed PostgreSQL + S3-compatible storage backend. Covers bucket creation, RLS policies, API key scoping, the storage backend env var switch, and the migration path from Railway's ephemeral storage.

---

### `b565cf4` — Fix 5 tool bugs + gitignore runtime data
**Date:** 2026-04-12 | **Files:** `.gitignore`, `sajhamcpserver/requirements.txt`, `duckdb_olap_advanced.py`, `operational_tools.py` + ~200 runtime data files deleted

**Major gitignore addition:** Added patterns to stop tracking `sajhamcpserver/data/` runtime files — audit logs, generated reports, chart HTML files, user uploads, test artifacts, and index files. These should never be in source control (they're runtime data). Removed ~200 tracked files from the index.

**Tool fixes (5):**
1. `duckdb_olap_advanced.py`: Fixed `AttributeError` — `pivot_engine.py` was calling a method that no longer existed after a refactor.
2. `operational_tools.py`: Fixed `file_read` for binary files — was crashing with `UnicodeDecodeError` when reading non-UTF8 content. Added `errors='replace'` fallback.
3. `operational_tools.py`: Fixed `fill_template` tool — template variable substitution was silently skipping keys with hyphens. Normalised variable names.
4. `operational_tools.py`: Fixed `md_to_docx` — `python-docx` import was conditional on a flag that was never set to True.
5. Added `lxml` to `sajhamcpserver/requirements.txt` (needed by `operational_tools.py` for HTML template parsing).

---

## 11. Tool Bug Fixes

### `0e3a446` — Fix Tavily key handling in tavily_tool_refactored.py
**Date:** 2026-04-12 | **Files:** `sajhamcpserver/sajha/tools/impl/tavily_tool_refactored.py`

`TavilyClient` was being instantiated at class load time with the API key from the environment. If the key wasn't set at startup (or was rotated), the client held a stale or missing key. Fixed to instantiate `TavilyClient` per-request inside `execute()`, reading `TAVILY_API_KEY` fresh from the environment on each call. Added fallback to check both `TAVILY_API_KEY` and the legacy `API_KEY` env var names.

---

### `84dceef` — Fix pdf_read: implement missing _read_pdfplumber fallback + add PyMuPDF
**Date:** 2026-04-12 | **Files:** `sajhamcpserver/requirements.txt`, `sajhamcpserver/sajha/tools/impl/operational_tools.py`

`pdf_read` was calling `self._read_pdfplumber(path)` but the method was not implemented — it was a stub from an earlier version. Implemented the full method using `pdfplumber`:
- Text extraction with layout preservation
- Table detection and extraction as markdown
- Page-range targeting (reads only specified pages to stay within token limits)
Added `pymupdf` to requirements as the primary PDF parser (faster, better table extraction). `pdfplumber` retained as fallback.

---

### `8b72d18` — REQ-14: Bug report doc + Tavily key rotation in tool configs
**Date:** 2026-04-11 | **Files (new):** `requirements/pending/REQ-14_Bug_Fixes_SubAgent_Audit_EDGAR.md` + 4 Tavily tool JSON configs

Rotated the Tavily API key in all 4 tool configs (`tavily_web_search.json`, `tavily_research_search.json`, `tavily_news_search.json`, `tavily_domain_search.json`) — the old key was exhausted. Added a requirements doc cataloguing 3 confirmed bugs: sub-agent result truncation (8KB limit), audit log missing sub-agent tool calls, and EDGAR tool fallback order.

---

## 12. April 11 — DB Audit & LLM Factory

### `4eb65f5` — REQ-07: Comprehensive DB audit coverage for all agent events
**Date:** 2026-04-11 | **Files:** `agent/tools.py`, `agent_server.py`, `public/mcp-agent.html`, `sajhamcpserver/sajha/db/repo.py`

Extended the audit log to capture all agent events, not just tool calls:
- `agent_server.py`: Added audit writes for session start, session end, HITL approval/rejection, context compression events, sub-agent spawn/complete/fail, token budget exceeded.
- `repo.py`: Added `write_audit_batch()` for bulk inserts (used at end of session to flush buffered events).
- `agent/tools.py`: Tool audit entries now include `duration_ms`, `token_cost_estimate`, and `worker_id` in addition to the existing fields.
- `mcp-agent.html`: Added event listener for `summary_occurred` SSE event to display a "context compressed" banner in the UI.

---

### `86e10c2` — llm_factory: enable stream_options for xAI and HuggingFace token usage
**Date:** 2026-04-11 | **Files:** `agent/llm_factory.py`

xAI (Grok) and HuggingFace providers were not returning token usage in streaming mode. Added `stream_options={"include_usage": True}` to both provider configurations. This makes token counts available in the `usage` SSE event for non-Anthropic providers, enabling the context gauge and budget enforcement to work correctly regardless of which LLM is selected.

---

## Summary Statistics

| Category | Commits | Net Lines Changed |
|---|---|---|
| DuckDB tool engine fixes | 6 | ~400 |
| MsDocs / Python executor | 2 | ~150 |
| SQLSelect | 1 | ~80 |
| Agent stability | 3 | ~50 |
| Production deployment | 9 | ~500 |
| Storage layer (DB + S3) | 5 | ~2,500 |
| Frontend | 7 | ~300 |
| Requirements / deps | 4 | ~40 |
| New workers + config | 2 | ~290 |
| Documentation | 10 | ~2,500 |
| Tool bug fixes (Tavily, PDF) | 3 | ~100 |
| DB audit + LLM factory | 2 | ~200 |
| **Apr 10–13 Total** | **54** | **~7,100** |

---

---

## April 6, 2026 — 18 Commits

---

## 13. April 6 — REQ-12: Heading Extraction, HuggingFace LLM, Handover Package

### `4c22047` — REQ-12: Heading extraction for Word/PDF, msdoc section standardization, HuggingFace LLM switch
**Date:** 2026-04-06 | **Files:** Many — see sub-entries below

This was the largest single-day commit of the sprint. It landed three major things simultaneously:

**1. Heading extraction (msdoc + pdf_read):** Both `msdoc_read_word` and `pdf_read` gained a `heading=` parameter. When specified, the tool returns only the section under that heading (e.g. `heading="Risk Factors"`) rather than the full document. This makes long documents usable within the context window — a 200-page Word doc produces ~500 tokens for a specific section instead of 50,000 tokens for the whole thing.

**2. HuggingFace LLM switch:** `llm_config.json` updated to support `huggingface` as a provider. `llm_factory.py` extended to instantiate `ChatHuggingFace` with `meta-llama/Llama-3.3-70B-Instruct` as the default HuggingFace model. Provider switchable via admin panel without restart.

**3. Handover package (new `handover/` directory):** Created a structured 6-subdirectory handover package for client/team onboarding:
- `handover/00_START_HERE.md` — navigation index, 107 lines
- `handover/01_project_overview/` — `CREDENTIALS.md` (92 lines), `NEXT_STEPS.md` (163 lines)
- `handover/02_architecture/` — `SAJHA_MCP_Server_Architecture.md` (1,789 lines — full architecture reference), `Glossary.md` (779 lines), 6 ERD diagrams as Word docs
- `handover/03_requirements/` — `Requirements_Gap_Analysis.md` (243 lines) + 12 requirements docs (REQ-01a through REQ-11)
- `handover/04_uat_and_testing/` — `UAT_Master_Index.md` (162 lines), `Functional_Test_Results.md` (457 lines), `GAP_Fixes_UAT_Results.md` (71 lines), 11 UAT plans and results docs
- `handover/05_user_guides/` — all 6 user-facing Word documents (Admin Guide, Super Admin Guide, End User Guide, Deployment Guide, Connectors Guide, Technical Documentation)
- `handover/06_tools_reference/` — 10 individual tool reference guides (DuckDB, SQL Select, EDGAR, Tavily, Yahoo Finance, Federal Reserve, Bank of Canada, Investor Relations, MCP Studio REST creator, MCP Studio Python creator) — total ~15,000 lines of documentation

**Misc config updates:** 12 DuckDB and OLAP tool JSON configs updated to point at the refactored implementation class names.

---

### `9ea1649` — Add heading= extraction to msdoc_read_word and pdf_read
**Date:** 2026-04-06 | **Files:** `agent/tools.py`, `msdoc_read_word.json`, `pdf_read.json`, `msdoc_tools_tool_refactored.py`, `operational_tools.py`

Implementation commit for the heading extraction feature:
- `msdoc_tools_tool_refactored.py`: Added `_extract_section_by_heading()` method. Uses `python-docx` paragraph style inspection to find the heading, then collects all body text until the next heading of the same or higher level.
- `operational_tools.py`: Added `_extract_pdf_section_by_heading()` method. Uses `pdfplumber` to find text lines matching the heading pattern, then extracts subsequent lines until the next major heading is detected.
- `pdf_read.json`: Added `heading` to the input schema as an optional string parameter.
- `msdoc_read_word.json`: Added `heading` to the input schema.
- `agent/tools.py`: Updated `_TOOL_OUTPUT_LIMITS` — `msdoc_read_word` raised from 12k to 60k chars (heading extraction can still return large sections; 60k = ~15k tokens, matching `pdf_read`'s limit).

---

## 14. April 6 — Tool Additions & LLM Config UI

### `cbc0ca7` — LLM Provider config in Super Admin UI
**Date:** 2026-04-06 | **Files:** `agent/agent.py`, `agent/llm_factory.py`, `agent_server.py`, `public/admin.html`, `sajhamcpserver/config/llm_config.json`

Added a full LLM provider configuration panel to the Super Admin UI:
- **`admin.html`**: New "LLM Config" tab (273 lines added). Dropdowns for provider (`anthropic`, `xai`, `huggingface`, `bedrock`) and model name. On save, calls `PUT /api/super/llm-config`. Shows current provider/model at top.
- **`agent_server.py`**: Added `GET /api/super/llm-config` and `PUT /api/super/llm-config` endpoints. Write updates `llm_config.json` on disk. After write, calls `agent.reload_llm()` so the running agent picks up the new config without restart.
- **`agent/agent.py`**: Added `reload_llm()` function that re-reads `llm_config.json` and re-instantiates the LLM client. Wired to the hot-reload mechanism.
- **`agent/llm_factory.py`**: Refactored to read from `llm_config.json` on every call to `get_llm()` rather than caching at startup. Added `HuggingFaceEndpoint` support alongside existing Anthropic, xAI, and AWS Bedrock providers.
- **`llm_config.json`**: Added `huggingface` block with model, API key env var, and inference endpoint URL.

---

### `59a32c47` — Add file_read tool — read text files from all three data layers
**Date:** 2026-04-06 | **Files (new):** `sajhamcpserver/config/tools/file_read.json`, `sajhamcpserver/sajha/tools/impl/file_read_tool.py`

New tool: `file_read` — reads any plain-text file (`.md`, `.txt`, `.py`, `.json`, `.csv`, `.yaml`) from domain_data, my_data, or common. 186-line implementation:
- Accepts `file_path` (relative to data root) and optional `section` (`domain_data` / `my_data` / `common`)
- Resolves the file against the correct worker-scoped directory
- Returns full text content up to 60,000 chars (truncates with a warning at limit)
- Used by the agent to read Python scripts, markdown documents, and config files that don't need the full msdoc/pdf parser overhead

---

### `067e750` — Add xAI Grok provider to LLM factory
**Date:** 2026-04-06 | **Files:** `agent/llm_factory.py`

Added xAI Grok as a configurable LLM provider. Uses the `langchain-xai` package's `ChatXAI` class. Default model: `grok-3`. API key from `XAI_API_KEY` env var. Temperature=0, streaming=True, max_tokens from config. Added to the provider switch in `get_llm()` alongside Anthropic, HuggingFace, and Bedrock.

---

## 15. April 6 — EDGAR Fixes & SEC Filing Workflow

### `75fb96e` — Fix EDGAR timeout + add sec_filing_to_markdown workflow
**Date:** 2026-04-06 | **Files:** `agent/tools.py`, `workflows/verified/sec_filing_to_markdown.md`, `sajhamcpserver/sajha/tools/impl/edgar_tavily_client.py`

- **EDGAR timeout fix**: `edgar_tavily_client.py` was using a 10s HTTP timeout for SEC EDGAR archive requests. Large 10-K filings can be 10–15MB HTML files — hitting the timeout consistently. Raised to 60s. Also added streaming response handling for very large files.
- **`agent/tools.py`**: Added `edgar_extract_section` and `stream_sec_section` to `_TOOL_TIMEOUTS` with 120s timeout each.
- **New workflow `sec_filing_to_markdown.md`** (99 lines): Multi-agent workflow that takes a company ticker, fetches the most recent 10-K from SEC EDGAR, extracts MD&A + Risk Factors sections, and saves the result as a structured markdown file to `my_data`. Demonstrates the `edgar_extract_section` → `file_write` → `bm25_search` chain.

---

### `6115db7` — file_read: heading extraction for markdown + 60k output limit
**Date:** 2026-04-06 | **Files:** `agent/tools.py`, `sajhamcpserver/sajha/tools/impl/file_read_tool.py`

Extended `file_read_tool.py` to support `heading=` extraction for Markdown files (mirrors the Word/PDF feature). When `heading="Risk Management"` is passed, the tool returns only the markdown section starting with that `#` heading through the next heading of the same level. Added output limit of 60,000 chars to `_TOOL_OUTPUT_LIMITS` in `agent/tools.py`.

---

## 16. April 6 — Worker Path Resolution & Upload Tools

### `0ddec8d` — Fix msdoc + sqlselect: standardized worker-scoped data path resolution
**Date:** 2026-04-06 | **Files:** 11 msdoc JSON tool configs, `msdoc_tools_tool_refactored.py`, `sqlselect_tool_refactored.py`

**Problem:** msdoc and sqlselect tools were using hardcoded absolute paths from their JSON configs (`tool.msdoc.docs_directory`, `tool.sqlselect.data_directory`). When a different worker made a request, the tools still pointed at the default worker's data directory.

**Fix:**
- `msdoc_tools_tool_refactored.py` (303 lines changed): Replaced all hardcoded path reads with `path_resolve('domain_data', worker_ctx)` called per-request inside `execute()`. Added support for `my_data` and `common` data layers. Updated all 11 msdoc tool JSON configs to remove the static `data_directory` property.
- `sqlselect_tool_refactored.py` (46 lines added): Added per-request worker context resolution — `_ensure_worker_sources()` now reads `g.worker_data_root` on each call rather than once at init.

---

### `4f6fc27` — Fix worker-scoped path resolution, compact file listing, and UI robustness
**Date:** 2026-04-06 | **Files:** `CLAUDE.md`, `agent/prompt.py`, `agent_server.py`, `public/admin.html`, `public/js/file-tree.js`, `public/mcp-agent.html`, `sajhamcpserver/config/users.json`, `sajhamcpserver/config/workers.json`, `sajhamcpserver/sajha/tools/impl/python_executor.py`, `sajhamcpserver/sajha/tools/impl/upload_tools.py`

Large robustness commit:
- **`CLAUDE.md`**: Expanded from stub to 337-line developer reference covering all architecture layers, data paths, API endpoints, middleware stack, SSE protocol, and worker configuration options (the document is now the primary dev onboarding reference).
- **`agent/prompt.py`**: Added `PYTHON_ADDENDUM` (injected when python tools are enabled) and `MULTI_AGENT_ADDENDUM` (injected for multi-agent workers) to the system prompt factory. These addenda give the agent specific instructions for using python_execute with DATA_DIR, and for spawning sub-agents via the `task()` tool.
- **`agent_server.py`**: Fixed the `GET /api/fs/{section}/tree` endpoint to return a compact flat-list format instead of a deeply nested tree object (the nested tree was causing JSON serialisation timeouts for workers with many files).
- **`python_executor.py`**: Added `DATA_DIR` environment variable injection — every sandbox execution now has `DATA_DIR` set to the worker's `domain_data` path so scripts can read files with `pd.read_csv(f"{DATA_DIR}/iris/data.csv")` without needing `os` module access.
- **`upload_tools.py`**: Rewrote `list_uploaded_files` to search all three data layers (domain_data, my_data, common) and return compact `{filename, path, size, modified}` records instead of verbose metadata objects. Fixed `upload_file` to use worker-scoped destination path.
- **Config updates**: `users.json` — added test users, fixed bcrypt hashes. `workers.json` — updated enabled_tools lists, fixed data paths.
- **Admin/frontend**: Multiple `admin.html` and `file-tree.js` improvements — loading states, error messages on file ops, breadcrumb path display.

---

## 17. April 6 — Frontend: Auth Guards, Canvas, UI Hardening

### `8569f50` — UI security hardening: auth guards, 401 handling, remove deprecated key
**Date:** 2026-04-06 | **Files:** `public/admin.html`, `public/mcp-agent.html`, `public/regression_tests.html`, `public/regression_tests_v2.html`

- **`admin.html`**: Added auth guard — checks for valid JWT in localStorage on page load, redirects to `/login.html` if missing or expired.
- **`mcp-agent.html`**: Added `401` response handler on all API calls — if a response comes back 401, clears the stored token and redirects to login.
- **`public/regression_tests_v2.html`** (new, 1,356 lines): Full regression test runner — 45 test cases covering auth, file ops, tool calls, workflow execution, and HITL. Runs in-browser, reports pass/fail per test with response time.

---

### `a5e00b8` — mcp-agent.html: redirect to login if no session token
**Date:** 2026-04-06 | **Files:** `public/mcp-agent.html`

Added check at page load: if `localStorage.getItem('rg_token')` is null or empty, immediately redirect to `/login.html`. Prevents the chat UI from loading in a broken state for unauthenticated users (previously showed an empty chat with all API calls returning 401).

---

### `99505630` — index.html: add auth guard — route to login or role-appropriate page
**Date:** 2026-04-06 | **Files:** `public/index.html`

`index.html` is the default landing page. Added a JS auth check on load:
- No token → redirect to `/login.html`
- Token present, role = `super_admin` → redirect to `/admin.html`
- Token present, role = `admin` → redirect to `/admin.html`
- Token present, role = `user` → redirect to `/mcp-agent.html`

---

### `48218a5` — Fix canvas detection + shared library preview
**Date:** 2026-04-06 | **Files:** `agent_server.py`

Fixed the canvas SSE event detection logic in `agent_server.py`. The agent was returning Plotly HTML chart outputs as tool results — the server-side SSE handler needed to detect the `_chart_ready: true` flag in the tool result and emit a `canvas` event with the chart URL instead of embedding the raw HTML in the text stream. Previously the detection was checking the wrong field name; fixed to check `result.get('_chart_ready')`.

---

### `84d07f1` — Fix markdown headers + shared library preview in admin panel
**Date:** 2026-04-06 | **Files:** `public/admin.html`, `public/mcp-agent.html`

- **`admin.html`**: Fixed the "Shared Library" (common data) preview pane — it was showing raw JSON instead of rendered content. Added `marked.js` rendering for `.md` files and a table viewer for `.csv` files.
- **`mcp-agent.html`**: Fixed markdown header rendering in the chat canvas — `##` and `###` headers were being escaped as literals instead of rendering as `<h2>` / `<h3>` elements. Fixed the `marked.js` config to not sanitise heading tags.

---

### `dcbc704` — mcp-agent.html: remove cost pill, keep context gauge only
**Date:** 2026-04-06 | **Files:** `public/mcp-agent.html`

Removed the "cost" display pill from the chat header (54 lines removed). Cost calculations were unreliable across different LLM providers (Anthropic token pricing differs from xAI/HuggingFace). Kept the context window gauge (shows % of 200k context used) which is provider-agnostic and genuinely useful.

---

## 18. April 6 — Sub-Agent Deadlock Fix

### `ea668b8` — Fix sub-agent checkpointer event-loop deadlock + UI insertBefore DOM error
**Date:** 2026-04-06 | **Files:** `agent/agent.py`, `agent/sub_agent_executor.py`, `public/mcp-agent.html`

**Deadlock fix (`sub_agent_executor.py`):** Sub-agents were being initialised with `AsyncSqliteSaver` (the async LangGraph checkpointer) inside a `ThreadPoolExecutor` thread. The async checkpointer tried to get the running event loop — which doesn't exist in a bare thread — and deadlocked. Fixed by using `MemorySaver` (in-memory, no I/O) for sub-agents. Sub-agent state doesn't need to be persisted across sessions, so memory saver is correct and eliminates the async/thread boundary problem.

**`agent/agent.py`**: Added `sub_agent=True` parameter to `create_agent_for_worker()`. When True, uses `MemorySaver` and skips the async DB checkpoint initialisation.

**DOM error (`mcp-agent.html`)**: The sub-agent status cards were being inserted with `insertBefore(node, null)` — in some browsers this throws a `TypeError`. Changed to `appendChild()`.

---

### `62a930e` — Housekeeping: config updates, docs reorganisation, data files
**Date:** 2026-04-06 | **Files:** Many — config, requirements docs, data directory scaffolding

Organisational commit:
- Moved root-level planning files (`INSTRUCTIONS.md`, `NEXT_STEPS.md`, `PLAN.md`, `PROMPTS.md`) into `requirements/` directory to reduce root clutter.
- Deleted stale draft documents from `requirements/drafts/` (9 Word/Markdown files that had been superseded by the handover package).
- `sajhamcpserver/config/users.json`: Added 102 lines — additional test users for QA.
- `sajhamcpserver/config/workers.json`: Updated worker definitions — corrected `domain_data_path` values for 3 workers that were pointing at non-existent paths.
- `sajhamcpserver/config/llm_config.json`: Added `temperature`, `max_tokens`, and `stream` fields to all provider configs for explicit control.
- Created scaffold `.index.json` files for 3 new worker data directories (`w-1ddc8c61`, `w-76933a6b`, `w-da082632`).
- Added initial domain data files to common layer for testing (freshness test markers, policy test markers, FRTB sensitivity doc).

---

## Summary Statistics — Full 7-Day Period

| Category | Apr 6 Commits | Apr 10–13 Commits | Total Commits |
|---|---|---|---|
| DuckDB tool engine | — | 6 | 6 |
| MsDocs / Python executor | 2 | 2 | 4 |
| SQLSelect | 1 | 1 | 2 |
| Agent stability / sub-agent | 1 | 3 | 4 |
| Production deployment | — | 9 | 9 |
| Storage layer (DB + S3) | — | 5 | 5 |
| Frontend / UI | 6 | 7 | 13 |
| Requirements & dependencies | — | 4 | 4 |
| New workers & config | 1 | 2 | 3 |
| Documentation | 1 | 10 | 11 |
| Tool additions & bug fixes | 4 | 3 | 7 |
| DB audit & LLM config | 1 | 2 | 3 |
| Housekeeping & handover | 1 | — | 1 |
| **Total** | **18** | **54** | **72** |

---

*Generated: 2026-04-13. Covers commits `067e750` (Apr 6) through `0ee10b3` (Apr 12) on branch `main`.*
