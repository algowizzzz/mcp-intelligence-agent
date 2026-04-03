import urllib.request, urllib.error, json, sys, time, os, uuid, pathlib, base64

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'
RESULTS = []

def req(method, path, body=None, token=None, api_key=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {'Content-Type': 'application/json'}
    if token:   headers['Authorization'] = f'Bearer {token}'
    if api_key: headers['Authorization'] = f'Bearer {api_key}'
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            try: return resp.status, json.loads(raw)
            except: return resp.status, {'_text': raw.decode('utf-8', errors='replace')}
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as ex:
        return 0, {'_error': str(ex)}

def login(user_id, password):
    s, d = req('POST', '/api/auth/login', {'user_id': user_id, 'password': password})
    return d.get('token'), d.get('role'), d

def check(name, cond, detail=''):
    RESULTS.append((cond, name))
    icon = '✅' if cond else '❌'
    suffix = f' — {detail}' if detail and not cond else ''
    print(f'  {icon} {name}{suffix}')

def section(title):
    print(f'\n{"─"*50}')
    print(f' {title}')
    print(f'{"─"*50}')

def decode_jwt(token):
    parts = token.split('.')
    pad = parts[1] + '=' * (4 - len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(pad))

# ── Section 1: Infrastructure ────────────────────────────────────────────────
section('1. INFRASTRUCTURE')
s, d = req('GET', '/health')
check('Server reachable', s == 200)
check('/health returns ok', d.get('status') == 'ok')

for page in ['/login.html', '/admin.html', '/mcp-agent.html']:
    s, _ = req('GET', page)
    check(f'Static file served: {page}', s == 200, f'got {s} — nginx static serving required')

try:
    urllib.request.urlopen('http://localhost:3002/api/tools/list', timeout=2)
    check('SAJHA port 3002 NOT externally reachable', False, 'port 3002 open — must bind to 127.0.0.1')
except:
    check('SAJHA port 3002 NOT externally reachable', True)

# ── Section 2: Authentication ────────────────────────────────────────────────
section('2. AUTHENTICATION')
sa_tok, sa_role, sa_data = login('risk_agent', 'RiskAgent2025!')
check('super_admin login returns 200', sa_tok is not None)
check('super_admin role correct', sa_role == 'super_admin')
check('super_admin onboarding_complete=true', sa_data.get('onboarding_complete') == True)
check('super_admin has worker_id', sa_data.get('worker_id') is not None)
check('super_admin has worker_name', bool(sa_data.get('worker_name')))

adm_tok, adm_role, adm_data = login('admin', 'admin123')
check('admin login returns 200', adm_tok is not None)
check('admin role correct', adm_role == 'admin')
check('admin has worker_id w-market-risk', adm_data.get('worker_id') == 'w-market-risk')

usr_tok, usr_role, usr_data = login('test_user', 'TestUser2025!')
check('user login returns 200', usr_tok is not None)
check('user role correct', usr_role == 'user')

s, _ = req('POST', '/api/auth/login', {'user_id': 'risk_agent', 'password': 'wrongpass'})
check('Wrong password returns 401', s == 401)
s, _ = req('POST', '/api/auth/login', {'user_id': 'nobody', 'password': 'x'})
check('Unknown user returns 401', s == 401)
s, _ = req('POST', '/api/auth/login', {'user_id': '', 'password': ''})
check('Empty credentials returns 400 or 401', s in [400, 401])

if sa_tok:
    claims = decode_jwt(sa_tok)
    check('JWT has user_id', 'user_id' in claims)
    check('JWT has role', claims.get('role') == 'super_admin')
    check('JWT has worker_id', 'worker_id' in claims)
    check('JWT has exp in future', claims.get('exp', 0) > time.time())

s, d = req('GET', '/api/auth/me', token=sa_tok)
check('/api/auth/me returns 200 with valid JWT', s == 200)
s, _ = req('GET', '/api/auth/me')
check('/api/auth/me returns 401 with no token', s == 401)

# ── Section 3: Role-Based Access Control ────────────────────────────────────
section('3. ROLE-BASED ACCESS CONTROL')

# Super admin endpoints
for path in ['/api/super/workers', '/api/super/users']:
    s, _ = req('GET', path, token=sa_tok); check(f'super_admin: GET {path} → 200', s == 200)
    s, _ = req('GET', path, token=adm_tok); check(f'admin: GET {path} → 403', s == 403)
    s, _ = req('GET', path, token=usr_tok); check(f'user: GET {path} → 403', s == 403)
    s, _ = req('GET', path); check(f'no token: GET {path} → 401', s == 401)

# Admin endpoints
for path in ['/api/admin/worker', '/api/mcp/tools']:
    s, _ = req('GET', path, token=sa_tok); check(f'super_admin: GET {path} → 200', s == 200)
    s, _ = req('GET', path, token=adm_tok); check(f'admin: GET {path} → 200', s == 200)
    s, _ = req('GET', path, token=usr_tok); check(f'user: GET {path} → 403', s == 403)
    s, _ = req('GET', path); check(f'no token: GET {path} → 401', s == 401)

# Agent run — admin+super_admin only (JWT-based after Phase 1)
tid = str(uuid.uuid4())
s, _ = req('POST', '/api/agent/run', {'query': 'ping', 'thread_id': tid}, token=sa_tok)
check('/api/agent/run: super_admin JWT → allowed', s in [200, 204])
s, _ = req('POST', '/api/agent/run', {'query': 'ping', 'thread_id': str(uuid.uuid4())}, token=adm_tok)
check('/api/agent/run: admin JWT → allowed', s in [200, 204])
s, _ = req('POST', '/api/agent/run', {'query': 'ping', 'thread_id': str(uuid.uuid4())}, token=usr_tok)
check('/api/agent/run: user JWT → 403', s == 403)
s, _ = req('POST', '/api/agent/run', {'query': 'ping'})
check('/api/agent/run: no token → 401', s == 401)

# ── Section 4: Worker Management ────────────────────────────────────────────
section('4. WORKER MANAGEMENT')
s, wd = req('GET', '/api/super/workers', token=sa_tok)
check('GET /api/super/workers returns list', s == 200 and 'workers' in wd)
workers = wd.get('workers', [])
check('w-market-risk worker exists', any(w['worker_id'] == 'w-market-risk' for w in workers))
if workers:
    w = workers[0]
    check('Worker has non-empty system_prompt', len(w.get('system_prompt', '')) > 100)
    check('Worker has enabled_tools list', len(w.get('enabled_tools', [])) > 0)
    check('Worker has domain_data_path', bool(w.get('domain_data_path')))
    check('Worker has workflows_path', bool(w.get('workflows_path')))

s, aw = req('GET', '/api/admin/worker', token=adm_tok)
check('admin GET /api/admin/worker → 200', s == 200)
check('admin worker has system_prompt', len(aw.get('system_prompt', '')) > 0)

s, _ = req('PUT', '/api/super/workers/w-market-risk', {'name': 'Hack'}, token=adm_tok)
check('admin cannot PUT /api/super/workers/* → 403', s == 403)

# ── Section 5: User Management ───────────────────────────────────────────────
section('5. USER MANAGEMENT')
s, ud = req('GET', '/api/super/users', token=sa_tok)
check('GET /api/super/users returns list', s == 200 and 'users' in ud)
check('At least 2 users exist', len(ud.get('users', [])) >= 2)
s, _ = req('GET', '/api/super/users', token=adm_tok)
check('admin blocked from /api/super/users → 403', s == 403)

new_uid = f'tmp_{uuid.uuid4().hex[:6]}'
s, nu = req('POST', '/api/super/users', {
    'user_id': new_uid, 'password': 'TmpPass2025!',
    'display_name': 'Tmp', 'role': 'user',
    'worker_id': 'w-market-risk', 'enabled': True
}, token=sa_tok)
check(f'super_admin can create user', s in [200, 201])
if s in [200, 201]:
    t2, r2, _ = login(new_uid, 'TmpPass2025!')
    check('New user can log in immediately (no SAJHA restart)', t2 is not None)
    req('DELETE', f'/api/super/users/{new_uid}', token=sa_tok)

# ── Section 6: Tools ─────────────────────────────────────────────────────────
section('6. TOOLS')
s, td = req('GET', '/api/mcp/tools', token=sa_tok)
check('GET /api/mcp/tools returns list', s == 200 and 'tools' in td)
tools = td.get('tools', [])
check('80+ tools returned', len(tools) >= 80)
for t in ['tavily_web_search','get_counterparty_exposure','iris_counterparty_dashboard',
          'edgar_company_brief','osfi_list_docs','workflow_list','duckdb_sql','md_save']:
    check(f'Tool exists: {t}', any(x['name'] == t for x in tools))

# ── Section 7: File Management ───────────────────────────────────────────────
section('7. FILE MANAGEMENT')
for section_name, label in [('domain_data','Domain Data'),('verified_workflows','Workflows')]:
    s, tree = req('GET', f'/api/admin/tree/{section_name}', token=sa_tok)
    check(f'{label}: tree loads (super_admin)', s == 200)
    check(f'{label}: has items', len(tree.get('tree', [])) > 0)
    s, _ = req('GET', f'/api/admin/tree/{section_name}', token=adm_tok)
    check(f'{label}: tree loads (admin)', s == 200)
    s, _ = req('GET', f'/api/admin/tree/{section_name}', token=usr_tok)
    check(f'{label}: user blocked → 403', s == 403)

fn = f'test_{uuid.uuid4().hex[:6]}'
s, _ = req('POST', '/api/admin/folder', {'section': 'domain_data', 'path': fn}, token=sa_tok)
check('Create folder', s == 200)
s, _ = req('PATCH', '/api/admin/rename', {'section': 'domain_data', 'path': fn, 'new_name': fn+'_r'}, token=sa_tok)
check('Rename folder', s == 200)
s, _ = req('DELETE', '/api/admin/item', {'section': 'domain_data', 'path': fn+'_r', 'recursive': True}, token=sa_tok)
check('Delete folder', s == 200)

wf = f'test_{uuid.uuid4().hex[:6]}.md'
s, _ = req('POST', '/api/admin/file', {'section': 'verified_workflows', 'filename': wf, 'folder': ''}, token=adm_tok)
check('Admin creates workflow', s == 200)
s, fc = req('GET', f'/api/admin/file?section=verified_workflows&path={wf}', token=adm_tok)
check('Admin reads workflow (text response)', s == 200)
s, _ = req('DELETE', '/api/admin/item', {'section': 'verified_workflows', 'path': wf, 'recursive': False}, token=adm_tok)
check('Admin deletes workflow', s == 200)

# ── Section 8: Password Security ─────────────────────────────────────────────
section('8. PASSWORD SECURITY')
uf = pathlib.Path('sajhamcpserver/config/users.json')
if uf.exists():
    ucfg = json.loads(uf.read_text()).get('users', [])
    for u in ucfg:
        uid = u['user_id']
        check(f'{uid}: has password_hash ($2b$)', u.get('password_hash','').startswith('$2b$'))
        check(f'{uid}: no plaintext password field', not u.get('password',''))
    check('All users have password_hash', all(u.get('password_hash','').startswith('$2b$') for u in ucfg))

# ── Section 9: Frontend Hygiene ───────────────────────────────────────────────
section('9. FRONTEND CREDENTIAL HYGIENE')
for fname in ['public/mcp-agent.html', 'public/admin.html', 'public/login.html']:
    fp = pathlib.Path(fname)
    if fp.exists():
        c = fp.read_text()
        name = fp.name
        check(f'{name}: no hardcoded risk_agent', 'risk_agent' not in c)
        check(f'{name}: no hardcoded RiskAgent2025!', 'RiskAgent2025!' not in c)
        check(f'{name}: no hardcoded admin123', 'admin123' not in c)

# ── Section 10: Onboarding ────────────────────────────────────────────────────
section('10. ONBOARDING FLOW')
ob_uid = f'ob_{uuid.uuid4().hex[:6]}'
s, _ = req('POST', '/api/super/users', {
    'user_id': ob_uid, 'password': 'ObPass2025!',
    'display_name': 'OnboardMe', 'role': 'user',
    'worker_id': 'w-market-risk', 'enabled': True
}, token=sa_tok)
if s in [200, 201]:
    ob_tok, _, ob_d = login(ob_uid, 'ObPass2025!')
    check('New user: onboarding_complete=false', ob_d.get('onboarding_complete') == False)
    if ob_tok:
        s, _ = req('POST', '/api/auth/onboarding', {
            'display_name': 'Done', 'new_password': 'NewOb2025!', 'confirm_password': 'NewOb2025!'
        }, token=ob_tok)
        check('Onboarding endpoint returns 200', s == 200)
        ob_tok2, _, ob_d2 = login(ob_uid, 'NewOb2025!')
        check('Post-onboarding login with new password', ob_tok2 is not None)
        check('Post-onboarding: onboarding_complete=true', ob_d2.get('onboarding_complete') == True)
    req('DELETE', f'/api/super/users/{ob_uid}', token=sa_tok)

# ── Section 11: Worker Config Updates ─────────────────────────────────────────
section('11. WORKER CONFIG UPDATES')
s, w_before = req('GET', '/api/admin/worker', token=sa_tok)
orig_prompt = w_before.get('system_prompt','')
s, _ = req('PUT', '/api/admin/worker/prompt', {'system_prompt': '__test_prompt__'}, token=sa_tok)
check('super_admin updates system_prompt → 200', s == 200)
s, w_after = req('GET', '/api/admin/worker', token=sa_tok)
check('system_prompt change persisted', w_after.get('system_prompt') == '__test_prompt__')
req('PUT', '/api/admin/worker/prompt', {'system_prompt': orig_prompt}, token=sa_tok)

s, _ = req('PUT', '/api/admin/worker/tools', {'enabled_tools': ['tavily_web_search']}, token=adm_tok)
check('admin updates enabled_tools → 200', s == 200)
s, w2 = req('GET', '/api/admin/worker', token=adm_tok)
check('enabled_tools change persisted', w2.get('enabled_tools') == ['tavily_web_search'])
req('PUT', '/api/admin/worker/tools', {'enabled_tools': ['*']}, token=sa_tok)

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for r in RESULTS if r[0])
total = len(RESULTS)
print(f'\n{"═"*50}')
print(f' FINAL: {passed}/{total} passed   {total-passed} failed')
print(f'{"═"*50}')
fails = [r for r in RESULTS if not r[0]]
if fails:
    print('\nFailed:')
    for _, name in fails:
        print(f'  ❌ {name}')
sys.exit(0 if passed == total else 1)
