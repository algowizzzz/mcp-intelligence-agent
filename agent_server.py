import os, json, uuid, pathlib, base64, sys as _sys, hmac, hashlib, time, shutil
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
import httpx
from agent.agent import agent
from agent.tools import _get_token, SAJHA_BASE

_WORKFLOWS_DIR = pathlib.Path('sajhamcpserver/data/workflows')
_UPLOADS_DIR   = pathlib.Path('sajhamcpserver/data/uploads')
_METADATA_FILE = _WORKFLOWS_DIR / '.metadata.json'

_sys.path.insert(0, str(pathlib.Path(__file__).parent / 'sajhamcpserver'))
from sajha.tools.impl.fs_index import build_index, get_index

_JWT_SECRET = os.getenv('JWT_SECRET', 'sajha-dev-secret-change-in-prod')
_SAJHA_USERS_FILE  = pathlib.Path('sajhamcpserver/config/users.json')
_SAJHA_WORKERS_FILE = pathlib.Path('sajhamcpserver/config/workers.json')


# ── JWT helpers ────────────────────────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += '=' * pad
    return base64.urlsafe_b64decode(s)


def _jwt_encode(payload: dict) -> str:
    header = _b64url_encode(b'{"alg":"HS256","typ":"JWT"}')
    body = _b64url_encode(json.dumps(payload).encode())
    sig_input = f"{header}.{body}".encode()
    sig = hmac.new(_JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def _jwt_decode(token: str) -> dict:
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    header, body, sig = parts
    sig_input = f"{header}.{body}".encode()
    expected = hmac.new(_JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    provided = _b64url_decode(sig)
    if not hmac.compare_digest(expected, provided):
        raise ValueError("Invalid JWT signature")
    payload = json.loads(_b64url_decode(body))
    if payload.get('exp', float('inf')) < time.time():
        raise ValueError("JWT expired")
    return payload


# ── Users & Workers persistence ────────────────────────────────────────────────

def _load_users() -> list:
    try:
        return json.loads(_SAJHA_USERS_FILE.read_text()).get('users', [])
    except Exception:
        return []


def _save_users(users: list):
    _SAJHA_USERS_FILE.write_text(json.dumps({'users': users}, indent=2))


def _find_user(user_id: str) -> Optional[dict]:
    for u in _load_users():
        if u.get('user_id') == user_id:
            return u
    return None


def _load_workers() -> list:
    try:
        return json.loads(_SAJHA_WORKERS_FILE.read_text()).get('workers', [])
    except Exception:
        return []


def _save_workers(workers: list):
    _SAJHA_WORKERS_FILE.write_text(json.dumps({'workers': workers}, indent=2))


def _find_worker(worker_id: str) -> Optional[dict]:
    for w in _load_workers():
        if w.get('worker_id') == worker_id:
            return w
    return None


def _verify_password(plain: str, user: dict) -> bool:
    """Check password against hash (bcrypt if available) or plaintext fallback."""
    stored_hash = user.get('password_hash', '')
    if stored_hash:
        try:
            import bcrypt
            return bcrypt.checkpw(plain.encode(), stored_hash.encode())
        except Exception:
            pass
    # Plaintext fallback (migration period)
    return plain == user.get('password', '')


def _hash_password(plain: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()
    except ImportError:
        return ''  # bcrypt not installed — plaintext fallback


def _get_user_role(user: dict) -> str:
    """Return canonical role string from user record."""
    if user.get('role'):
        return user['role']
    roles = user.get('roles', [])
    if 'super_admin' in roles:
        return 'super_admin'
    if 'admin' in roles:
        return 'admin'
    return 'user'


def _resolve_worker_for_user(user: dict, requested_worker_id: str = None) -> Optional[dict]:
    """Return the worker context for a user. Super admins can specify any worker."""
    role = _get_user_role(user)
    if role == 'super_admin':
        wid = requested_worker_id or (user.get('worker_id'))
        if wid:
            return _find_worker(wid)
        # Default to first worker
        workers = _load_workers()
        return workers[0] if workers else None
    else:
        wid = user.get('worker_id')
        return _find_worker(wid) if wid else None


def _seed_worker_folders(worker_id: str):
    """Create the folder structure for a new worker."""
    base = pathlib.Path(f'sajhamcpserver/data/workers/{worker_id}')
    for sub in ['domain_data/iris', 'domain_data/osfi', 'domain_data/counterparties',
                'domain_data/analytics', 'domain_data/templates',
                'workflows/verified', 'my_data']:
        (base / sub).mkdir(parents=True, exist_ok=True)


load_dotenv()

_DATA_ROOT     = pathlib.Path('sajhamcpserver/data')
_DOMAIN_DATA   = _DATA_ROOT / 'domain_data'
_MY_DATA       = _DATA_ROOT / 'uploads'
_VERIFIED_WF   = _DATA_ROOT / 'workflows' / 'verified'
_MY_WF         = _DATA_ROOT / 'workflows' / 'my'

_SECTION_ROOTS = {
    'domain_data':   _DOMAIN_DATA,
    'uploads':       _MY_DATA,
    'verified':      _VERIFIED_WF,
    'my_workflows':  _MY_WF,
}
_WRITABLE_SECTIONS = {'uploads', 'my_workflows'}

_ADMIN_SECTION_ROOTS = {
    'domain_data':        _DOMAIN_DATA,
    'verified_workflows': _VERIFIED_WF,
}


def _resolve_admin_path(section: str, rel: str = '') -> pathlib.Path:
    root = _ADMIN_SECTION_ROOTS.get(section)
    if root is None:
        raise HTTPException(status_code=400, detail=f'Unknown admin section: {section}')
    if rel:
        full = (root / rel).resolve()
        if not str(full).startswith(str(root.resolve())):
            raise HTTPException(status_code=400, detail='Path traversal not allowed')
        return full
    return root


def _admin_section_roots_for_worker(worker: dict) -> dict:
    """Return admin section roots scoped to a worker's paths."""
    base = pathlib.Path('sajhamcpserver')
    dd = base / worker.get('domain_data_path', './data/domain_data').lstrip('./')
    wf = base / worker.get('workflows_path', './data/workflows/verified').lstrip('./')
    return {'domain_data': dd, 'verified_workflows': wf}


def _resolve_admin_path_for_worker(worker: dict, section: str, rel: str = '') -> pathlib.Path:
    roots = _admin_section_roots_for_worker(worker)
    root = roots.get(section)
    if root is None:
        raise HTTPException(status_code=400, detail=f'Unknown admin section: {section}')
    if rel:
        full = (root / rel).resolve()
        if not str(full).startswith(str(root.resolve())):
            raise HTTPException(status_code=400, detail='Path traversal not allowed')
        return full
    return root


# Build indexes on startup
def _build_all_indexes():
    for root in [_DOMAIN_DATA, _MY_DATA, _VERIFIED_WF, _MY_WF]:
        root.mkdir(parents=True, exist_ok=True)
        try:
            build_index(str(root))
        except Exception:
            pass

_build_all_indexes()

app = FastAPI(title='MCP Intelligence Agent')
_cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:8080,http://127.0.0.1:8080').split(',')
# 'null' allows file:// origins in local dev (browser sends Origin: null for file:// pages)
_cors_origins = list({*_cors_origins, 'null', 'http://localhost:8000', 'http://127.0.0.1:8000'})
app.add_middleware(CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r'https://.*\.vercel\.app',
    allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
)

# API key auth — for agent run endpoint
_raw_keys = os.getenv('AGENT_API_KEYS', '')
_VALID_KEYS: set = {k.strip() for k in _raw_keys.split(',') if k.strip()} if _raw_keys else set()

_bearer = HTTPBearer(auto_error=False)


def require_api_key(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    if not _VALID_KEYS:
        return  # auth disabled
    if creds is None or creds.credentials not in _VALID_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or missing API key')


def _decode_bearer(creds: HTTPAuthorizationCredentials | None) -> dict:
    if creds is None:
        raise HTTPException(status_code=401, detail='Missing token')
    try:
        return _jwt_decode(creds.credentials)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


def require_jwt(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    """Require any valid JWT."""
    return _decode_bearer(creds)


def require_admin(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    """Require admin or super_admin role."""
    payload = _decode_bearer(creds)
    role = payload.get('role', '')
    if role not in ('admin', 'super_admin'):
        # Legacy is_admin support
        if not payload.get('is_admin'):
            raise HTTPException(status_code=403, detail='Admin access required')
    return payload


def require_super_admin(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    """Require super_admin role."""
    payload = _decode_bearer(creds)
    if payload.get('role') != 'super_admin':
        raise HTTPException(status_code=403, detail='Super Admin access required')
    return payload


@app.get('/health')
async def health():
    return {'status': 'ok'}


# ── Auth endpoints ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    user_id: str
    password: str

@app.post('/api/auth/login')
async def auth_login(req: LoginRequest):
    """Authenticate user, return JWT with role/worker/onboarding claims."""
    if not req.user_id or not req.password:
        raise HTTPException(status_code=400, detail='user_id and password required')

    # Look up user from users.json first
    user = _find_user(req.user_id)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid credentials')

    # Validate against SAJHA (keeps SAJHA as source of truth for its known users)
    # If SAJHA returns 401, fall back to local users.json verification
    # (covers users created via API that aren't in SAJHA's in-memory cache yet)
    sajha_auth_ok = False
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(
                f'{SAJHA_BASE}/api/auth/login',
                json={'user_id': req.user_id, 'password': req.password},
            )
            if r.status_code == 401:
                # SAJHA doesn't know this user — fall back to local verification
                if not _verify_password(req.password, user):
                    raise HTTPException(status_code=401, detail='Invalid credentials')
            elif not r.is_success:
                r.raise_for_status()
            else:
                sajha_auth_ok = True
    except HTTPException:
        raise
    except Exception as e:
        # SAJHA unreachable — fall back to local verification
        if not _verify_password(req.password, user):
            raise HTTPException(status_code=502, detail=f'SAJHA unreachable: {e}')

    if not user.get('enabled', True):
        raise HTTPException(status_code=403, detail='Account disabled. Contact your administrator.')

    role = _get_user_role(user)
    worker_id = user.get('worker_id')
    worker_name = None
    if worker_id:
        w = _find_worker(worker_id)
        worker_name = w.get('name') if w else None
    elif role == 'super_admin':
        workers = _load_workers()
        if workers:
            worker_id = workers[0]['worker_id']
            worker_name = workers[0].get('name')

    is_admin = role in ('admin', 'super_admin')
    token = _jwt_encode({
        'user_id': req.user_id,
        'role': role,
        'is_admin': is_admin,
        'worker_id': worker_id,
        'display_name': user.get('display_name', user.get('user_name', req.user_id)),
        'avatar_initials': user.get('avatar_initials', req.user_id[:2].upper()),
        'onboarding_complete': user.get('onboarding_complete', True),
        'exp': time.time() + 86400 * 7,
    })

    return {
        'token': token,
        'role': role,
        'is_admin': is_admin,
        'user_id': req.user_id,
        'display_name': user.get('display_name', user.get('user_name', req.user_id)),
        'worker_id': worker_id,
        'worker_name': worker_name,
        'onboarding_complete': user.get('onboarding_complete', True),
    }


@app.get('/api/auth/me')
async def auth_me(payload: dict = Depends(require_jwt)):
    return payload


class OnboardingRequest(BaseModel):
    display_name: str
    new_password: str
    confirm_password: str

@app.post('/api/auth/onboarding')
async def auth_onboarding(req: OnboardingRequest, payload: dict = Depends(require_jwt)):
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail='Passwords do not match')
    if len(req.new_password) < 10:
        raise HTTPException(status_code=400, detail='Password must be at least 10 characters')
    if len(req.display_name.strip()) < 2:
        raise HTTPException(status_code=400, detail='Display name must be at least 2 characters')

    user_id = payload['user_id']
    users = _load_users()
    for u in users:
        if u.get('user_id') == user_id:
            u['display_name'] = req.display_name.strip()
            # Auto-derive initials
            parts = req.display_name.strip().split()
            u['avatar_initials'] = ''.join(p[0].upper() for p in parts[:3])
            u['password'] = req.new_password  # plaintext during transition
            ph = _hash_password(req.new_password)
            if ph:
                u['password_hash'] = ph
            u['onboarding_complete'] = True
            break
    _save_users(users)
    return {'ok': True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@app.post('/api/auth/change-password')
async def auth_change_password(req: ChangePasswordRequest, payload: dict = Depends(require_jwt)):
    if len(req.new_password) < 10:
        raise HTTPException(status_code=400, detail='Password must be at least 10 characters')
    user_id = payload['user_id']
    users = _load_users()
    for u in users:
        if u.get('user_id') == user_id:
            if not _verify_password(req.current_password, u):
                raise HTTPException(status_code=401, detail='Current password is incorrect')
            u['password'] = req.new_password
            ph = _hash_password(req.new_password)
            if ph:
                u['password_hash'] = ph
            break
    _save_users(users)
    return {'ok': True}


# ── Super Admin — Worker Management ──────────────────────────────────────────

@app.get('/api/super/workers')
async def super_list_workers(_: dict = Depends(require_super_admin)):
    workers = _load_workers()
    users = _load_users()
    result = []
    for w in workers:
        wid = w['worker_id']
        admins = [u for u in users if u.get('worker_id') == wid and _get_user_role(u) == 'admin']
        members = [u for u in users if u.get('worker_id') == wid and _get_user_role(u) == 'user']
        result.append({**w, 'admin_count': len(admins), 'user_count': len(members)})
    return {'workers': result}


class WorkerCreateRequest(BaseModel):
    name: str
    description: str = ''
    system_prompt: str = ''
    enabled_tools: list = ['*']
    clone_from: Optional[str] = None

@app.post('/api/super/workers', status_code=201)
async def super_create_worker(req: WorkerCreateRequest, payload: dict = Depends(require_super_admin)):
    wid = f'w-{uuid.uuid4().hex[:8]}'
    new_worker = {
        'worker_id': wid,
        'name': req.name,
        'description': req.description,
        'created_by': payload['user_id'],
        'created_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
        'enabled': True,
        'system_prompt': req.system_prompt,
        'domain_data_path': f'./data/workers/{wid}/domain_data',
        'workflows_path': f'./data/workers/{wid}/workflows/verified',
        'my_data_path': f'./data/workers/{wid}/my_data',
        'enabled_tools': req.enabled_tools,
        'assigned_admins': [],
        'assigned_users': [],
    }
    if req.clone_from:
        src = _find_worker(req.clone_from)
        if src:
            new_worker['system_prompt'] = src.get('system_prompt', '')
            new_worker['enabled_tools'] = src.get('enabled_tools', ['*'])

    workers = _load_workers()
    workers.append(new_worker)
    _save_workers(workers)
    _seed_worker_folders(wid)
    return new_worker


@app.get('/api/super/workers/{worker_id}')
async def super_get_worker(worker_id: str, _: dict = Depends(require_super_admin)):
    w = _find_worker(worker_id)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    return w


class WorkerUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    enabled_tools: Optional[list] = None
    enabled: Optional[bool] = None

@app.put('/api/super/workers/{worker_id}')
async def super_update_worker(worker_id: str, req: WorkerUpdateRequest, _: dict = Depends(require_super_admin)):
    workers = _load_workers()
    for w in workers:
        if w['worker_id'] == worker_id:
            if req.name is not None: w['name'] = req.name
            if req.description is not None: w['description'] = req.description
            if req.system_prompt is not None: w['system_prompt'] = req.system_prompt
            if req.enabled_tools is not None: w['enabled_tools'] = req.enabled_tools
            if req.enabled is not None: w['enabled'] = req.enabled
            _save_workers(workers)
            return w
    raise HTTPException(status_code=404, detail='Worker not found')


class DeleteWorkerRequest(BaseModel):
    confirm_name: str

@app.delete('/api/super/workers/{worker_id}')
async def super_delete_worker(worker_id: str, req: DeleteWorkerRequest, _: dict = Depends(require_super_admin)):
    w = _find_worker(worker_id)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    if req.confirm_name != w['name']:
        raise HTTPException(status_code=400, detail='Confirmation name does not match worker name')
    # Delete folder tree
    base = pathlib.Path(f'sajhamcpserver/data/workers/{worker_id}')
    if base.exists():
        shutil.rmtree(str(base))
    # Remove from workers
    workers = [x for x in _load_workers() if x['worker_id'] != worker_id]
    _save_workers(workers)
    # Unassign users
    users = _load_users()
    for u in users:
        if u.get('worker_id') == worker_id:
            u['worker_id'] = None
    _save_users(users)
    return {'ok': True}


class AssignRequest(BaseModel):
    user_id: str
    role: str  # 'admin' | 'user'

@app.post('/api/super/workers/{worker_id}/assign')
async def super_assign_user(worker_id: str, req: AssignRequest, _: dict = Depends(require_super_admin)):
    if req.role not in ('admin', 'user'):
        raise HTTPException(status_code=400, detail='role must be admin or user')
    w = _find_worker(worker_id)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    users = _load_users()
    for u in users:
        if u.get('user_id') == req.user_id:
            u['worker_id'] = worker_id
            u['role'] = req.role
            break
    _save_users(users)
    return {'ok': True}


@app.delete('/api/super/workers/{worker_id}/assign/{user_id}')
async def super_unassign_user(worker_id: str, user_id: str, _: dict = Depends(require_super_admin)):
    users = _load_users()
    for u in users:
        if u.get('user_id') == user_id and u.get('worker_id') == worker_id:
            u['worker_id'] = None
            break
    _save_users(users)
    return {'ok': True}


# ── Super Admin — User Management ─────────────────────────────────────────────

@app.get('/api/super/users')
async def super_list_users(_: dict = Depends(require_super_admin)):
    return {'users': _load_users()}


class UserCreateRequest(BaseModel):
    user_id: str
    display_name: str
    email: str = ''
    password: str
    role: str = 'user'
    worker_id: Optional[str] = None

@app.post('/api/super/users', status_code=201)
async def super_create_user(req: UserCreateRequest, _: dict = Depends(require_super_admin)):
    if req.role not in ('admin', 'user'):
        raise HTTPException(status_code=400, detail='role must be admin or user')
    users = _load_users()
    if any(u['user_id'] == req.user_id for u in users):
        raise HTTPException(status_code=409, detail='user_id already exists')

    parts = req.display_name.strip().split()
    initials = ''.join(p[0].upper() for p in parts[:3])
    ph = _hash_password(req.password)
    now = __import__('datetime').datetime.utcnow().isoformat() + 'Z'
    new_user = {
        'user_id': req.user_id,
        'user_name': req.display_name,
        'display_name': req.display_name,
        'avatar_initials': initials,
        'password': req.password,
        'password_hash': ph,
        'role': req.role,
        'roles': [req.role],
        'worker_id': req.worker_id,
        'tools': ['*'],
        'enabled': True,
        'onboarding_complete': False,
        'email': req.email,
        'created_at': now,
        'last_login': None,
    }
    users.append(new_user)
    _save_users(users)
    return new_user


class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    worker_id: Optional[str] = None
    enabled: Optional[bool] = None

@app.put('/api/super/users/{user_id}')
async def super_update_user(user_id: str, req: UserUpdateRequest, _: dict = Depends(require_super_admin)):
    users = _load_users()
    for u in users:
        if u['user_id'] == user_id:
            if req.display_name is not None:
                u['display_name'] = req.display_name
                parts = req.display_name.strip().split()
                u['avatar_initials'] = ''.join(p[0].upper() for p in parts[:3])
            if req.email is not None: u['email'] = req.email
            if req.role is not None:
                u['role'] = req.role
                u['roles'] = [req.role]
            if req.worker_id is not None: u['worker_id'] = req.worker_id
            if req.enabled is not None: u['enabled'] = req.enabled
            _save_users(users)
            return u
    raise HTTPException(status_code=404, detail='User not found')


@app.delete('/api/super/users/{user_id}')
async def super_delete_user(user_id: str, _: dict = Depends(require_super_admin)):
    users = [u for u in _load_users() if u['user_id'] != user_id]
    _save_users(users)
    return {'ok': True}


class ResetPasswordRequest(BaseModel):
    pass

@app.post('/api/super/users/{user_id}/reset-password')
async def super_reset_password(user_id: str, _: dict = Depends(require_super_admin)):
    import secrets, string
    tmp = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    users = _load_users()
    for u in users:
        if u['user_id'] == user_id:
            u['password'] = tmp
            ph = _hash_password(tmp)
            if ph: u['password_hash'] = ph
            u['onboarding_complete'] = False
            break
    _save_users(users)
    return {'temp_password': tmp, 'onboarding_complete': False}


# ── Admin — Own Worker Config ──────────────────────────────────────────────────

def _get_admin_worker(payload: dict) -> dict:
    role = payload.get('role', '')
    if role == 'super_admin':
        wid = payload.get('worker_id')
        workers = _load_workers()
        return _find_worker(wid) if wid else (workers[0] if workers else None)
    elif role == 'admin':
        wid = payload.get('worker_id')
        w = _find_worker(wid) if wid else None
        if not w:
            raise HTTPException(status_code=404, detail='No worker assigned to this admin')
        return w
    else:
        raise HTTPException(status_code=403, detail='Admin access required')


@app.get('/api/mcp/tools')
async def mcp_tools_list(_: dict = Depends(require_admin)):
    """Return tool list built from SAJHA config/tools JSON files — no live SAJHA needed."""
    tools_dir = pathlib.Path('sajhamcpserver/config/tools')
    tools = []
    for f in sorted(tools_dir.glob('*.json')):
        try:
            cfg = json.loads(f.read_text())
        except Exception:
            continue
        name = cfg.get('name') or f.stem
        meta = cfg.get('metadata', {})
        tools.append({
            'name': name,
            'description': cfg.get('description', ''),
            'category': meta.get('category', _infer_category(name)),
            'enabled': cfg.get('enabled', True),
            'tags': meta.get('tags', []),
        })
    return {'tools': tools}


def _infer_category(name: str) -> str:
    prefixes = {
        'edgar_': 'SEC / EDGAR',
        'iris_': 'IRIS CCR',
        'osfi_': 'OSFI Regulatory',
        'tavily_': 'Web Search',
        'ir_': 'Investor Relations',
        'duckdb_': 'DuckDB Analytics',
        'sqlselect_': 'SQL / Data',
        'msdoc_': 'Documents',
        'olap_': 'OLAP Analytics',
        'sharepoint_': 'SharePoint',
        'get_': 'Market Risk',
        'iris_': 'IRIS CCR',
        'workflow_': 'Workflows',
        'md_': 'Markdown / Docs',
    }
    for prefix, cat in prefixes.items():
        if name.startswith(prefix):
            return cat
    return 'General'


@app.get('/api/admin/worker')
async def admin_get_worker(payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    return w


class PromptUpdateRequest(BaseModel):
    system_prompt: str

@app.put('/api/admin/worker/prompt')
async def admin_update_prompt(req: PromptUpdateRequest, payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    workers = _load_workers()
    for wk in workers:
        if wk['worker_id'] == w['worker_id']:
            wk['system_prompt'] = req.system_prompt
            break
    _save_workers(workers)
    return {'ok': True}


class ToolsUpdateRequest(BaseModel):
    enabled_tools: list

@app.put('/api/admin/worker/tools')
async def admin_update_tools(req: ToolsUpdateRequest, payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    workers = _load_workers()
    for wk in workers:
        if wk['worker_id'] == w['worker_id']:
            wk['enabled_tools'] = req.enabled_tools
            break
    _save_workers(workers)
    return {'ok': True}


@app.get('/api/admin/worker/users')
async def admin_list_worker_users(payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    wid = w['worker_id']
    users = [u for u in _load_users() if u.get('worker_id') == wid]
    return {'users': users}


# ── File upload ────────────────────────────────────────────────────────────────

@app.post('/api/files/upload')
async def upload_file(file: UploadFile = File(...), _: None = Depends(require_api_key)):
    from agent.tools import _sajha_token as _tok
    import agent.tools as _agent_tools
    try:
        content = await file.read()

        async def _do_upload(retry: bool = True):
            token = await _get_token()
            async with httpx.AsyncClient(timeout=30.0) as c:
                r = await c.post(
                    f'{SAJHA_BASE}/api/files/upload',
                    headers={'Authorization': f'Bearer {token}'},
                    files={'file': (file.filename, content,
                                    file.content_type or 'application/octet-stream')},
                )
                if r.status_code == 401 and retry:
                    _agent_tools._sajha_token = None
                    return await _do_upload(retry=False)
                r.raise_for_status()
                return JSONResponse(content=r.json())

        return await _do_upload()
    except httpx.HTTPStatusError as e:
        return JSONResponse(status_code=e.response.status_code,
                            content={'success': False, 'error': f'SAJHA returned {e.response.status_code}'})
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e)})


def _read_metadata() -> dict:
    try:
        return json.loads(_METADATA_FILE.read_text()) if _METADATA_FILE.exists() else {}
    except Exception:
        return {}

def _write_metadata(data: dict):
    _METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    _METADATA_FILE.write_text(json.dumps(data, indent=2))

def _safe_filename(filename: str) -> str:
    name = pathlib.Path(filename).name
    if not name.endswith('.md') or '/' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail='filename must be a plain .md filename')
    return name


# ── Workspace files ────────────────────────────────────────────────────────────

@app.get('/api/workspace/files')
async def list_workspace_files(_: None = Depends(require_api_key)):
    files = []
    if _UPLOADS_DIR.exists():
        for f in sorted(_UPLOADS_DIR.iterdir()):
            if f.is_file() and not f.name.startswith('.'):
                files.append({'name': f.name, 'size': f.stat().st_size,
                               'modified': f.stat().st_mtime})
    return {'files': files}


# ── Workflows ──────────────────────────────────────────────────────────────────

@app.get('/api/workflows')
async def list_workflows(_: None = Depends(require_api_key)):
    _WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    meta = _read_metadata()
    workflows = []
    for f in sorted(_WORKFLOWS_DIR.iterdir()):
        if f.is_file() and f.suffix == '.md':
            workflows.append({
                'filename': f.name,
                'name': f.stem.replace('_', ' ').title(),
                'size': f.stat().st_size,
                'last_used': meta.get(f.name),
            })
    workflows.sort(key=lambda w: w['last_used'] or '', reverse=True)
    return {'workflows': workflows}


@app.get('/api/workflows/{filename}')
async def get_workflow(filename: str, _: None = Depends(require_api_key)):
    name = _safe_filename(filename)
    path = _WORKFLOWS_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail='Workflow not found')
    return {'filename': name, 'content': path.read_text()}


class WorkflowCreate(BaseModel):
    filename: str
    content: str

@app.post('/api/workflows', status_code=201)
async def create_workflow(req: WorkflowCreate, _: None = Depends(require_api_key)):
    name = _safe_filename(req.filename)
    _WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    (_WORKFLOWS_DIR / name).write_text(req.content)
    return {'filename': name, 'ok': True}


@app.delete('/api/workflows/{filename}')
async def delete_workflow(filename: str, _: None = Depends(require_api_key)):
    name = _safe_filename(filename)
    path = _WORKFLOWS_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail='Workflow not found')
    path.unlink()
    meta = _read_metadata()
    meta.pop(name, None)
    _write_metadata(meta)
    return {'ok': True}


@app.patch('/api/workflows/{filename}/used')
async def mark_workflow_used(filename: str, _: None = Depends(require_api_key)):
    name = _safe_filename(filename)
    from datetime import datetime, timezone
    meta = _read_metadata()
    meta[name] = {"last_used": datetime.now(timezone.utc).isoformat()}
    _write_metadata(meta)
    return {'ok': True}


def _resolve_section_path(section: str, rel: str = '') -> pathlib.Path:
    root = _SECTION_ROOTS.get(section)
    if root is None:
        raise HTTPException(status_code=400, detail=f'Unknown section: {section}')
    if rel:
        full = (root / rel).resolve()
        if not str(full).startswith(str(root.resolve())):
            raise HTTPException(status_code=400, detail='Path traversal not allowed')
        return full
    return root


# ── FileTree API ───────────────────────────────────────────────────────────────

@app.get('/api/fs/{section}/tree')
async def fs_tree(section: str, _: None = Depends(require_api_key)):
    root = _resolve_section_path(section)
    root.mkdir(parents=True, exist_ok=True)
    idx = get_index(str(root))
    return idx


@app.get('/api/fs/{section}/file')
async def fs_file(section: str, path: str = '', _: None = Depends(require_api_key)):
    root = _resolve_section_path(section)
    if not path:
        raise HTTPException(status_code=400, detail='path required')
    full = _resolve_section_path(section, path)
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail='File not found')
    content_bytes = full.read_bytes()
    try:
        text = content_bytes.decode('utf-8')
        return {'path': path, 'encoding': 'utf-8', 'content': text}
    except UnicodeDecodeError:
        return {'path': path, 'encoding': 'base64', 'content': base64.b64encode(content_bytes).decode('ascii')}


@app.post('/api/fs/{section}/upload')
async def fs_upload(
    section: str,
    path: str = '',
    file: UploadFile = File(...),
    _: None = Depends(require_api_key)
):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    root = _resolve_section_path(section)
    folder = _resolve_section_path(section, path) if path else root
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / pathlib.Path(file.filename).name
    dest.write_bytes(await file.read())
    build_index(str(root))
    return {'ok': True, 'path': str(dest.relative_to(root)).replace('\\', '/')}


class FsUpdateRequest(BaseModel):
    path: str
    content: str

@app.patch('/api/fs/{section}/file')
async def fs_update_file(section: str, req: FsUpdateRequest, _: None = Depends(require_api_key)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    root = _resolve_section_path(section)
    full = _resolve_section_path(section, req.path)
    full.write_text(req.content, encoding='utf-8')
    build_index(str(root))
    return {'ok': True}


class FsMkdirRequest(BaseModel):
    path: str

@app.post('/api/fs/{section}/folder')
async def fs_mkdir(section: str, req: FsMkdirRequest, _: None = Depends(require_api_key)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    root = _resolve_section_path(section)
    full = _resolve_section_path(section, req.path)
    full.mkdir(parents=True, exist_ok=True)
    build_index(str(root))
    return {'ok': True}


class FsMoveRequest(BaseModel):
    src: str
    dst: str

@app.post('/api/fs/{section}/move')
async def fs_move(section: str, req: FsMoveRequest, _: None = Depends(require_api_key)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    root = _resolve_section_path(section)
    src_full = _resolve_section_path(section, req.src)
    dst_full = _resolve_section_path(section, req.dst)
    if not src_full.exists():
        raise HTTPException(status_code=404, detail='Source not found')
    dst_full.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_full), str(dst_full))
    build_index(str(root))
    return {'ok': True}


class FsRenameRequest(BaseModel):
    path: str
    new_name: str

@app.post('/api/fs/{section}/rename')
async def fs_rename(section: str, req: FsRenameRequest, _: None = Depends(require_api_key)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    root = _resolve_section_path(section)
    full = _resolve_section_path(section, req.path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='Not found')
    new_name = pathlib.Path(req.new_name).name
    new_full = full.parent / new_name
    full.rename(new_full)
    build_index(str(root))
    return {'ok': True}


@app.delete('/api/fs/{section}/file')
async def fs_delete_file(section: str, path: str = '', _: None = Depends(require_api_key)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    root = _resolve_section_path(section)
    full = _resolve_section_path(section, path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='File not found')
    full.unlink()
    build_index(str(root))
    return {'ok': True}


@app.delete('/api/fs/{section}/folder')
async def fs_delete_folder(section: str, path: str = '', _: None = Depends(require_api_key)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    root = _resolve_section_path(section)
    full = _resolve_section_path(section, path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='Folder not found')
    try:
        full.rmdir()
    except OSError:
        raise HTTPException(status_code=400, detail='Folder is not empty')
    build_index(str(root))
    return {'ok': True}


# ── Admin API ─────────────────────────────────────────────────────────────────

class AdminFolderRequest(BaseModel):
    section: str
    path: str

class AdminDeleteRequest(BaseModel):
    section: str
    path: str
    recursive: bool = False

class AdminRenameRequest(BaseModel):
    section: str
    path: str
    new_name: str

class AdminMoveRequest(BaseModel):
    section: str
    src_path: str
    dest_folder: str

class AdminFileRequest(BaseModel):
    section: str
    folder: str = ''
    filename: str

_MD_STUB = '''---
name:
description:
inputs:
tags: []
version: "1.0"
---

## Step 1
'''


@app.get('/api/admin/tree/{section}')
async def admin_tree(section: str, worker_id: str = '', _: dict = Depends(require_admin)):
    root = _resolve_admin_path(section)
    root.mkdir(parents=True, exist_ok=True)
    idx = get_index(str(root))
    return idx


@app.post('/api/admin/upload')
async def admin_upload(
    section: str,
    path: str = '',
    overwrite: bool = False,
    file: UploadFile = File(...),
    _: dict = Depends(require_admin),
):
    root = _resolve_admin_path(section).resolve()
    if section == 'verified_workflows' and not file.filename.endswith('.md'):
        raise HTTPException(status_code=415, detail='Verified Workflows only accepts .md files')
    folder = _resolve_admin_path(section, path).resolve() if path else root
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / pathlib.Path(file.filename).name
    if dest.exists() and not overwrite:
        raise HTTPException(status_code=409, detail='File already exists')
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='File exceeds 20 MB limit')
    dest.write_bytes(content)
    build_index(str(root))
    stat = dest.stat()
    from datetime import datetime, timezone
    return {
        'path': str(dest.relative_to(root)).replace('\\', '/'),
        'size_bytes': stat.st_size,
        'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


@app.post('/api/admin/folder')
async def admin_folder(req: AdminFolderRequest, _: dict = Depends(require_admin)):
    root = _resolve_admin_path(req.section)
    full = _resolve_admin_path(req.section, req.path)
    full.mkdir(parents=True, exist_ok=True)
    build_index(str(root))
    return {'created': True, 'path': req.path}


@app.delete('/api/admin/item')
async def admin_delete(req: AdminDeleteRequest, _: dict = Depends(require_admin)):
    root = _resolve_admin_path(req.section)
    full = _resolve_admin_path(req.section, req.path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='Not found')
    if full.is_dir():
        items = list(full.rglob('*'))
        count = len([x for x in items if x.is_file()])
        if count > 0 and not req.recursive:
            raise HTTPException(status_code=409, detail=f'Folder contains {count} items. Use recursive=true to delete.')
        shutil.rmtree(full)
    else:
        full.unlink()
    build_index(str(root))
    return {'ok': True}


@app.patch('/api/admin/rename')
async def admin_rename(req: AdminRenameRequest, _: dict = Depends(require_admin)):
    root = _resolve_admin_path(req.section)
    full = _resolve_admin_path(req.section, req.path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='Not found')
    # Block root-level section folders from being renamed
    if full == root:
        raise HTTPException(status_code=400, detail='Cannot rename root section folder')
    new_name = pathlib.Path(req.new_name).name
    if not new_name or '/' in new_name or '\\' in new_name:
        raise HTTPException(status_code=400, detail='Invalid name')
    new_full = full.parent / new_name
    if new_full.exists():
        raise HTTPException(status_code=409, detail='A file or folder with this name already exists')
    full.rename(new_full)
    build_index(str(root))
    new_path = str(new_full.relative_to(root.resolve())).replace('\\', '/')
    return {'new_path': new_path}


@app.post('/api/admin/move')
async def admin_move(req: AdminMoveRequest, _: dict = Depends(require_admin)):
    root = _resolve_admin_path(req.section).resolve()
    src_full = _resolve_admin_path(req.section, req.src_path).resolve()
    dst_full = _resolve_admin_path(req.section, req.dest_folder).resolve() / src_full.name
    if not src_full.exists():
        raise HTTPException(status_code=404, detail='Source not found')
    # Prevent moving into self or descendant
    try:
        dst_full.relative_to(src_full)
        raise HTTPException(status_code=400, detail='Cannot move a folder into itself or its own subfolder')
    except ValueError:
        pass
    if dst_full.exists():
        raise HTTPException(status_code=409, detail=f'"{src_full.name}" already exists in target folder')
    dst_full.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_full), str(dst_full))
    build_index(str(root))
    return {'ok': True, 'new_path': str(dst_full.relative_to(root)).replace('\\', '/')}


@app.post('/api/admin/file')
async def admin_new_file(req: AdminFileRequest, _: dict = Depends(require_admin)):
    root = _resolve_admin_path(req.section)
    folder_path = req.folder if req.folder else ''
    folder_full = _resolve_admin_path(req.section, folder_path) if folder_path else root
    folder_full.mkdir(parents=True, exist_ok=True)
    name = pathlib.Path(req.filename).name
    dest = folder_full / name
    dest.write_text(_MD_STUB, encoding='utf-8')
    build_index(str(root))
    rel_path = str(dest.relative_to(root)).replace('\\', '/')
    return {'path': rel_path}


@app.get('/api/admin/file')
async def admin_read_file(section: str, path: str, _: dict = Depends(require_admin)):
    """Return file content for preview. Truncated at 2MB for text files."""
    from fastapi.responses import Response as _Resp
    full = _resolve_admin_path(section, path).resolve()
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail='File not found')
    size = full.stat().st_size
    TRUNCATE = 2 * 1024 * 1024
    TEXT_EXTS = {'.md', '.txt', '.csv', '.tsv', '.json', '.html', '.xml', '.yaml', '.yml'}
    BINARY_EXTS = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.parquet', '.pq', '.png', '.jpg'}
    ext = full.suffix.lower()
    headers = {'X-File-Size': str(size), 'X-File-Name': full.name,
               'Access-Control-Expose-Headers': 'X-File-Size,X-File-Name,X-Truncated'}
    if ext in BINARY_EXTS:
        content = full.read_bytes()
        media = ('application/pdf' if ext == '.pdf' else
                 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' if ext == '.docx' else
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if ext == '.xlsx' else
                 'application/octet-stream')
        return _Resp(content=content, media_type=media, headers=headers)
    try:
        raw = full.read_bytes()
        truncated = len(raw) > TRUNCATE
        if truncated:
            raw = raw[:TRUNCATE]
            headers['X-Truncated'] = '1'
        text = raw.decode('utf-8', errors='replace')
        return _Resp(content=text, media_type='text/plain; charset=utf-8', headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/admin/validate/{section}/{path:path}')
async def admin_validate(section: str, path: str, _: dict = Depends(require_admin)):
    full = _resolve_admin_path(section, path)
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail='File not found')
    content = full.read_text(encoding='utf-8', errors='replace')
    valid = False
    missing = []
    if content.startswith('---'):
        end = content.find('---', 3)
        if end != -1:
            fm_block = content[3:end].strip()
            required = ['name', 'description', 'inputs']
            found = {k: False for k in required}
            for line in fm_block.splitlines():
                for k in required:
                    if line.strip().startswith(k + ':'):
                        val = line.split(':', 1)[1].strip()
                        if val:
                            found[k] = True
            missing = [k for k, v in found.items() if not v]
            valid = len(missing) == 0
    else:
        missing = ['name', 'description', 'inputs']
    return {'valid': valid, 'missing': missing}


# ── Agent run ──────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    query: str
    thread_id: str = ''
    resume: str | None = None

@app.post('/api/agent/run')
async def run_agent(req: RunRequest, _: None = Depends(require_api_key)):
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {'configurable': {'thread_id': thread_id}}

    async def stream():
        yield f"data: {json.dumps({'type': 'session', 'thread_id': thread_id})}\n\n"
        try:
            inp = ({'messages': [{'role': 'user', 'content': req.query}]}
                   if not req.resume else {'resume': req.resume})
            full_text = []
            async for event in agent.astream_events(inp, config=config, version='v2'):
                t = event['event']
                if t == 'on_chat_model_stream':
                    chunk = event['data']['chunk']
                    if hasattr(chunk, 'content'):
                        content = chunk.content
                        if isinstance(content, str) and content:
                            full_text.append(content)
                            yield f"data: {json.dumps({'type': 'text', 'text': content})}\n\n"
                        elif isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get('type') == 'text' and block.get('text'):
                                    full_text.append(block['text'])
                                    yield f"data: {json.dumps({'type': 'text', 'text': block['text']})}\n\n"
                                elif hasattr(block, 'text') and block.text:
                                    full_text.append(block.text)
                                    yield f"data: {json.dumps({'type': 'text', 'text': block.text})}\n\n"
                elif t == 'on_tool_start':
                    yield f"data: {json.dumps({'type': 'tool_start', 'name': event['name'], 'input': event['data'].get('input', {}), 'run_id': event['run_id']})}\n\n"
                elif t == 'on_tool_end':
                    output = event['data'].get('output', '')
                    if hasattr(output, 'content'):
                        output = output.content
                    if not isinstance(output, (str, dict, list)):
                        output = str(output)
                    yield f"data: {json.dumps({'type': 'tool_end', 'name': event['name'], 'output': output, 'run_id': event['run_id']})}\n\n"
                elif t == 'on_interrupt':
                    yield f"data: {json.dumps({'type': 'hitl', 'question': event['data'].get('question', ''), 'options': event['data'].get('options', []), 'thread_id': thread_id})}\n\n"
                elif t == 'on_chat_model_end':
                    output = event['data'].get('output')
                    usage = {}
                    if output and hasattr(output, 'usage_metadata'):
                        um = output.usage_metadata
                        if um:
                            usage = um if isinstance(um, dict) else dict(um)
                    if usage:
                        yield f"data: {json.dumps({'type': 'usage', 'usage': usage})}\n\n"
            import json as _json, re as _re
            assembled = ''.join(full_text).strip()

            def _try_parse_envelope(s):
                try:
                    obj = _json.loads(s)
                    if 'summary' in obj and 'canvas' in obj:
                        return obj
                except Exception:
                    pass
                return None

            envelope = None
            _fence_match = _re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', assembled)
            if _fence_match:
                envelope = _try_parse_envelope(_fence_match.group(1).strip())
            if not envelope and assembled.startswith('{'):
                envelope = _try_parse_envelope(assembled)
            if not envelope:
                _json_start = assembled.find('{\n  "summary"')
                if _json_start == -1:
                    _json_start = assembled.find('{"summary"')
                if _json_start != -1:
                    envelope = _try_parse_envelope(assembled[_json_start:])

            if envelope:
                canvas = envelope['canvas']
                yield f"data: {_json.dumps({'type': 'replace_text', 'text': envelope.get('summary', '')})}\n\n"
                yield f"data: {_json.dumps({'type': 'canvas', 'title': canvas.get('title','Document'), 'content': canvas.get('content',''), 'canvas_type': canvas.get('type','report')})}\n\n"
            yield 'data: [DONE]\n\n'
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield 'data: [DONE]\n\n'

    return StreamingResponse(stream(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
