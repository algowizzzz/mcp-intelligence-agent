# REQ-16 — Hetzner Object Storage Migration (S3-Compatible)

**Status:** Pending  
**Version:** 1.0 (2026-04-12)  
**Author:** Saad Ahmed  
**Branch:** `feature/req-16-hetzner-s3`  
**Prerequisite:** REQ-07 (PostgreSQL running on Hetzner — already complete)  

---

## 1. Objective

Migrate all file storage from Docker local volumes to Hetzner Object Storage.  
Hetzner Object Storage is S3-compatible — the AWS SDK (boto3) works unchanged with a custom `endpoint_url`. This means the same code will run on AWS S3 later by only changing environment variables — no code changes required at migration time.

**What this is NOT:**
- Not an AWS migration (that's a future infra swap, zero code changes needed after this)
- Not changing the database (Postgres stays on Hetzner VPS)
- Not changing the compute layer (Docker on Hetzner stays as-is)

---

## 2. Why This Is Needed

| Problem Today | Impact |
|---|---|
| All files in Docker volume `/app/sajhamcpserver/data` | Data is tied to one container — volume rebuild = data loss |
| 15 tool files bypass the storage abstraction | Direct `os.walk`, `open()`, `shutil` calls will silently break if volume isn't mounted |
| BM25 index written to local disk | Lost on container restart, rebuilt from scratch every time |
| DuckDB passes local filesystem paths | `read_csv_auto('/path/to/file.csv')` — won't work on object storage without DuckDB httpfs |
| No disaster recovery for user files | Hetzner volume failure = unrecoverable |
| AWS migration blocked | Can't move to ECS/Fargate without object storage for files |

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
        └──► PostgreSQL (already on Hetzner VPS)
                  checkpoints, audit, user config — unchanged
```

On AWS migration: change `S3_ENDPOINT_URL` → empty, update `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` to IAM role. Nothing in application code changes.

---

## 4. Current State (Audit Results — 2026-04-12)

### 4.1 Storage abstraction — already complete

`sajhamcpserver/sajha/storage.py` has a fully implemented `S3StorageBackend` class with:
- `read_bytes`, `write_bytes`, `read_text`, `write_text`
- `list_prefix`, `exists`, `delete`, `copy`
- `generate_presigned_url`
- `write_stream` (buffers to memory then PUT — safe for files ≤ 50MB)
- Switches on `STORAGE_BACKEND=s3` env var
- Reads `S3_ENDPOINT_URL`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

**No changes needed to `storage.py`.**

### 4.2 Files that bypass the storage abstraction (must be fixed)

Full audit across all 41 tool implementation files:

| # | File | Severity | What bypasses storage |
|---|------|----------|----------------------|
| 1 | `fs_index.py` | HIGH | `os.walk`, `open()` for index cache — index never persists across restarts |
| 2 | `python_executor.py` | HIGH | `shutil.copy2()` copies chart output to local path — charts lost on restart |
| 3 | `operational_tools.py` | HIGH | `shutil.move()` for file versioning; `doc.save()` writes DOCX directly to disk |
| 4 | `workflow_tools.py` | HIGH | `os.walk` to discover workflows — returns empty on object storage |
| 5 | `duckdb_olap_tools_refactored.py` | HIGH | `read_csv_auto('/local/path')` — DuckDB needs httpfs for S3 paths |
| 6 | `sqlselect_tool_refactored.py` | HIGH | `read_csv_auto('/local/path')` — same DuckDB issue |
| 7 | `duckdb_olap_advanced.py` | HIGH | Hardcoded local CSV paths (`customers.csv`, `orders.csv`, `products.csv`) |
| 8 | `upload_tools.py` | MEDIUM | `os.walk` for file listing — returns empty without volume |
| 9 | `bm25_search_tool.py` | MEDIUM | `os.path.getmtime` for cache fingerprint — fails silently on S3 |
| 10 | `msdoc_tools_tool_refactored.py` | MEDIUM | `os.path.isfile` existence checks — returns false on S3 |
| 11 | `data_transform_tools.py` | MEDIUM | PyArrow `read_table(str(path))` and `write_table()` use direct filesystem paths |
| 12 | `file_read_tool.py` | LOW | `target.read_text()` direct pathlib call — should use `storage.read_text()` |

### 4.3 Clean — no changes needed (29 files)

All connector tools (Teams, Outlook, Jira, Confluence, SharePoint, PowerBI), all web/API tools (EDGAR, Tavily, Yahoo Finance, IR tools), all CCR/risk data tools (counterparty, credit limits, trades, VaR, historical exposure), and all helper modules (connector_base, connector_client, edgar helpers, studio_saad_fib).

---

## 5. Phase Plan

### Phase 1 — Infrastructure Setup (Hetzner Console)
Create the bucket and credentials in Hetzner. No code changes.

**Steps:**
1. Log into Hetzner Cloud Console → Object Storage
2. Create bucket: `sajha-prod` in region `nbg1` (same DC as VPS)
3. Generate S3-compatible Access Key and Secret Key
4. Save credentials — will go into server `.env` and GitHub Secrets

**Bucket settings:**
- Access: Private (no public read)
- Versioning: Enabled (protects against accidental deletes)
- CORS: allow `https://yourdomain.com` for presigned URL downloads

**Hetzner S3 endpoint format:**
```
https://{bucket}.{region}.your-objectstorage.com
# e.g.: https://sajha-prod.nbg1.your-objectstorage.com
```

Or path-style (used in boto3 `endpoint_url`):
```
https://{region}.your-objectstorage.com
```

---

### Phase 2 — Environment Variable Updates

Update `docker-compose.prod.yml` and `.github/workflows/deploy.yml`:

**Add to `docker-compose.prod.yml` `app` service environment:**
```yaml
STORAGE_BACKEND: ${STORAGE_BACKEND:-local}      # change to 's3' at cutover
S3_ENDPOINT_URL: ${S3_ENDPOINT_URL:-}           # e.g. https://nbg1.your-objectstorage.com
S3_BUCKET: ${S3_BUCKET:-sajha-prod}
AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-}
AWS_REGION: ${AWS_REGION:-eu-central-1}
```

**Add to GitHub Secrets (used in deploy.yml .env write step):**
```
S3_ENDPOINT_URL
S3_BUCKET
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

**Add to deploy.yml .env block:**
```bash
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=${{ secrets.S3_ENDPOINT_URL }}
S3_BUCKET=${{ secrets.S3_BUCKET }}
AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }}
AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }}
AWS_REGION=eu-central-1
```

**AWS migration later:** Remove `S3_ENDPOINT_URL`, update `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` to IAM role credentials or use instance profile (no key needed). Zero code changes.

---

### Phase 3 — Fix Tool Files (12 files)

#### 3A — `fs_index.py` (HIGH)

Replace `os.walk` directory scan and local `open()` index cache with storage-abstracted equivalents.

```python
# BEFORE
def build_tree(base, rel=""):
    for entry in os.listdir(os.path.join(base, rel)):
        ...

def build_index(root_path):
    tree = build_tree(root_path)
    with open(os.path.join(root_path, '.index.json'), 'w') as f:
        json.dump(tree, f)

# AFTER
def build_tree_from_prefix(prefix: str) -> dict:
    keys = storage.list_prefix(prefix)
    # Build nested dict from flat key list
    tree = {}
    for key in keys:
        parts = key.split('/')
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = {'type': 'file', 'key': key}
    return tree

def build_index(root_path):
    tree = build_tree_from_prefix(root_path)
    storage.write_text(
        os.path.join(root_path, '.index.json'),
        json.dumps(tree)
    )
```

#### 3B — `workflow_tools.py` (HIGH)

Replace `os.walk` with `storage.list_prefix()`:

```python
# BEFORE
for dirpath, dirnames, filenames in os.walk(workflows_dir):
    for fname in filenames:
        if fname.endswith('.md'):
            ...

# AFTER
keys = storage.list_prefix(workflows_dir)
for key in keys:
    if key.endswith('.md'):
        content = storage.read_text(os.path.join(workflows_dir, key))
        ...
```

#### 3C — `upload_tools.py` (MEDIUM)

Replace `os.walk` with `storage.list_prefix()`:

```python
# BEFORE
for root_path, section in data_roots:
    if not os.path.exists(root_path):
        continue
    for dirpath, _, filenames in os.walk(root_path):
        for fname in filenames:
            ...

# AFTER
for root_path, section in data_roots:
    keys = storage.list_prefix(root_path)
    for key in keys:
        ...
```

#### 3D — `python_executor.py` (HIGH)

After sandbox execution, push chart output to storage instead of relying on local disk:

```python
# BEFORE
shutil.copy2(src_path, dest_path)

# AFTER
with open(src_path, 'rb') as f:
    storage.write_bytes(dest_path, f.read())
```

Charts are written to `/tmp` during execution (ephemeral is fine) then pushed to storage as the final step. Reading them back for the canvas SSE event uses `storage.read_bytes()`.

#### 3E — `operational_tools.py` (HIGH)

Two fixes:

1. **File versioning** (`shutil.move` → `storage.copy` + `storage.delete`):
```python
# BEFORE
shutil.move(str(dest), str(archive_path))

# AFTER
storage.copy(str(dest), str(archive_path))
storage.delete(str(dest))
```

2. **DOCX save** (`doc.save(path)` → write to buffer + `storage.write_bytes`):
```python
# BEFORE
doc.save(str(out_path))

# AFTER
import io
buf = io.BytesIO()
doc.save(buf)
storage.write_bytes(str(out_path), buf.getvalue())
```

#### 3F — `bm25_search_tool.py` (MEDIUM)

Replace `os.path.getmtime` fingerprint with `storage.get_size()` which works on S3:

```python
# BEFORE
mtime = os.path.getmtime(abs_path)
fingerprint_parts.append(f"{rel}:{mtime}")

# AFTER
size = storage.get_size(abs_path)
fingerprint_parts.append(f"{rel}:{size}")
```

Note: size-based fingerprinting is slightly less precise than mtime (won't detect same-size rewrites) but is correct, reliable, and S3-compatible. Acceptable tradeoff.

#### 3G — `msdoc_tools_tool_refactored.py` (MEDIUM)

Replace `os.path.isfile` with `storage.exists()`:

```python
# BEFORE
if os.path.isfile(candidate_path):
    return candidate_path

# AFTER
if storage.exists(candidate_path):
    return candidate_path
```

#### 3H — `data_transform_tools.py` (MEDIUM)

Parquet read/write via buffer:

```python
# BEFORE — read
table = pq.read_table(str(path))

# AFTER — read
import io
raw = storage.read_bytes(str(path))
table = pq.read_table(io.BytesIO(raw))

# BEFORE — write
pq.write_table(table, str(out_path))

# AFTER — write
buf = io.BytesIO()
pq.write_table(table, buf)
storage.write_bytes(str(out_path), buf.getvalue())
```

#### 3I — `file_read_tool.py` (LOW)

One-line fix:

```python
# BEFORE
content = target.read_text(encoding='utf-8')

# AFTER
content = storage.read_text(str(target), encoding='utf-8')
```

#### 3J — DuckDB tools: `duckdb_olap_tools_refactored.py`, `sqlselect_tool_refactored.py`, `duckdb_olap_advanced.py` (HIGH — Phase 4)

DuckDB requires its `httpfs` extension to read from S3. This is the most complex fix and is deferred to Phase 4. In Phase 3, these tools continue reading from local paths.

**Interim strategy for Phase 3:** DuckDB data files (CSV, Parquet) are synced from S3 to a local temp directory on container startup using a bootstrap script. DuckDB reads local copies. Files are re-synced on upload via a background task.

```python
# bootstrap.py — run at container start before SAJHA server starts
import boto3, os
s3 = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT_URL'], ...)
paginator = s3.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket=bucket, Prefix='sajhamcpserver/data/'):
    for obj in page.get('Contents', []):
        local_path = obj['Key']
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        s3.download_file(bucket, obj['Key'], local_path)
```

This unblocks Phase 3 cutover while DuckDB httpfs work happens in Phase 4.

---

### Phase 4 — DuckDB httpfs (Deferred, post-cutover)

Configure DuckDB's S3 extension so all `read_csv_auto()` calls use `s3://` paths directly.

**DuckDB S3 configuration (run once per connection):**
```sql
INSTALL httpfs;
LOAD httpfs;
SET s3_endpoint='nbg1.your-objectstorage.com';
SET s3_access_key_id='...';
SET s3_secret_access_key='...';
SET s3_region='eu-central-1';
SET s3_url_style='path';   -- Hetzner uses path-style
```

**Path conversion helper:**
```python
def _to_s3_path(local_path: str) -> str:
    """Convert local data path to s3:// key for DuckDB httpfs."""
    if os.environ.get('STORAGE_BACKEND') != 's3':
        return local_path   # local mode unchanged
    bucket = os.environ['S3_BUCKET']
    key = local_path.lstrip('./').lstrip('/')
    return f's3://{bucket}/{key}'
```

All three DuckDB tools call `_to_s3_path(file_path)` before passing to `read_csv_auto()`. The bootstrap sync script from Phase 3 is removed once this is complete.

**AWS compatibility note:** On AWS, `SET s3_endpoint` is not needed — DuckDB defaults to `s3.amazonaws.com`. The `_to_s3_path()` helper still works unchanged.

---

### Phase 5 — Data Migration (Existing Files → Hetzner Object Storage)

Run once at cutover. All existing data from the Docker volume is uploaded to the bucket.

```bash
# On the Hetzner VPS
aws s3 sync /opt/sajha/data/app/workers/ \
    s3://sajha-prod/sajhamcpserver/data/workers/ \
    --endpoint-url https://nbg1.your-objectstorage.com \
    --no-verify-ssl

aws s3 sync /opt/sajha/data/app/common/ \
    s3://sajha-prod/sajhamcpserver/data/common/ \
    --endpoint-url https://nbg1.your-objectstorage.com \
    --no-verify-ssl
```

After sync, set `STORAGE_BACKEND=s3` and redeploy. Docker volume can be kept as backup for 30 days then removed.

---

### Phase 6 — agent_server.py `serve_file()` Update

`serve_file()` currently returns `FileResponse` (local) or raises `NotImplementedError` (S3). Fix:

```python
def serve_file(path: str, media_type: str = None) -> Response:
    if _STORAGE_BACKEND == 'local':
        return FileResponse(path, media_type=media_type) if media_type else FileResponse(path)
    else:
        # S3: generate presigned URL and redirect
        url = storage.generate_presigned_url(path, expiry=300)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=url)
```

Also fix `_seed_worker_folders()` and `_clone_worker_folder()` which currently `return` immediately in S3 mode:

```python
def _seed_worker_folders(worker_id: str):
    if _S3_MODE:
        # S3 has no directories — write placeholder keys to establish structure
        sections = ['domain_data', 'my_data', 'uploads', 'workflows/verified',
                    'workflows/my', 'templates', 'charts']
        for section in sections:
            key = f'sajhamcpserver/data/workers/{worker_id}/{section}/.keep'
            storage.write_text(key, '')
        return
    ...
```

---

## 6. Environment Variables Reference

| Variable | Hetzner Value | AWS Value | Notes |
|---|---|---|---|
| `STORAGE_BACKEND` | `s3` | `s3` | Same |
| `S3_ENDPOINT_URL` | `https://nbg1.your-objectstorage.com` | *(empty)* | **Only difference between Hetzner and AWS** |
| `S3_BUCKET` | `sajha-prod` | `sajha-prod` | Same bucket name |
| `AWS_ACCESS_KEY_ID` | Hetzner Object Storage key | IAM key or empty (IAM role) | |
| `AWS_SECRET_ACCESS_KEY` | Hetzner Object Storage secret | IAM secret or empty (IAM role) | |
| `AWS_REGION` | `eu-central-1` | `us-east-1` (or your region) | |

**Local development with MinIO (no Hetzner/AWS account needed):**
```bash
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET=sajha-dev
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1
```

Run MinIO locally:
```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

---

## 7. Add boto3 to requirements

```
# requirements.txt (root, for agent_server.py)
boto3>=1.34.0

# sajhamcpserver/requirements.txt (for SAJHA tools)
boto3>=1.34.0
```

---

## 8. AWS Migration Path (Future — Zero Code Changes)

When an enterprise client (e.g., BMO) wants AWS deployment, the only changes are:

1. Create S3 bucket in target AWS region
2. Attach IAM role to ECS task with `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`
3. Update env vars:
   - Remove `S3_ENDPOINT_URL` (blank = real AWS)
   - Update `AWS_REGION` to their region
   - Remove `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (IAM role handles auth)
4. For DuckDB httpfs: remove `SET s3_endpoint` line from connection setup

No application code changes. Same Docker image. Same boto3 calls.

---

## 9. Files Changed Summary

| File | Change |
|---|---|
| `docker-compose.prod.yml` | Add S3 env vars |
| `.github/workflows/deploy.yml` | Add S3 secrets to .env write step |
| `sajhamcpserver/requirements.txt` | Add `boto3>=1.34.0` |
| `requirements.txt` | Add `boto3>=1.34.0` |
| `sajhamcpserver/sajha/tools/impl/fs_index.py` | Replace `os.walk` + `open()` with `storage.*` |
| `sajhamcpserver/sajha/tools/impl/workflow_tools.py` | Replace `os.walk` with `storage.list_prefix()` |
| `sajhamcpserver/sajha/tools/impl/upload_tools.py` | Replace `os.walk` with `storage.list_prefix()` |
| `sajhamcpserver/sajha/tools/impl/python_executor.py` | Replace `shutil.copy2` with `storage.write_bytes` |
| `sajhamcpserver/sajha/tools/impl/operational_tools.py` | Replace `shutil.move` + `doc.save` with storage calls |
| `sajhamcpserver/sajha/tools/impl/bm25_search_tool.py` | Replace `os.path.getmtime` with `storage.get_size()` |
| `sajhamcpserver/sajha/tools/impl/msdoc_tools_tool_refactored.py` | Replace `os.path.isfile` with `storage.exists()` |
| `sajhamcpserver/sajha/tools/impl/data_transform_tools.py` | Replace PyArrow direct paths with buffer + storage |
| `sajhamcpserver/sajha/tools/impl/file_read_tool.py` | Replace `target.read_text()` with `storage.read_text()` |
| `agent_server.py` | Fix `serve_file()`, `_seed_worker_folders()`, `_clone_worker_folder()` |
| `sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py` | Phase 4: add httpfs config + `_to_s3_path()` |
| `sajhamcpserver/sajha/tools/impl/sqlselect_tool_refactored.py` | Phase 4: add httpfs config + `_to_s3_path()` |
| `sajhamcpserver/sajha/tools/impl/duckdb_olap_advanced.py` | Phase 4: add httpfs config + `_to_s3_path()` |

---

## 10. Acceptance Criteria

### Phase 1–3 (Cutover)
- [ ] Hetzner Object Storage bucket `sajha-prod` created, credentials generated
- [ ] `STORAGE_BACKEND=s3` + Hetzner endpoint works — file upload/download/list via admin UI
- [ ] All 9 non-DuckDB tool files updated to use `storage.*` — no direct `os.walk`, `open()`, `shutil` on user data
- [ ] `serve_file()` returns presigned redirect in S3 mode
- [ ] `_seed_worker_folders()` creates placeholder keys in S3 mode
- [ ] Existing data migrated from Docker volume to S3 bucket via `aws s3 sync`
- [ ] Charts generated by `python_executor.py` survive a container restart (stored in S3)
- [ ] Workflows listed correctly after container restart (no local index required)
- [ ] BM25 search works after container restart (index rebuilt from S3 file list)
- [ ] `STORAGE_BACKEND=local` still works unchanged — no regression on local dev

### Phase 4 (DuckDB httpfs)
- [ ] DuckDB connections configured with `LOAD httpfs` + Hetzner S3 endpoint
- [ ] `duckdb_query` tool executes SQL against CSV files in S3 bucket
- [ ] Bootstrap sync script removed
- [ ] `read_csv_auto()` paths use `s3://` prefix in S3 mode, local paths in local mode

### AWS Readiness Check
- [ ] Removing `S3_ENDPOINT_URL` from env and pointing `AWS_REGION` + credentials at a real AWS S3 bucket works with zero code changes
- [ ] DuckDB httpfs works against AWS S3 by removing `SET s3_endpoint` line

---

## 11. Out of Scope

- Apache Iceberg analytical tables → REQ-08b
- CDK infrastructure-as-code for AWS → separate REQ
- Multi-region replication
- S3 lifecycle policies (charts expiry, versioning cleanup)
- Azure Blob / GCS compatibility
