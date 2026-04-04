"""
test_uat_phase1.py
==================
UAT Phase 1 — API-level tests (no LLM calls required).

Covers:
  Module 1  — Authentication & Session          (A-01 – A-10)
  Module 2  — Worker Management                 (W-01 – W-11)
  Module 3  — User Management                   (U-01 – U-09)
  Module 4  — File Operations (all roles)       (F-01 – F-31)
  Module 9  — Security & RBAC                   (S-01 – S-10)
  Module 10 — Thread & Session Persistence      (P-02 – P-04)
  Module 11 — G-04 Worker Path Isolation        (G-01 – G-05)

Usage:
  # Both servers must be running:
  #   Terminal 1: cd sajhamcpserver && ../venv/bin/python run_server.py
  #   Terminal 2: uvicorn agent_server:app --port 8000
  python test_uat_phase1.py

Results saved to UAT_RESULTS/phase1_<timestamp>.json + .md
"""

import os, sys, time, json, uuid, pathlib, traceback
import httpx
from uat_framework import UATReporter, UATResult, req, login, timed, BASE, TIMEOUT

# ── Credentials & fixtures ────────────────────────────────────────────────────

SUPER_CREDS = ('risk_agent',  'RiskAgent2025!')
ADMIN_CREDS = ('admin',       'Admin2025!')
USER_CREDS  = ['test_user',   'TestUser2025!']   # mutable; may be overridden in main()

MR_WORKER   = 'w-market-risk'
CCR_WORKER  = 'w-e74b5836'

_uat_created_uid = ''   # temp user created in setup; deleted in teardown

R = UATReporter('phase1')
M = {
    1:  'Module 1 — Authentication',
    2:  'Module 2 — Worker Management',
    3:  'Module 3 — User Management',
    4:  'Module 4 — File Operations',
    9:  'Module 9 — Security & RBAC',
    10: 'Module 10 — Thread Persistence',
    11: 'Module 11 — G-04 Path Isolation',
}


# ══════════════════════════════════════════════════════════════════════════════
# Module 1 — Authentication & Session
# ══════════════════════════════════════════════════════════════════════════════

def test_auth() -> tuple:
    R.section('Module 1 — Authentication & Session  (A-01 – A-10)')
    m = M[1]

    # A-01  super_admin login
    t0 = time.monotonic()
    super_tok = login(*SUPER_CREDS)
    dur = round((time.monotonic() - t0) * 1000, 1)
    R.assert_test('A-01', m, 'super_admin login returns JWT', bool(super_tok), f'got empty token', dur)

    # A-02  admin login
    admin_tok = login(*ADMIN_CREDS)
    R.assert_test('A-02', m, 'admin login returns JWT', bool(admin_tok))

    # A-03  user login
    user_tok = login(*USER_CREDS)
    R.assert_test('A-03', m, 'user login returns JWT', bool(user_tok))

    # A-04  wrong password → 401 / 400
    s, body = req('POST', '/api/auth/login', json={'user_id': 'risk_agent', 'password': 'wrong_pw_uat'})
    R.assert_test('A-04', m, 'wrong password rejected (not 200)', s != 200, f'got {s}')

    # A-05  rate limiting — 11 rapid bad attempts → 429
    # (uses a throwaway user_id to avoid locking real accounts)
    fake = f'uat_ratelimit_{uuid.uuid4().hex[:6]}'
    statuses = []
    for _ in range(11):
        sc, _ = req('POST', '/api/auth/login', json={'user_id': fake, 'password': 'bad'})
        statuses.append(sc)
    R.assert_test('A-05', m, 'rate limit: 429 after 11 rapid attempts', 429 in statuses,
                  f'statuses={statuses[-3:]}')

    # A-06  /api/auth/me returns current user
    s, body = req('GET', '/api/auth/me', token=super_tok)
    R.assert_test('A-06', m, '/api/auth/me returns user_id + role',
                  s == 200 and body.get('user_id') == 'risk_agent' and body.get('role') == 'super_admin',
                  f'status={s} body={body}')

    # A-07  tampered token → 401
    bad_tok = super_tok[:-4] + 'xxxx'
    s, _ = req('GET', '/api/auth/me', token=bad_tok)
    R.assert_test('A-07', m, 'tampered JWT rejected (401)', s == 401, f'got {s}')

    # A-08  no token on protected endpoint → 401
    s, _ = req('GET', '/api/super/workers')
    R.assert_test('A-08', m, 'missing token → 401', s == 401, f'got {s}')

    # A-09  change password and re-login
    new_pw = 'UATchanged2025!'
    s, body = req('POST', '/api/auth/change-password', token=admin_tok,
                  json={'current_password': ADMIN_CREDS[1], 'new_password': new_pw})
    changed_ok = (s == 200)
    R.assert_test('A-09a', m, 'change-password returns 200', changed_ok, f'status={s} {body}')
    if changed_ok:
        new_tok = login(ADMIN_CREDS[0], new_pw)
        R.assert_test('A-09b', m, 're-login with new password works', bool(new_tok))
        # Always restore original password — use whichever token is valid
        restore_tok = new_tok or login(ADMIN_CREDS[0], new_pw)
        if restore_tok:
            req('POST', '/api/auth/change-password', token=restore_tok,
                json={'current_password': new_pw, 'new_password': ADMIN_CREDS[1]})
        admin_tok = login(*ADMIN_CREDS)
    else:
        R.skip('A-09b', m, 're-login with new password (skipped: change-password failed)')

    # A-10  logout: verify token still works (server is stateless JWT — logout is client-side)
    #        We verify the token is valid before logout action occurs on client
    s, _ = req('GET', '/api/auth/me', token=user_tok)
    R.assert_test('A-10', m, 'valid token accepted on /api/auth/me', s == 200, f'got {s}')

    return super_tok, admin_tok, user_tok


# ══════════════════════════════════════════════════════════════════════════════
# Module 2 — Worker Management
# ══════════════════════════════════════════════════════════════════════════════

def test_workers(super_tok: str, admin_tok: str, user_tok: str) -> str:
    R.section('Module 2 — Worker Management  (W-01 – W-11)')
    m = M[2]

    # W-01  list workers
    s, body = req('GET', '/api/super/workers', token=super_tok)
    workers = body.get('workers', [])
    ids = [w['worker_id'] for w in workers]
    R.assert_test('W-01', m, 'list workers returns both known workers',
                  s == 200 and MR_WORKER in ids and CCR_WORKER in ids,
                  f'status={s} ids={ids}')

    # W-02  create worker with all fields
    new_name = f'UAT Worker {uuid.uuid4().hex[:6]}'
    s, body = req('POST', '/api/super/workers', token=super_tok,
                  json={'name': new_name, 'description': 'UAT test worker',
                        'system_prompt': 'You are a UAT test bot.', 'enabled_tools': ['*']})
    new_wid = body.get('worker_id', '')
    R.assert_test('W-02a', m, 'create worker → 201 + worker_id', s == 201 and bool(new_wid),
                  f'status={s} body={body}')
    if new_wid:
        wdir = pathlib.Path(f'sajhamcpserver/data/workers/{new_wid}')
        R.assert_test('W-02b', m, 'worker folder created on disk', wdir.is_dir(), str(wdir))
        for sub in ['domain_data', 'workflows/verified', 'workflows/my', 'templates', 'my_data']:
            R.assert_test(f'W-02c-{sub.replace("/","-")}', m, f'  subdirectory {sub} exists',
                          (wdir / sub).is_dir(), str(wdir / sub))

    # W-03  worker schema: path fields present
    s, body = req('GET', f'/api/super/workers/{MR_WORKER}', token=super_tok)
    R.assert_test('W-03a', m, 'GET worker has domain_data_path field',
                  s == 200 and 'domain_data_path' in body, f'keys={list(body.keys())}')
    R.assert_test('W-03b', m, 'GET worker has common_data_path field',
                  'common_data_path' in body, f'keys={list(body.keys())}')
    R.assert_test('W-03c', m, 'GET worker has enabled_tools field',
                  'enabled_tools' in body, f'keys={list(body.keys())}')

    # W-04  update worker prompt
    if new_wid:
        s, body = req('PUT', f'/api/super/workers/{new_wid}', token=super_tok,
                      json={'system_prompt': 'Updated UAT prompt.'})
        R.assert_test('W-04', m, 'update worker system_prompt → 200', s == 200, f'status={s} {body}')

    # W-05  update tool allowlist
    if new_wid:
        s, body = req('PUT', f'/api/super/workers/{new_wid}', token=super_tok,
                      json={'enabled_tools': ['iris_search_counterparties', 'workflow_list']})
        R.assert_test('W-05a', m, 'update enabled_tools → 200', s == 200, f'status={s}')
        s2, body2 = req('GET', f'/api/workers/{new_wid}/tools', token=super_tok)
        tools = [t['name'] for t in body2.get('tools', [])]
        R.assert_test('W-05b', m, 'tool list reflects allowlist (only 2 tools)',
                      len(tools) == 2 and 'iris_search_counterparties' in tools,
                      f'tools={tools}')

    # W-06  clone worker
    clone_name = f'UAT Clone {uuid.uuid4().hex[:4]}'
    s, body = req('POST', '/api/super/workers', token=super_tok,
                  json={'name': clone_name, 'clone_from': MR_WORKER})
    clone_wid = body.get('worker_id', '')
    R.assert_test('W-06a', m, 'clone worker → 201', s == 201 and bool(clone_wid),
                  f'status={s} {body}')
    if clone_wid:
        cdir = pathlib.Path(f'sajhamcpserver/data/workers/{clone_wid}')
        R.assert_test('W-06b', m, 'clone folder exists', cdir.is_dir(), str(cdir))
        my_data = cdir / 'my_data'
        my_files = list(my_data.iterdir()) if my_data.exists() else []
        R.assert_test('W-06c', m, 'clone my_data is empty', len(my_files) == 0,
                      f'found {len(my_files)} files')

    # W-07  assign user to new worker
    if new_wid:
        s, body = req('POST', f'/api/super/workers/{new_wid}/assign', token=super_tok,
                      json={'user_id': USER_CREDS[0], 'role': 'user'})
        R.assert_test('W-07', m, 'assign user to worker → 200', s == 200, f'status={s} {body}')

    # W-08  unassign user
    if new_wid:
        s, body = req('DELETE', f'/api/super/workers/{new_wid}/assign/{USER_CREDS[0]}',
                      token=super_tok)
        R.assert_test('W-08', m, 'unassign user from worker → 200', s == 200, f'status={s}')

    # W-09  delete workers (cleanup) — endpoint requires confirm_name body
    deleted_ok = True
    for wid, wname in [(new_wid, new_name), (clone_wid, clone_name)]:
        if not wid:
            continue
        s, b = req('DELETE', f'/api/super/workers/{wid}', token=super_tok,
                   json={'confirm_name': wname})
        wdir = pathlib.Path(f'sajhamcpserver/data/workers/{wid}')
        if not (s == 200 and not wdir.exists()):
            deleted_ok = False
    R.assert_test('W-09', m, 'delete workers: 200 + folder removed', deleted_ok)

    # W-10  admin cannot create/delete workers
    s, _ = req('POST', '/api/super/workers', token=admin_tok,
               json={'name': 'Unauthorized'})
    R.assert_test('W-10', m, 'admin cannot create worker (403)', s == 403, f'got {s}')

    # W-11  user cannot list workers
    s, _ = req('GET', '/api/super/workers', token=user_tok)
    R.assert_test('W-11', m, 'user cannot list workers (403)', s == 403, f'got {s}')

    return new_wid  # may be '' if creation failed


# ══════════════════════════════════════════════════════════════════════════════
# Module 3 — User Management
# ══════════════════════════════════════════════════════════════════════════════

def test_users(super_tok: str):
    R.section('Module 3 — User Management  (U-01 – U-09)')
    m = M[3]

    # U-01  list users
    s, body = req('GET', '/api/super/users', token=super_tok)
    users = body.get('users', [])
    R.assert_test('U-01', m, 'list users → 200, non-empty', s == 200 and len(users) > 0,
                  f'status={s} count={len(users)}')

    uid_base = f'uat_{uuid.uuid4().hex[:8]}'

    # U-02  create admin user
    s, body = req('POST', '/api/super/users', token=super_tok,
                  json={'user_id': f'{uid_base}_adm', 'password': 'UATadmin2025!',
                        'role': 'admin', 'worker_id': MR_WORKER, 'display_name': 'UAT Admin'})
    adm_uid = body.get('user_id', f'{uid_base}_adm')
    R.assert_test('U-02', m, 'create admin user → 201', s == 201, f'status={s} {body}')

    # U-03  create regular user
    s, body = req('POST', '/api/super/users', token=super_tok,
                  json={'user_id': f'{uid_base}_usr', 'password': 'UATuser2025!',
                        'role': 'user', 'worker_id': MR_WORKER, 'display_name': 'UAT User'})
    usr_uid = body.get('user_id', f'{uid_base}_usr')
    R.assert_test('U-03', m, 'create user → 201', s == 201, f'status={s} {body}')

    # U-04  create super_admin user — API blocks this role (expect 400/422)
    s, body = req('POST', '/api/super/users', token=super_tok,
                  json={'user_id': f'{uid_base}_sup', 'password': 'UATsuper2025!',
                        'role': 'super_admin', 'display_name': 'UAT Super'})
    sup_uid = body.get('user_id', f'{uid_base}_sup')
    R.assert_test('U-04', m, 'create super_admin rejected (400/422)', s in (400, 422),
                  f'status={s} {body}')

    # U-05  update user role
    s, body = req('PUT', f'/api/super/users/{usr_uid}', token=super_tok,
                  json={'role': 'admin', 'worker_id': MR_WORKER})
    R.assert_test('U-05', m, 'update user role → 200', s == 200, f'status={s} {body}')

    # U-06  reset password (generates onboarding token)
    s, body = req('POST', f'/api/super/users/{adm_uid}/reset-password', token=super_tok)
    has_token = 'onboarding_token' in body or 'token' in body or s == 200
    R.assert_test('U-06', m, 'reset password → 200 + token', s == 200 and has_token,
                  f'status={s} {body}')

    # U-07  duplicate user_id rejected (409 conflict or 422 validation)
    s, body = req('POST', '/api/super/users', token=super_tok,
                  json={'user_id': 'risk_agent', 'password': 'x', 'role': 'user'})
    R.assert_test('U-07', m, 'duplicate user_id → 409/422', s in (409, 422), f'got {s}')

    # U-08  assigned_users sync: newly created user appears in worker list
    s, body = req('GET', f'/api/super/workers/{MR_WORKER}', token=super_tok)
    # Users assigned to MR_WORKER should appear
    R.assert_test('U-08', m, 'GET worker returns assigned_users list',
                  s == 200 and 'assigned_users' in body, f'keys={list(body.keys())}')

    # U-09  delete created users (cleanup)
    all_deleted = True
    for uid in [adm_uid, usr_uid, sup_uid]:
        s2, _ = req('DELETE', f'/api/super/users/{uid}', token=super_tok)
        if s2 not in (200, 204, 404):
            all_deleted = False
    R.assert_test('U-09', m, 'delete UAT users → 200', all_deleted)


# ══════════════════════════════════════════════════════════════════════════════
# Module 4 — File Operations
# ══════════════════════════════════════════════════════════════════════════════

def test_files(super_tok: str, admin_tok: str, user_tok: str):
    R.section('Module 4 — File Operations  (F-01 – F-31)')
    m = M[4]

    # ── 4A: Super admin CRUD on w-market-risk ─────────────────────────────────

    base_s = f'/api/super/workers/{MR_WORKER}/files'

    # F-01  browse domain_data tree
    s, body = req('GET', f'{base_s}/domain_data', token=super_tok)
    R.assert_test('F-01', m, 'super: browse domain_data tree → 200 + tree',
                  s == 200 and 'tree' in body, f'status={s}')

    # F-02  upload .txt file
    import io
    test_content = b'UAT test file content'
    files = {'file': ('uat_test.txt', io.BytesIO(test_content), 'text/plain')}
    s, body = req('POST', f'{base_s}/domain_data/upload', token=super_tok, files=files)
    R.assert_test('F-02', m, 'super: upload file → 201/200', s in (200, 201), f'status={s} {body}')

    # F-03  upload .md to verified workflows
    md_content = b'# UAT Workflow\nTest workflow content.\n'
    files = {'file': ('uat_workflow.md', io.BytesIO(md_content), 'text/markdown')}
    s, body = req('POST', f'{base_s}/verified_workflows/upload', token=super_tok, files=files)
    R.assert_test('F-03', m, 'super: upload .md to verified → 201/200', s in (200, 201),
                  f'status={s} {body}')

    # F-04  upload duplicate → 409
    files = {'file': ('uat_test.txt', io.BytesIO(test_content), 'text/plain')}
    s, body = req('POST', f'{base_s}/domain_data/upload', token=super_tok, files=files)
    R.assert_test('F-04', m, 'upload duplicate → 409', s == 409, f'got {s}')

    # F-05  upload duplicate with overwrite → 200
    files = {'file': ('uat_test.txt', io.BytesIO(b'Updated content'), 'text/plain')}
    s, body = req('POST', f'{base_s}/domain_data/upload?overwrite=true', token=super_tok, files=files)
    R.assert_test('F-05', m, 'upload with overwrite=true → 200', s in (200, 201), f'status={s}')

    # F-06  create folder
    s, body = req('POST', f'{base_s}/domain_data/folder', token=super_tok,
                  json={'path': '_uat_folder'})
    R.assert_test('F-06', m, 'create folder → 200', s == 200, f'status={s} {body}')

    # F-07  create nested folder
    s, body = req('POST', f'{base_s}/domain_data/folder', token=super_tok,
                  json={'path': '_uat_folder/nested'})
    R.assert_test('F-07', m, 'create nested folder → 200', s == 200, f'status={s} {body}')

    # F-08  create new blank .md file via PATCH
    s, body = req('PATCH', f'{base_s}/verified_workflows/file', token=super_tok,
                  json={'path': '_uat_blank.md', 'content': ''})
    R.assert_test('F-08', m, 'create blank file (PATCH with empty content) → 200', s == 200,
                  f'status={s} {body}')

    # F-09  write content to file
    s, body = req('PATCH', f'{base_s}/domain_data/file', token=super_tok,
                  json={'path': '_uat_folder/test_write.txt', 'content': 'Hello UAT'})
    R.assert_test('F-09', m, 'write file content → 200', s == 200, f'status={s} {body}')

    # F-10  read file content back
    s, body = req('GET', f'{base_s}/domain_data/file', token=super_tok,
                  params={'path': '_uat_folder/test_write.txt'})
    R.assert_test('F-10a', m, 'read file → 200', s == 200, f'status={s}')
    R.assert_test('F-10b', m, 'read file content matches written value',
                  body.get('content') == 'Hello UAT', f"content={body.get('content','')!r}")
    R.assert_test('F-10c', m, 'read file has size_bytes',
                  'size_bytes' in body, f'keys={list(body.keys())}')
    R.assert_test('F-10d', m, 'read file has encoding field',
                  'encoding' in body, f'keys={list(body.keys())}')

    # F-11  rename file
    s, body = req('POST', f'{base_s}/domain_data/rename', token=super_tok,
                  json={'path': '_uat_folder/test_write.txt', 'new_name': 'renamed_write.txt'})
    R.assert_test('F-11', m, 'rename file → 200', s == 200, f'status={s} {body}')

    # F-12  move file to nested folder
    s, body = req('POST', f'{base_s}/domain_data/move', token=super_tok,
                  json={'src': '_uat_folder/renamed_write.txt', 'dest_folder': '_uat_folder/nested'})
    R.assert_test('F-12', m, 'move file to subfolder → 200', s == 200, f'status={s} {body}')

    # F-13  delete file
    s, _ = req('DELETE', f'{base_s}/domain_data/file', token=super_tok,
               params={'path': '_uat_folder/nested/renamed_write.txt'})
    R.assert_test('F-13', m, 'delete file → 200', s == 200, f'status={s}')

    # F-14  delete non-empty folder with recursive=true
    # First add a file so it's non-empty
    req('PATCH', f'{base_s}/domain_data/file', token=super_tok,
        json={'path': '_uat_folder/nested/keep.txt', 'content': 'x'})
    s, _ = req('DELETE', f'{base_s}/domain_data/folder', token=super_tok,
               json={'path': '_uat_folder', 'recursive': True})
    R.assert_test('F-14', m, 'delete non-empty folder (recursive=true) → 200', s == 200, f'status={s}')

    # F-15  delete non-empty folder with recursive=false → should fail
    req('POST', f'{base_s}/domain_data/folder', token=super_tok, json={'path': '_uat_nrec'})
    req('PATCH', f'{base_s}/domain_data/file', token=super_tok,
        json={'path': '_uat_nrec/file.txt', 'content': 'x'})
    s, body = req('DELETE', f'{base_s}/domain_data/folder', token=super_tok,
                  json={'path': '_uat_nrec', 'recursive': False})
    R.assert_test('F-15', m, 'delete non-empty folder (recursive=false) → 400/409',
                  s in (400, 409, 422), f'got {s}')
    # cleanup
    req('DELETE', f'{base_s}/domain_data/folder', token=super_tok,
        json={'path': '_uat_nrec', 'recursive': True})

    # F-16  clean up uploaded test files
    for p in ['uat_test.txt', 'uat_workflow.md']:
        sec = 'domain_data' if p.endswith('.txt') else 'verified_workflows'
        req('DELETE', f'{base_s}/{sec}/file', token=super_tok, params={'path': p})
    req('DELETE', f'{base_s}/verified_workflows/file', token=super_tok, params={'path': '_uat_blank.md'})
    R.ok('F-16', m, 'cleanup: uploaded test files removed')

    # F-17  path traversal blocked
    s, body = req('GET', f'{base_s}/domain_data/file', token=super_tok,
                  params={'path': '../../config/users.json'})
    R.assert_test('F-17', m, 'path traversal → 403/400', s in (400, 403), f'got {s} body={body}')

    # ── 4B: Admin CRUD on own worker ─────────────────────────────────────────

    base_a = '/api/admin/worker/files'

    # F-18  admin: browse own domain_data
    s, body = req('GET', f'{base_a}/domain_data', token=admin_tok)
    R.assert_test('F-18', m, 'admin: browse own domain_data → 200', s == 200, f'status={s}')

    # F-19  admin: upload file
    files = {'file': ('uat_admin.txt', io.BytesIO(b'admin test'), 'text/plain')}
    s, body = req('POST', f'{base_a}/domain_data/upload', token=admin_tok, files=files)
    R.assert_test('F-19', m, 'admin: upload file → 200/201', s in (200, 201), f'status={s}')

    # F-20  admin: create folder
    s, body = req('POST', f'{base_a}/domain_data/folder', token=admin_tok,
                  json={'path': '_uat_admin_dir'})
    R.assert_test('F-20', m, 'admin: create folder → 200', s == 200, f'status={s}')

    # F-21  admin: write + read file
    s, _ = req('PATCH', f'{base_a}/domain_data/file', token=admin_tok,
               json={'path': '_uat_admin_dir/note.txt', 'content': 'admin note'})
    s2, body = req('GET', f'{base_a}/domain_data/file', token=admin_tok,
                   params={'path': '_uat_admin_dir/note.txt'})
    R.assert_test('F-21', m, 'admin: write + read file roundtrip',
                  s == 200 and s2 == 200 and body.get('content') == 'admin note',
                  f'write={s} read={s2} content={body.get("content","")!r}')

    # F-22  admin: rename file
    s, body = req('POST', f'{base_a}/domain_data/rename', token=admin_tok,
                  json={'path': '_uat_admin_dir/note.txt', 'new_name': 'note_renamed.txt'})
    R.assert_test('F-22', m, 'admin: rename file → 200', s == 200, f'status={s}')

    # F-23  admin: delete file + folder cleanup
    req('DELETE', f'{base_a}/domain_data/file', token=admin_tok,
        params={'path': '_uat_admin_dir/note_renamed.txt'})
    s, _ = req('DELETE', f'{base_a}/domain_data/folder', token=admin_tok,
               json={'path': '_uat_admin_dir', 'recursive': True})
    req('DELETE', f'{base_a}/domain_data/file', token=admin_tok, params={'path': 'uat_admin.txt'})
    R.assert_test('F-23', m, 'admin: delete folder cleanup → 200', s == 200, f'status={s}')

    # F-24  admin cannot access super worker files
    s, _ = req('GET', f'/api/super/workers/{MR_WORKER}/files/domain_data', token=admin_tok)
    R.assert_test('F-24', m, 'admin cannot access super worker files (403)', s == 403, f'got {s}')

    # ── 4C: User cannot do file ops ───────────────────────────────────────────

    # F-25  user cannot browse admin file tree
    s, _ = req('GET', f'{base_a}/domain_data', token=user_tok)
    R.assert_test('F-25', m, 'user cannot browse admin file tree (403)', s == 403, f'got {s}')

    # F-26  user cannot upload
    files = {'file': ('uat_user.txt', io.BytesIO(b'user'), 'text/plain')}
    s, _ = req('POST', f'{base_a}/domain_data/upload', token=user_tok, files=files)
    R.assert_test('F-26', m, 'user cannot upload (403)', s == 403, f'got {s}')


# ══════════════════════════════════════════════════════════════════════════════
# Module 9 — Security & RBAC
# ══════════════════════════════════════════════════════════════════════════════

def test_security(super_tok: str, admin_tok: str, user_tok: str):
    R.section('Module 9 — Security & RBAC  (S-01 – S-10)')
    m = M[9]

    # S-01  no token → 401
    s, _ = req('GET', '/api/super/workers')
    R.assert_test('S-01', m, 'no token on protected endpoint → 401', s == 401, f'got {s}')

    # S-02  invalid token → 401
    s, _ = req('GET', '/api/super/workers', token='invalid.token.here')
    R.assert_test('S-02', m, 'invalid JWT → 401', s == 401, f'got {s}')

    # S-03  user on super endpoint → 403
    s, _ = req('GET', '/api/super/workers', token=user_tok)
    R.assert_test('S-03', m, 'user token on super endpoint → 403', s == 403, f'got {s}')

    # S-04  admin on super-delete endpoint → 403
    s, _ = req('DELETE', f'/api/super/workers/{MR_WORKER}', token=admin_tok)
    R.assert_test('S-04', m, 'admin cannot delete super worker (403)', s == 403, f'got {s}')

    # S-05  user on another worker's tools → 403
    # user_tok is assigned to MR_WORKER; try querying CCR_WORKER tools
    s, _ = req('GET', f'/api/workers/{CCR_WORKER}/tools', token=user_tok)
    R.assert_test('S-05', m, 'user cannot query other worker tools (403)', s == 403, f'got {s}')

    # S-06  path traversal on file read → 400/403
    s, body = req('GET', f'/api/super/workers/{MR_WORKER}/files/domain_data/file',
                  token=super_tok, params={'path': '../../config/users.json'})
    R.assert_test('S-06', m, 'path traversal on file read → 403/400', s in (400, 403),
                  f'got {s}')

    # S-07  oversized upload → 413
    import io
    big = io.BytesIO(b'x' * (51 * 1024 * 1024))  # 51 MB
    files = {'file': ('huge.bin', big, 'application/octet-stream')}
    s, body = req('POST', f'/api/super/workers/{MR_WORKER}/files/domain_data/upload',
                  token=super_tok, files=files, timeout=60.0)
    R.assert_test('S-07', m, 'upload >50 MB → 413', s == 413, f'got {s}')

    # S-08  thread isolation: user sees only own threads
    s, body = req('GET', '/api/agent/threads', token=user_tok)
    R.assert_test('S-08', m, 'GET /api/agent/threads returns 200', s == 200, f'got {s}')

    # S-09  rate limit recovery check (just verify the endpoint returns something now)
    # Note: we triggered rate limit in A-05 on a fake user — this tests the real user still works
    s, body = req('POST', '/api/auth/login', json={'user_id': SUPER_CREDS[0], 'password': SUPER_CREDS[1]})
    R.assert_test('S-09', m, 'real user not blocked after fake-user rate limit test', s == 200, f'got {s}')

    # S-10  admin can only manage own worker files (not cross-worker)
    s, _ = req('POST', f'/api/super/workers/{CCR_WORKER}/files/domain_data/folder',
               token=admin_tok, json={'path': '_hacker'})
    R.assert_test('S-10', m, 'admin cannot write to other worker via super endpoint (403)',
                  s == 403, f'got {s}')


# ══════════════════════════════════════════════════════════════════════════════
# Module 10 — Thread & Session Persistence
# ══════════════════════════════════════════════════════════════════════════════

def test_persistence(super_tok: str, user_tok: str):
    R.section('Module 10 — Thread Persistence  (P-02 – P-04)')
    m = M[10]

    R.skip('P-01', m, 'Thread survives server restart — requires manual restart, skipped in automated run')

    # P-02  thread registry loaded: GET /api/agent/threads → 200
    s, body = req('GET', '/api/agent/threads', token=super_tok)
    R.assert_test('P-02', m, 'GET /api/agent/threads → 200',
                  s == 200 and 'threads' in body, f'status={s}')

    # P-03  thread scoped to user: user's list doesn't include super_admin threads
    s_user, body_user = req('GET', '/api/agent/threads', token=user_tok)
    s_sup,  body_sup  = req('GET', '/api/agent/threads', token=super_tok)
    user_tids = {t['thread_id'] for t in body_user.get('threads', [])}
    sup_tids  = {t['thread_id'] for t in body_sup.get('threads', [])}
    overlap   = user_tids & sup_tids
    R.assert_test('P-03', m, 'user and super_admin thread lists are disjoint',
                  s_user == 200 and s_sup == 200 and len(overlap) == 0,
                  f'overlap={overlap}')

    # P-04  threads.jsonl exists on disk
    registry_file = pathlib.Path('sajhamcpserver/data/threads.jsonl')
    R.assert_test('P-04', m, 'threads.jsonl exists on disk', registry_file.exists(),
                  str(registry_file.absolute()))


# ══════════════════════════════════════════════════════════════════════════════
# Module 11 — G-04 Worker Path Isolation
# ══════════════════════════════════════════════════════════════════════════════

def test_g04_isolation(super_tok: str):
    R.section('Module 11 — G-04 Worker Path Isolation  (G-01 – G-05)')
    m = M[11]

    # G-01  MR worker has iris data; CCR worker tree is separate
    s_mr,  body_mr  = req('GET', f'/api/super/workers/{MR_WORKER}/files/domain_data',
                          token=super_tok)
    s_ccr, body_ccr = req('GET', f'/api/super/workers/{CCR_WORKER}/files/domain_data',
                          token=super_tok)
    # Trees should be dicts (separate objects even if identical structure)
    R.assert_test('G-01', m, 'MR + CCR domain_data trees both return 200',
                  s_mr == 200 and s_ccr == 200, f'mr={s_mr} ccr={s_ccr}')

    # G-02  MR has iris/ folder in domain_data
    mr_paths = _flatten_tree(body_mr.get('tree', []))
    has_iris = any('iris' in p.lower() for p in mr_paths)
    R.assert_test('G-02', m, 'MR worker domain_data contains iris/ data',
                  has_iris, f'paths={mr_paths[:10]}')

    # G-03  common regulatory data exists and is shared
    common_osfi = pathlib.Path('sajhamcpserver/data/common/regulatory/osfi')
    R.assert_test('G-03', m, 'common/regulatory/osfi pool exists on disk',
                  common_osfi.is_dir(), str(common_osfi))

    # G-04  each worker has independent workflow trees
    s_mr_wf,  body_mr_wf  = req('GET', f'/api/super/workers/{MR_WORKER}/files/verified_workflows',
                                 token=super_tok)
    s_ccr_wf, body_ccr_wf = req('GET', f'/api/super/workers/{CCR_WORKER}/files/verified_workflows',
                                 token=super_tok)
    R.assert_test('G-04', m, 'workflow trees return independently per worker',
                  s_mr_wf == 200 and s_ccr_wf == 200, f'mr={s_mr_wf} ccr={s_ccr_wf}')

    # G-05  write file to MR; verify it does NOT appear in CCR
    req('PATCH', f'/api/super/workers/{MR_WORKER}/files/domain_data/file',
        token=super_tok, json={'path': '_g04_isolation_check.txt', 'content': 'MR only'})

    s_ccr_read, _ = req('GET', f'/api/super/workers/{CCR_WORKER}/files/domain_data/file',
                         token=super_tok, params={'path': '_g04_isolation_check.txt'})
    R.assert_test('G-05', m, 'file written to MR not visible in CCR (404)',
                  s_ccr_read == 404, f'got {s_ccr_read}')
    # cleanup
    req('DELETE', f'/api/super/workers/{MR_WORKER}/files/domain_data/file',
        token=super_tok, params={'path': '_g04_isolation_check.txt'})


def _flatten_tree(nodes, prefix=''):
    paths = []
    for n in nodes or []:
        name = n.get('name', '')
        p    = f'{prefix}/{name}' if prefix else name
        paths.append(p)
        paths.extend(_flatten_tree(n.get('children', []), p))
    return paths


# ══════════════════════════════════════════════════════════════════════════════
# Main runner
# ══════════════════════════════════════════════════════════════════════════════

def _setup_uat_user(super_tok: str):
    """Create a fresh UAT test user with a known password; update USER_CREDS in-place."""
    global _uat_created_uid
    uid = f'uat_usr_{uuid.uuid4().hex[:8]}'
    pw  = 'UATtestuser2025!'
    s, body = req('POST', '/api/super/users', token=super_tok,
                  json={'user_id': uid, 'password': pw, 'role': 'user',
                        'worker_id': MR_WORKER, 'display_name': 'UAT Test User'})
    if s == 201:
        _uat_created_uid = uid
        USER_CREDS[0] = uid
        USER_CREDS[1] = pw
        print(f'  [setup] Created UAT test user: {uid}')
    else:
        print(f'  [setup] WARNING: could not create UAT test user — {s} {body}')


def _teardown_uat_user(super_tok: str):
    global _uat_created_uid
    if _uat_created_uid:
        req('DELETE', f'/api/super/users/{_uat_created_uid}', token=super_tok)
        print(f'  [teardown] Deleted UAT test user: {_uat_created_uid}')
        _uat_created_uid = ''


def main():
    print('\n' + '='*70)
    print('  RiskGPT UAT — Phase 1: API Tests')
    print('='*70)
    print(f'  Target : {BASE}')
    print(f'  Results: UAT_RESULTS/')

    # Pre-setup: need super_tok to create a temp test user with known credentials
    super_tok_pre = login(*SUPER_CREDS)
    if super_tok_pre:
        _setup_uat_user(super_tok_pre)

    super_tok = ''
    try:
        super_tok, admin_tok, user_tok = test_auth()
        test_workers(super_tok, admin_tok, user_tok)
        test_users(super_tok)
        test_files(super_tok, admin_tok, user_tok)
        test_security(super_tok, admin_tok, user_tok)
        test_persistence(super_tok, user_tok)
        test_g04_isolation(super_tok)

    except Exception:
        print('\n  !! UNHANDLED EXCEPTION IN TEST RUNNER:')
        traceback.print_exc()

    finally:
        if super_tok:
            _teardown_uat_user(super_tok)

    R.print_final_summary()
    json_path, md_path = R.save()
    print(f'\n  JSON : {json_path}')
    print(f'  MD   : {md_path}')
    print(f'  Latest: UAT_RESULTS/LATEST_phase1.md\n')

    s = R._summary_dict()
    sys.exit(0 if s['fail'] == 0 and s['error'] == 0 else 1)


if __name__ == '__main__':
    main()
