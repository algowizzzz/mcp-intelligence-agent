# REQ-16 — Hetzner Object Storage Migration (S3-Compatible)

**Status:** Partial — foundation complete, ~11 tools still bypass it (verified 2026-05-17)
**Version:** 2.0 (2026-04-14)
**Author:** Saad Ahmed
**Prerequisite:** REQ-07 (PostgreSQL — code complete), REQ-08a (S3 storage layer — code complete)

> **Verification (2026-05-17):**
> - Foundation done: `storage.py` `S3StorageBackend` + `path_resolver.py` + `STORAGE_BACKEND=s3` switch all functional.
> - **Remaining work:** ~11 tool implementation files in `sajhamcpserver/sajha/tools/impl/` still call `pathlib.Path`, `open()`, `os.walk`, or `shutil` directly. Confirmed via repo-wide grep. Examples: `msdoc_tools_tool_refactored.py`, `duckdb_olap_advanced.py`, `workflow_tools.py`, `iris_ccr_tools.py`.
> - Earlier doc (`Infra_Agnostic_Strategy.md`) said "15 files" — actual count is closer to 11. Either count motivates the same migration plan.
> - Net: change is mechanical (per-tool refactor to call `storage.*`). No blockers besides reviewer time.

---

## 1. Objective

Migrate all file storage from Docker local volumes to Hetzner Object Storage (S3-compatible).
The storage abstraction layer (`storage.py`), S3 backend, and PostgreSQL layer are already
built and wired into the server. This REQ is about fixing the 9 tool files that bypass that
abstraction, then activating it with env vars and migrating the data.

**What this is NOT:**
- Not building new infrastructure code — `storage.py`, `path_resolver.py`, DB layer are complete
- Not an AWS migration — that's a future env-var-only swap, no code changes needed after this
- Not changing the compute layer — Docker on Hetzner VPS stays as-is

---

## 2. Why This Is Needed

| Problem Today | Impact |
|---|---|
| All files in Docker volume `/app/sajhamcpserver/data` | Volume rebuild = data loss; can't scale horizontally |
| 9 tool files bypass storage abstraction | Direct `os.walk`, `open()`, `shutil` silently break without a mounted volume |
| DuckDB passes local filesystem paths | `read_csv_auto('/path/to/file.csv')` fails on object storage |
| BM25 index written to local disk | Lost on container restart, rebuilt from scratch every time |
| No disaster recovery for user files | Hetzner volume failure = unrecoverable |

---

## 3. Architecture After This REQ

```
User Upload (browser)
        │
        ▼
Agent Server (FastAPI :8000)
        │
        ├──► Hetzner Object Storage (S3-compatible)
        │         Bucket: sajha-prod
        │         sajhamcpserver/data/workers/{worker_id}/domain_data/
        │         sajhamcpserver/data/workers/{worker_id}/my_data/{user_id}/
        │         sajhamcpserver/data/workers/{worker_id}/workflows/
        │         sajhamcpserver/data/workers/{worker_id}/templates/
        │         sajhamcpserver/data/common/
        │
        └──► PostgreSQL (Hetzner VPS)
                  users, workers, audit, checkpoints, file_metadata
```

On AWS migration later: remove `S3_ENDPOINT_URL`, update credentials to IAM role. Zero code changes.

---

## 4. What Is Already Built (Do Not Touch)

| Component | File | Status |
|---|---|---|
| S3 + Local storage backends | `sajhamcpserver/sajha/storage.py` | Complete |
| Path resolver (local ↔ S3 routing) | `sajhamcpserver/sajha/path_resolver.py` | Complete |
| `serve_file()` presigned URL redirect | `agent_server.py` | Complete |
| `STORAGE_BACKEND` env var check | `agent_server.py` line 35 | Complete |
| PostgreSQL models + Alembic migrations | `sajhamcpserver/sajha/db/` | Complete |
| Dual-write pattern (DB + JSON fallback) | `agent_server.py` lines 103–172 | Complete |
| Migration script (JSON → Postgres) | `scripts/migrate_json_to_pg.py` | Complete — already run in production |
| `fs_index.py` S3 path | `sajhamcpserver/sajha/tools/impl/fs_index.py` | S3 path done; local path still uses `os.walk` |

---

## 5. Phase Plan

### Execution Sequence

```
Phase 1 — Provision Hetzner bucket + keys        (30 min, no code)
       ↓
Phase 2 — Fix 9 tool files + /tmp DuckDB interim (1–2 days, code)
       ↓
Phase 3 — Data migration: aws s3 sync            (1 hour, ops)
       ↓
Phase 4 — Deploy: add env vars, activate S3+PG   (30 min, config)
       ↓
Phase 5 — Smoke test                             (2 hours)
       ↓
Phase 6 — DuckDB httpfs (deferred, post-cutover) (separate PR)
```

**Important:** Phase 2 must be complete before Phase 4. Setting `STORAGE_BACKEND=s3` before
tool files are fixed will cause silent failures (tools return empty results, charts lost, etc).

---

### Phase 1 — Provision Hetzner Object Storage

**COMPLETE.** Bucket already provisioned. Credentials in `CREDENTIALS.md`.

| Field | Value |
|---|---|
| Bucket | `sajha-storage` |
| Endpoint | `hel1.your-objectstorage.com` |
| Access Key ID | `KV4XOKA59Z0DYQB6ZF5G` |
| Secret Key | in CREDENTIALS.md |

**Remaining action:** Add credentials to GitHub Secrets:
- `S3_ENDPOINT_URL` = `https://hel1.your-objectstorage.com`
- `S3_BUCKET` = `sajha-storage`
- `AWS_ACCESS_KEY_ID` = `KV4XOKA59Z0DYQB6ZF5G`
- `AWS_SECRET_ACCESS_KEY` = _(from CREDENTIALS.md)_

**DuckDB httpfs endpoint (Phase 6):**
```
s3://sajha-storage/path/to/key
SET s3_endpoint='hel1.your-objectstorage.com';
```

---

### Phase 2 — Fix Tool Files

9 files that bypass `storage.*`. Fix these before activating S3.

#### 2A — `fs_index.py`

Local path still uses `os.walk`. Complete the S3 path and unify:

```python
# BEFORE (local path)
for entry in os.listdir(os.path.join(base, rel)):
    ...

# AFTER — unified, works local + S3
keys = storage.list_prefix(prefix)
# build nested tree dict from flat key list
```

Index cache write:
```python
# BEFORE
with open(os.path.join(root_path, '.index.json'), 'w') as f:
    json.dump(tree, f)

# AFTER
storage.write_text(os.path.join(root_path, '.index.json'), json.dumps(tree))
```

#### 2B — `workflow_tools.py`

```python
# BEFORE
for dirpath, dirnames, filenames in os.walk(workflows_dir):
    for fname in filenames:
        if fname.endswith('.md'): ...

# AFTER
for key in storage.list_prefix(workflows_dir):
    if key.endswith('.md'):
        content = storage.read_text(key)
        ...
```

#### 2C — `upload_tools.py`

```python
# BEFORE
for root_path, section in data_roots:
    for dirpath, _, filenames in os.walk(root_path):
        for fname in filenames: ...

# AFTER
for root_path, section in data_roots:
    for key in storage.list_prefix(root_path):
        ...
```

#### 2D — `python_executor.py`

Chart output: write to `/tmp` during execution (fine), then push to storage:

```python
# BEFORE
shutil.copy2(src_path, dest_path)

# AFTER
with open(src_path, 'rb') as f:
    storage.write_bytes(dest_path, f.read())
```

#### 2E — `operational_tools.py`

File versioning:
```python
# BEFORE
shutil.move(str(dest), str(archive_path))

# AFTER
storage.copy(str(dest), str(archive_path))
storage.delete(str(dest))
```

DOCX save via buffer:
```python
# BEFORE
doc.save(str(out_path))

# AFTER
buf = io.BytesIO()
doc.save(buf)
storage.write_bytes(str(out_path), buf.getvalue())
```

#### 2F — `bm25_search_tool.py`

```python
# BEFORE
mtime = os.path.getmtime(abs_path)
fingerprint_parts.append(f"{rel}:{mtime}")

# AFTER
size = storage.get_size(abs_path)   # works on S3 via HeadObject
fingerprint_parts.append(f"{rel}:{size}")
```

Note: size-based fingerprinting won't detect same-size rewrites. Acceptable tradeoff
vs. mtime which is unavailable on S3.

#### 2G — `msdoc_tools_tool_refactored.py`

```python
# BEFORE
if os.path.isfile(candidate_path):
    return candidate_path

# AFTER
if storage.exists(candidate_path):
    return candidate_path
```

#### 2H — `data_transform_tools.py`

```python
# BEFORE — read
table = pq.read_table(str(path))

# AFTER — read
raw = storage.read_bytes(str(path))
table = pq.read_table(io.BytesIO(raw))

# BEFORE — write
pq.write_table(table, str(out_path))

# AFTER — write
buf = io.BytesIO()
pq.write_table(table, buf)
storage.write_bytes(str(out_path), buf.getvalue())

# Versioned move
# BEFORE: shutil.move(src, dst)
# AFTER:  storage.copy(src, dst); storage.delete(src)
```

#### 2I — `file_read_tool.py`

```python
# BEFORE
content = target.read_text(encoding='utf-8')

# AFTER
content = storage.read_text(str(target), encoding='utf-8')
```

#### 2J — DuckDB tools: `/tmp` interim strategy

`duckdb_olap_tools_refactored.py`, `sqlselect_tool_refactored.py`, `duckdb_olap_advanced.py`
call `read_csv_auto('/local/path')` — these cannot read S3 paths without the httpfs extension.

**Interim (Phase 2):** add a `_ensure_local()` helper that downloads a file from S3 to `/tmp`
on demand if `STORAGE_BACKEND=s3`, then returns the local path:

```python
def _ensure_local(path: str) -> str:
    """Return a local filesystem path usable by DuckDB.
    In S3 mode: downloads to /tmp on first access, returns /tmp path.
    In local mode: returns path unchanged.
    """
    if os.environ.get('STORAGE_BACKEND') != 's3':
        return path
    import hashlib, tempfile
    cache_key = hashlib.md5(path.encode()).hexdigest()
    tmp_path = os.path.join(tempfile.gettempdir(), f'sajha_duckdb_{cache_key}')
    if not os.path.exists(tmp_path):
        data = storage.read_bytes(path)
        with open(tmp_path, 'wb') as f:
            f.write(data)
    return tmp_path
```

Wrap every DuckDB file path with `_ensure_local()` before passing to `read_csv_auto()`.
The file is cached in `/tmp` for the container lifetime — re-downloaded fresh on next restart.

This is a temporary bridge. Phase 6 replaces it with direct `s3://` paths via httpfs.

---

### Phase 3 — Data Migration

Run once at cutover from the Hetzner VPS. Uploads all existing Docker volume data to the bucket.

```bash
# SSH into VPS: ssh root@62.238.3.148
aws s3 sync /app/sajhamcpserver/data/ \
    s3://sajha-storage/sajhamcpserver/data/ \
    --endpoint-url https://hel1.your-objectstorage.com

# Verify counts match
aws s3 ls s3://sajha-storage/sajhamcpserver/data/ --recursive --summarize \
    --endpoint-url https://hel1.your-objectstorage.com
```

Keep Docker volume mounted for 30 days as fallback. Remove after stable.

---

### Phase 4 — Deploy: Activate S3

**PostgreSQL is already running.** `docker-compose.prod.yml` has a `postgres:16-alpine` sidecar
container and `DATABASE_URL` is already wired into the app service. No Postgres activation
needed here. See REQ-07 for remaining Postgres gaps (checkpointer, WorkerRepository, etc).

This phase is purely about flipping S3 on.

**Add to GitHub Secrets** (Settings → Secrets → Actions):
```
S3_ENDPOINT_URL  = https://hel1.your-objectstorage.com
S3_BUCKET        = sajha-storage
AWS_ACCESS_KEY_ID        = KV4XOKA59Z0DYQB6ZF5G
AWS_SECRET_ACCESS_KEY    = <from CREDENTIALS.md>
```

**Add to `.github/workflows/deploy.yml`** (`.env` write step):
```bash
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=${{ secrets.S3_ENDPOINT_URL }}
S3_BUCKET=${{ secrets.S3_BUCKET }}
AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }}
AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }}
AWS_REGION=eu-central-1
```

**Add to `docker-compose.prod.yml`** app service environment:
```yaml
STORAGE_BACKEND: ${STORAGE_BACKEND:-local}
S3_ENDPOINT_URL: ${S3_ENDPOINT_URL:-}
S3_BUCKET: ${S3_BUCKET:-sajha-storage}
AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-}
AWS_REGION: ${AWS_REGION:-eu-central-1}
```

Once deployed, `STORAGE_BACKEND=s3` activates the S3 backend throughout the app.
`STORAGE_BACKEND=local` remains the default for local development.

---

### Phase 5 — Smoke Test Checklist

- [ ] File tree loads in chat UI (domain_data, my_data, shared library)
- [ ] File preview works for CSV, XLSX, PDF
- [ ] File upload (admin UI + chat attachment) stores to S3
- [ ] `duckdb_query` tool returns results (files downloaded to `/tmp`, query runs)
- [ ] `python_execute` chart saved to S3, canvas renders
- [ ] Workflow list populates correctly
- [ ] BM25 search returns results after index rebuild
- [ ] Container restart: file tree still populated, charts persist
- [ ] `STORAGE_BACKEND=local` still works locally — no regression

---

### Phase 6 — DuckDB httpfs (Deferred, Post-Cutover)

Replaces the `/tmp` interim from Phase 2J. DuckDB reads CSVs directly from S3 — no local cache needed.

Configure once per DuckDB connection (add to `_get_connection()` in DuckDB tools when `STORAGE_BACKEND=s3`):

```sql
INSTALL httpfs;
LOAD httpfs;
SET s3_endpoint='hel1.your-objectstorage.com';
SET s3_access_key_id='...';
SET s3_secret_access_key='...';
SET s3_region='eu-central-1';
SET s3_url_style='path';   -- Hetzner uses path-style, not virtual-hosted
```

Path conversion helper (replaces `_ensure_local()`):

```python
def _to_s3_uri(local_path: str) -> str:
    """Convert local data path to s3:// URI for DuckDB httpfs."""
    if os.environ.get('STORAGE_BACKEND') != 's3':
        return local_path
    bucket = os.environ['S3_BUCKET']
    key = local_path.lstrip('./').lstrip('/')
    return f's3://{bucket}/{key}'
```

Remove the `/tmp` cache helper and replace `_ensure_local(path)` calls with `_to_s3_uri(path)`.

**AWS compatibility:** On AWS, omit the `SET s3_endpoint` line — DuckDB defaults to `s3.amazonaws.com`. Helper unchanged.

---

## 6. Files Changed

| File | Change | Phase |
|---|---|---|
| `docker-compose.prod.yml` | Add S3 + DB env vars | 4 |
| `.github/workflows/deploy.yml` | Add S3 + DB secrets to .env step | 4 |
| `sajhamcpserver/requirements.txt` | Ensure `boto3>=1.34.0` present | 2 |
| `sajhamcpserver/sajha/tools/impl/fs_index.py` | Unify local + S3 path to use `storage.*` | 2 |
| `sajhamcpserver/sajha/tools/impl/workflow_tools.py` | `os.walk` → `storage.list_prefix()` | 2 |
| `sajhamcpserver/sajha/tools/impl/upload_tools.py` | `os.walk` → `storage.list_prefix()` | 2 |
| `sajhamcpserver/sajha/tools/impl/python_executor.py` | `shutil.copy2` → `storage.write_bytes` | 2 |
| `sajhamcpserver/sajha/tools/impl/operational_tools.py` | `shutil.move` + `doc.save` → storage calls | 2 |
| `sajhamcpserver/sajha/tools/impl/bm25_search_tool.py` | `os.path.getmtime` → `storage.get_size()` | 2 |
| `sajhamcpserver/sajha/tools/impl/msdoc_tools_tool_refactored.py` | `os.path.isfile` → `storage.exists()` | 2 |
| `sajhamcpserver/sajha/tools/impl/data_transform_tools.py` | PyArrow paths → buffer + storage | 2 |
| `sajhamcpserver/sajha/tools/impl/file_read_tool.py` | `pathlib.read_text` → `storage.read_text` | 2 |
| `sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py` | Add `_ensure_local()` helper | 2 (interim) |
| `sajhamcpserver/sajha/tools/impl/sqlselect_tool_refactored.py` | Add `_ensure_local()` helper | 2 (interim) |
| `sajhamcpserver/sajha/tools/impl/duckdb_olap_advanced.py` | Add `_ensure_local()` helper | 2 (interim) |
| *(same 3 DuckDB files)* | Replace `_ensure_local` with httpfs + `_to_s3_uri` | 6 |

---

## 7. Environment Variables Reference

| Variable | Hetzner Value | AWS Value | Notes |
|---|---|---|---|
| `STORAGE_BACKEND` | `s3` | `s3` | Same |
| `S3_ENDPOINT_URL` | `https://nbg1.your-objectstorage.com` | *(omit — use AWS default)* | **Only difference between Hetzner and AWS** |
| `S3_BUCKET` | `sajha-prod` | `sajha-prod` | Same |
| `AWS_ACCESS_KEY_ID` | Hetzner key | IAM key or empty (IAM role) | |
| `AWS_SECRET_ACCESS_KEY` | Hetzner secret | IAM secret or empty (IAM role) | |
| `AWS_REGION` | `eu-central-1` | `us-east-1` (or target region) | |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host/db` | Same pattern | Activates Postgres; JSON fallback when unset |

**Local dev with MinIO:**
```bash
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET=sajha-dev
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1
```

---

## 8. AWS Migration Path (Future — Zero Code Changes)

1. Create S3 bucket in target AWS region
2. Attach IAM role with `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`
3. Env var changes only: remove `S3_ENDPOINT_URL`, update region + credentials
4. DuckDB httpfs: remove `SET s3_endpoint` line from connection setup

No application code changes. Same Docker image. Same boto3 calls.

---

## 9. Acceptance Criteria

### Phase 1–5 (Cutover)
- [ ] Hetzner bucket `sajha-prod` created and credentials in GitHub Secrets
- [ ] All 9 non-DuckDB tool files use `storage.*` — no `os.walk`, `open()`, `shutil` on user data
- [ ] DuckDB tools use `_ensure_local()` — queries work in S3 mode via `/tmp` cache
- [ ] Existing data migrated via `aws s3 sync`
- [ ] `STORAGE_BACKEND=s3` deploy passes Phase 5 smoke test
- [ ] Container restart: files persist, charts persist, workflows load
- [ ] `STORAGE_BACKEND=local` still works — no regression

### Phase 6 (DuckDB httpfs)
- [ ] DuckDB connections load httpfs extension with Hetzner endpoint
- [ ] `duckdb_query` executes SQL directly against `s3://` paths
- [ ] `/tmp` cache helper removed
- [ ] AWS S3 works by removing `SET s3_endpoint` line only

---

## 10. Out of Scope

- Apache Iceberg analytical tables → REQ-08b (depends on this REQ)
- CDK / Terraform infrastructure-as-code → separate REQ
- Multi-region replication, S3 lifecycle policies
- Azure Blob / GCS compatibility
- Supabase (REQ-15 killed)
