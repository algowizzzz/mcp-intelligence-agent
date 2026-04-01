import os, json, uuid
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from agent.agent import agent
from agent.tools import _get_token, SAJHA_BASE

load_dotenv()

app = FastAPI(title='MCP Intelligence Agent')
_cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:8080,http://127.0.0.1:8080').split(',')
app.add_middleware(CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r'https://.*\.vercel\.app',
    allow_methods=['GET', 'POST', 'OPTIONS'],
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


@app.get('/health')
async def health():
    return {'status': 'ok'}


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
