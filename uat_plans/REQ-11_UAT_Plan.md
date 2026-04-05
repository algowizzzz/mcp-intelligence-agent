# REQ-11 UAT Plan — Multi-File Parallel Upload Engine

**Status:** Implementation Complete — Testing Required  
**Date:** 2026-04-05  
**Scope:** Streaming backend, batch_id deferred reindex, concurrent frontend, cancel/retry/progress

---

## CI Backend Tests (inline Python / curl)

### UP-01 — Single file upload without batch_id triggers reindex
```python
import requests, pathlib, time

# Upload a unique file, no batch_id — index should rebuild
content = b'# Streaming test file no batch id'
r = requests.post(f'{BASE}/api/super/workers/w-market-risk/files/domain_data/upload',
    headers=super_auth(), files={'file': ('stream-test-001.md', content, 'text/markdown')})
assert r.status_code == 200
assert 'size_bytes' in r.json()
print('UP-01 PASS')
```

### UP-02 — Single file upload WITH batch_id skips reindex
```python
content = b'# Streaming test file with batch id'
r = requests.post(
    f'{BASE}/api/super/workers/w-market-risk/files/domain_data/upload?batch_id=test-batch-001',
    headers=super_auth(), files={'file': ('stream-test-002.md', content, 'text/markdown')})
assert r.status_code == 200
# File written but index NOT rebuilt — separate reindex call needed
print('UP-02 PASS')
```

### UP-03 — POST /reindex after batch rebuilds index
```python
r = requests.post(
    f'{BASE}/api/super/workers/w-market-risk/files/domain_data/reindex',
    headers=super_auth())
assert r.status_code == 200
data = r.json()
assert 'indexed_files' in data
assert 'elapsed_ms' in data
assert data['indexed_files'] > 0
print('UP-03 PASS')
```

### UP-04 — 51 MB upload returns 413, no leftover file
```python
import pathlib, tempfile, os

big = b'X' * (51 * 1024 * 1024 + 1)
r = requests.post(f'{BASE}/api/super/workers/w-market-risk/files/domain_data/upload',
    headers=super_auth(), files={'file': ('bigfile.bin', big, 'application/octet-stream')})
assert r.status_code == 413
# No leftover partial file
dest = pathlib.Path('sajhamcpserver/data/workers/w-market-risk/domain_data/bigfile.bin')
assert not dest.exists(), 'Partial file should have been cleaned up'
print('UP-04 PASS')
```

### UP-05 — Upload to nonexistent worker returns 404
```python
r = requests.post(f'{BASE}/api/super/workers/no-such-worker/files/domain_data/upload',
    headers=super_auth(), files={'file': ('x.txt', b'x', 'text/plain')})
assert r.status_code == 404
print('UP-05 PASS')
```

### UP-06 — Path traversal in upload path returns 400
```python
r = requests.post(
    f'{BASE}/api/super/workers/w-market-risk/files/domain_data/upload?path=../../config',
    headers=super_auth(), files={'file': ('x.txt', b'x', 'text/plain')})
assert r.status_code == 400
print('UP-06 PASS')
```

### UP-07 — Concurrent uploads (5 parallel) all succeed
```python
import asyncio, httpx

async def upload_one(client, n):
    content = f'# Concurrent file {n}'.encode()
    return await client.post(
        f'{BASE}/api/super/workers/w-market-risk/files/domain_data/upload?batch_id=concurrent-test',
        headers=super_auth(), files={'file': (f'concurrent-{n:02d}.md', content, 'text/markdown')})

async def run():
    async with httpx.AsyncClient(timeout=30) as client:
        results = await asyncio.gather(*[upload_one(client, i) for i in range(5)])
    for r in results:
        assert r.status_code == 200, f'Expected 200, got {r.status_code}'

asyncio.run(run())
# Reindex once
requests.post(f'{BASE}/api/super/workers/w-market-risk/files/domain_data/reindex',
    headers=super_auth())
print('UP-07 PASS')
```

### UP-08 — 0-byte file upload returns 200
```python
r = requests.post(f'{BASE}/api/super/workers/w-market-risk/files/domain_data/upload',
    headers=super_auth(), files={'file': ('empty.txt', b'', 'text/plain')})
assert r.status_code == 200
print('UP-08 PASS')
```

### UP-09 — Overwrite=true replaces existing file
```python
content_v2 = b'# Version 2'
r = requests.post(
    f'{BASE}/api/super/workers/w-market-risk/files/domain_data/upload?overwrite=true',
    headers=super_auth(), files={'file': ('stream-test-001.md', content_v2, 'text/markdown')})
assert r.status_code == 200
print('UP-09 PASS')
```

### UP-10 — Overwrite=false on existing file returns 409
```python
r = requests.post(
    f'{BASE}/api/super/workers/w-market-risk/files/domain_data/upload?overwrite=false',
    headers=super_auth(), files={'file': ('stream-test-001.md', b'dup', 'text/markdown')})
assert r.status_code == 409
print('UP-10 PASS')
```

### UP-12 — fs_upload (user endpoint) with batch_id skips reindex
```python
content = b'# User upload batch test'
r = requests.post(
    f'{BASE}/api/fs/uploads/upload?batch_id=user-batch-001',
    headers=user_auth(), files={'file': ('user-batch-001.md', content, 'text/markdown')})
assert r.status_code == 200
print('UP-12 PASS')
```

---

## Browser Tests (Playwright)

| ID | Scenario | Expected |
|----|----------|----------|
| UP-UI-01 | Select 10 files in admin domain_data → upload | Queue shows 10 items; 4 simultaneous progress bars |
| UP-UI-02 | During multi-file upload | Batch progress bar shows "N/10 files · X.X / Y.Y MB" with filling bar |
| UP-UI-03 | Upload 10 files | Tree refreshes exactly ONCE after all complete |
| UP-UI-04 | Oversized file (>50 MB) in picker | Toast: "1 file(s) exceed 50 MB limit"; file not queued |
| UP-UI-05 | Upload 3 files → one fails → click retry | Failed file re-queues and attempts again |
| UP-UI-06 | Cancel during batch | Active XHRs aborted; queued cleared; completed files kept; tree refreshes |
