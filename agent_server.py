import os, json, uuid, pathlib, base64, sys as _sys, hmac, hashlib, time, shutil
import aiofiles
import os as _os
from contextlib import asynccontextmanager
from contextvars import ContextVar
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
import httpx
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import agent.agent as _agent_module
from agent.agent import create_agent_for_worker
from agent.prompt import get_system_prompt, SYSTEM_PROMPT
from agent.tools import _service_headers, _worker_ctx, SAJHA_BASE, get_tools_for_worker, AGENT_TOOLS
from agent.summariser import count_tokens_accurate

_WORKFLOWS_DIR = pathlib.Path('sajhamcpserver/data/workflows')
_UPLOADS_DIR   = pathlib.Path('sajhamcpserver/data/uploads')
_METADATA_FILE = _WORKFLOWS_DIR / '.metadata.json'

_sys.path.insert(0, str(pathlib.Path(__file__).parent / 'sajhamcpserver'))
from sajha.tools.impl.fs_index import build_index, get_index
from sajha.worker_repository import WorkerRepository as _WorkerRepository

_JWT_SECRET = os.getenv('JWT_SECRET', 'sajha-dev-secret-change-in-prod')
_SAJHA_USERS_FILE  = pathlib.Path('sajhamcpserver/config/users.json')
_SAJHA_WORKERS_FILE = pathlib.Path('sajhamcpserver/config/workers.json')

_STORAGE_BACKEND = _os.environ.get('STORAGE_BACKEND', 'local')

# WorkerRepository singleton — all worker config reads go through this (REQ-PREP-06)
_worker_repo = _WorkerRepository(config_path=str(_SAJHA_WORKERS_FILE))


def serve_file(path: str, media_type: str = None) -> Response:
    """Serve a file. Local: FileResponse. S3: pre-signed URL (not implemented locally). (REQ-PREP-07)"""
    if _STORAGE_BACKEND == 'local':
        return FileResponse(path, media_type=media_type) if media_type else FileResponse(path)
    else:
        raise NotImplementedError("S3 file serving not configured")


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
    """Persist users list. Strips deprecated plaintext password and roles[] on every write (G-10, G-11)."""
    for u in users:
        u.pop('password', None)
        u.pop('roles', None)
    _SAJHA_USERS_FILE.write_text(json.dumps({'users': users}, indent=2))


def _find_user(user_id: str) -> Optional[dict]:
    for u in _load_users():
        if u.get('user_id') == user_id:
            return u
    return None


def _load_workers() -> list:
    """Return all workers via WorkerRepository (REQ-PREP-06)."""
    return _worker_repo.list()


def _save_workers(workers: list):
    """Persist workers to disk, then reload the repository cache (REQ-PREP-06)."""
    _SAJHA_WORKERS_FILE.write_text(json.dumps({'workers': workers}, indent=2))
    _worker_repo.reload()


def _find_worker(worker_id: str) -> Optional[dict]:
    """Find a worker by ID via WorkerRepository (REQ-PREP-06)."""
    return _worker_repo.find(worker_id)


def _verify_password(plain: str, user: dict) -> bool:
    """Check password against bcrypt hash. Plaintext fallback removed (G-11)."""
    stored_hash = user.get('password_hash', '')
    if stored_hash:
        try:
            import bcrypt
            return bcrypt.checkpw(plain.encode(), stored_hash.encode())
        except Exception:
            pass
    return False


def _hash_password(plain: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()
    except ImportError:
        return ''  # bcrypt not installed — plaintext fallback


def _get_user_role(user: dict) -> str:
    """Return canonical role string. Reads role field only (G-10 — roles[] array removed)."""
    return user.get('role', 'user')


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
    """Create the full scoped folder tree for a new worker (G-07)."""
    base = pathlib.Path(f'sajhamcpserver/data/workers/{worker_id}')
    for sub in [
        'domain_data/iris', 'domain_data/counterparties', 'domain_data/market_data',
        'domain_data/uploads', 'domain_data/analytics',
        'workflows/verified', 'workflows/my',
        'templates', 'my_data',
    ]:
        (base / sub).mkdir(parents=True, exist_ok=True)


def _clone_worker_folder(src_id: str, dst_id: str):
    """Clone source worker's folder to destination, excluding my_data (user-owned, REQ-MD-01)."""
    src = pathlib.Path(f'sajhamcpserver/data/workers/{src_id}')
    dst = pathlib.Path(f'sajhamcpserver/data/workers/{dst_id}')
    if src.exists():
        shutil.copytree(str(src), str(dst),
                        ignore=shutil.ignore_patterns('my_data'),  # exclude entire my_data tree
                        dirs_exist_ok=True)
    # Ensure my_data exists but is empty (no user data copied into the clone)
    (dst / 'my_data').mkdir(parents=True, exist_ok=True)


load_dotenv()

_DATA_ROOT     = pathlib.Path('sajhamcpserver/data')
_COMMON_DATA   = _DATA_ROOT / 'common'
_AUDIT_LOG     = _DATA_ROOT / 'audit' / 'tool_calls.jsonl'

# Sections that users may write to (uploads, my-docs, personal workflows)
_WRITABLE_SECTIONS = {'uploads', 'my_workflows', 'my_data'}

# REQ-WF-01/REQ-DD-01/REQ-DD-02: global _DOMAIN_DATA, _MY_DATA, _VERIFIED_WF, _MY_WF constants
# retired — global directories migrated to worker-scoped paths. Legacy admin endpoints now
# route through _admin_section_roots_for_worker() or worker-scoped paths directly.
_ADMIN_SECTION_ROOTS: dict = {}  # no global sections remain; kept for legacy endpoint compatibility

# Thread ownership registry — maps thread_id → {user_id, worker_id, created_at}
_THREAD_REGISTRY_FILE = _DATA_ROOT / 'threads.jsonl'
_thread_registry: dict = {}

def _load_thread_registry():
    """Load thread registry from disk on startup (G-08 persistence)."""
    if not _THREAD_REGISTRY_FILE.exists():
        return
    for line in _THREAD_REGISTRY_FILE.read_text().splitlines():
        try:
            entry = json.loads(line)
            tid = entry.pop('thread_id', None)
            if tid:
                _thread_registry[tid] = entry
        except Exception:
            pass

def _persist_thread(thread_id: str, meta: dict):
    """Append a new thread registration to disk."""
    _THREAD_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_THREAD_REGISTRY_FILE, 'a') as f:
        f.write(json.dumps({'thread_id': thread_id, **meta}) + '\n')

# Login rate-limit: {user_id: [timestamp, ...]}
_login_attempts: dict = {}
_LOGIN_WINDOW = 60   # seconds
_LOGIN_MAX    = 10   # max attempts per window


def _resolve_worker_path(worker: dict, section: str, rel: str = '') -> pathlib.Path:
    """Resolve a worker-scoped filesystem path for a given section (G-03).

    All paths are relative to sajhamcpserver/ as the base directory.
    Creates the root if it doesn't exist (lazy mkdir on first access).
    """
    base = pathlib.Path('sajhamcpserver')
    dd = worker.get('domain_data_path', './data/domain_data')
    mapping = {
        'domain_data':        dd,
        'uploads':            dd.rstrip('/') + '/uploads',
        'verified':           worker.get('workflows_path',    './data/workflows/verified'),
        'verified_workflows': worker.get('workflows_path',    './data/workflows/verified'),  # canonical alias (REQ-WF-02)
        'my_workflows':       worker.get('my_workflows_path', './data/workflows/my'),
        'templates':          worker.get('templates_path',    './data/domain_data/templates'),
        'my_data':            worker.get('my_data_path',      './data/uploads'),
        'common':             worker.get('common_data_path',  './data/common'),
    }
    raw = mapping.get(section)
    if raw is None:
        raise HTTPException(status_code=400, detail=f'Unknown section: {section}')
    root = (base / raw.lstrip('./')).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if rel:
        full = (root / rel).resolve()
        if not str(full).startswith(str(root)):
            raise HTTPException(status_code=400, detail='Path traversal not allowed')
        return full
    return root


def _assign_user_to_worker(user_id: str, worker_id: str | None, role: str | None = None):
    """Atomically update both users.json and workers.json when assigning a user (G-09)."""
    import datetime
    users = _load_users()
    workers = _load_workers()

    old_worker_id = None
    for u in users:
        if u.get('user_id') == user_id:
            old_worker_id = u.get('worker_id')
            u['worker_id'] = worker_id
            if role:
                u['role'] = role
            break

    # Remove from old worker's assigned_users
    if old_worker_id and old_worker_id != worker_id:
        for w in workers:
            if w['worker_id'] == old_worker_id:
                w['assigned_users'] = [uid for uid in w.get('assigned_users', []) if uid != user_id]
                break

    # Add to new worker's assigned_users
    if worker_id:
        for w in workers:
            if w['worker_id'] == worker_id:
                assigned = w.get('assigned_users', [])
                if user_id not in assigned:
                    assigned.append(user_id)
                w['assigned_users'] = assigned
                break

    _save_users(users)
    _save_workers(workers)


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
    """Return admin-accessible section roots scoped to a worker's paths (REQ-WF-03).

    Only exposes sections that admin/super-admin may browse and mutate.
    my_data is intentionally excluded (user-owned, REQ-MD-01).
    common is writable by admin+ and read-only for users (REQ-10).
    """
    base = pathlib.Path('sajhamcpserver')
    dd     = base / worker.get('domain_data_path',  './data/domain_data').lstrip('./')
    wf     = base / worker.get('workflows_path',     './data/workflows/verified').lstrip('./')
    mywf   = base / worker.get('my_workflows_path',  './data/workflows/my').lstrip('./')
    common = base / worker.get('common_data_path',   './data/common').lstrip('./')
    return {'domain_data': dd, 'verified_workflows': wf, 'my_workflows': mywf, 'common': common}


def _resolve_admin_path_for_worker(worker: dict, section: str, rel: str = '') -> pathlib.Path:
    roots = _admin_section_roots_for_worker(worker)
    root = roots.get(section)
    if root is None:
        raise HTTPException(status_code=400, detail=f'Unknown admin section: {section}')
    root_resolved = root.resolve()
    root_resolved.mkdir(parents=True, exist_ok=True)
    if rel:
        full = (root_resolved / rel).resolve()
        if not str(full).startswith(str(root_resolved)):
            raise HTTPException(status_code=400, detail='Path traversal not allowed')
        return full
    return root_resolved


# Ensure common data directory exists
_COMMON_DATA.mkdir(parents=True, exist_ok=True)
_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
_load_thread_registry()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Initialize AsyncSqliteSaver on startup; close it on shutdown."""
    _db_path = os.getenv('CHECKPOINT_DB_PATH', './sajhamcpserver/data/checkpoints.db')
    pathlib.Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(_db_path) as cp:
        _agent_module.set_checkpointer(cp)
        yield
    # AsyncSqliteSaver context exits automatically — connection closed


app = FastAPI(title='MCP Intelligence Agent', lifespan=_lifespan)
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

    # Rate limit: max _LOGIN_MAX attempts per _LOGIN_WINDOW seconds per user_id
    now = time.time()
    attempts = [t for t in _login_attempts.get(req.user_id, []) if now - t < _LOGIN_WINDOW]
    if len(attempts) >= _LOGIN_MAX:
        raise HTTPException(status_code=429, detail='Too many login attempts. Try again in 60 seconds.')
    attempts.append(now)
    _login_attempts[req.user_id] = attempts

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
            parts = req.display_name.strip().split()
            u['avatar_initials'] = ''.join(p[0].upper() for p in parts[:3])
            u.pop('password', None)
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
            u.pop('password', None)
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
        'domain_data_path':  f'./data/workers/{wid}/domain_data',
        'workflows_path':    f'./data/workers/{wid}/workflows/verified',
        'my_workflows_path': f'./data/workers/{wid}/workflows/my',
        'templates_path':    f'./data/workers/{wid}/templates',
        'my_data_path':      f'./data/workers/{wid}/my_data',
        'common_data_path':  './data/common',
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

    if req.clone_from:
        _clone_worker_folder(req.clone_from, wid)
    else:
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
    if not _find_worker(worker_id):
        raise HTTPException(status_code=404, detail='Worker not found')
    if not _find_user(req.user_id):
        raise HTTPException(status_code=404, detail='User not found')
    _assign_user_to_worker(req.user_id, worker_id, role=req.role)
    return {'ok': True}


@app.delete('/api/super/workers/{worker_id}/assign/{user_id}')
async def super_unassign_user(worker_id: str, user_id: str, _: dict = Depends(require_super_admin)):
    _assign_user_to_worker(user_id, None)
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
        'password_hash': ph,
        'role': req.role,
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
    # Sync worker's assigned_users if worker_id is set
    if req.worker_id:
        _assign_user_to_worker(req.user_id, req.worker_id, role=req.role)
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
            if req.role is not None: u['role'] = req.role
            if req.worker_id is not None:
                _assign_user_to_worker(user_id, req.worker_id, role=req.role)
                # reload since _assign_user_to_worker saved
                users = _load_users()
                u = next((x for x in users if x['user_id'] == user_id), u)
            if req.enabled is not None: u['enabled'] = req.enabled
            _save_users(users)
            return u
    raise HTTPException(status_code=404, detail='User not found')


@app.delete('/api/super/users/{user_id}')
async def super_delete_user(user_id: str, _: dict = Depends(require_super_admin)):
    # Remove from worker's assigned_users before deleting (G-09)
    _assign_user_to_worker(user_id, None)
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
            ph = _hash_password(tmp)
            if ph: u['password_hash'] = ph
            u.pop('password', None)
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


@app.put('/api/admin/worker')
async def admin_update_worker(req: Request, payload: dict = Depends(require_admin)):
    """Admin: update own worker name, description, system_prompt."""
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    data = await req.json()
    workers = _load_workers()
    for wk in workers:
        if wk['worker_id'] == w['worker_id']:
            for field in ('name', 'description', 'system_prompt'):
                if field in data:
                    wk[field] = data[field]
            break
    _save_workers(workers)
    return {'ok': True}


@app.post('/api/admin/worker/users', status_code=201)
async def admin_create_worker_user(req: Request, payload: dict = Depends(require_admin)):
    """Admin: create a user scoped to their worker."""
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    data = await req.json()
    user_id = data.get('user_id', '').strip()
    if not user_id:
        raise HTTPException(status_code=400, detail='user_id required')
    users = _load_users()
    if any(u['user_id'] == user_id for u in users):
        raise HTTPException(status_code=409, detail='User already exists')
    import bcrypt as _bcrypt
    password = data.get('password', 'ChangeMe2025!')
    hashed = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    new_user = {
        'user_id': user_id,
        'display_name': data.get('display_name', user_id),
        'role': 'user',
        'worker_id': w['worker_id'],
        'password_hash': hashed,
        'enabled': True,
        'onboarding_complete': False,
    }
    users.append(new_user)
    _save_users(users)
    return {'ok': True, 'user_id': user_id}


@app.put('/api/admin/worker/users/{user_id}')
async def admin_update_worker_user(user_id: str, req: Request, payload: dict = Depends(require_admin)):
    """Admin: enable/disable a user in their worker."""
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    data = await req.json()
    users = _load_users()
    for u in users:
        if u['user_id'] == user_id and u.get('worker_id') == w['worker_id']:
            if 'enabled' in data:
                u['enabled'] = bool(data['enabled'])
            break
    else:
        raise HTTPException(status_code=404, detail='User not found in this worker')
    _save_users(users)
    return {'ok': True}


@app.post('/api/admin/worker/users/{user_id}/reset-password')
async def admin_reset_worker_user_password(user_id: str, payload: dict = Depends(require_admin)):
    """Admin: reset a user's password (scoped to their worker)."""
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    import secrets as _secrets, bcrypt as _bcrypt
    tmp_password = 'Tmp' + _secrets.token_urlsafe(8) + '!'
    hashed = _bcrypt.hashpw(tmp_password.encode(), _bcrypt.gensalt()).decode()
    users = _load_users()
    for u in users:
        if u['user_id'] == user_id and u.get('worker_id') == w['worker_id']:
            u['password_hash'] = hashed
            u['onboarding_complete'] = False
            break
    else:
        raise HTTPException(status_code=404, detail='User not found in this worker')
    _save_users(users)
    return {'ok': True, 'temp_password': tmp_password}


@app.delete('/api/admin/worker/users/{user_id}')
async def admin_delete_worker_user(user_id: str, payload: dict = Depends(require_admin)):
    """Admin: delete a user scoped to their worker. Cannot delete self."""
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    if user_id == payload['user_id']:
        raise HTTPException(status_code=400, detail='Cannot delete your own account')
    users = _load_users()
    target = next((u for u in users if u['user_id'] == user_id and u.get('worker_id') == w['worker_id']), None)
    if not target:
        raise HTTPException(status_code=404, detail='User not found in this worker')
    users = [u for u in users if u['user_id'] != user_id]
    _save_users(users)
    return {'ok': True}


# ── File upload ────────────────────────────────────────────────────────────────

_UPLOAD_ALLOWED_EXT = {'pdf', 'docx', 'xlsx', 'csv', 'txt', 'parquet', 'md', 'json', 'png', 'jpg', 'jpeg'}
_UPLOAD_MAX_MB = 50
_UPLOAD_CHUNK_SIZE = 65536        # 64 KB streaming chunk (REQ-11)
_UPLOAD_MAX_BYTES  = 50 * 1024 * 1024  # 50 MB hard limit (REQ-11)


async def _stream_upload(file: UploadFile, dest: pathlib.Path) -> int:
    """Stream upload to disk in 64 KB chunks. Returns bytes written.
    Raises HTTP 413 if file exceeds 50 MB. Cleans up partial file on error. (REQ-11)"""
    bytes_written = 0
    try:
        async with aiofiles.open(dest, 'wb') as f:
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                await f.write(chunk)
                bytes_written += len(chunk)
                if bytes_written > _UPLOAD_MAX_BYTES:
                    raise HTTPException(status_code=413, detail='File exceeds 50 MB limit')
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f'Upload failed: {exc}')
    return bytes_written

@app.post('/api/files/upload')
async def upload_file(file: UploadFile = File(...), payload: dict = Depends(require_jwt)):
    """Upload a file to the authenticated user's my_data directory (REQ-MD-01).

    Saves directly to the worker's my_data/{user_id}/ path — no SAJHA proxy needed.
    """
    from datetime import datetime, timezone as _tz
    try:
        user_id = payload.get('user_id', '')
        user    = _find_user(user_id)
        worker  = (_resolve_worker_for_user(user, None) if user else None)
        if not worker:
            raise HTTPException(status_code=404, detail='No worker assigned to this user')

        # Resolve per-user my_data directory (REQ-MD-01)
        raw_my_data = worker.get('my_data_path', './data/uploads')
        my_data_dir = (pathlib.Path('sajhamcpserver') / raw_my_data.lstrip('./')).resolve()
        user_dir = my_data_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        # Validate extension
        ext = file.filename.rsplit('.', 1)[-1].lower() if file.filename and '.' in file.filename else ''
        if ext not in _UPLOAD_ALLOWED_EXT:
            raise HTTPException(status_code=400,
                                detail=f'Unsupported file type. Allowed: {", ".join(sorted(_UPLOAD_ALLOWED_EXT))}')

        # Safe filename
        safe_name = pathlib.Path(file.filename).name
        dest = user_dir / safe_name
        if dest.exists():
            ts = datetime.now(_tz.utc).strftime('%Y%m%d_%H%M%S')
            stem, suffix = safe_name.rsplit('.', 1) if '.' in safe_name else (safe_name, '')
            safe_name = f'{stem}_{ts}.{suffix}' if suffix else f'{stem}_{ts}'
            dest = user_dir / safe_name

        await _stream_upload(file, dest)
        build_index(str(user_dir))   # refresh tree cache immediately
        stat = dest.stat()
        return JSONResponse(content={
            'success': True,
            'filename': safe_name,
            'path': str(dest.relative_to(pathlib.Path('sajhamcpserver').resolve())).replace('\\', '/'),
            'size_bytes': stat.st_size,
            'uploaded_at': datetime.fromtimestamp(stat.st_mtime, tz=_tz.utc).isoformat(),
            'file_type': ext,
        })
    except HTTPException:
        raise
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
async def list_workspace_files(payload: dict = Depends(require_jwt)):
    user = _find_user(payload['user_id'])
    worker = _resolve_worker_for_user(user) if user else None
    if not worker:
        raise HTTPException(status_code=404, detail='No worker assigned to this user')
    raw = worker.get('my_data_path', './data/uploads')
    base = pathlib.Path('sajhamcpserver')
    user_dir = (base / raw.lstrip('./')).resolve() / payload['user_id']
    user_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(user_dir.iterdir()):
        if f.is_file() and not f.name.startswith('.'):
            files.append({'name': f.name, 'size': f.stat().st_size,
                           'modified': f.stat().st_mtime})
    return {'files': files}


# ── Workflows ──────────────────────────────────────────────────────────────────

@app.get('/api/workflows')
async def list_workflows(payload: dict = Depends(require_jwt)):
    user = _find_user(payload['user_id'])
    worker = _resolve_worker_for_user(user) if user else None
    if not worker:
        raise HTTPException(status_code=404, detail='No worker assigned to this user')
    wf_dir = _resolve_worker_path(worker, 'verified_workflows')
    meta = _read_metadata()
    workflows = []
    for f in sorted(wf_dir.iterdir()):
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
async def get_workflow(filename: str, payload: dict = Depends(require_jwt)):
    user = _find_user(payload['user_id'])
    worker = _resolve_worker_for_user(user) if user else None
    if not worker:
        raise HTTPException(status_code=404, detail='No worker assigned to this user')
    name = _safe_filename(filename)
    # Check verified_workflows first, then my_workflows (BUG-NEW-007 fix)
    for section in ('verified_workflows', 'my_workflows'):
        wf_dir = _resolve_worker_path(worker, section)
        path = wf_dir / name
        if path.exists():
            return {'filename': name, 'content': path.read_text()}
    raise HTTPException(status_code=404, detail='Workflow not found')


class WorkflowCreate(BaseModel):
    filename: str
    content: str

@app.post('/api/workflows', status_code=201)
async def create_workflow(req: WorkflowCreate, payload: dict = Depends(require_jwt)):
    user = _find_user(payload['user_id'])
    worker = _resolve_worker_for_user(user) if user else None
    if not worker:
        raise HTTPException(status_code=404, detail='No worker assigned to this user')
    name = _safe_filename(req.filename)
    my_wf_dir = _resolve_worker_path(worker, 'my_workflows')
    (my_wf_dir / name).write_text(req.content)
    return {'filename': name, 'ok': True}


@app.delete('/api/workflows/{filename}')
async def delete_workflow(filename: str, payload: dict = Depends(require_jwt)):
    user = _find_user(payload['user_id'])
    worker = _resolve_worker_for_user(user) if user else None
    if not worker:
        raise HTTPException(status_code=404, detail='No worker assigned to this user')
    name = _safe_filename(filename)
    my_wf_dir = _resolve_worker_path(worker, 'my_workflows')
    path = my_wf_dir / name
    if not path.exists():
        raise HTTPException(status_code=404, detail='Workflow not found')
    path.unlink()
    meta = _read_metadata()
    meta.pop(name, None)
    _write_metadata(meta)
    return {'ok': True}


@app.patch('/api/workflows/{filename}/used')
async def mark_workflow_used(filename: str, payload: dict = Depends(require_jwt)):
    user = _find_user(payload['user_id'])
    worker = _resolve_worker_for_user(user) if user else None
    if not worker:
        raise HTTPException(status_code=404, detail='No worker assigned to this user')
    name = _safe_filename(filename)
    wf_dir = _resolve_worker_path(worker, 'verified_workflows')
    from datetime import datetime, timezone
    meta = _read_metadata()
    meta[name] = {"last_used": datetime.now(timezone.utc).isoformat()}
    _write_metadata(meta)
    return {'ok': True}


# ── FileTree API — worker-scoped (G-03) ────────────────────────────────────────

def _fs_worker(payload: dict) -> dict:
    """Resolve the worker for an fs endpoint caller. Any authenticated user allowed."""
    user = _find_user(payload['user_id'])
    worker = _resolve_worker_for_user(user) if user else None
    if not worker:
        raise HTTPException(status_code=404, detail='No worker assigned to this user')
    return worker


def _resolve_fs_path(worker: dict, user_id: str, section: str, rel: str = '') -> pathlib.Path:
    """Resolve an fs section path. 'uploads' maps to my_data/{user_id}/ (REQ-MD-01)."""
    if section == 'uploads':
        raw = worker.get('my_data_path', './data/uploads')
        base = pathlib.Path('sajhamcpserver')
        root = (base / raw.lstrip('./')).resolve() / user_id
        root.mkdir(parents=True, exist_ok=True)
        if rel:
            full = (root / rel).resolve()
            if not str(full).startswith(str(root)):
                raise HTTPException(status_code=400, detail='Path traversal not allowed')
            return full
        return root
    return _resolve_worker_path(worker, section, rel)


@app.get('/api/fs/quota')
async def fs_quota(payload: dict = Depends(require_jwt)):
    worker = _fs_worker(payload)
    uid = payload['user_id']
    my_data_root = _resolve_fs_path(worker, uid, 'uploads')
    used_bytes = sum(f.stat().st_size for f in my_data_root.rglob('*') if f.is_file()) if my_data_root.exists() else 0
    # Default quota: 5 GB. Could be configurable via properties.
    limit_bytes = 5 * 1024 * 1024 * 1024
    used_pct = round((used_bytes / limit_bytes) * 100, 2) if limit_bytes > 0 else 0
    return {'used_bytes': used_bytes, 'limit_bytes': limit_bytes, 'used_pct': used_pct}


@app.get('/api/fs/{section}/tree')
async def fs_tree(section: str, payload: dict = Depends(require_jwt)):
    worker = _fs_worker(payload)
    root = _resolve_fs_path(worker, payload['user_id'], section)
    idx = get_index(str(root))
    return idx


@app.get('/api/fs/{section}/file')
async def fs_file(section: str, path: str = '', payload: dict = Depends(require_jwt)):
    worker = _fs_worker(payload)
    if not path:
        raise HTTPException(status_code=400, detail='path required')
    full = _resolve_fs_path(worker, payload['user_id'], section, path)
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
    batch_id: str = '',
    file: UploadFile = File(...),
    payload: dict = Depends(require_jwt),
):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    worker = _fs_worker(payload)
    uid = payload['user_id']
    root = _resolve_fs_path(worker, uid, section)
    folder = _resolve_fs_path(worker, uid, section, path) if path else root
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / pathlib.Path(file.filename).name
    await _stream_upload(file, dest)
    if not batch_id:
        build_index(str(root))
    return {'ok': True, 'path': str(dest.relative_to(root)).replace('\\', '/')}


class FsUpdateRequest(BaseModel):
    path: str
    content: str

@app.patch('/api/fs/{section}/file')
async def fs_update_file(section: str, req: FsUpdateRequest, payload: dict = Depends(require_jwt)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    worker = _fs_worker(payload)
    uid = payload['user_id']
    root = _resolve_fs_path(worker, uid, section)
    full = _resolve_fs_path(worker, uid, section, req.path)
    full.write_text(req.content, encoding='utf-8')
    build_index(str(root))
    return {'ok': True}


class FsMkdirRequest(BaseModel):
    path: str

@app.post('/api/fs/{section}/folder')
async def fs_mkdir(section: str, req: FsMkdirRequest, payload: dict = Depends(require_jwt)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    worker = _fs_worker(payload)
    uid = payload['user_id']
    root = _resolve_fs_path(worker, uid, section)
    full = _resolve_fs_path(worker, uid, section, req.path)
    full.mkdir(parents=True, exist_ok=True)
    build_index(str(root))
    return {'ok': True}


class FsMoveRequest(BaseModel):
    src: str
    dst: str

@app.post('/api/fs/{section}/move')
async def fs_move(section: str, req: FsMoveRequest, payload: dict = Depends(require_jwt)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    worker = _fs_worker(payload)
    uid = payload['user_id']
    root = _resolve_fs_path(worker, uid, section)
    src_full = _resolve_fs_path(worker, uid, section, req.src)
    dst_full = _resolve_fs_path(worker, uid, section, req.dst)
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
async def fs_rename(section: str, req: FsRenameRequest, payload: dict = Depends(require_jwt)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    worker = _fs_worker(payload)
    uid = payload['user_id']
    root = _resolve_fs_path(worker, uid, section)
    full = _resolve_fs_path(worker, uid, section, req.path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='Not found')
    new_name = pathlib.Path(req.new_name).name
    new_full = full.parent / new_name
    full.rename(new_full)
    build_index(str(root))
    return {'ok': True}


class FsCopyRequest(BaseModel):
    src_path: str
    dest_section: str
    dest_path: str

@app.post('/api/fs/{section}/copy')
async def fs_copy(section: str, req: FsCopyRequest, payload: dict = Depends(require_jwt)):
    worker = _fs_worker(payload)
    uid = payload['user_id']
    if req.dest_section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Destination section is read-only')
    src_full = _resolve_fs_path(worker, uid, section, req.src_path)
    if not src_full.exists() or not src_full.is_file():
        raise HTTPException(status_code=404, detail='Source file not found')
    dst_full = _resolve_fs_path(worker, uid, req.dest_section, req.dest_path)
    if dst_full.exists():
        raise HTTPException(status_code=409, detail='Destination already exists')
    dst_full.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src_full), str(dst_full))
    dst_root = _resolve_fs_path(worker, uid, req.dest_section)
    build_index(str(dst_root))
    return {'ok': True, 'dest_path': req.dest_path}


class FsBatchDeleteRequest(BaseModel):
    paths: list
    include_dirs: bool = False

@app.post('/api/fs/{section}/batch-delete')
async def fs_batch_delete(section: str, req: FsBatchDeleteRequest, payload: dict = Depends(require_jwt)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    worker = _fs_worker(payload)
    uid = payload['user_id']
    root = _resolve_fs_path(worker, uid, section)
    deleted = []
    errors = []
    for p in req.paths:
        try:
            full = _resolve_fs_path(worker, uid, section, p)
            if not full.exists():
                errors.append({'path': p, 'error': 'Not found'})
                continue
            if full.is_dir():
                if not req.include_dirs:
                    errors.append({'path': p, 'error': 'Is a directory; set include_dirs=true'})
                    continue
                shutil.rmtree(str(full))
            else:
                full.unlink()
            deleted.append(p)
        except Exception as e:
            errors.append({'path': p, 'error': str(e)})
    build_index(str(root))
    return {'deleted': deleted, 'errors': errors}


@app.patch('/api/fs/{section}/file/used')
async def fs_mark_file_used(section: str, request: Request, path: str = '', payload: dict = Depends(require_jwt)):
    """Mark a workflow file as recently used. Updates last_used timestamp in section metadata.
    Also appends an audit entry to sajhamcpserver/data/audit/file_used.jsonl (BUG-FS-002)."""
    # Accept path from query string or JSON body
    if not path:
        try:
            body = await request.json()
            path = body.get('path', '')
        except Exception:
            pass
    worker = _fs_worker(payload)
    if not path:
        raise HTTPException(status_code=400, detail='path required')
    # Record usage in a simple metadata sidecar
    root = _resolve_fs_path(worker, payload['user_id'], section)
    meta_path = root / '.used_metadata.json'
    try:
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    except Exception:
        meta = {}
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    meta[path] = {'last_used': now_iso}
    meta_path.write_text(json.dumps(meta, indent=2))
    # Audit log (BUG-FS-002)
    entry = {
        'user_id': payload.get('sub', ''),
        'worker_id': payload.get('worker_id', ''),
        'section': section,
        'path': path,
        'used_at': now_iso
    }
    audit_path = pathlib.Path('sajhamcpserver/data/audit/file_used.jsonl')
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, 'a') as f:
        f.write(json.dumps(entry) + '\n')
    return {'ok': True, 'path': path}


@app.delete('/api/fs/{section}/file')
async def fs_delete_file(section: str, path: str = '', payload: dict = Depends(require_jwt)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    worker = _fs_worker(payload)
    uid = payload['user_id']
    root = _resolve_fs_path(worker, uid, section)
    full = _resolve_fs_path(worker, uid, section, path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='File not found')
    full.unlink()
    build_index(str(root))
    return {'ok': True}


@app.delete('/api/fs/{section}/folder')
async def fs_delete_folder(section: str, path: str = '', payload: dict = Depends(require_jwt)):
    if section not in _WRITABLE_SECTIONS:
        raise HTTPException(status_code=403, detail='Section is read-only')
    worker = _fs_worker(payload)
    uid = payload['user_id']
    root = _resolve_fs_path(worker, uid, section)
    full = _resolve_fs_path(worker, uid, section, path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='Folder not found')
    try:
        full.rmdir()
    except OSError:
        raise HTTPException(status_code=400, detail='Folder is not empty')
    build_index(str(root))
    return {'ok': True}


# ── Chart serving endpoints (REQ-03) ───────────────────────────────────────────

def _resolve_charts_root(worker: dict, user_id: str) -> pathlib.Path:
    """Resolve per-user charts directory from worker my_data_path."""
    raw = worker.get('my_data_path', './data/uploads')
    base = pathlib.Path('sajhamcpserver')
    return (base / raw.lstrip('./')).resolve() / user_id / 'charts'


@app.get('/api/fs/charts')
async def list_charts(payload: dict = Depends(require_jwt)):
    """List available charts (HTML and PNG) for the authenticated user."""
    worker = _fs_worker(payload)
    charts_root = _resolve_charts_root(worker, payload['user_id'])
    if not charts_root.exists():
        return {'charts': []}
    charts = []
    for f in sorted(charts_root.iterdir()):
        if f.suffix in ('.html', '.png') and f.is_file():
            charts.append({
                'filename': f.name,
                'type': 'html' if f.suffix == '.html' else 'png',
                'url': f'/api/fs/charts/{f.name}',
                'size': f.stat().st_size,
                'modified': f.stat().st_mtime,
            })
    return {'charts': charts}


@app.get('/api/fs/charts/{filename}')
async def serve_chart(filename: str, token: str = '', payload: dict = None,
                      creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    """Serve a chart file (HTML or PNG).

    Accepts auth via Bearer header OR ?token= query param so iframes can load
    charts without needing custom request headers.
    """
    # Resolve JWT from header or query param
    raw_token = token or (creds.credentials if creds else '')
    if not raw_token:
        raise HTTPException(status_code=401, detail='Not authenticated')
    try:
        payload = _jwt_decode(raw_token)
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid token')

    # Reject path traversal attempts
    if '/' in filename or '\\' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail='Invalid filename')
    worker = _fs_worker(payload)
    charts_root = _resolve_charts_root(worker, payload['user_id'])
    chart_path = (charts_root / filename).resolve()
    if not str(chart_path).startswith(str(charts_root)):
        raise HTTPException(status_code=400, detail='Path traversal not allowed')
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail='Chart not found')
    if chart_path.suffix == '.png':
        return serve_file(str(chart_path), media_type='image/png')
    return serve_file(str(chart_path), media_type='text/html')


# ── Admin API ──────────────────────────────────────────────────────────────────

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
    worker_id: Optional[str] = None

@app.post('/api/agent/run')
async def run_agent(req: RunRequest, payload: dict = Depends(require_jwt)):
    """Run the agent for the calling user's worker.
    - Builds a per-request agent with the worker's current system_prompt + enabled_tools (G-01, G-02).
    - Sets _worker_ctx so tool calls carry X-Worker-Id / X-Worker-Data-Root headers (G-04).
    - Validates thread ownership on resume (G-08).
    - All roles (user, admin, super_admin) may call this endpoint.
    """
    user = _find_user(payload['user_id'])
    worker = _resolve_worker_for_user(user, req.worker_id) if user else None
    if not worker:
        raise HTTPException(status_code=404, detail='No worker assigned to this user')

    # Per-request agent: fresh system prompt + filtered tools on every call (G-01 + G-02)
    system_prompt = get_system_prompt(worker['worker_id'])
    tools = get_tools_for_worker(worker.get('enabled_tools', ['*']))
    agent_instance = create_agent_for_worker(system_prompt, tools)

    thread_id = req.thread_id or str(uuid.uuid4())
    config = {'configurable': {'thread_id': thread_id}}

    # Thread ownership — validate on resume, register on new thread (G-08)
    if req.thread_id or req.resume:
        owner = _thread_registry.get(thread_id)
        if owner:
            if owner['user_id'] != payload['user_id'] or owner['worker_id'] != worker['worker_id']:
                raise HTTPException(status_code=403, detail='Thread belongs to a different user or worker')
    if not (req.thread_id or req.resume):
        import datetime
        meta = {
            'user_id': payload['user_id'],
            'worker_id': worker['worker_id'],
            'created_at': datetime.datetime.utcnow().isoformat() + 'Z',
        }
        _thread_registry[thread_id] = meta
        _persist_thread(thread_id, meta)

    async def stream():
        # Inject worker context into ContextVar for this async task (G-04 + G-13)
        ctx_token = _worker_ctx.set({**worker, 'user_id': payload['user_id']})
        try:
            yield f"data: {json.dumps({'type': 'session', 'thread_id': thread_id})}\n\n"
            inp = ({'messages': [{'role': 'user', 'content': req.query}]}
                   if not req.resume else {'resume': req.resume})
            full_text = []
            async for event in agent_instance.astream_events(inp, config=config, version='v2'):
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
                    # LangGraph may serialize ToolMessage content as a JSON string — parse it back
                    if isinstance(output, str):
                        try:
                            _parsed = json.loads(output)
                            if isinstance(_parsed, dict):
                                output = _parsed
                        except (ValueError, TypeError):
                            pass
                    yield f"data: {json.dumps({'type': 'tool_end', 'name': event['name'], 'output': output, 'run_id': event['run_id']})}\n\n"
                    if isinstance(output, dict) and output.get('_chart_ready'):
                        # Unified chart-ready SSE: covers generate_chart (html_file) and python_execute (figures)
                        if output.get('html_file'):
                            chart_title = output.get('title', 'Chart')
                            chart_url = '/api/fs/charts/' + output['html_file']
                            yield f"data: {json.dumps({'type': 'canvas', 'title': chart_title, 'content': '', 'canvas_type': 'chart', 'chart_url': chart_url})}\n\n"
                        elif output.get('figures'):
                            first_fig = output['figures'][0]
                            chart_title = output.get('title', 'Python Chart')
                            yield f"data: {json.dumps({'type': 'canvas', 'title': chart_title, 'canvas_type': 'chart', 'chart_url': first_fig['url']})}\n\n"
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
            # REQ-05: emit context gauge + summary notice if compression fired
            try:
                final_state = await agent_instance.aget_state(config)
                if final_state and final_state.values:
                    sv = final_state.values
                    msgs = sv.get('messages', [])
                    token_count = count_tokens_accurate(msgs)
                    yield f"data: {_json.dumps({'type': 'context_gauge', 'tokens': token_count, 'limit': 200000})}\n\n"
                    if sv.get('_summary_occurred'):
                        exchanges_compressed = sv.get('exchanges_compressed', 0)
                        tokens_before = sv.get('tokens_before', 0)
                        tokens_after = sv.get('tokens_after', token_count)
                        yield f"data: {_json.dumps({'type': 'summary_occurred', 'exchanges_compressed': exchanges_compressed, 'tokens_before': tokens_before, 'tokens_after': tokens_after})}\n\n"
            except Exception:
                pass
            yield 'data: [DONE]\n\n'
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield 'data: [DONE]\n\n'
        finally:
            _worker_ctx.reset(ctx_token)

    return StreamingResponse(stream(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ── Super Admin — Worker-scoped file browser ──────────────────────────────────

@app.get('/api/super/workers/{worker_id}/files/{section}')
@app.get('/api/super/workers/{worker_id}/files/{section}/tree')
async def super_worker_tree(worker_id: str, section: str, _: dict = Depends(require_super_admin)):
    """Browse any worker's file tree (super_admin only). Uses admin resolver (REQ-WF-03)."""
    w = _find_worker(worker_id)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    root = _resolve_admin_path_for_worker(w, section)
    return get_index(str(root))


@app.post('/api/super/workers/{worker_id}/files/{section}/upload')
async def super_worker_upload(
    worker_id: str,
    section: str,
    path: str = '',
    overwrite: bool = False,
    batch_id: str = '',
    file: UploadFile = File(...),
    _: dict = Depends(require_super_admin),
):
    """Upload a file into any worker's scoped section (super_admin only). Uses admin resolver (REQ-WF-03)."""
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
    from datetime import datetime, timezone
    stat = dest.stat()
    return {
        'path': str(dest.relative_to(root)).replace('\\', '/'),
        'size_bytes': stat.st_size,
        'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def _count_files_in_tree(tree: list) -> int:
    """Recursively count file entries in an .index.json tree. (REQ-11)"""
    count = 0
    for item in tree:
        if item.get('type') == 'file':
            count += 1
        elif item.get('type') == 'folder':
            count += _count_files_in_tree(item.get('children', []))
    return count


@app.post('/api/super/workers/{worker_id}/files/{section}/reindex')
async def super_worker_reindex(
    worker_id: str,
    section: str,
    _: dict = Depends(require_super_admin),
):
    """Rebuild .index.json for a section. Called once after batch upload completes. (REQ-11)"""
    w = _find_worker(worker_id)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    root = _resolve_admin_path_for_worker(w, section)
    t0 = time.time()
    idx = build_index(str(root))
    elapsed = round((time.time() - t0) * 1000, 1)
    file_count = _count_files_in_tree(idx.get('tree', []))
    return {'indexed_files': file_count, 'elapsed_ms': elapsed, 'section': section}


# ── Admin — Own worker file browser ───────────────────────────────────────────

@app.get('/api/admin/worker/files/{section}')
@app.get('/api/admin/worker/files/{section}/tree')
async def admin_worker_tree(section: str, payload: dict = Depends(require_admin)):
    """Browse the admin's own worker file tree."""
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    root = _resolve_worker_path(w, section)
    return get_index(str(root))


@app.post('/api/admin/worker/files/{section}/upload')
async def admin_worker_upload(
    section: str,
    path: str = '',
    overwrite: bool = False,
    batch_id: str = '',
    file: UploadFile = File(...),
    payload: dict = Depends(require_admin),
):
    """Upload a file into the admin's own worker section."""
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    root = _resolve_worker_path(w, section)
    folder = _resolve_worker_path(w, section, path) if path else root
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / pathlib.Path(file.filename).name
    if dest.exists() and not overwrite:
        raise HTTPException(status_code=409, detail='File already exists')
    await _stream_upload(file, dest)
    if not batch_id:
        build_index(str(root))
    from datetime import datetime, timezone
    stat = dest.stat()
    return {
        'path': str(dest.relative_to(root)).replace('\\', '/'),
        'size_bytes': stat.st_size,
        'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


@app.post('/api/admin/worker/files/{section}/reindex')
async def admin_worker_reindex(section: str, payload: dict = Depends(require_admin)):
    """Rebuild .index.json for a section. Called once after batch upload completes. (REQ-11)"""
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    root = _resolve_worker_path(w, section)
    t0 = time.time()
    idx = build_index(str(root))
    elapsed = round((time.time() - t0) * 1000, 1)
    file_count = _count_files_in_tree(idx.get('tree', []))
    return {'indexed_files': file_count, 'elapsed_ms': elapsed, 'section': section}


@app.post('/api/admin/common/upload')
async def admin_common_upload(
    path: str = '',
    overwrite: bool = False,
    batch_id: str = '',
    file: UploadFile = File(...),
    payload: dict = Depends(require_admin),
):
    """Upload a file to common shared data (admin + super_admin). (REQ-10)"""
    w = _get_admin_worker(payload)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    common_root = _resolve_worker_path(w, 'common')
    folder = _resolve_worker_path(w, 'common', path) if path else common_root
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / pathlib.Path(file.filename).name
    if dest.exists() and not overwrite:
        raise HTTPException(status_code=409, detail='File already exists')
    await _stream_upload(file, dest)
    if not batch_id:
        build_index(str(common_root))
    from datetime import datetime, timezone
    stat = dest.stat()
    return {
        'path': str(dest.relative_to(common_root)).replace('\\', '/'),
        'size_bytes': stat.st_size,
        'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


# ── Shared helpers for worker-scoped file CRUD ────────────────────────────────

def _wf_read(w, section, path, _res=None):
    _r = _res or _resolve_worker_path
    full = _r(w, section, path)
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail='File not found')
    content_bytes = full.read_bytes()
    root = _r(w, section)
    size = full.stat().st_size
    try:
        return {'path': path, 'encoding': 'utf-8', 'content': content_bytes.decode('utf-8'), 'size_bytes': size}
    except UnicodeDecodeError:
        return {'path': path, 'encoding': 'base64', 'content': base64.b64encode(content_bytes).decode('ascii'), 'size_bytes': size}

def _wf_write(w, section, path, content, _res=None):
    _r = _res or _resolve_worker_path
    full = _r(w, section, path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding='utf-8')
    build_index(str(_r(w, section)))
    return {'ok': True}

def _wf_delete_file(w, section, path, _res=None):
    _r = _res or _resolve_worker_path
    full = _r(w, section, path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='File not found')
    full.unlink()
    build_index(str(_r(w, section)))
    return {'ok': True}

def _wf_delete_folder(w, section, path, recursive: bool = False, _res=None):
    _r = _res or _resolve_worker_path
    full = _r(w, section, path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='Folder not found')
    items = list(full.rglob('*'))
    count = len([x for x in items if x.is_file()])
    if count > 0 and not recursive:
        raise HTTPException(status_code=409, detail=f'Folder contains {count} items. Use recursive=true to delete.')
    shutil.rmtree(full)
    build_index(str(_r(w, section)))
    return {'ok': True}

def _wf_mkdir(w, section, path, _res=None):
    _r = _res or _resolve_worker_path
    full = _r(w, section, path)
    full.mkdir(parents=True, exist_ok=True)
    build_index(str(_r(w, section)))
    return {'ok': True}

def _wf_rename(w, section, path, new_name, _res=None):
    _r = _res or _resolve_worker_path
    full = _r(w, section, path)
    if not full.exists():
        raise HTTPException(status_code=404, detail='Not found')
    n = pathlib.Path(new_name).name
    if not n or '/' in n or '\\' in n:
        raise HTTPException(status_code=400, detail='Invalid name')
    new_full = full.parent / n
    if new_full.exists():
        raise HTTPException(status_code=409, detail='A file or folder with this name already exists')
    full.rename(new_full)
    root = _r(w, section)
    build_index(str(root))
    return {'new_path': str(new_full.relative_to(root)).replace('\\', '/')}

def _wf_move(w, section, src, dest_folder, _res=None):
    _r = _res or _resolve_worker_path
    root = _r(w, section)
    src_full = _r(w, section, src)
    dst_full = _r(w, section, dest_folder) / src_full.name
    if not src_full.exists():
        raise HTTPException(status_code=404, detail='Source not found')
    try:
        dst_full.relative_to(src_full)
        raise HTTPException(status_code=400, detail='Cannot move a folder into itself')
    except ValueError:
        pass
    if dst_full.exists():
        raise HTTPException(status_code=409, detail=f'"{src_full.name}" already exists in target folder')
    dst_full.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_full), str(dst_full))
    build_index(str(root))
    return {'ok': True, 'new_path': str(dst_full.relative_to(root)).replace('\\', '/')}


# ── Super Admin — Worker-scoped file CRUD ─────────────────────────────────────

class _WfUpdate(BaseModel):
    path: str
    content: str

class _WfMkdir(BaseModel):
    path: str

class _WfRename(BaseModel):
    path: str
    new_name: str

class _WfMove(BaseModel):
    src: str
    dest_folder: str

class _WfDelete(BaseModel):
    path: str
    recursive: bool = False


@app.get('/api/super/workers/{worker_id}/files/{section}/file')
async def super_worker_read_file(worker_id: str, section: str, path: str = '', _: dict = Depends(require_super_admin)):
    w = _find_worker(worker_id)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    if not path: raise HTTPException(status_code=400, detail='path required')
    return _wf_read(w, section, path, _res=_resolve_admin_path_for_worker)

@app.patch('/api/super/workers/{worker_id}/files/{section}/file')
async def super_worker_write_file(worker_id: str, section: str, req: _WfUpdate, _: dict = Depends(require_super_admin)):
    w = _find_worker(worker_id)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    return _wf_write(w, section, req.path, req.content, _res=_resolve_admin_path_for_worker)

@app.delete('/api/super/workers/{worker_id}/files/{section}/file')
async def super_worker_delete_file(worker_id: str, section: str, path: str = '', _: dict = Depends(require_super_admin)):
    w = _find_worker(worker_id)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    if not path: raise HTTPException(status_code=400, detail='path required')
    return _wf_delete_file(w, section, path, _res=_resolve_admin_path_for_worker)

@app.delete('/api/super/workers/{worker_id}/files/{section}/folder')
async def super_worker_delete_folder(worker_id: str, section: str, req: _WfDelete, _: dict = Depends(require_super_admin)):
    w = _find_worker(worker_id)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    return _wf_delete_folder(w, section, req.path, req.recursive, _res=_resolve_admin_path_for_worker)

@app.post('/api/super/workers/{worker_id}/files/{section}/folder')
async def super_worker_mkdir(worker_id: str, section: str, req: _WfMkdir, _: dict = Depends(require_super_admin)):
    w = _find_worker(worker_id)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    return _wf_mkdir(w, section, req.path, _res=_resolve_admin_path_for_worker)

@app.post('/api/super/workers/{worker_id}/files/{section}/rename')
async def super_worker_rename(worker_id: str, section: str, req: _WfRename, _: dict = Depends(require_super_admin)):
    w = _find_worker(worker_id)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    return _wf_rename(w, section, req.path, req.new_name, _res=_resolve_admin_path_for_worker)

@app.post('/api/super/workers/{worker_id}/files/{section}/move')
async def super_worker_move(worker_id: str, section: str, req: _WfMove, _: dict = Depends(require_super_admin)):
    w = _find_worker(worker_id)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    return _wf_move(w, section, req.src, req.dest_folder, _res=_resolve_admin_path_for_worker)


# ── Admin — Own worker file CRUD ──────────────────────────────────────────────

@app.get('/api/admin/worker/files/{section}/file')
async def admin_worker_read_file(section: str, path: str = '', payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    if not path: raise HTTPException(status_code=400, detail='path required')
    return _wf_read(w, section, path)

@app.patch('/api/admin/worker/files/{section}/file')
async def admin_worker_write_file(section: str, req: _WfUpdate, payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    return _wf_write(w, section, req.path, req.content)

@app.delete('/api/admin/worker/files/{section}/file')
async def admin_worker_delete_file(section: str, path: str = '', payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    if not path: raise HTTPException(status_code=400, detail='path required')
    if section == 'common' and payload.get('role') != 'super_admin':
        raise HTTPException(status_code=403, detail='Only super_admin can delete from common data')
    return _wf_delete_file(w, section, path)

@app.delete('/api/admin/worker/files/{section}/folder')
async def admin_worker_delete_folder(section: str, req: _WfDelete, payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    if section == 'common' and payload.get('role') != 'super_admin':
        raise HTTPException(status_code=403, detail='Only super_admin can delete from common data')
    return _wf_delete_folder(w, section, req.path, req.recursive)

@app.post('/api/admin/worker/files/{section}/folder')
async def admin_worker_mkdir(section: str, req: _WfMkdir, payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    return _wf_mkdir(w, section, req.path)

@app.post('/api/admin/worker/files/{section}/rename')
async def admin_worker_rename(section: str, req: _WfRename, payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    return _wf_rename(w, section, req.path, req.new_name)

@app.post('/api/admin/worker/files/{section}/move')
async def admin_worker_move(section: str, req: _WfMove, payload: dict = Depends(require_admin)):
    w = _get_admin_worker(payload)
    if not w: raise HTTPException(status_code=404, detail='Worker not found')
    return _wf_move(w, section, req.src, req.dest_folder)


# ── Worker tool list ───────────────────────────────────────────────────────────

@app.get('/api/workers/{worker_id}/tools')
async def worker_tools_list(worker_id: str, payload: dict = Depends(require_jwt)):
    """Return tool list for a worker, filtered to its enabled_tools allowlist."""
    role = payload.get('role', 'user')
    # Users can only query their own worker; admins/super_admins can query any
    if role == 'user' and payload.get('worker_id') != worker_id:
        raise HTTPException(status_code=403, detail='Access denied')
    w = _find_worker(worker_id)
    if not w:
        raise HTTPException(status_code=404, detail='Worker not found')
    enabled = w.get('enabled_tools', ['*'])
    tools_dir = pathlib.Path('sajhamcpserver/config/tools')
    tools = []
    for f in sorted(tools_dir.glob('*.json')):
        try:
            cfg = json.loads(f.read_text())
        except Exception:
            continue
        name = cfg.get('name') or f.stem
        if enabled != ['*'] and name not in enabled:
            continue
        meta = cfg.get('metadata', {})
        tools.append({
            'name': name,
            'description': cfg.get('description', ''),
            'category': meta.get('category', _infer_category(name)),
            'enabled': cfg.get('enabled', True),
            'tags': meta.get('tags', []),
            'input_schema': cfg.get('input_schema', {}),
        })
    return {'worker_id': worker_id, 'tools': tools, 'enabled_tools': enabled}


# ── Thread listing (G-08) ──────────────────────────────────────────────────────

@app.get('/api/agent/threads')
async def list_threads(payload: dict = Depends(require_jwt)):
    """List thread IDs owned by the calling user + worker."""
    user_id = payload['user_id']
    worker_id = payload.get('worker_id')
    threads = [
        {'thread_id': tid, **meta}
        for tid, meta in _thread_registry.items()
        if meta['user_id'] == user_id and meta.get('worker_id') == worker_id
    ]
    return {'threads': threads}


# ── Audit log (G-13) ───────────────────────────────────────────────────────────

@app.get('/api/super/audit')
async def super_audit_log(
    worker_id: str = '',
    user_id: str = '',
    limit: int = 100,
    offset: int = 0,
    _: dict = Depends(require_super_admin),
):
    """Return recent tool-call audit log lines, optionally filtered. Supports pagination via offset."""
    if not _AUDIT_LOG.exists():
        return {'entries': [], 'total_matched': 0, 'offset': offset, 'limit': limit}
    lines = _AUDIT_LOG.read_text().splitlines()
    matched = []
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if worker_id and entry.get('worker_id') != worker_id:
            continue
        if user_id and entry.get('user_id') != user_id:
            continue
        matched.append(entry)
    total_matched = len(matched)
    page = matched[offset: offset + limit]
    return {'entries': page, 'total_matched': total_matched, 'total_returned': len(page), 'offset': offset, 'limit': limit}


# ── Connectors API ────────────────────────────────────────────────────────────

_CONNECTORS_FILE = pathlib.Path('sajhamcpserver/config/connectors.json')

_CONNECTOR_DEFAULTS = [
    {
        'connector_type': 'microsoft_azure',
        'display_name': 'Microsoft 365',
        'status': 'not_configured',
        'enabled': False,
        'has_credentials': False,
        'tool_count': 24,
    },
    {
        'connector_type': 'atlassian',
        'display_name': 'Atlassian',
        'status': 'not_configured',
        'enabled': False,
        'has_credentials': False,
        'tool_count': 12,
    },
]


def _load_connectors() -> list:
    try:
        data = json.loads(_CONNECTORS_FILE.read_text())
        saved = {c['connector_type']: c for c in data.get('connectors', [])}
    except Exception:
        saved = {}
    result = []
    for d in _CONNECTOR_DEFAULTS:
        ct = d['connector_type']
        if ct in saved:
            safe = {k: v for k, v in saved[ct].items() if k != 'credentials'}
            safe['has_credentials'] = bool(saved[ct].get('credentials'))
            safe.setdefault('tool_count', d['tool_count'])
            result.append(safe)
        else:
            result.append(dict(d))
    return result


def _save_connector(connector_type: str, data: dict):
    try:
        existing = json.loads(_CONNECTORS_FILE.read_text())
        connectors = {c['connector_type']: c for c in existing.get('connectors', [])}
    except Exception:
        connectors = {}
    connectors[connector_type] = data
    _CONNECTORS_FILE.write_text(json.dumps({'connectors': list(connectors.values())}, indent=2))


@app.get('/api/super/connectors')
async def list_connectors(_: dict = Depends(require_super_admin)):
    """List all connector definitions with status (credentials redacted)."""
    return {'connectors': _load_connectors()}


@app.put('/api/super/connectors/{connector_type}')
async def upsert_connector(connector_type: str, request: Request, _: dict = Depends(require_super_admin)):
    """Create or update a connector's credentials and configuration."""
    body = await request.json()
    if connector_type not in [d['connector_type'] for d in _CONNECTOR_DEFAULTS]:
        raise HTTPException(status_code=400, detail=f'Unknown connector type: {connector_type}')
    try:
        existing = json.loads(_CONNECTORS_FILE.read_text())
        connectors = {c['connector_type']: c for c in existing.get('connectors', [])}
    except Exception:
        connectors = {}
    prev = connectors.get(connector_type, {})
    creds = {}
    if connector_type == 'microsoft_azure':
        if body.get('tenant_id'):  creds['tenant_id']     = body['tenant_id']
        if body.get('client_id'):  creds['client_id']     = body['client_id']
        if body.get('client_secret'): creds['client_secret'] = body['client_secret']
    elif connector_type == 'atlassian':
        if body.get('email'):          creds['email']           = body['email']
        if body.get('api_token'):      creds['api_token']       = body['api_token']
        if body.get('confluence_url'): creds['confluence_url']  = body['confluence_url']
        if body.get('jira_url'):       creds['jira_url']        = body['jira_url']
    # Merge: keep old creds if new ones not supplied
    merged_creds = {**prev.get('credentials', {}), **creds}
    record = {
        'connector_type': connector_type,
        'display_name': body.get('display_name', prev.get('display_name', connector_type)),
        'status': 'disconnected' if merged_creds else 'not_configured',
        'enabled': body.get('enabled', prev.get('enabled', False)),
        'credentials': merged_creds,
    }
    _save_connector(connector_type, record)
    safe = {k: v for k, v in record.items() if k != 'credentials'}
    safe['has_credentials'] = bool(merged_creds)
    return safe


@app.post('/api/super/connectors/{connector_type}/test')
async def test_connector(connector_type: str, _: dict = Depends(require_super_admin)):
    """Test connector reachability. Returns {ok, message}."""
    try:
        data = json.loads(_CONNECTORS_FILE.read_text())
        connectors = {c['connector_type']: c for c in data.get('connectors', [])}
    except Exception:
        connectors = {}
    connector = connectors.get(connector_type)
    if not connector or not connector.get('credentials'):
        return {'ok': False, 'message': 'Connector not configured. Save credentials first.'}
    creds = connector.get('credentials', {})
    # Basic reachability test (no actual OAuth — just validate fields present)
    if connector_type == 'microsoft_azure':
        required = ['tenant_id', 'client_id', 'client_secret']
        missing = [k for k in required if not creds.get(k)]
        if missing:
            return {'ok': False, 'message': f'Missing fields: {", ".join(missing)}'}
        # Try a token endpoint ping
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                tenant = creds['tenant_id']
                resp = await client.get(
                    f'https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration'
                )
            if resp.status_code == 200:
                return {'ok': True, 'message': 'Microsoft tenant endpoint reachable. Credentials format valid.'}
            return {'ok': False, 'message': f'Microsoft endpoint returned HTTP {resp.status_code}'}
        except Exception as e:
            return {'ok': False, 'message': f'Network error: {str(e)[:120]}'}
    elif connector_type == 'atlassian':
        required = ['email', 'api_token']
        missing = [k for k in required if not creds.get(k)]
        if missing:
            return {'ok': False, 'message': f'Missing fields: {", ".join(missing)}'}
        try:
            import base64 as _b64
            token = _b64.b64encode(f"{creds['email']}:{creds['api_token']}".encode()).decode()
            base_url = creds.get('confluence_url') or creds.get('jira_url', '')
            if not base_url:
                return {'ok': False, 'message': 'No Confluence or Jira URL provided.'}
            base_url = base_url.rstrip('/')
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f'{base_url}/rest/api/user/current',
                    headers={'Authorization': f'Basic {token}', 'Accept': 'application/json'}
                )
            if resp.status_code == 200:
                data = resp.json()
                name = data.get('displayName') or data.get('name', 'unknown')
                return {'ok': True, 'message': f'Authenticated as {name}'}
            return {'ok': False, 'message': f'Atlassian returned HTTP {resp.status_code}'}
        except Exception as e:
            return {'ok': False, 'message': f'Network error: {str(e)[:120]}'}
    return {'ok': False, 'message': 'Test not implemented for this connector type.'}


@app.delete('/api/super/connectors/{connector_type}')
async def delete_connector(connector_type: str, _: dict = Depends(require_super_admin)):
    """Delete a connector configuration."""
    try:
        existing = json.loads(_CONNECTORS_FILE.read_text())
        connectors = {c['connector_type']: c for c in existing.get('connectors', [])}
    except Exception:
        connectors = {}
    if connector_type not in connectors:
        raise HTTPException(status_code=404, detail='Connector not found')
    del connectors[connector_type]
    _CONNECTORS_FILE.write_text(json.dumps({'connectors': list(connectors.values())}, indent=2))
    return {'ok': True, 'deleted': connector_type}


@app.get('/api/super/workers/{worker_id}/connector-scope')
async def get_worker_connector_scope(worker_id: str, _: dict = Depends(require_super_admin)):
    """Return the connector_scope for a worker."""
    worker = _find_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail='Worker not found')
    return {'worker_id': worker_id, 'connector_scope': worker.get('connector_scope', {})}


@app.put('/api/super/workers/{worker_id}/connector-scope/{connector_type}')
async def set_worker_connector_scope(
    worker_id: str,
    connector_type: str,
    request: Request,
    _: dict = Depends(require_super_admin),
):
    """Set the connector scope for a specific connector on a worker."""
    body = await request.json()
    workers = _load_workers()
    target = None
    for w in workers:
        if w.get('worker_id') == worker_id:
            target = w
            break
    if not target:
        raise HTTPException(status_code=404, detail='Worker not found')
    if 'connector_scope' not in target:
        target['connector_scope'] = {}
    target['connector_scope'][connector_type] = body
    _save_workers(workers)
    return {'worker_id': worker_id, 'connector_type': connector_type, 'scope': body}


@app.get('/api/admin/tools')
async def list_tools_for_admin(user: dict = Depends(require_admin)):
    """Return all tools from SAJHA with their config (for admin tool library view)."""
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            from agent.tools import SAJHA_BASE, _service_headers
            r = await client.get(SAJHA_BASE + '/api/tools/list', headers=_service_headers())
        if r.status_code == 200:
            return r.json()
        return {'tools': [], 'error': f'SAJHA returned {r.status_code}'}
    except Exception as e:
        return {'tools': [], 'error': str(e)}


# ── Documentation screenshot helper ────────────────────────────────────────────
import base64 as _b64

class _ScreenshotPayload(BaseModel):
    name: str
    data: str

@app.post('/api/dev/screenshot')
async def save_dev_screenshot(payload: _ScreenshotPayload):
    """Accept a base64 screenshot from the browser and save it to Documentation/screenshots/."""
    save_dir = pathlib.Path(__file__).parent / 'Documentation' / 'screenshots'
    save_dir.mkdir(parents=True, exist_ok=True)
    img_data = payload.data
    if ',' in img_data:
        img_data = img_data.split(',', 1)[1]
    filepath = save_dir / f"{payload.name}.png"
    with open(str(filepath), 'wb') as f:
        f.write(_b64.b64decode(img_data))
    return {'saved': str(filepath)}


# ── Static frontend (dev: one port; Docker: nginx serves this instead) ─────────
_PUBLIC = pathlib.Path(__file__).parent / 'public'
if _PUBLIC.is_dir():
    app.mount('/', StaticFiles(directory=str(_PUBLIC), html=True), name='static')
