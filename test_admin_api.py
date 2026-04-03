#!/usr/bin/env python3
"""
Comprehensive API test for all admin file management endpoints in agent_server.py
Uses urllib only (no requests library).
"""

import urllib.request
import urllib.error
import urllib.parse
import json
import uuid
import io

BASE = 'http://localhost:8000'

passed = 0
failed = 0


def p(ok, role, op, path, status, detail=''):
    global passed, failed
    if ok:
        passed += 1
        print(f'  ✅ PASS  [{role}] {op} {path} — {status}')
    else:
        failed += 1
        print(f'  ❌ FAIL  [{role}] {op} {path} — {status}: {detail}')


def login(user_id, password):
    data = json.dumps({'user_id': user_id, 'password': password}).encode()
    req = urllib.request.Request(
        f'{BASE}/api/auth/login',
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def do_request(method, path, token=None, body=None, content_type='application/json',
               expect_json=True):
    """Generic request returning (status_code, body_dict_or_str)."""
    url = f'{BASE}{path}'
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if body is not None and content_type:
        headers['Content-Type'] = content_type

    data = None
    if body is not None:
        if isinstance(body, bytes):
            data = body
        else:
            data = json.dumps(body).encode()

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            if expect_json:
                try:
                    return resp.status, json.loads(raw)
                except Exception:
                    return resp.status, raw.decode(errors='replace')
            return resp.status, raw.decode(errors='replace')
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors='replace')


def build_multipart(fields, files):
    """Build multipart/form-data body. files = [(field, filename, content_bytes, content_type)]"""
    boundary = f'----FormBoundary{uuid.uuid4().hex}'
    body = io.BytesIO()

    for name, value in fields:
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.write(f'{value}\r\n'.encode())

    for name, filename, content, ctype in files:
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        body.write(f'Content-Type: {ctype}\r\n\r\n'.encode())
        body.write(content)
        body.write(b'\r\n')

    body.write(f'--{boundary}--\r\n'.encode())
    return body.getvalue(), f'multipart/form-data; boundary={boundary}'


def upload_file(token, section, path, filename, content, ctype='text/csv'):
    """POST /api/admin/upload with multipart."""
    fields = [('section', section)]
    if path:
        fields.append(('path', path))
    files = [('file', filename, content, ctype)]
    body_bytes, content_type = build_multipart(fields, files)

    url = f'{BASE}/api/admin/upload?section={urllib.parse.quote(section)}'
    if path:
        url += f'&path={urllib.parse.quote(path)}'

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': content_type}
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}


# ─── Get tokens ───────────────────────────────────────────────────────────────

print('\n=== Authenticating ===')
sa_resp, sa_status = login('risk_agent', 'RiskAgent2025!')
if sa_status == 200:
    sa_token = sa_resp['token']
    print(f'  super_admin token obtained (role={sa_resp.get("role")})')
else:
    sa_token = None
    print(f'  ❌ super_admin login failed: {sa_status} {sa_resp}')

ad_resp, ad_status = login('admin', 'admin123')
if ad_status == 200:
    ad_token = ad_resp['token']
    print(f'  admin token obtained (role={ad_resp.get("role")})')
else:
    ad_token = None
    print(f'  ❌ admin login failed: {ad_status} {ad_resp}')

usr_resp, usr_status = login('test_user', 'TestUser2025!')
if usr_status == 200:
    usr_token = usr_resp['token']
    print(f'  user token obtained (role={usr_resp.get("role")})')
else:
    usr_token = None
    print(f'  ❌ user login failed: {usr_status} {usr_resp}')

print()


# ─── Helper to run the full domain_data + verified_workflows suite for one role ──

def run_admin_suite(role_label, token):
    print(f'\n{"="*60}')
    print(f'  Testing role: {role_label}')
    print(f'{"="*60}')

    # ── DOMAIN DATA ──────────────────────────────────────────────
    print('\n  -- Domain Data --')
    section = 'domain_data'

    # 1. GET tree
    st, body = do_request('GET', f'/api/admin/tree/{section}', token=token)
    p(st == 200, role_label, 'GET tree', section, st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # 2. POST folder
    folder_name = 'test_upload_folder'
    st, body = do_request('POST', '/api/admin/folder', token=token,
                          body={'section': section, 'path': folder_name})
    p(st == 200, role_label, 'POST folder', f'{section}/{folder_name}', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # 3. POST upload (CSV into folder)
    csv_content = b'id,name,value\n1,alpha,10\n2,beta,20\n'
    st, body = upload_file(token, section, folder_name, 'test_data.csv', csv_content)
    p(st == 200, role_label, 'POST upload', f'{section}/{folder_name}/test_data.csv', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # 4. GET file — read the uploaded CSV
    file_path = f'{folder_name}/test_data.csv'
    st, body = do_request('GET', f'/api/admin/file?section={section}&path={urllib.parse.quote(file_path)}',
                          token=token, expect_json=False)
    p(st == 200, role_label, 'GET file', f'{section}/{file_path}', st,
      str(body)[:80] if st != 200 else '')

    # 5. PATCH rename CSV to test_renamed.csv
    st, body = do_request('PATCH', '/api/admin/rename', token=token,
                          body={'section': section, 'path': file_path, 'new_name': 'test_renamed.csv'})
    p(st == 200, role_label, 'PATCH rename', f'{section}/{file_path} → test_renamed.csv', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    renamed_path = f'{folder_name}/test_renamed.csv'

    # 6. POST folder — create move destination
    dest_folder = 'test_move_dest'
    st, body = do_request('POST', '/api/admin/folder', token=token,
                          body={'section': section, 'path': dest_folder})
    p(st == 200, role_label, 'POST folder (dest)', f'{section}/{dest_folder}', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # 7. POST move — move test_renamed.csv into test_move_dest
    st, body = do_request('POST', '/api/admin/move', token=token,
                          body={'section': section, 'src_path': renamed_path, 'dest_folder': dest_folder})
    p(st == 200, role_label, 'POST move', f'{section}/{renamed_path} → {dest_folder}', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # 8. DELETE test_move_dest (recursive, contains the CSV)
    st, body = do_request('DELETE', '/api/admin/item', token=token,
                          body={'section': section, 'path': dest_folder, 'recursive': True})
    p(st == 200, role_label, 'DELETE folder (recursive)', f'{section}/{dest_folder}', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # 9. DELETE test_upload_folder (now empty)
    st, body = do_request('DELETE', '/api/admin/item', token=token,
                          body={'section': section, 'path': folder_name, 'recursive': True})
    p(st == 200, role_label, 'DELETE folder', f'{section}/{folder_name}', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # ── VERIFIED WORKFLOWS ────────────────────────────────────────
    print('\n  -- Verified Workflows --')
    section = 'verified_workflows'

    # 1. GET tree
    st, body = do_request('GET', f'/api/admin/tree/{section}', token=token)
    p(st == 200, role_label, 'GET tree', section, st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # 2. POST file — create new workflow markdown
    wf_filename = 'test_workflow.md'
    st, body = do_request('POST', '/api/admin/file', token=token,
                          body={'section': section, 'folder': '', 'filename': wf_filename})
    p(st == 200, role_label, 'POST file (new md)', f'{section}/{wf_filename}', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # 3. GET file — read its content
    st, body = do_request('GET', f'/api/admin/file?section={section}&path={urllib.parse.quote(wf_filename)}',
                          token=token, expect_json=False)
    p(st == 200, role_label, 'GET file', f'{section}/{wf_filename}', st,
      str(body)[:80] if st != 200 else '')

    # 4. PATCH rename to test_workflow_renamed.md
    st, body = do_request('PATCH', '/api/admin/rename', token=token,
                          body={'section': section, 'path': wf_filename, 'new_name': 'test_workflow_renamed.md'})
    p(st == 200, role_label, 'PATCH rename', f'{section}/{wf_filename} → test_workflow_renamed.md', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    renamed_wf = 'test_workflow_renamed.md'

    # 5. GET validate
    st, body = do_request('GET', f'/api/admin/validate/{section}/{renamed_wf}', token=token)
    p(st == 200, role_label, 'GET validate', f'{section}/{renamed_wf}', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])

    # 6. DELETE the renamed workflow
    st, body = do_request('DELETE', '/api/admin/item', token=token,
                          body={'section': section, 'path': renamed_wf, 'recursive': False})
    p(st == 200, role_label, 'DELETE file', f'{section}/{renamed_wf}', st,
      body.get('detail', '') if isinstance(body, dict) else str(body)[:80])


def run_user_403_suite(role_label, token):
    """Verify that the user token gets 403 on all admin endpoints."""
    print(f'\n{"="*60}')
    print(f'  Testing role: {role_label} (all should → 403)')
    print(f'{"="*60}')

    tests = [
        ('GET',    '/api/admin/tree/domain_data',     None,    None),
        ('POST',   '/api/admin/folder',               None,    {'section': 'domain_data', 'path': 'x'}),
        ('DELETE', '/api/admin/item',                 None,    {'section': 'domain_data', 'path': 'x'}),
        ('PATCH',  '/api/admin/rename',               None,    {'section': 'domain_data', 'path': 'x', 'new_name': 'y'}),
        ('POST',   '/api/admin/move',                 None,    {'section': 'domain_data', 'src_path': 'a', 'dest_folder': 'b'}),
        ('POST',   '/api/admin/file',                 None,    {'section': 'verified_workflows', 'filename': 'x.md'}),
        ('GET',    '/api/admin/file?section=domain_data&path=x', None, None),
        ('GET',    '/api/admin/validate/verified_workflows/x.md', None, None),
    ]

    op_labels = [
        'GET tree domain_data',
        'POST folder',
        'DELETE item',
        'PATCH rename',
        'POST move',
        'POST file (new md)',
        'GET file',
        'GET validate',
    ]

    # Upload needs special handling (multipart)
    # Test it separately
    st, body = upload_file(token, 'domain_data', '', 'x.csv', b'a,b\n1,2\n')
    p(st == 403, role_label, 'POST upload (multipart)', 'domain_data', st,
      f'expected 403, got {st}' if st != 403 else '')

    for (method, path, _body_unused, body_data), label in zip(tests, op_labels):
        st, body = do_request(method, path, token=token, body=body_data)
        p(st == 403, role_label, label, path.split('?')[0], st,
          f'expected 403, got {st}' if st != 403 else '')


# ─── Run tests ────────────────────────────────────────────────────────────────

if sa_token:
    run_admin_suite('super_admin', sa_token)
else:
    print('\n⚠️  Skipping super_admin tests — no token')

if ad_token:
    run_admin_suite('admin', ad_token)
else:
    print('\n⚠️  Skipping admin tests — no token')

if usr_token:
    run_user_403_suite('user', usr_token)
else:
    print('\n⚠️  Skipping user tests — no token')

# ─── Summary ──────────────────────────────────────────────────────────────────

total = passed + failed
print(f'\n{"="*60}')
print(f'  SUMMARY: {passed}/{total} tests passed')
print(f'{"="*60}\n')
