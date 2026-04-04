# RiskGPT — Enterprise Migration Preparation Requirements
**Status:** Pending
**Date:** 2026-04-03
**Author:** Saad Ahmed
**Scope:** Local codebase changes to enable a low-friction migration to S3-backed storage. No Postgres in scope. No behaviour changes to existing functionality.

---

## 1. Objective

RiskGPT currently has file I/O and path resolution scattered across 10+ tool modules, each using its own pattern. When the platform moves to enterprise infrastructure (S3, cloud compute), every one of those modules would need to be touched individually.

This document defines the preparatory changes to make locally — before any infrastructure move — that collapse the enterprise migration to a config change and a single storage backend swap. All changes here are **refactors only**: existing behaviour is preserved, no new features are introduced.

---

## 2. Design Principles

**Principle 1 — Separate what from where.** Tools should express *what* data they need (category + worker context), not *where* it physically lives. Path resolution is infrastructure detail; tools shouldn't care.

**Principle 2 — One seam for storage.** All file reads and writes go through one module. Swapping that module swaps the storage backend for the entire platform.

**Principle 3 — Config drives the backend.** Whether the platform is running locally or on S3 is determined by an environment variable, not by code changes.

**Principle 4 — No behaviour change.** Every requirement in this document must produce identical runtime behaviour to the current system when running locally.

---

## 3. Target Architecture (Post-Prep)

```
agent_server.py
  └── path_resolver.py          ← resolves category + context → path/prefix
  └── worker_repository.py      ← finds worker config (JSON today, DB later)

sajhamcpserver/sajha/
  ├── storage.py                ← read/write/list/delete (pathlib today, boto3 later)
  ├── path_resolver.py          ← single canonical path resolver for tools
  ├── worker_repository.py      ← worker config access abstraction
  └── tools/impl/
      └── [all tools]           ← call storage.py + path_resolver.py only
```

On migration day:
- `storage.py` gets a boto3 implementation → all tools on S3
- `path_resolver.py` returns S3 prefixes → correct bucket layout
- Environment variable `STORAGE_BACKEND=s3` activates the new backend
- `aws s3 sync` copies local data to bucket → data migrated

---

## 4. Requirements

---

### REQ-PREP-01 — Storage Abstraction Layer

**File:** `sajhamcpserver/sajha/storage.py`
**Priority:** High — blocks REQ-PREP-03 and REQ-PREP-05

Create a single storage client module that all tools use for file I/O. The module exposes a backend-agnostic interface. The active backend is determined at startup from the `STORAGE_BACKEND` environment variable (`local` by default).

**Interface:**

```python
def read_bytes(path: str) -> bytes
    """Read file contents. path is an absolute local path or S3 key."""

def write_bytes(path: str, data: bytes) -> None
    """Write bytes to path. Creates intermediate directories (local) or
    puts object (S3)."""

def read_text(path: str, encoding: str = 'utf-8') -> str
    """Convenience wrapper: read_bytes decoded as text."""

def write_text(path: str, text: str, encoding: str = 'utf-8') -> None
    """Convenience wrapper: write text encoded as bytes."""

def list_prefix(prefix: str) -> list[str]
    """List all file keys/paths under prefix. Returns relative paths."""

def exists(path: str) -> bool
    """Check if a file exists at path."""

def delete(path: str) -> None
    """Delete a file. Does not raise if not found."""

def copy(src: str, dst: str) -> None
    """Copy a file within the same backend."""
```

**Local implementation:** All operations backed by `pathlib.Path`. `write_bytes` creates parent directories automatically.

**S3 implementation (stub only, not activated locally):** All operations backed by `boto3.client('s3')`. Configured from `AWS_BUCKET`, `AWS_REGION` environment variables. The stub class must exist in the file but is only instantiated when `STORAGE_BACKEND=s3`.

**Acceptance criteria:**
- `storage.py` exists and exports a module-level instance (`storage`) via `get_storage()` factory.
- Local backend passes a unit test for each interface method (read/write/list/exists/delete/copy).
- S3 stub class is present but gated behind the env var — it does not need to be functional locally.
- No tool file reads or writes occur outside this module after REQ-PREP-03 is complete.

---

### REQ-PREP-02 — Unified Path Resolver

**File:** `sajhamcpserver/sajha/path_resolver.py`
**Priority:** High — blocks REQ-PREP-03

Create a single canonical path resolver that all tools and `agent_server.py` import. This replaces the 5+ scattered `_domain_root()`, `_my_data_root()`, `_workflows_dir()` functions currently duplicated across:

- `operational_tools.py`
- `data_transform_tools.py`
- `visualisation_tools.py`
- `workflow_tools.py`
- `iris_ccr_tools.py`

**Interface:**

```python
def resolve(category: str, worker_ctx: dict, user_id: str = None) -> str
    """
    Returns the root path/prefix for the given category and worker context.

    Categories:
      'domain_data'    → worker-scoped analytical data root
      'my_data'        → user-scoped working files root (requires user_id)
      'common_data'    → platform-wide shared reference data root
      'workflows'      → worker-scoped verified workflows root
      'my_workflows'   → worker-scoped user-created workflows root
      'templates'      → worker-scoped templates root

    worker_ctx is the worker dict from workers.json (or WorkerRepository).
    Raises ValueError for unknown categories.
    """
```

**Resolution logic (local):**

| Category | Resolution order |
|---|---|
| `domain_data` | `worker_ctx['domain_data_path']` → `./data/domain_data` fallback |
| `my_data` | `worker_ctx['my_data_path']/{user_id}` → error if no user_id |
| `common_data` | `worker_ctx['common_data_path']` → `./data/common` fallback |
| `workflows` | `worker_ctx['workflows_path']` → `./data/workflows/verified` fallback |
| `my_workflows` | `worker_ctx['my_workflows_path']` → `./data/workflows/my` fallback |
| `templates` | `worker_ctx['templates_path']` → `./data/domain_data/templates` fallback |

**On S3:** Returns `s3://{bucket}/{prefix}` strings instead of filesystem paths. The resolver function itself does not change — it reads the same worker_ctx keys and applies the same logic. Only the base path format changes.

**Worker context source:** The resolver reads worker_ctx from the Flask `g` object (SAJHA tools) or from the FastAPI worker context (agent_server). This replaces the current per-tool `getattr(_g, 'worker_data_root', None)` pattern.

**Acceptance criteria:**
- All 5 scattered resolver functions are deleted and replaced with imports of `path_resolver.resolve()`.
- `resolve()` raises `ValueError` for unknown categories — no silent directory creation.
- `resolve('my_data', ctx)` without a `user_id` raises `ValueError`.
- `agent_server.py`'s `_resolve_worker_path()` and `_admin_section_roots_for_worker()` delegate to `path_resolver.resolve()` internally (these functions remain for API compatibility but are thin wrappers).
- REQ-API-02 from the path architecture requirements is satisfied as a byproduct — all tools now go through one context-aware resolver.

---

### REQ-PREP-03 — Migrate All Tools to Storage + Resolver

**Priority:** High — depends on REQ-PREP-01 and REQ-PREP-02

All tool modules that currently use `open()`, `os.walk()`, `os.listdir()`, `pathlib.Path`, or `shutil` directly must be migrated to use `storage.py` and `path_resolver.py` instead.

**Tools to migrate and their current operations:**

| Tool | Current file operations | Migration action |
|---|---|---|
| `workflow_tools.py` | `os.walk`, `open(file)` to read `.md` files | `storage.list_prefix`, `storage.read_text` |
| `osfi_tools.py` | `os.walk`, `open(file)` to read `.md` docs | `storage.list_prefix`, `storage.read_text` |
| `iris_ccr_tools.py` | `pd.read_csv(local_path)` | `storage.read_bytes` → `BytesIO` → `pd.read_csv` |
| `operational_tools.py` | `fitz.open(str(path))`, `open()` for PDF/template reads | `storage.read_bytes` → `BytesIO` → library open |
| `msdoc_tools_tool_refactored.py` | `python-docx`, `openpyxl` open from local path | `storage.read_bytes` → `BytesIO` → library open |
| `data_transform_tools.py` | `pd.read_csv/parquet(local_path)` | `storage.read_bytes` → `BytesIO` → pandas |
| `upload_tools.py` | `os.walk`, `os.stat` on uploads dir | `storage.list_prefix` with metadata |
| `visualisation_tools.py` | `open(path, 'w')` to write chart HTML | `storage.write_text` |
| `sqlselect_tool_refactored.py` | File path passed to DuckDB SQL | Path from `path_resolver.resolve()` |

**Migration pattern for read operations:**

```python
# Before
with open(local_path, 'rb') as f:
    data = f.read()

# After
data = storage.read_bytes(path_resolver.resolve('domain_data', worker_ctx) + '/file.csv')
```

**Migration pattern for library file opens** (fitz, python-docx, openpyxl):

```python
# Before
doc = fitz.open(str(local_path))

# After
import io
raw = storage.read_bytes(resolved_path)
doc = fitz.open(stream=io.BytesIO(raw), filetype='pdf')
```

All three libraries (PyMuPDF, python-docx, openpyxl) support `BytesIO` input natively.

**Acceptance criteria:**
- No tool file directly after migration contains `import pathlib`, `open(`, `os.walk(`, `os.listdir(`, or `shutil.` for data file access (utility imports for path manipulation are acceptable).
- All existing tool functionality continues to work identically against local filesystem.
- Each migrated tool has at least one manual smoke test confirming it reads and returns data correctly post-migration.

---

### REQ-PREP-04 — DuckDB In-Memory + Worker Context Routing

**File:** `sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py` (and `duckdb_olap_advanced.py`)
**Priority:** High — DuckDB is the hardest S3 migration otherwise

**Current problems:**
1. `duckdb.connect(db_path)` uses a persistent `.db` file on disk. This cannot live on S3 and cannot be shared across multiple server instances.
2. `data_directory` is hardcoded in the class constructor from a static config value — not worker-context-aware.
3. `_initialize_views_from_files()` uses `os.listdir()` to discover files and register views.
4. An auto-refresh background thread polls `os.listdir` on a timer.

**Required changes:**

**1 — Switch to in-memory DuckDB:**

```python
# Before
self.conn = duckdb.connect(self.db_path)

# After
self.conn = duckdb.connect()  # in-memory, no file
```

Views are recreated from source files on first query or on explicit refresh. The persistent `.db` file and `db_path` config are removed.

**2 — Route data_directory through worker context:**

`data_directory` must come from `path_resolver.resolve('domain_data', worker_ctx)` at query time, not from a static config at init time. The class must not store a single `data_directory` — it must resolve it per-request from the active worker context.

**3 — Replace os.listdir with storage.list_prefix:**

`_scan_data_files()` and `_initialize_views_from_files()` must use `storage.list_prefix(data_dir)` instead of `os.listdir`.

**4 — Remove auto-refresh background thread:**

The background polling thread (`_start_auto_refresh`, `_auto_refresh_worker`) must be removed. View refresh happens on demand (explicit `duckdb_refresh_views` tool call) or lazily on first query. This makes the DuckDB tool stateless — safe to run across multiple server instances.

**5 — Install httpfs extension at connection time (stub, not activated):**

Add a commented-out block at connection setup time:

```python
# S3 migration: uncomment and configure when STORAGE_BACKEND=s3
# conn.execute("INSTALL httpfs; LOAD httpfs;")
# conn.execute(f"SET s3_region='{os.environ.get('AWS_REGION')}'")
# conn.execute(f"SET s3_access_key_id='{os.environ.get('AWS_ACCESS_KEY_ID')}'")
```

This is present but inert locally, ready to activate on S3 day.

**Acceptance criteria:**
- No persistent `.db` file is created at startup.
- DuckDB connection is in-memory; multiple server instances do not conflict.
- `data_directory` resolves from worker context per-request.
- View listing uses `storage.list_prefix`.
- Background refresh thread is absent.
- All existing DuckDB query tools (list_tables, query, sql, describe, stats) return correct results against local filesystem data.
- `duckdb_refresh_views` tool explicitly recreates views on demand.

---

### REQ-PREP-05 — BytesIO Write Pattern for All Output Tools

**Priority:** Medium — depends on REQ-PREP-01

All tools that generate and write output files must write to an in-memory `BytesIO` buffer first, then flush via `storage.write_bytes()`. This is a zero-behaviour-change refactor locally — the file ends up in the same place — but on S3 the flush becomes `s3.put_object(Body=buffer.getvalue())` with no further changes needed.

**Tools affected:**

| Tool / class | Output type | Current write | Target write |
|---|---|---|---|
| `MdSaveTool` (operational_tools.py) | Markdown file | `open(path, 'w')` | `storage.write_text(path, content)` |
| `FillTemplateTool` (operational_tools.py) | Filled template | `open(path, 'wb')` | `storage.write_bytes(path, buf.getvalue())` |
| `DocxGeneratorTool` (operational_tools.py) | `.docx` file | `doc.save(str(path))` | `doc.save(buf); storage.write_bytes(path, buf.getvalue())` |
| `DataExportTool` (data_transform_tools.py) | CSV / Parquet | `df.to_csv(path)` / `df.to_parquet(path)` | Write to `BytesIO`, then `storage.write_bytes` |
| `GenerateChartTool` (visualisation_tools.py) | HTML chart | `open(path, 'w')` | `storage.write_text(path, html)` |

**Pattern for binary output libraries (python-docx, openpyxl):**

```python
import io
buf = io.BytesIO()
doc.save(buf)
buf.seek(0)
storage.write_bytes(resolved_path, buf.read())
```

**Acceptance criteria:**
- No output tool writes directly to disk via `open()` after this change.
- All generated files are present in the same locations as before (behaviour unchanged locally).
- Output paths are resolved via `path_resolver.resolve()` not hardcoded strings.

---

### REQ-PREP-06 — WorkerRepository

**File:** `sajhamcpserver/sajha/worker_repository.py` and corresponding `agent_server.py` update
**Priority:** Medium

Wrap all access to `workers.json` behind a repository class. All code that currently reads `workers.json` directly or calls `_find_worker()` in `agent_server.py` must go through this class.

**Interface:**

```python
class WorkerRepository:
    def find(self, worker_id: str) -> dict | None
        """Return worker config dict or None if not found."""

    def list(self) -> list[dict]
        """Return all worker configs."""

    def find_by_user(self, user_id: str) -> dict | None
        """Return the worker a user is assigned to, or None."""
```

**Local implementation:** Reads from `workers.json` file path configured in `application.properties` or an environment variable. File is read and cached at startup; a `reload()` method forces a re-read for hot-reload support.

**Postgres implementation (stub only):** A `PostgresWorkerRepository` class must be present in the file but is not instantiated locally. It has the same interface with method bodies that raise `NotImplementedError`. This makes the Postgres migration a drop-in swap when the time comes.

**agent_server.py:** The existing `_find_worker()` function must be replaced with `WorkerRepository().find(worker_id)`. The `_load_workers()` / hot-reload logic moves into the repository's `reload()` method.

**Acceptance criteria:**
- `WorkerRepository` is the only place in the codebase that reads `workers.json`.
- `agent_server.py` contains no direct `json.load` calls against the workers file.
- `PostgresWorkerRepository` stub is present and raises `NotImplementedError` on all methods.
- `find()`, `list()`, and `find_by_user()` return correct results from the local JSON file.

---

### REQ-PREP-07 — File Serve Abstraction in agent_server.py

**Priority:** Medium

`agent_server.py` currently serves files to the admin panel and user-facing file download endpoints using FastAPI's `FileResponse(local_path)`. On S3 this needs to become either a pre-signed URL redirect or a streaming proxy.

Add a `serve_file(path: str) -> Response` helper function in `agent_server.py`:

```python
def serve_file(path: str) -> Response:
    if STORAGE_BACKEND == 'local':
        return FileResponse(path)
    else:
        # S3: return pre-signed URL redirect (not implemented locally)
        raise NotImplementedError("S3 file serving not configured")
```

All file download endpoints must call `serve_file(resolved_path)` instead of `FileResponse(path)` directly.

Locally this is identical to the current behaviour. On S3 the `else` branch is implemented with `s3.generate_presigned_url()` — one function, one change point.

**Acceptance criteria:**
- All file-serving endpoints in `agent_server.py` use `serve_file()`.
- `FileResponse` is not used directly anywhere outside this helper.
- Local file serving behaviour is unchanged.

---

## 5. What Does NOT Change

The following are explicitly out of scope — they must not be touched during this preparation work:

- Tool schemas and JSON config files in `config/tools/`
- LangGraph agent logic and prompts
- MCP protocol between agent_server and SAJHA
- Worker context header names (`X-Worker-Data-Root`, `X-Worker-My-Data-Root`, etc.)
- JWT auth flow and role gating
- Frontend HTML (admin.html, mcp-agent.html)
- SAJHA Flask routing layer
- Any data on disk (no files moved as part of this work)
- EDGAR, Tavily, Yahoo Finance, SharePoint tools (no filesystem access — zero changes needed)

---

## 6. Summary Table

| REQ ID | Description | Priority | Effort | Migration payoff |
|---|---|---|---|---|
| REQ-PREP-01 | Storage abstraction layer (`storage.py`) | High | Small | All tool file I/O on S3 for free |
| REQ-PREP-02 | Unified path resolver (`path_resolver.py`) | High | Small | All paths on S3 for free; fixes REQ-API-02 |
| REQ-PREP-03 | Migrate all tools to storage + resolver | High | Medium | No tool changes on S3 day |
| REQ-PREP-04 | DuckDB in-memory + worker context | High | Medium | DuckDB on S3 in one connection config |
| REQ-PREP-05 | BytesIO write pattern for output tools | Medium | Small | All writes to S3 for free |
| REQ-PREP-06 | WorkerRepository class | Medium | Small | Postgres worker migration is a drop-in swap |
| REQ-PREP-07 | File serve abstraction in agent_server | Medium | Small | Pre-signed URL in one function |

---

## 7. Implementation Sequence

1. **REQ-PREP-01 + REQ-PREP-02** in parallel — create both modules first, no tool changes yet; write unit tests
2. **REQ-PREP-06** — wrap WorkerRepository; update agent_server; isolated change
3. **REQ-PREP-03** — migrate tools one at a time, smoke-test each before moving to the next; start with `workflow_tools.py` (simplest) then `operational_tools.py` (most complex)
4. **REQ-PREP-04** — DuckDB in-memory; isolated to duckdb tool files; test all DuckDB queries
5. **REQ-PREP-05** — BytesIO writes; quick pass across output tools
6. **REQ-PREP-07** — file serve helper; one-line change per endpoint

---

## 8. What Migration Day Looks Like After This Work

| Task | Action |
|---|---|
| Provision S3 bucket | Infrastructure — no code |
| Provision compute (EC2/ECS) | Infrastructure — no code |
| IAM role + bucket policy | Infrastructure — no code |
| Set environment variables | `STORAGE_BACKEND=s3`, `AWS_BUCKET`, `AWS_REGION` |
| Activate S3 storage backend | Implement `S3StorageBackend` in `storage.py` (~50 lines of boto3) |
| Activate S3 path prefixes | `path_resolver.py` returns `s3://` strings when `STORAGE_BACKEND=s3` |
| DuckDB S3 | Uncomment 3 lines in connection setup; activate httpfs |
| Activate file serve pre-signed URLs | Implement `else` branch in `serve_file()` (~5 lines) |
| Data migration | `aws s3 sync ./data/workers/ s3://bucket/workers/` |
| | `aws s3 sync ./data/common/ s3://bucket/common/` |
| Secrets | Move JWT secret and API keys to Secrets Manager; read from env |

No tool files change on migration day. The entire application code delta is approximately 60 lines across 3 files.

---

*This document covers local refactoring requirements only. No infrastructure changes, no Postgres, no behaviour changes. S3 backend code exists as stubs but is not activated until migration day.*
