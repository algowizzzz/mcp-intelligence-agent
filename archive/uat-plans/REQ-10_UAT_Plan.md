# REQ-10 UAT Plan — Common Data Path (Shared Library)

**Status:** Implementation Complete — Testing Required  
**Date:** 2026-04-05  
**Scope:** Backend API, BM25 search extension, frontend sidebar + admin panel

---

## CI Tests (inline Python)

### CD-01 — User can browse common tree
```python
r = requests.get(f'{BASE}/api/fs/common/tree', headers=user_auth())
assert r.status_code == 200
assert 'tree' in r.json() or isinstance(r.json(), dict)
print('CD-01 PASS')
```

### CD-02 — User can read a common file
```python
r = requests.get(f'{BASE}/api/fs/common/file?path=regulatory/basel-iii-overview.md', headers=user_auth())
assert r.status_code == 200
assert 'content' in r.json()
assert 'Basel' in r.json()['content']
print('CD-02 PASS')
```

### CD-03 — User upload to common is blocked
```python
import io
r = requests.post(f'{BASE}/api/fs/common/upload',
    headers=user_auth(), files={'file': ('test.md', b'# test', 'text/markdown')})
assert r.status_code == 403
print('CD-03 PASS')
```

### CD-04 — super_admin can upload to common via super endpoint
```python
content = b'# FRTB Overview\nFundamental Review of the Trading Book test document.'
r = requests.post(f'{BASE}/api/super/workers/w-market-risk/files/common/upload',
    headers=super_auth(), files={'file': ('frtb-test.md', content, 'text/markdown')})
assert r.status_code == 200
assert r.json()['path'].endswith('frtb-test.md')
print('CD-04 PASS')
```

### CD-05 — admin can upload to common via /api/admin/common/upload
```python
content = b'# Test Policy\nCorporate risk appetite statement placeholder.'
r = requests.post(f'{BASE}/api/admin/common/upload',
    headers=admin_auth(), files={'file': ('policy-test.md', content, 'text/markdown')})
assert r.status_code == 200
print('CD-05 PASS')
```

### CD-06 — super_admin can delete from common
```python
r = requests.delete(
    f'{BASE}/api/super/workers/w-market-risk/files/common/file?path=frtb-test.md',
    headers=super_auth())
assert r.status_code == 200
print('CD-06 PASS')
```

### CD-07 — admin cannot delete from common
```python
r = requests.delete(
    f'{BASE}/api/admin/worker/files/common/file?path=policy-test.md',
    headers=admin_auth())
assert r.status_code == 403
assert 'super_admin' in r.json()['detail']
print('CD-07 PASS')
```

### CD-08 — document_search includes common files
```python
import requests, json

# First upload a file with unique keyword
keyword = 'xq7zbaselpillartesttoken'
content = f'# Common Test\nThis document contains the unique keyword {keyword}.'.encode()
requests.post(f'{BASE}/api/super/workers/w-market-risk/files/common/upload',
    headers=super_auth(), files={'file': ('common-search-test.md', content, 'text/markdown')})

# Now search
r = requests.post(f'{SAJHA}/mcp', json={
    'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
    'params': {'name': 'document_search', 'arguments': {'query': keyword}}
}, headers=sajha_auth())
result = r.json()['result']['content'][0]['text']
data = json.loads(result)
assert any(keyword in res.get('excerpt', '') + res.get('full_content', '')
           for res in data.get('results', []))
print('CD-08 PASS')
```

### CD-09 — Fingerprint refresh: new common file shows in search
```python
# Upload after initial index build
content2 = b'# Post-index common file\nFRTB sensitivity based approach test file unique_freshness_99z.'
requests.post(f'{BASE}/api/super/workers/w-market-risk/files/common/upload',
    headers=super_auth(), files={'file': ('freshness-test.md', content2, 'text/markdown')})
# Search immediately
r = requests.post(f'{SAJHA}/mcp', json={
    'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
    'params': {'name': 'document_search', 'arguments': {'query': 'unique_freshness_99z'}}
}, headers=sajha_auth())
data = json.loads(r.json()['result']['content'][0]['text'])
assert data['rebuilt'] is True, 'Fingerprint should trigger rebuild'
assert data['total_results'] >= 1
print('CD-09 PASS')
```

### CD-10 — Path traversal rejected
```python
r = requests.get(f'{BASE}/api/fs/common/file?path=../../config/users.json', headers=user_auth())
assert r.status_code in (400, 403)
print('CD-10 PASS')
```

---

## Browser Tests (Playwright)

| ID | Steps | Expected |
|----|-------|----------|
| CD-UI-01 | Login as user → Data & Workflows tab | "Shared Library" section visible between Domain Data and My Data |
| CD-UI-02 | Expand Shared Library → click `regulatory/basel-iii-overview.md` | Preview opens with Basel content |
| CD-UI-03 | Inspect Shared Library toolbar | Only Refresh button; no Upload/Folder/Select/Delete |
| CD-UI-04 | Login as admin → Admin panel | "Shared Library" nav item in Data & Workflows group |
| CD-UI-05 | Admin: navigate to Shared Library → upload a .md file | File appears in tree, toast shown |
| CD-UI-06 | Admin: inspect Shared Library toolbar | No Delete/Select buttons (admin role) |
| CD-UI-07 | Super admin: navigate to Shared Library → Select → Delete | File removed, toast shown |
| CD-UI-08 | Chat as user: ask about "Basel III framework" | `document_search` results include `common/regulatory/basel-iii-overview.md` |
| CD-UI-09 | User chat sidebar: expand Shared Library | Badge shows correct file count |
