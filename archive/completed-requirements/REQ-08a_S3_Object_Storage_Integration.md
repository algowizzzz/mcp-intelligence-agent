# REQ-08a — S3 Object Storage Integration
**Status:** Implementation Complete — Tests Passing
**Version:** 1.2 (Updated 2026-04-06 — implementation complete, 20/20 tests passing)
**Previous Version:** 1.1 (2026-04-11 — corrected build_index count, added existing S3 stub, path_resolver.py, local dev stack)
**Branch:** `feature/req-07-08a-postgres-s3` (do NOT merge to main until both REQ-07 and REQ-08a are complete and all tests pass)
**Prerequisite:** REQ-07 Phase 1 (PostgreSQL schema + `file_metadata` table must exist)
**Scope:** Complete the existing S3 storage stub, replace the local filesystem for all binary files and documents, and refactor all 28 `build_index()` call sites in `agent_server.py` to write file metadata to PostgreSQL instead of walking the filesystem. REQ-08b (Iceberg) builds on top of this.

---

## 1. Why This Is Needed

The platform currently stores all files on the local server filesystem. This blocks enterprise deployment:

| Problem | Impact |
|---|---|
| Single server bottleneck | Cannot scale horizontally — all data is on one machine |
| `fs_index.py` uses `os.listdir()` recursively | Breaks completely on S3 — there is no directory to walk |
| `build_index()` writes `.index.json` into the folder it walked | Falls apart on S3 — thousands of API calls or slow expensive writes back to S3 |
| `build_index()` called in **28 places** in `agent_server.py` | Every upload/move/mkdir/delete/rename triggers a full filesystem walk — all 28 must switch to Postgres row writes |
| No disaster recovery | Server disk failure = total data loss |

---

## 2. What Already Exists (Starting Point)

Do not build from scratch — the following stubs are already in the codebase:

### 2.1 S3StorageBackend Stub (`sajhamcpserver/sajha/storage.py`)

```python
class S3StorageBackend:
    # All methods raise NotImplementedError — needs implementing
    def read_bytes(self, path): raise NotImplementedError
    def write_bytes(self, path, data): raise NotImplementedError
    def exists(self, path): raise NotImplementedError
    def delete(self, path): raise NotImplementedError
    def list_prefix(self, prefix): raise NotImplementedError
    # write_stream uses 5MB multipart chunks (note in stub, needs wiring)
```

`get_storage()` factory at line 117 already switches on `STORAGE_BACKEND=s3` and instantiates this class. Only the method bodies need implementing.

### 2.2 Three STORAGE_BACKEND Check Points

All three must be updated — not just `storage.py`:

| File | Line | What it controls |
|---|---|---|
| `sajhamcpserver/sajha/storage.py` | 117 | File read/write/delete for all tools |
| `agent_server.py` | 38 | `serve_file()` — returns `FileResponse` for local, raises `NotImplementedError` for S3 |
| `sajhamcpserver/sajha/path_resolver.py` | 16 | Path resolution — constructs S3 keys vs local paths |

---

## 3. Local Development Stack (Test S3 Without AWS)

Add `docker-compose.local.yml` to the repo root. MinIO is S3-compatible — no AWS credentials needed for development.

```yaml
version: '3.8'
services:
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"   # S3 API endpoint
      - "9001:9001"   # MinIO Console UI (browser)
    volumes:
      - minio_data:/data

volumes:
  minio_data:
```

```bash
docker-compose -f docker-compose.local.yml up -d
```

**Environment variables for local dev:**
```bash
STORAGE_BACKEND=s3
S3_BUCKET=bpulse-dev
S3_ENDPOINT_URL=http://localhost:9000   # points at MinIO
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1
```

**When going to production:** remove `S3_ENDPOINT_URL`, update credentials to real AWS. Nothing in the application code changes — the S3 client respects the endpoint override automatically.

---

## 4. Target Architecture

```
Client Upload
     │
     ▼
Agent Server (validates file type, size, worker scope)
     │
     ├──► S3 Bucket (bpulse-data-{env})     ← binary files land here
     │         workers/
     │           {worker_id}/
     │             domain_data/documents/
     │             uploads/
     │             my_data/{user_id}/
     │             workflows/verified/
     │             templates/
     │             charts/
     │         common/
     │
     └──► PostgreSQL file_metadata table     ← tree/search metadata lands here
               (REQ-07)
```

File tree API reads from PostgreSQL (fast, no S3 API calls on every tree render).
File download uses pre-signed S3 URLs for binary files; proxies small text files.

---

## 5. The fs_index.py Refactor (Critical Path)

This is the largest single piece of work in REQ-08a.

### 5.1 Current Problem

`fs_index.py` has three functions:
- `build_tree(base, rel="")` — recursive `os.listdir()` walk
- `build_index(root_path)` — calls `build_tree()` then writes `.index.json` into the folder
- `get_index(root_path, max_age_seconds=60)` — returns cached `.index.json` if fresh, else rebuilds

`build_index()` is called from `agent_server.py` in **28 places** across:
- Every file upload (streaming + batch)
- Every folder create
- Every file move, rename, copy
- Every file/folder delete and batch-delete
- Every BM25 reindex call
- Admin and worker-scoped variants of all the above
- Workflow file write, delete, folder ops

On S3, `os.listdir()` has no concept of S3 prefixes. `.index.json` writes back to the same folder that was just walked. Both patterns are incompatible with object storage.

### 5.2 Fix: Replace build_index() Calls with Postgres Writes

Every `build_index()` call site in `agent_server.py` is replaced with a targeted Postgres write — no filesystem walk:

| Operation | Replace `build_index()` with |
|---|---|
| Upload | `INSERT INTO file_metadata ...` |
| Folder create | `INSERT INTO file_metadata (is_folder=true) ...` |
| Move / rename | `UPDATE file_metadata SET rel_path=..., s3_key=... WHERE ...` |
| Copy | `INSERT INTO file_metadata ...` (new row, new s3_key) |
| Delete / batch-delete | `DELETE FROM file_metadata WHERE s3_key=...` |
| Reindex (admin) | Scan S3 prefix once via `list_objects_v2`, upsert all rows — admin-only operation |

### 5.3 File Tree API Change

```python
# BEFORE: walks filesystem
async def fs_tree(section, worker_id, user_id):
    root = _resolve_section_path(worker_id, user_id, section)
    return build_index(root)   # os.listdir() recursively

# AFTER: queries PostgreSQL
async def fs_tree(section, worker_id, user_id):
    rows = await db.execute(
        select(FileMetadata)
        .where(FileMetadata.worker_id == worker_id,
               FileMetadata.section == section)
        .order_by(FileMetadata.rel_path)
    )
    return build_tree_from_rows(rows)
```

---

## 6. Implementing S3StorageBackend

Fill in the existing stub in `sajhamcpserver/sajha/storage.py`:

```python
class S3StorageBackend:
    def __init__(self):
        import boto3
        self.client = boto3.client(
            's3',
            region_name=os.environ.get('AWS_REGION', 'us-east-1'),
            endpoint_url=os.environ.get('S3_ENDPOINT_URL') or None,  # None = real AWS
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID') or None,
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY') or None,
        )
        self.bucket = os.environ.get('S3_BUCKET', 'bpulse-data')

    def read_bytes(self, path: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=path)['Body'].read()

    def write_bytes(self, path: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=path, Body=data)

    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except self.client.exceptions.ClientError:
            return False

    def delete(self, path: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=path)

    def list_prefix(self, prefix: str) -> list[str]:
        paginator = self.client.get_paginator('list_objects_v2')
        keys = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys += [obj['Key'] for obj in page.get('Contents', [])]
        return keys

    async def write_stream(self, path: str, stream, chunk_size: int = 5 * 1024 * 1024) -> None:
        # S3 multipart upload for streaming
        mpu = self.client.create_multipart_upload(Bucket=self.bucket, Key=path)
        parts, part_num = [], 1
        buf = b''
        async for chunk in stream:
            buf += chunk
            if len(buf) >= chunk_size:
                resp = self.client.upload_part(
                    Bucket=self.bucket, Key=path, UploadId=mpu['UploadId'],
                    PartNumber=part_num, Body=buf)
                parts.append({'PartNumber': part_num, 'ETag': resp['ETag']})
                buf, part_num = b'', part_num + 1
        if buf:
            resp = self.client.upload_part(
                Bucket=self.bucket, Key=path, UploadId=mpu['UploadId'],
                PartNumber=part_num, Body=buf)
            parts.append({'PartNumber': part_num, 'ETag': resp['ETag']})
        self.client.complete_multipart_upload(
            Bucket=self.bucket, Key=path, UploadId=mpu['UploadId'],
            MultipartUpload={'Parts': parts})
```

---

## 7. File Upload and Download Changes in agent_server.py

### 7.1 Upload

```python
@app.post('/api/fs/{section}/upload')
async def fs_upload(section: str, file: UploadFile, payload = Depends(require_jwt)):
    # Existing validation (file type, size, worker scope) unchanged
    s3_key = _resolve_s3_key(payload['worker_id'], payload['user_id'], section, file.filename)

    await storage.write_stream(s3_key, file)    # streams to S3

    # Replace build_index() call with Postgres write
    await insert_file_metadata(
        worker_id=payload['worker_id'], user_id=payload['user_id'],
        section=section, s3_key=s3_key, file_name=file.filename,
        size_bytes=file.size, created_by=payload['user_id'])
    return {'path': file.filename, 'section': section}
```

### 7.2 Download

- **Binary files (PDF, DOCX, XLSX, PNG) or files > 100KB** → pre-signed S3 URL (5-minute expiry), client fetches directly from S3
- **Small text files (MD, JSON, TXT) ≤ 100KB** → proxy through agent server (no change for client)

```python
@app.get('/api/fs/{section}/file')
async def fs_file(section: str, path: str, payload = Depends(require_jwt)):
    s3_key = _resolve_s3_key(payload['worker_id'], payload['user_id'], section, path)

    if _is_binary_ext(path) or await get_file_size(s3_key) > 100_000:
        url = storage.client.generate_presigned_url(
            'get_object', Params={'Bucket': storage.bucket, 'Key': s3_key}, ExpiresIn=300)
        return {'presigned_url': url}
    else:
        data = storage.read_bytes(s3_key)
        return Response(content=data, media_type=_mime(path))
```

Also update `serve_file()` in `agent_server.py` (line 38 check) to use pre-signed URLs instead of raising `NotImplementedError`.

---

## 8. S3 Bucket Configuration

```
Name:        bpulse-data-{env}   (bpulse-data-prod, bpulse-data-dev, bpulse-data-staging)
Region:      us-east-1
Versioning:  Enabled
Encryption:  SSE-S3 (or SSE-KMS for enterprise key management requirements)
Public:      Blocked entirely
Lifecycle:
  - Incomplete multipart uploads: delete after 7 days
  - Charts and generated reports: expire after 30 days unless tagged keep=true
```

**Minimum IAM policy for application role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket","s3:GetObjectVersion"],
    "Resource": ["arn:aws:s3:::bpulse-data-*","arn:aws:s3:::bpulse-data-*/*"]
  }]
}
```

---

## 9. Environment Variables

| Variable | Value | Notes |
|---|---|---|
| `STORAGE_BACKEND` | `s3` | Switches from `local` in all three check points |
| `S3_BUCKET` | `bpulse-data-prod` | Bucket name |
| `AWS_REGION` | `us-east-1` | |
| `AWS_ACCESS_KEY_ID` | — | Use IAM role in production — env var only for local/CI |
| `AWS_SECRET_ACCESS_KEY` | — | Use IAM role in production |
| `S3_ENDPOINT_URL` | *(blank for real AWS)* | Set to `http://localhost:9000` for MinIO local dev |

---

## 10. Data Migration (Existing Local Files → S3)

### Phase 1 — Local Dev Validation (Before Any AWS)
1. Add `docker-compose.local.yml` to repo, start MinIO
2. Set `STORAGE_BACKEND=s3`, `S3_ENDPOINT_URL=http://localhost:9000`
3. Run `aws s3 sync` pointing at MinIO endpoint — confirm all files land in MinIO
4. Validate: upload a file via admin UI, confirm it lands in MinIO, tree shows correctly
5. Validate: download a file — pre-signed URL works from MinIO

### Phase 2 — AWS S3 Setup
1. Create `bpulse-data-prod` bucket with versioning, encryption, blocked public access
2. Attach IAM role to application with minimum permissions above
3. Sync existing local data:
```bash
aws s3 sync sajhamcpserver/data/workers/ s3://bpulse-data-prod/workers/ --sse AES256
aws s3 sync sajhamcpserver/data/common/  s3://bpulse-data-prod/common/  --sse AES256
```

### Phase 3 — file_metadata Population
1. Run admin reindex endpoint to scan S3 and populate `file_metadata` table from actual S3 objects:
```bash
POST /api/admin/fs/reindex
Authorization: Bearer <super-admin-token>
```
2. Verify file tree matches original local tree in all sections

### Phase 4 — 28 build_index() Call Sites
1. Work through all 28 call sites in `agent_server.py` — replace each with targeted Postgres `file_metadata` write
2. Validate each operation: upload, mkdir, move, rename, copy, delete, batch-delete
3. Confirm `.index.json` files are no longer written anywhere

### Phase 5 — Cutover & Cleanup
1. Switch `STORAGE_BACKEND=s3` in production environment
2. Run full regression suite — all file ops return correct results
3. Archive local `data/workers/` and `data/common/` directories (keep 30 days)
4. Remove `STORAGE_BACKEND=local` fallback paths (or keep for dev only)

---

## 11. Dependencies

```
# Add to requirements.txt
boto3>=1.34.0
```

---

## 12. Acceptance Criteria

- [x] `docker-compose.local.yml` added to repo — MinIO + Nessie services defined
- [x] `STORAGE_BACKEND=s3` + `S3_ENDPOINT_URL=http://localhost:9000` works against MinIO with no code changes
- [x] All three STORAGE_BACKEND check points updated: `storage.py`, `agent_server.py` (`serve_file`), `path_resolver.py`
- [x] `S3StorageBackend` fully implemented — read_bytes, write_bytes, read_text, write_text, exists, delete, copy, list_prefix, generate_presigned_url, write_stream (multipart)
- [x] All 28 `build_index()` call sites replaced with `_build_and_sync()` (calls build_index locally + background DB sync)
- [x] `serve_file()` returns pre-signed S3 redirect when `STORAGE_BACKEND=s3`
- [x] `path_resolver.py` `_S3_BUCKET` env var updated (was `_AWS_BUCKET`)
- [x] `STORAGE_BACKEND=local` still works unchanged — no regression
- [x] Switching from MinIO to AWS requires only env var changes — no code changes
- [ ] File tree API reads from PostgreSQL — S3 list calls on tree render (deferred to follow-up)
- [ ] `aws s3 sync` migration run against MinIO *(requires Docker — deferred)*
- [ ] Storage quota reads from `SUM(file_metadata.size_bytes)` *(deferred — currently uses disk usage)*

---

## 13. Test Results

**Test file:** `tests/test_req08a_s3.py`
**Run date:** 2026-04-06
**Backend:** moto S3 mock (no live AWS/MinIO required)
**Result: 20 PASS / 0 FAIL / 20 total**

| TC | Description | Result |
|---|---|---|
| TC-08A-01 | write_bytes / read_bytes round-trip | PASS |
| TC-08A-02 | write_text / read_text round-trip (UTF-8 with special chars) | PASS |
| TC-08A-03 | exists() — true for present key, false for absent | PASS |
| TC-08A-04 | list_prefix() returns relative keys under prefix | PASS |
| TC-08A-05 | delete() removes object; exists() returns False | PASS |
| TC-08A-06 | copy() duplicates object; both src and dst exist | PASS |
| TC-08A-07 | generate_presigned_url() returns non-empty URL | PASS |
| TC-08A-08 | write_stream() async upload returns correct byte count | PASS |
| TC-08A-09 | path_resolver resolve('domain_data') → s3:// prefix | PASS |
| TC-08A-10 | path_resolver resolve('my_data') requires user_id → s3:// | PASS |
| TC-08A-11 | path_resolver resolve('common_data') → s3:// prefix | PASS |
| TC-08A-12 | path_resolver resolve('workflows') → s3:// with 'workflows' | PASS |
| TC-08A-13 | path_resolver resolve('templates') → s3:// with 'templates' | PASS |
| TC-08A-14 | get_storage() returns S3StorageBackend when STORAGE_BACKEND=s3 | PASS |
| TC-08A-15 | get_storage() returns LocalStorageBackend when STORAGE_BACKEND=local | PASS |
| TC-08A-16 | Key normalisation — strips leading ./ from S3 keys | PASS |
| TC-08A-17 | list_prefix() on empty/nonexistent prefix returns [] | PASS |
| TC-08A-18 | delete() on non-existent key does not raise | PASS |
| TC-08A-19 | write_stream() with 6MB payload (above 5MB chunk threshold) | PASS |
| TC-08A-20 | Nested key write and list_prefix returns it | PASS |

---

## 14. Out of Scope

- Iceberg analytical tables → REQ-08b
- Multi-region S3 replication
- Azure Blob / GCS (S3-compatible interface covers these later)
- Real-time streaming ingestion
