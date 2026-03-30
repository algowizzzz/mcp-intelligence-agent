import os, json, uuid
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from agent.agent import agent

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
            async for event in agent.astream_events(inp, config=config, version='v2'):
                t = event['event']
                if t == 'on_chat_model_stream':
                    chunk = event['data']['chunk']
                    # Only stream text content, not tool_use blocks
                    if hasattr(chunk, 'content'):
                        content = chunk.content
                        if isinstance(content, str) and content:
                            yield f"data: {json.dumps({'type': 'text', 'text': content})}\n\n"
                        elif isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get('type') == 'text' and block.get('text'):
                                    yield f"data: {json.dumps({'type': 'text', 'text': block['text']})}\n\n"
                                elif hasattr(block, 'text') and block.text:
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
            yield 'data: [DONE]\n\n'
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield 'data: [DONE]\n\n'

    return StreamingResponse(stream(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
