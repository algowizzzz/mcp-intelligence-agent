# REQ-11 — Multi-File Parallel Upload Engine

**Status:** Pending Implementation
**Version:** 2.0 (2026-04-05)
**Scope:** Replace serial single-file upload pipeline with a concurrent, streaming, S3-ready upload engine supporting batch uploads of hundreds of large files across all sections and roles.

---

## 1. Background

### 1.1 Current Bottlenecks

The upload pipeline has four serial bottlenecks that make bulk uploads (400 × 5 MB = 2 GB) impractical:

| Bottleneck | Where | Code Reference | Impact |
|-----------|-------|---------------|--------|
| **Serial XHR queue** | `public/js/file-tree.js` line 896 | `if (self._uploading) return` | One file in flight at a time |
| **Full memory read** | `agent_server.py` line 1982 | `content = await file.read()` | Entire 5 MB held in RAM per upload |
| **Sync disk write** | `agent_server.py` line 1985 | `dest.write_bytes(content)` | Blocking I/O on async event loop |
| **Per-file index rebuild** | `agent_server.py` line 1986 | `build_index(str(root))` | Filesystem walk grows O(n); 400th upload walks 400 files |

**Current timing for 400 × 5 MB files:**
- Localhost: ~5 minutes (serial XHR + 400 index rebuilds)
- 100 Mbps network: ~27 minutes (network-bound + index overhead)
- Memory peak: 5 MB per upload × 1 concurrent = 5 MB

### 1.2 Design Goals

1. **Parallel uploads** — N concurrent XHR slots (configurable, default 4) on frontend
2. **Streaming writes** — chunked read/write on backend, never hold full file in memory
3. **Deferred indexing** — rebuild `.index.json` once per batch via explicit `/reindex` endpoint
4. **S3-ready** — upload path abstracted through storage backend; local today, S3 multipart tomorrow
5. **Progress visibility** — per-file progress bars, batch progress summary
6. **Resumability** — failed files retryable without re-uploading the batch
7. **Cancel support** — abort active XHRs, clear queue, keep completed files

### 1.3 Affected Endpoints

All upload endpoints get streaming writes + batch_id support:

| Endpoint | Role | File |
|----------|------|------|
| `POST /api/super/workers/{id}/files/{section}/upload` | super_admin | `agent_server.py` line 1963 |
| `POST /api/admin/worker/files/{section}/upload` | admin | `agent_server.py` line 2009 |
| `POST /api/fs/{section}/upload` | user | `agent_server.py` line 1282 |
| `POST /api/admin/common/upload` | admin | New from REQ-10 |
| `POST /api/files/upload` | user (legacy chat) | `agent_server.py` line 1038 |

---

## 2. Architecture

### 2.1 Frontend — Parallel Upload Manager

```
User drops 400 files onto admin file tree
    │
    ▼
BPulseFileTree.upload(files, destFolder)
    │
    ├── Generates batch_id = crypto.randomUUID() (client-side)
    ├── Queue: 400 items, status=queued
    │
    ├── Slot 1 ─── XHR → POST .../upload?batch_id=abc → progress → done
    ├── Slot 2 ─── XHR → POST .../upload?batch_id=abc → progress → done
    ├── Slot 3 ─── XHR → POST .../upload?batch_id=abc → progress → done
    └── Slot 4 ─── XHR → POST .../upload?batch_id=abc → progress → done
         │
         ├── On each completion: pick next queued item, start XHR
         ├── On all complete: POST .../reindex → refresh tree ONCE
         └── On error: mark item failed, continue others, show retry
```

**Key decisions:**
- **XHR not fetch** — XHR has `upload.onprogress` for real per-file progress (BUG-FS-003 precedent)
- **4 parallel slots** — browser throttles above ~6 connections per host; 4 is safe
- **batch_id is client-generated** — `crypto.randomUUID()` or `Math.random().toString(36).slice(2)`. Server doesn't track batch state — batch_id is just a flag meaning "skip index rebuild"
- **Tree refresh deferred** — `self.load()` called ONCE when entire batch completes, not per file

### 2.2 Backend — Streaming Write

```
POST /api/super/workers/{id}/files/{section}/upload?batch_id=abc123
    │
    ├── Validate section, path traversal, filename
    │
    ├── Streaming write (replaces await file.read()):
    │   async with aiofiles.open(dest, 'wb') as f:
    │       while chunk := await file.read(65536):
    │           await f.write(chunk)
    │           bytes_written += len(chunk)
    │           if bytes_written > 50 * 1024 * 1024:
    │               cleanup and raise 413
    │
    ├── If batch_id is non-empty:
    │   └── Skip build_index() — caller will POST /reindex
    │
    └── Return { path, size_bytes, modified_at }
```

### 2.3 Reindex Endpoint

```
POST /api/super/workers/{id}/files/{section}/reindex
POST /api/admin/worker/files/{section}/reindex
    │
    └── build_index(str(root))  → called ONCE after batch
```

### 2.4 S3 Path — Multipart Upload (Design Now, Implement Later)

When `STORAGE_BACKEND=s3`, the flow changes to S3 multipart upload (5 MB parts). The storage abstraction needs a `write_stream()` method so endpoint code is identical for both backends:

```python
class StorageBackend:
    async def write_stream(self, path: str, stream, chunk_size: int = 65536) -> int:
        """Write from async stream. Returns bytes written."""
        raise NotImplementedError
```

**Local:** Opens file, writes chunks via `aiofiles`.
**S3:** Uses `boto3.create_multipart_upload` → `upload_part` per 5 MB → `complete_multipart_upload`.

---

## 3. Frontend Changes (`public/js/file-tree.js`)

### 3.1 Replace Serial Queue with Concurrent Manager

Replace `_processUploadQueue` (line ~894):

```javascript
BPulseFileTree.prototype._processUploadQueue = function () {
  var self = this;
  var MAX = self._uploadConcurrency || 4;
  var active = self._uploadQueue.filter(function(i) { return i.status === 'uploading'; }).length;

  while (active < MAX) {
    var next = null;
    for (var i = 0; i < self._uploadQueue.length; i++) {
      if (self._uploadQueue[i].status === 'queued') { next = self._uploadQueue[i]; break; }
    }
    if (!next) break;
    self._startUpload(next);
    active++;
  }
};
```

### 3.2 Per-File Upload with Batch ID

```javascript
BPulseFileTree.prototype._startUpload = function (item) {
  var self = this;
  item.status = 'uploading';
  self._renderUploadQueue();

  var fd = new FormData();
  fd.append('file', item.file);
  var batchId = self._currentBatchId || '';
  var url = self._url('upload')
    + '?path=' + encodeURIComponent(item.destFolder || '')
    + (batchId ? '&batch_id=' + encodeURIComponent(batchId) : '');

  var xhr = new XMLHttpRequest();
  xhr.open('POST', url);
  var tok = self._token();
  if (tok) xhr.setRequestHeader('Authorization', 'Bearer ' + tok);

  xhr.upload.onprogress = function (e) {
    if (e.lengthComputable) {
      item.progress = Math.round(e.loaded / e.total * 100);
      item.bytesLoaded = e.loaded;
      self._renderUploadQueueItem(item);
      self._renderBatchProgress();
    }
  };

  xhr.onload = function () {
    if (xhr.status >= 200 && xhr.status < 300) {
      item.status = 'done';
      item.progress = 100;
    } else {
      item.status = 'error';
      try { item.error = JSON.parse(xhr.responseText).detail; }
      catch (e) { item.error = 'HTTP ' + xhr.status; }
    }
    self._renderUploadQueue();
    self._processUploadQueue();
    self._checkBatchComplete();
  };

  xhr.onerror = function () {
    item.status = 'error';
    item.error = 'Network error';
    self._renderUploadQueue();
    self._processUploadQueue();
    self._checkBatchComplete();
  };

  item._xhr = xhr;  // store for cancel
  xhr.send(fd);
};
```

### 3.3 Batch Completion — Single Reindex + Tree Refresh

```javascript
BPulseFileTree.prototype._checkBatchComplete = function () {
  var self = this;
  var q = self._uploadQueue;
  var remaining = q.filter(function(i) { return i.status === 'queued' || i.status === 'uploading'; });
  if (remaining.length > 0) return;

  var done = q.filter(function(i) { return i.status === 'done'; }).length;
  var failed = q.filter(function(i) { return i.status === 'error'; }).length;
  self._toast('Upload complete: ' + done + ' succeeded' + (failed ? ', ' + failed + ' failed' : ''),
              done > 0 ? 'success' : 'error');

  if (done > 0) {
    fetch(self._url('reindex'), {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + self._token() }
    }).then(function() { self.load(); });
  }

  setTimeout(function () {
    self._uploadQueue = q.filter(function(i) { return i.status === 'error'; });
    self._currentBatchId = '';
    self._renderUploadQueue();
  }, 5000);
};
```

### 3.4 Batch Progress Bar

```javascript
BPulseFileTree.prototype._renderBatchProgress = function () {
  var q = this._uploadQueue;
  if (!q.length) return;
  var total = q.length;
  var done = q.filter(function(i) { return i.status === 'done'; }).length;
  var failed = q.filter(function(i) { return i.status === 'error'; }).length;
  var active = q.filter(function(i) { return i.status === 'uploading'; }).length;
  var totalBytes = q.reduce(function(s, i) { return s + (i.file.size || 0); }, 0);
  var loadedBytes = q.reduce(function(s, i) {
    if (i.status === 'done') return s + (i.file.size || 0);
    return s + (i.bytesLoaded || 0);
  }, 0);
  var pct = totalBytes > 0 ? Math.round(loadedBytes / totalBytes * 100) : 0;
  var mbDone = (loadedBytes / 1048576).toFixed(1);
  var mbTotal = (totalBytes / 1048576).toFixed(1);

  var el = document.getElementById(this._containerId + '-batch-progress');
  if (el) {
    el.innerHTML = '<div style="font-size:11px;color:#aaa;padding:4px 8px">' +
      done + '/' + total + ' files · ' + mbDone + ' / ' + mbTotal + ' MB · ' +
      active + ' active' + (failed ? ' · <span style="color:#f87171">' + failed + ' failed</span>' : '') +
      '<div style="height:3px;background:#333;border-radius:2px;margin-top:4px">' +
        '<div style="height:100%;width:' + pct + '%;background:#3b82f6;border-radius:2px;transition:width 0.3s"></div>' +
      '</div></div>';
  }
};
```

### 3.5 Cancel Mid-Batch

```javascript
BPulseFileTree.prototype.cancelBatch = function () {
  var self = this;
  self._uploadQueue.forEach(function(item) {
    if (item.status === 'uploading' && item._xhr) {
      item._xhr.abort();
      item.status = 'cancelled';
    } else if (item.status === 'queued') {
      item.status = 'cancelled';
    }
  });
  self._uploadQueue = self._uploadQueue.filter(function(i) { return i.status === 'done'; });
  self._currentBatchId = '';
  self._renderUploadQueue();
  self._toast('Upload cancelled', 'info');
  self.load();  // refresh tree to show completed files
};
```

### 3.6 Retry Failed Files

```javascript
BPulseFileTree.prototype.retryFailed = function () {
  var self = this;
  self._uploadQueue.forEach(function(item) {
    if (item.status === 'error') {
      item.status = 'queued';
      item.progress = 0;
      item.error = null;
      item.bytesLoaded = 0;
    }
  });
  self._currentBatchId = crypto.randomUUID ? crypto.randomUUID() :
                          Math.random().toString(36).slice(2);
  self._renderUploadQueue();
  self._processUploadQueue();
};
```

### 3.7 Client-Side File Size Validation

In `upload()` method, reject files over 50 MB before queuing:

```javascript
BPulseFileTree.prototype.upload = function (files, destFolder) {
  var self = this;
  if (!files || !files.length) return;
  var MAX_SIZE = 50 * 1024 * 1024;
  var rejected = [];
  files.forEach(function (f) {
    if (f.size > MAX_SIZE) {
      rejected.push(f.name);
      return;
    }
    self._uploadQueue.push({
      file: f, destFolder: destFolder || '',
      id: Math.random().toString(36).slice(2),
      status: 'queued', progress: 0, bytesLoaded: 0, error: null, _xhr: null,
    });
  });
  if (rejected.length) {
    self._toast(rejected.length + ' file(s) exceed 50 MB limit', 'error');
  }
  self._currentBatchId = crypto.randomUUID ? crypto.randomUUID() :
                          Math.random().toString(36).slice(2);
  self._renderUploadQueue();
  self._processUploadQueue();
};
```

### 3.8 Configuration

Add to BPulseFileTree constructor:

```javascript
this._uploadConcurrency = opts.uploadConcurrency || 4;
```

---

## 4. Backend Changes (`agent_server.py`)

### 4.1 Dependencies

Add to `requirements.txt`:
```
aiofiles>=23.0
```

### 4.2 Streaming Write — All Upload Endpoints

Replace `content = await file.read(); dest.write_bytes(content)` pattern with:

```python
import aiofiles

UPLOAD_CHUNK_SIZE = 65536  # 64 KB
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

async def _stream_upload(file: UploadFile, dest: pathlib.Path) -> int:
    """Stream upload to disk in 64 KB chunks. Returns bytes written.
    Raises HTTPException(413) if file exceeds limit. Cleans up partial file on error."""
    bytes_written = 0
    try:
        async with aiofiles.open(dest, 'wb') as f:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                await f.write(chunk)
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail='File exceeds 50 MB limit')
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f'Upload failed: {e}')
    return bytes_written
```

Apply to all five upload endpoints. Example for `super_worker_upload`:

```python
@app.post('/api/super/workers/{worker_id}/files/{section}/upload')
async def super_worker_upload(
    worker_id: str, section: str, path: str = '',
    overwrite: bool = False, batch_id: str = '',
    file: UploadFile = File(...),
    _: dict = Depends(require_super_admin),
):
    w = _find_worker(worker_id)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    root = _resolve_admin_path_for_worker(w, section)
    folder = _resolve_admin_path_for_worker(w, section, path) if path else root
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / pathlib.Path(file.filename).name
    if dest.exists() and not overwrite:
        raise HTTPException(status_code=409, detail='File already exists')

    await _stream_upload(file, dest)

    if not batch_id:
        build_index(str(root))

    stat = dest.stat()
    return {
        'path': str(dest.relative_to(root)).replace('\\', '/'),
        'size_bytes': stat.st_size,
        'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }
```

### 4.3 Reindex Endpoint

```python
@app.post('/api/super/workers/{worker_id}/files/{section}/reindex')
async def super_worker_reindex(
    worker_id: str, section: str,
    _: dict = Depends(require_super_admin),
):
    """Rebuild .index.json for a section. Called once after batch upload completes."""
    w = _find_worker(worker_id)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    root = _resolve_admin_path_for_worker(w, section)
    t0 = time.time()
    idx = build_index(str(root))
    elapsed = round((time.time() - t0) * 1000, 1)
    file_count = _count_files_in_tree(idx.get('tree', []))
    return {'indexed_files': file_count, 'elapsed_ms': elapsed, 'section': section}


@app.post('/api/admin/worker/files/{section}/reindex')
async def admin_worker_reindex(section: str, payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    root = _resolve_worker_path(w, section)
    t0 = time.time()
    idx = build_index(str(root))
    elapsed = round((time.time() - t0) * 1000, 1)
    file_count = _count_files_in_tree(idx.get('tree', []))
    return {'indexed_files': file_count, 'elapsed_ms': elapsed, 'section': section}


def _count_files_in_tree(tree: list) -> int:
    count = 0
    for item in tree:
        if item.get('type') == 'file':
            count += 1
        elif item.get('type') == 'folder':
            count += _count_files_in_tree(item.get('children', []))
    return count
```

### 4.4 Storage Backend Extension (`sajha/storage.py`)

```python
class LocalStorageBackend:
    # ... existing methods ...

    async def write_stream(self, path: str, stream, chunk_size: int = 65536) -> int:
        """Write from async file-like stream. Returns bytes written."""
        import aiofiles
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        async with aiofiles.open(p, 'wb') as f:
            while True:
                chunk = await stream.read(chunk_size)
                if not chunk:
                    break
                await f.write(chunk)
                total += len(chunk)
        return total


class S3StorageBackend:
    # ... existing stubs ...

    async def write_stream(self, path: str, stream, chunk_size: int = 5242880) -> int:
        """S3 multipart upload. 5 MB parts (S3 minimum for multipart)."""
        raise NotImplementedError(
            "S3 streaming upload not yet implemented. "
            "Set STORAGE_BACKEND=s3 and implement boto3 multipart upload."
        )
```

---

## 5. Performance Projections

### 5.1 After Implementation

| Scenario | Current (serial) | After (4 parallel) | Improvement |
|----------|-----------------|-------------------|-------------|
| 400 × 5 MB localhost | ~5 min | ~75 sec | 4× |
| 400 × 5 MB @ 100 Mbps | ~27 min | ~7 min | 4× |
| 1000 × 2 MB localhost | ~8 min | ~2 min | 4× |
| Index rebuild (400 files) | 400 × 200ms = 80s | 1 × 500ms = 0.5s | 160× |
| Memory per upload | 5 MB (full file) | 64 KB (streaming) | 80× |
| Memory peak (4 concurrent) | 5 MB | 256 KB | 20× |

---

## 6. Implementation Stories

| Story | Description | Depends On |
|-------|-------------|-----------|
| S1 | Add `aiofiles` to `requirements.txt` | — |
| S2 | Create `_stream_upload()` helper in `agent_server.py` | S1 |
| S3 | Refactor `super_worker_upload` to use streaming + `batch_id` | S2 |
| S4 | Refactor `admin_worker_upload` to use streaming + `batch_id` | S2 |
| S5 | Refactor `fs_upload` (user endpoint) to use streaming + `batch_id` | S2 |
| S6 | Refactor legacy `upload_file` endpoint to use streaming | S2 |
| S7 | Add `POST .../reindex` endpoints (super_admin + admin) | — |
| S8 | Add `write_stream()` to `LocalStorageBackend` in `storage.py` | S1 |
| S9 | Add `write_stream()` stub to `S3StorageBackend` | — |
| S10 | Frontend: replace serial `_processUploadQueue` with concurrent manager | — |
| S11 | Frontend: add batch_id generation in `upload()` method | S10 |
| S12 | Frontend: deferred reindex — call `/reindex` once on batch complete | S7, S10 |
| S13 | Frontend: add batch progress bar UI | S10 |
| S14 | Frontend: add cancel mid-batch (`cancelBatch()`) | S10 |
| S15 | Frontend: add retry failed (`retryFailed()`) | S10 |
| S16 | Frontend: client-side file size validation before queue | S10 |

---

## 7. QA Test Plan

### 7.1 Backend Tests

| ID | Test | Expected |
|----|------|----------|
| UP-01 | Upload 1 file without `batch_id` | File written, index rebuilt, 200 |
| UP-02 | Upload 1 file with `batch_id=abc` | File written, index NOT rebuilt, 200 |
| UP-03 | `POST .../reindex` after batch | Index rebuilt, `indexed_files` count correct |
| UP-04 | Upload 51 MB file | 413 error, partial file cleaned up, no leftover on disk |
| UP-05 | Upload to nonexistent worker | 404 |
| UP-06 | Upload with path traversal `?path=../../etc` | 400 |
| UP-07 | 10 concurrent uploads to same section (httpx async) | All succeed, no file corruption |
| UP-08 | Upload 0-byte file | 200, file created |
| UP-09 | Upload with `overwrite=true` on existing file | 200, file replaced |
| UP-10 | Upload with `overwrite=false` on existing file | 409 |
| UP-11 | Streaming memory check: upload 20 MB file, monitor RSS | Process RSS increase < 5 MB during upload |
| UP-12 | `fs_upload` (user endpoint) with `batch_id` | File written, index NOT rebuilt |

### 7.2 Playwright UI Tests

| ID | Scenario | Steps | Expected |
|----|----------|-------|----------|
| UP-UI-01 | Multi-file upload | Select 20 files via picker → confirm | Queue shows 20 items; 4 uploading simultaneously; progress bars animate |
| UP-UI-02 | Batch progress bar | During multi-upload | Summary shows "N/20 files · X.X / Y.Y MB" with progress fill |
| UP-UI-03 | Tree refreshes once | Upload 10 files | Tree refreshes ONCE after all complete (no intermediate refreshes) |
| UP-UI-04 | Failed file retry | Upload file to nonexistent path → click Retry after fix | Failed item re-queues and uploads |
| UP-UI-05 | Oversized file rejected | Select a 60 MB file | Toast: "1 file(s) exceed 50 MB limit"; file not in queue |
| UP-UI-06 | Drag-drop to folder | Drag 5 files onto a folder in tree | Files uploaded to that folder path |
| UP-UI-07 | Cancel mid-batch | Click Cancel during batch | Active XHRs aborted; queued cleared; completed files kept; tree refreshes |

---

## 8. Acceptance Criteria

- [ ] UP-01 through UP-12 backend tests pass
- [ ] UP-UI-01 through UP-UI-07 Playwright tests pass
- [ ] 400 × 5 MB upload completes in under 2 minutes on localhost
- [ ] Memory stays under 10 MB during bulk upload (streaming verified)
- [ ] `.index.json` rebuilt once per batch, not per file
- [ ] 4 concurrent upload slots active during batch (visible in UI)
- [ ] Failed files show retry button; retry works
- [ ] Cancel aborts active XHRs and clears queue
- [ ] Batch progress bar shows files/MB/active count
- [ ] S3 `write_stream()` stub raises `NotImplementedError` with activation instructions
- [ ] `aiofiles` added to requirements.txt
- [ ] All five upload endpoints use streaming (no `await file.read()` anywhere)
- [ ] No regressions in single-file upload from chat
- [ ] No regressions in admin panel file operations (rename, delete, preview)

---

## 9. Sequencing with REQ-10

REQ-10 (Common Data Path) and REQ-11 (Parallel Upload) are **independent** and can run in parallel:
- REQ-10 adds `common` as a new section — it uses the existing upload endpoints
- REQ-11 improves upload mechanics for all sections — it doesn't care which sections exist
- Once both are complete, uploading to common benefits from parallel streaming automatically

---

## 10. Out of Scope

- S3 multipart upload implementation (stub only — activated with future S3 REQ)
- Upload progress reported server-side via SSE (frontend XHR progress is sufficient)
- Folder upload (preserving directory structure) — user creates folders first, then uploads into them
- Compression/deduplication of uploaded files
- Upload quotas per-user or per-worker (beyond the 50 MB per-file cap)
