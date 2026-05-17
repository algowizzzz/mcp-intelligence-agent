# REQ-15 — Supabase Persistent Storage

**Status:** Stubbed — foundation present, wiring incomplete (verified 2026-05-17)
**Version:** 1.0 (2026-04-12)
**Author:** Saad Ahmed
**Priority:** P0 — Blocker for production use on Railway
**Scope:** Wire Supabase Storage (S3-compatible) and Supabase Postgres across all file I/O and checkpoint paths so that uploaded files and conversation history survive Railway redeploys.

> **Verification (2026-05-17):**
> - Storage abstraction layer exists (`sajhamcpserver/sajha/storage.py`) with both `LocalStorageBackend` and `S3StorageBackend`. Switch via `STORAGE_BACKEND` env var.
> - **However**, `agent_server.py` file routes (`/api/fs/{section}/upload`, `tree`, `move`, etc.) still call `pathlib.Path` directly rather than going through the storage abstraction. So even when `STORAGE_BACKEND=s3` is set, agent-level file ops won't use it.
> - Checkpointer: the agent uses `AsyncSqliteSaver` by default (`agent/agent.py:15`); `AsyncPostgresSaver` is wired but only when `DATABASE_URL` is set (REQ-07 complete).
> - Net: REQ-07 (Postgres) is done. REQ-08a (S3 backend code) is done. **What's still needed for REQ-15 specifically** is rewiring `agent_server.py` file routes to call `storage.read_bytes/write_bytes/list_prefix` instead of `pathlib`, and choosing Supabase vs RDS for the Postgres target.

---

## 1. Problem Statement

Railway deploys run in ephemeral Docker containers. Every push to `main` triggers a fresh container build from the git image — any files uploaded to the container's local disk are permanently lost on the next deploy.

### 1.1 What Gets Lost Today on Every Deploy

| Data | Where Stored Now | Lost on Redeploy? |
|------|-----------------|-------------------|
| Domain data uploads (xlsx, pdf, docx, csv…) | `/app/sajhamcpserver/data/workers/{id}/domain_data/` | ✅ Yes |
| User my_data uploads | `/app/sajhamcpserver/data/workers/{id}/my_data/{user}/` | ✅ Yes |
| Shared Library (common) files | `/app/sajhamcpserver/data/common/` | ✅ Yes |
| Workflow files | `/app/sajhamcpserver/data/workers/{id}/workflows/` | ✅ Yes |
| BM25 index files (`.index.json`) | Same directories as above | ✅ Yes |
| Generated charts (from python_execute / generate_chart) | `/app/sajhamcpserver/data/workers/{id}/my_data/{user}/charts/` | ✅ Yes |
| LangGraph conversation checkpoints | `/app/sajhamcpserver/data/checkpoints.db` (SQLite) | ✅ Yes |
| Audit log | `/app/sajhamcpserver/data/audit/tool_calls.jsonl` | ✅ Yes |

### 1.2 Root Cause

Two separate bypass problems:

**Problem A — agent_server.py bypasses storage abstraction**
`agent_server.py` uses raw `pathlib.Path` for all file operations (upload, list, move, rename, copy, delete, download, file tree). The `storage` abstraction in `sajhamcpserver/sajha/storage.py` (already fully implemented for both local and S3) is never called from agent_server.py.

**Problem B — Checkpoints use SQLite**
LangGraph checkpoints use `AsyncSqliteSaver` pointed at `./sajhamcpserver/data/checkpoints.db`. SQLite is a local file — it cannot live on S3.

---

## 2. Solution Architecture

### 2.1 Storage Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     Railway Container                           │
│                                                                 │
│  agent_server.py ──► storage abstraction ──► Supabase Storage  │
│  SAJHA tools     ──► storage abstraction ──►  (S3-compatible)  │
│                                                                 │
│  LangGraph ──► AsyncPostgresSaver ──► Supabase Postgres         │
│  Audit log ──► Supabase Postgres  ──► (already wired via DB_URL)│
└─────────────────────────────────────────────────────────────────┘
```

**For local development:** `STORAGE_BACKEND=local` (default) — no change, everything works exactly as today.

**For Railway production:** Set 6 env vars → all file I/O and checkpoints go to Supabase.

### 2.2 Supabase Services Used

| Supabase Service | Used For | Protocol |
|-----------------|----------|----------|
| **Storage** | All binary files (uploads, charts, workflows, common data) | S3-compatible via boto3 |
| **Postgres** | LangGraph checkpoints, audit log | `psycopg` / `asyncpg` |

### 2.3 Environment Variables (Railway)

| Variable | Value | Purpose |
|----------|-------|---------|
| `STORAGE_BACKEND` | `s3` | Activates S3StorageBackend in storage.py |
| `S3_ENDPOINT_URL` | `https://<project-ref>.supabase.co/storage/v1/s3` | Supabase S3 endpoint |
| `S3_BUCKET` | `bpulse-data` | Supabase Storage bucket name |
| `AWS_ACCESS_KEY_ID` | `<supabase-project-ref>` | Supabase S3 access key |
| `AWS_SECRET_ACCESS_KEY` | `<supabase-service-role-key>` | Supabase S3 secret |
| `AWS_REGION` | `us-east-1` | Required by boto3 (any value works for Supabase) |
| `DATABASE_URL` | `postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres` | Supabase Postgres |

---

## 3. Scope of Changes

### Phase 1 — Wire agent_server.py to Storage Abstraction

`agent_server.py` currently uses raw `pathlib` for all file I/O. Every place that reads or writes a file must be routed through the `storage` singleton from `sajhamcpserver/sajha/storage.py`.

#### 3.1 Upload Endpoints

Five upload endpoints all call `_stream_upload(file, dest)` which writes to a `pathlib.Path`. Replace with `storage.write_stream(path_str, file, chunk_size)`.

| Endpoint | Function | File |
|----------|----------|------|
| `POST /api/fs/{section}/upload` | user upload | `agent_server.py` |
| `POST /api/admin/worker/files/{section}/upload` | admin upload | `agent_server.py` |
| `POST /api/super/workers/{id}/files/{section}/upload` | super admin upload | `agent_server.py` |
| `POST /api/admin/common/upload` | shared library upload | `agent_server.py` |
| `POST /api/files/upload` | legacy chat upload | `agent_server.py` |

Current `_stream_upload`:
```python
async def _stream_upload(file: UploadFile, dest: pathlib.Path) -> int:
    bytes_written = 0
    async with aiofiles.open(dest, 'wb') as f:
        while True:
            chunk = await file.read(_UPLOAD_CHUNK_SIZE)
            ...
```

New `_stream_upload`:
```python
async def _stream_upload(file: UploadFile, dest: str) -> int:
    from sajhamcpserver.sajha.storage import storage
    return await storage.write_stream(dest, file, _UPLOAD_CHUNK_SIZE)
```

`dest` changes from `pathlib.Path` to `str` (S3 key). All 5 callers pass the `str(path)` instead of a `Path` object.

#### 3.2 File Download / Serve

`GET /api/fs/{section}/file` and chart serving use `FileResponse(path)` which reads local disk. On S3 this must either:

- **Option A (preferred):** Read bytes from storage and stream them: `storage.read_bytes(key)` → `Response(content=..., media_type=...)`
- **Option B:** Generate a Supabase pre-signed URL and redirect. Only works if files are not private.

Use **Option A** — keeps files private (bucket is private), consistent behaviour local vs S3.

#### 3.3 File Operations (move, rename, copy, delete)

| Endpoint | Current | New |
|----------|---------|-----|
| `POST /api/fs/{section}/move` | `shutil.move(src, dst)` | `storage.copy(src, dst)` then `storage.delete(src)` |
| `POST /api/fs/{section}/rename` | `Path.rename(new)` | `storage.copy(old_key, new_key)` then `storage.delete(old_key)` |
| `POST /api/fs/{section}/copy` | `shutil.copy2(src, dst)` | `storage.copy(src, dst)` |
| `DELETE /api/fs/{section}/file` | `Path.unlink()` | `storage.delete(key)` |
| `DELETE /api/fs/{section}/folder` | `shutil.rmtree(dir)` | List prefix → delete each key |
| `POST /api/fs/{section}/batch-delete` | loop `Path.unlink()` | loop `storage.delete(key)` |

#### 3.4 File Read (PATCH /api/fs/{section}/file for content reads)

```python
# Current
content = pathlib.Path(full_path).read_text()

# New
content = storage.read_text(key)
```

#### 3.5 File Tree Listing

The file tree is built by `build_index()` which walks the local filesystem with `pathlib.rglob('*')`. On S3 this must use `storage.list_prefix(prefix)`.

```python
# Current (simplified)
def build_index(root: str) -> dict:
    for p in pathlib.Path(root).rglob('*'):
        if p.is_file():
            tree.append(...)

# New
def build_index(root: str) -> dict:
    for rel_path in storage.list_prefix(root):
        tree.append(...)
```

`storage.list_prefix()` already returns relative paths — the tree structure is built from the `/`-separated key segments.

#### 3.6 BM25 Index Persistence

`.index.json` files are written to the same directory as the data files. On S3, these become objects with key `{prefix}/.index.json`.

```python
# Current
index_path = pathlib.Path(root) / '.index.json'
index_path.write_text(json.dumps(index))

# New
storage.write_text(f'{root}/.index.json', json.dumps(index))
```

Reading the index:
```python
# New
raw = storage.read_text(f'{root}/.index.json')
index = json.loads(raw)
```

`storage.exists()` is used to check if the index file is present before reading.

---

### Phase 2 — LangGraph Checkpoints → Supabase Postgres

#### 3.7 Replace AsyncSqliteSaver with AsyncPostgresSaver

Current (`agent_server.py`):
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
_db_path = os.getenv('CHECKPOINT_DB_PATH', './sajhamcpserver/data/checkpoints.db')
memory = AsyncSqliteSaver.from_conn_string(_db_path)
```

New:
```python
import os
_db_url = os.getenv('DATABASE_URL')
if _db_url:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    memory = AsyncPostgresSaver.from_conn_string(_db_url)
    await memory.setup()   # creates tables if not exists (idempotent)
else:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    _db_path = os.getenv('CHECKPOINT_DB_PATH', './sajhamcpserver/data/checkpoints.db')
    memory = AsyncSqliteSaver.from_conn_string(_db_path)
```

This preserves local dev behaviour (SQLite) while using Postgres in production.

**Required package:** `langgraph-checkpoint-postgres` (add to `requirements.txt`).

---

### Phase 3 — Supabase Bucket Setup

#### 3.8 Bucket Structure

One private bucket `bpulse-data` with the following key namespace:

```
bpulse-data/
├── data/workers/{worker_id}/domain_data/          ← domain data uploads
│   ├── .index.json                                ← BM25 index
│   └── <uploaded files>
├── data/workers/{worker_id}/my_data/{user_id}/    ← user uploads
│   ├── charts/                                    ← generated charts
│   └── <uploaded files>
├── data/workers/{worker_id}/workflows/verified/   ← verified workflows
├── data/workers/{worker_id}/workflows/my/         ← user workflows
├── data/workers/{worker_id}/templates/            ← templates
└── data/common/                                   ← shared library
    └── .index.json
```

Keys mirror the existing local path structure exactly — no path changes required in workers.json or anywhere else.

#### 3.9 Supabase Bucket CORS Policy

The bucket must allow direct downloads when served via `FileResponse`. Since we use **Option A** (proxy through agent server), no CORS policy changes are needed — the browser never talks to Supabase Storage directly.

---

### Phase 4 — Audit Log

The audit log currently writes to `sajhamcpserver/data/audit/tool_calls.jsonl` (local file). The `DATABASE_URL` path for Postgres audit logging is already implemented in `agent/tools.py` (`_DB_ENABLED` flag). When `DATABASE_URL` is set, audit entries go to Postgres automatically — **no changes needed here**.

---

## 4. Files Changed

| File | Change |
|------|--------|
| `agent_server.py` | Replace all `pathlib`/`aiofiles`/`shutil` file I/O with `storage.*` calls. Replace `AsyncSqliteSaver` with `AsyncPostgresSaver` when `DATABASE_URL` is set. |
| `sajhamcpserver/sajha/storage.py` | Already complete — S3StorageBackend is fully implemented. Verify `write_stream` handles Supabase's 5MB multipart minimum correctly for files <5MB (use single-part upload as fallback). |
| `requirements.txt` | Add `langgraph-checkpoint-postgres`, `psycopg[binary]`, `psycopg[pool]` |
| `Dockerfile` | No change needed — env vars control backend selection at runtime. |
| `railway.toml` | No change needed — env vars set in Railway dashboard. |

---

## 5. What Does NOT Change

- Local development workflow — `STORAGE_BACKEND=local` (default) keeps everything on local disk as today. Zero config change for dev.
- SAJHA tool implementations — they already call `storage.read_bytes()`, `storage.exists()`, etc. They get Supabase for free once `STORAGE_BACKEND=s3` is set.
- workers.json paths — key structure mirrors the existing path structure. No config changes.
- nginx.conf — file serving goes through agent_server.py (Option A), not direct S3 URLs.
- Auth / JWT — unchanged.
- LLM / agent logic — unchanged.

---

## 6. Storage Backend Behaviour Comparison

| Operation | Local Backend | S3/Supabase Backend |
|-----------|--------------|---------------------|
| `write_stream` | `aiofiles.open` + chunked write | S3 multipart upload (5MB parts); single PUT for <5MB |
| `read_bytes` | `Path.read_bytes()` | `s3.get_object()` |
| `exists` | `Path.exists()` | `s3.head_object()` (returns bool) |
| `list_prefix` | `Path.rglob('*')` | `s3.list_objects_v2` paginator |
| `delete` | `Path.unlink()` | `s3.delete_object()` |
| `copy` | `shutil.copy2` | `s3.copy_object` (server-side, no data transfer) |
| File tree | pathlib walk → JSON | list_prefix → build tree from key segments |
| BM25 index | `.index.json` on disk | `.index.json` as S3 object |
| Checkpoints | SQLite file | Postgres table (AsyncPostgresSaver) |

---

## 7. Edge Cases and Constraints

| Case | Handling |
|------|---------|
| File <5MB uploaded to S3 | `write_stream` uses a single `put_object` call instead of multipart (S3 rejects multipart parts <5MB except the last). Add size check in `S3StorageBackend.write_stream`. |
| Folder delete on S3 | S3 has no folders. Delete all keys matching prefix `{folder_key}/`. Use `list_prefix` + loop `delete`. |
| Move/rename on S3 | S3 has no rename. Copy to new key + delete old key. If file is large this adds latency — acceptable for UI operations. |
| BM25 reindex latency | On S3, `list_prefix` involves an API call per reindex. Fine for current scale (<10,000 files per worker). |
| Concurrent uploads | S3 multipart uploads are independent — concurrent XHR uploads from REQ-11 work without modification. |
| Charts served to iframe | Charts are stored in `my_data/{user}/charts/`. Download via `storage.read_bytes()` proxied through `/api/fs/charts/{filename}` — no change to chart SSE events. |
| SQLite WAL files (`.db-shm`, `.db-wal`) | Only exist in local mode. Ignored in S3 mode since checkpoints go to Postgres. |
| First deploy with no data | Empty bucket is fine — `storage.exists()` returns False, file trees return empty, BM25 index is rebuilt on first upload. |

---

## 8. Testing Plan

### 8.1 Unit Tests — Storage Backend

**File:** `tests/test_storage_backends.py`

| Test ID | Test | Pass Condition |
|---------|------|----------------|
| `SB-01` | `LocalStorageBackend.write_bytes` + `read_bytes` round-trip | Bytes match |
| `SB-02` | `LocalStorageBackend.exists` returns False for missing path | Returns `False` |
| `SB-03` | `LocalStorageBackend.list_prefix` returns sorted relative paths | Correct list |
| `SB-04` | `LocalStorageBackend.copy` duplicates file | Both paths exist, bytes match |
| `SB-05` | `LocalStorageBackend.delete` removes file | `exists()` returns False after |
| `SB-06` | `S3StorageBackend.write_bytes` + `read_bytes` round-trip (Supabase) | Bytes match |
| `SB-07` | `S3StorageBackend.exists` returns False for missing key | Returns `False` |
| `SB-08` | `S3StorageBackend.list_prefix` returns objects under prefix | Correct list |
| `SB-09` | `S3StorageBackend.copy` (server-side copy) | Source and dest exist |
| `SB-10` | `S3StorageBackend.delete` removes object | `exists()` returns False after |
| `SB-11` | `S3StorageBackend.write_stream` with file <5MB uses single PUT | No multipart error |
| `SB-12` | `S3StorageBackend.write_stream` with file >5MB uses multipart | Upload completes |

### 8.2 Integration Tests — Upload API (S3 backend active)

**Environment:** `STORAGE_BACKEND=s3` pointing at Supabase test bucket

| Test ID | Test | Pass Condition |
|---------|------|----------------|
| `UP-01` | Upload `.xlsx` to domain_data via `POST /api/fs/domain_data/upload` | HTTP 200, file retrievable via `storage.read_bytes` |
| `UP-02` | Upload `.pdf` to my_data via same endpoint | HTTP 200, key includes user_id in path |
| `UP-03` | Upload file >20MB returns HTTP 413 | HTTP 413, no object created in S3 |
| `UP-04` | Upload `.exe` (disallowed extension) returns HTTP 400 | HTTP 400 |
| `UP-05` | Upload to shared library via `POST /api/admin/common/upload` | HTTP 200, key under `data/common/` |
| `UP-06` | Upload 5 files concurrently (REQ-11 parallel) | All 5 succeed, all 5 retrievable |
| `UP-07` | Upload file with spaces and special chars in filename (`Suppq125 (2).xlsx`) | HTTP 200, retrievable by exact filename |

### 8.3 Integration Tests — File Operations API (S3 backend active)

| Test ID | Test | Pass Condition |
|---------|------|----------------|
| `FO-01` | Move file between subfolders via `POST /api/fs/domain_data/move` | File at new key, old key gone |
| `FO-02` | Rename file via `POST /api/fs/domain_data/rename` | File at new key, old key gone |
| `FO-03` | Copy file via `POST /api/fs/domain_data/copy` | Both keys exist |
| `FO-04` | Delete file via `DELETE /api/fs/domain_data/file` | Key gone from S3 |
| `FO-05` | Delete folder (with files inside) via `DELETE /api/fs/domain_data/folder` | All keys under prefix gone |
| `FO-06` | Batch delete 3 files via `POST /api/fs/domain_data/batch-delete` | All 3 keys gone |
| `FO-07` | Read file content via `GET /api/fs/domain_data/file` | Returns correct bytes |

### 8.4 Integration Tests — File Tree and BM25 (S3 backend active)

| Test ID | Test | Pass Condition |
|---------|------|----------------|
| `FT-01` | Upload 3 files → `GET /api/fs/domain_data/tree` | Tree contains all 3 files |
| `FT-02` | Upload to subfolder → tree reflects subfolder structure | Correct nested tree |
| `FT-03` | Delete file → tree no longer contains it | Deleted file absent from tree |
| `FT-04` | Trigger `POST /api/fs/domain_data/reindex` → BM25 search finds uploaded content | `document_search` returns relevant result |
| `FT-05` | `.index.json` written to S3 after reindex | Key `{prefix}/.index.json` exists in bucket |
| `FT-06` | After Railway redeploy simulation (clear local disk) → tree and BM25 still work | Files and index survive via S3 |

### 8.5 Integration Tests — LangGraph Checkpoints (Postgres)

| Test ID | Test | Pass Condition |
|---------|------|----------------|
| `CP-01` | Start conversation → send message → `checkpoints` table has row in Supabase | Row exists |
| `CP-02` | Simulate redeploy (restart server) → resume same thread_id → agent has full history | Prior messages present in resumed context |
| `CP-03` | Two users start separate conversations → checkpoints isolated by thread_id | No cross-contamination |
| `CP-04` | `DATABASE_URL` unset → falls back to SQLite without error | Server starts, SQLite used |

### 8.6 End-to-End Tests — Full Flow on Railway

| Test ID | Test | Pass Condition |
|---------|------|----------------|
| `E2E-01` | Upload `Suppq125 (2).xlsx` to finance agent domain_data → push code → redeploy → call `msdoc_extract_text` | Returns file content (not 500) |
| `E2E-02` | Upload file → generate chart via `python_execute` → chart visible in canvas panel after redeploy | Chart URL still serves image |
| `E2E-03` | Start multi-turn conversation → push code → continue conversation with same thread_id | Agent recalls prior context |
| `E2E-04` | Admin uploads workflow → push code → workflow appears in `workflow_list` | Workflow persists |
| `E2E-05` | Upload to shared library → switch to different worker → `document_search` finds shared document | Cross-worker shared data works |

### 8.7 Regression Tests — Local Dev (storage=local)

Run existing test suite with `STORAGE_BACKEND` unset (local mode):

| Test ID | Test | Pass Condition |
|---------|------|----------------|
| `REG-01` | All existing upload tests pass with local backend | No regressions |
| `REG-02` | File tree loads correctly locally | Tree populated |
| `REG-03` | BM25 search finds locally uploaded content | Search returns results |
| `REG-04` | LangGraph uses SQLite when `DATABASE_URL` unset | Checkpoints in local `.db` file |
| `REG-05` | `msdoc_read_excel` and `python_execute` work locally | No tool errors |

---

## 9. Rollout Plan

### Step 1 — Implement (no Railway changes yet)
- Code changes to `agent_server.py` and `requirements.txt`
- Run local regression tests (`STORAGE_BACKEND=local`) — must all pass

### Step 2 — Test against Supabase from local
- Set env vars in `.env` pointing at Supabase project
- `STORAGE_BACKEND=s3`
- Run SB-*, UP-*, FO-*, FT-*, CP-* test suites
- Fix any issues

### Step 3 — Deploy to Railway staging
- Add all 7 env vars to Railway environment
- Push to Railway
- Run E2E-01 through E2E-05 manually

### Step 4 — Production cut-over
- All E2E tests passing → merge to main

---

## 10. Out of Scope

- **REQ-08b (Apache Iceberg)** — analytical tables remain a separate requirement
- **CDN / pre-signed URLs** — files are served proxied through agent_server.py; no CDN in this requirement
- **Supabase Row Level Security (RLS)** — bucket is private, access controlled at application layer (JWT auth in agent_server.py); RLS adds complexity with no benefit given the current auth model
- **File versioning** — S3 versioning not enabled; overwrite is the current behaviour and is preserved
- **Storage quota enforcement on S3** — quota check (`GET /api/fs/quota`) currently uses `du` (disk usage). On S3 this needs `list_objects` size sum. Deferred to a follow-up.
