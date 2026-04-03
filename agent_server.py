import os, json, uuid, pathlib, base64, sys as _sys, hmac, hashlib, time
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
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
_SAJHA_USERS_FILE = pathlib.Path('sajhamcpserver/config/users.json')


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


def _get_user_is_admin(user_id: str) -> bool:
    try:
        data = json.loads(_SAJHA_USERS_FILE.read_text())
        for u in data.get('users', []):
            if u.get('user_id') == user_id:
                return 'admin' in u.get('roles', [])
    except Exception:
        pass
    return False


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
app.add_middleware(CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r'https://.*\.vercel\.app',
    allow_methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
)

# API key auth — keys are a comma-separated list in AGENT_API_KEYS env var.
# If AGENT_API_KEYS is unset or empty, auth is disabled (local dev mode).
_raw_keys = os.getenv('AGENT_API_KEYS', '')
_VALID_KEYS: set[str] = {k.strip() for k in _raw_keys.split(',') if k.strip()} if _raw_keys else set()

_bearer = HTTPBearer(auto_error=False)

def require_api_key(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    if not _VALID_KEYS:
        return  # auth disabled
    if creds is None or creds.credentials not in _VALID_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or missing API key')


def require_admin(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing token')
    try:
        payload = _jwt_decode(creds.credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    if not payload.get('is_admin'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin access required')
    return payload


@app.get('/health')
async def health():
    return {'status': 'ok'}


class LoginRequest(BaseModel):
    user_id: str
    password: str

@app.post('/api/auth/login')
async def auth_login(req: LoginRequest):
    """Proxy login to SAJHA, return a JWT with is_admin claim."""
    if not req.user_id or not req.password:
        raise HTTPException(status_code=400, detail='user_id and password required')
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(
                f'{SAJHA_BASE}/api/auth/login',
                json={'user_id': req.user_id, 'password': req.password},
            )
            if r.status_code == 401:
                raise HTTPException(status_code=401, detail='Invalid credentials')
            r.raise_for_status()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'SAJHA unreachable: {e}')
    is_admin = _get_user_is_admin(req.user_id)
    token = _jwt_encode({
        'user_id': req.user_id,
        'is_admin': is_admin,
        'exp': time.time() + 86400 * 7,  # 7 days
    })
    return {'token': token, 'is_admin': is_admin, 'user_id': req.user_id}


@app.post('/api/files/upload')
async def upload_file(file: UploadFile = File(...), _: None = Depends(require_api_key)):
    """Proxy file uploads to SAJHA — frontend only needs the agent API key."""
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
                    # Token expired — clear cache and retry once (same as _call_sajha)
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
    """Reject filenames with path traversal or non-.md files."""
    name = pathlib.Path(filename).name
    if not name.endswith('.md') or '/' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail='filename must be a plain .md filename')
    return name


# ── Workspace files ────────────────────────────────────────────────────────────

@app.get('/api/workspace/files')
async def list_workspace_files(_: None = Depends(require_api_key)):
    """List files in the uploads directory."""
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
    """List all workflow MD files with metadata."""
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
    # Sort by last_used desc (None last)
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
        # Safety: resolve and confirm it stays inside root
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
    # Detect if text
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
    src_full.rename(dst_full)
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
    new_name = pathlib.Path(req.new_name).name  # safety: basename only
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
        full.rmdir()  # only succeeds if empty
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
async def admin_tree(section: str, _: dict = Depends(require_admin)):
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
    root = _resolve_admin_path(section)
    folder = _resolve_admin_path(section, path) if path else root
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
        import shutil
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
    new_name = pathlib.Path(req.new_name).name
    new_full = full.parent / new_name
    full.rename(new_full)
    build_index(str(root))
    new_path = str(new_full.relative_to(root)).replace('\\', '/')
    return {'new_path': new_path}


@app.post('/api/admin/move')
async def admin_move(req: AdminMoveRequest, _: dict = Depends(require_admin)):
    root = _resolve_admin_path(req.section)
    src_full = _resolve_admin_path(req.section, req.src_path)
    dst_full = _resolve_admin_path(req.section, req.dest_folder) / src_full.name
    if not src_full.exists():
        raise HTTPException(status_code=404, detail='Source not found')
    dst_full.parent.mkdir(parents=True, exist_ok=True)
    src_full.rename(dst_full)
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


@app.get('/api/admin/validate/{section}/{path:path}')
async def admin_validate(section: str, path: str, _: dict = Depends(require_admin)):
    full = _resolve_admin_path(section, path)
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail='File not found')
    content = full.read_text(encoding='utf-8', errors='replace')
    # Parse YAML frontmatter
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
                    # Only stream text content, not tool_use blocks
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
                    # ToolMessage output may be an object; convert to serializable form
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
            # Canvas envelope detection
            import json as _json, re as _re
            assembled = ''.join(full_text).strip()

            def _try_parse_envelope(s):
                """Try to parse a canvas envelope JSON from string s."""
                try:
                    obj = _json.loads(s)
                    if 'summary' in obj and 'canvas' in obj:
                        return obj
                except Exception:
                    pass
                return None

            envelope = None

            # 1. Code fence: ```json { ... } ```
            _fence_match = _re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', assembled)
            if _fence_match:
                envelope = _try_parse_envelope(_fence_match.group(1).strip())

            # 2. Bare JSON that is the entire response
            if not envelope and assembled.startswith('{'):
                envelope = _try_parse_envelope(assembled)

            # 3. JSON envelope anywhere in the text (agent prepended prose before the JSON)
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
