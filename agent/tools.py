from dotenv import load_dotenv
load_dotenv()

import httpx
import os
import json
import time
import pathlib
from contextvars import ContextVar
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field, create_model
from typing import Any, Optional

SAJHA_BASE = os.getenv('SAJHA_BASE_URL', 'http://localhost:3002')
# Service key for SAJHA — uses direct Authorization header (no "Bearer" prefix).
# Set SAJHA_API_KEY in .env to the full-access API key from sajhamcpserver/config/apikeys.json.
_SAJHA_API_KEY = os.getenv('SAJHA_API_KEY', 'sja_full_access_admin')

# REQ-17: Upstream SAJHA hardcodes is_admin=False for API-key auth, so it cannot
# grant tool access. We login as an admin user and cache a JWT instead.
# These env vars are only used when SAJHA_AUTH_MODE=jwt (i.e. against upstream).
_SAJHA_AUTH_MODE = os.getenv('SAJHA_AUTH_MODE', 'apikey')   # 'apikey' (legacy fork) or 'jwt' (upstream)
_SAJHA_ADMIN_USER = os.getenv('SAJHA_ADMIN_USER', 'admin')
_SAJHA_ADMIN_PASS = os.getenv('SAJHA_ADMIN_PASS', 'admin123')
_SAJHA_JWT_CACHE: dict = {'token': '', 'expires_at': 0}


def _get_sajha_jwt() -> str:
    """REQ-17: Login as admin once, cache JWT, refresh on expiry.
    Only used when SAJHA_AUTH_MODE=jwt (upstream pathway)."""
    import time as _time
    now = _time.time()
    if _SAJHA_JWT_CACHE['token'] and now < _SAJHA_JWT_CACHE['expires_at'] - 60:
        return _SAJHA_JWT_CACHE['token']
    try:
        import httpx as _httpx
        r = _httpx.post(
            f'{SAJHA_BASE}/api/auth/login',
            json={'user_id': _SAJHA_ADMIN_USER, 'password': _SAJHA_ADMIN_PASS},
            timeout=10.0, trust_env=False,
        )
        r.raise_for_status()
        data = r.json()
        token = data.get('token') or data.get('access_token') or ''
        if token:
            _SAJHA_JWT_CACHE['token'] = token
            _SAJHA_JWT_CACHE['expires_at'] = now + 3000  # token has 1hr life; refresh at 50min
            return token
    except Exception as e:
        print(f'WARNING: SAJHA JWT login failed: {e}; falling back to API key')
    return ''

# Per-request worker context — set by agent_server before each agent invocation.
# Carries user_id, worker_id, domain_data_path, common_data_path for SAJHA headers + audit.
_worker_ctx: ContextVar[dict] = ContextVar('worker_ctx', default={})

_AUDIT_FILE = pathlib.Path('sajhamcpserver/data/audit/tool_calls.jsonl')


def _service_headers() -> dict:
    """Build SAJHA request headers, injecting worker context for path scoping and audit.

    REQ-17: Upstream SAJHA v5.0.0 expects `X-API-Key` (not bare `Authorization`).
    We send both so the call works against either our legacy fork or upstream.
    """
    ctx = _worker_ctx.get()
    if _SAJHA_AUTH_MODE == 'jwt':
        jwt = _get_sajha_jwt()
        headers = {'Authorization': f'Bearer {jwt}'} if jwt else {'X-API-Key': _SAJHA_API_KEY}
    else:
        headers = {
            'Authorization': _SAJHA_API_KEY,   # legacy fork — bare key as Authorization
            'X-API-Key': _SAJHA_API_KEY,        # upstream v5.0.0 expects this header
        }
    if ctx:
        if ctx.get('worker_id'):
            headers['X-Worker-Id'] = ctx['worker_id']
        if ctx.get('user_id'):
            headers['X-User-Id'] = ctx['user_id']
        if ctx.get('domain_data_path'):
            headers['X-Worker-Data-Root'] = ctx['domain_data_path']
        if ctx.get('common_data_path'):
            headers['X-Worker-Common-Root'] = ctx['common_data_path']
        if ctx.get('my_data_path'):
            # REQ-MD-01: my_data is per-user — append user_id sub-directory at runtime
            uid = ctx.get('user_id', '')
            if uid:
                headers['X-Worker-My-Data-Root'] = ctx['my_data_path'].rstrip('/') + '/' + uid
            else:
                headers['X-Worker-My-Data-Root'] = ctx['my_data_path']
        # Workflow paths — forwarded directly so workflow_tools don't need to derive them
        if ctx.get('workflows_path'):
            headers['X-Worker-Verified-Workflows'] = ctx['workflows_path']
        if ctx.get('my_workflows_path'):
            headers['X-Worker-My-Workflows'] = ctx['my_workflows_path']
    return headers


def _worker_context_for_args() -> dict:
    """REQ-17: Build the `_worker_context` dict that gets embedded in tool arguments.

    Upstream's tool.execute() only receives `arguments` — it has no access to HTTP
    headers. So we embed worker scope inside arguments under a `_worker_context` key.
    Our tools-pack tools read from this dict via tools_pack_lib.worker_ctx.get_data_layers().

    Paths are converted to absolute so they resolve correctly regardless of upstream's CWD.
    """
    ctx = _worker_ctx.get() or {}
    uid = ctx.get('user_id', '')
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    sajha_root = repo_root / 'sajhamcpserver'

    def _abs(p: str) -> str:
        if not p:
            return ''
        path = pathlib.Path(p)
        if path.is_absolute():
            return str(path)
        # Strip leading ./ then resolve against sajhamcpserver/ where worker data lives
        p_clean = p.lstrip('./').lstrip('/')
        return str(sajha_root / p_clean)

    my_data = ctx.get('my_data_path', '')
    if my_data and uid:
        my_data = my_data.rstrip('/') + '/' + uid
    return {
        'worker_id':         ctx.get('worker_id', ''),
        'user_id':           uid,
        'domain_data_path':  _abs(ctx.get('domain_data_path', '')),
        'common_data_path':  _abs(ctx.get('common_data_path', '')),
        'my_data_path':      _abs(my_data),
        'workflows_path':    _abs(ctx.get('workflows_path', '')),
        'my_workflows_path': _abs(ctx.get('my_workflows_path', '')),
    }


# Keep _get_token for any legacy callers — delegates to API key path
async def _get_token() -> str:
    return _SAJHA_API_KEY


_MAX_TOOL_OUTPUT_CHARS = 400_000  # ~100k tokens per tool

# Per-tool output limits (override _MAX_TOOL_OUTPUT_CHARS for tools that legitimately return large text)
_TOOL_OUTPUT_LIMITS: dict = {
    'file_read':       400_000,  # markdown — large filing sections
    'msdoc_read_word': 400_000,  # Word docs — heading extraction can return large sections
    'pdf_read':        400_000,  # PDFs — heading extraction or ranged page reads
}

# Per-tool HTTP timeouts (override 30s default for tools that hit large external docs)
_TOOL_TIMEOUTS: dict = {
    'edgar_extract_section': 120.0,  # streams up to 15MB SEC filing HTML
    'edgar_get_statements':   90.0,
    'edgar_risk_summary':     90.0,
    'edgar_earnings_brief':   90.0,
    'edgar_company_brief':    90.0,
    'stream_sec_section':    120.0,
    # DuckDB: first-call initializes C extension thread pool — give extra headroom
    'duckdb_list_files':      60.0,
    'duckdb_query':           60.0,
    'duckdb_list_tables':     60.0,
    'duckdb_get_schema':      60.0,
    'duckdb_refresh_views':   60.0,
    # Python execution can involve computation-heavy analytics
    'python_execute':         120.0,
    'python_run_script':      120.0,
}

# Tools that return large HTML content — strip html field, set _chart_ready flag instead
_HTML_OUTPUT_TOOLS = {'generate_chart', 'create_report', 'render_document', 'create_dashboard',
                      'python_execute', 'python_run_script'}


def _truncate_result(result: dict, tool_name: str) -> dict:
    """Truncate oversized tool results before they enter the LangGraph checkpoint.
    For visualization/python tools: strip html field, keep metadata + _chart_ready flag.
    """
    import os as _os

    if tool_name in _HTML_OUTPUT_TOOLS and isinstance(result, dict):
        stripped = {k: v for k, v in result.items() if k != 'html'}
        # Basename only — never expose full server paths
        if 'html_file' in stripped and stripped['html_file']:
            stripped['html_file'] = _os.path.basename(stripped['html_file'])
        if 'png_path' in stripped and stripped['png_path']:
            stripped['png_path'] = _os.path.basename(stripped['png_path'])
        # Mark as chart-ready so agent_server emits canvas SSE event
        stripped['_chart_ready'] = True
        serialised = json.dumps(stripped)
        if len(serialised) <= _MAX_TOOL_OUTPUT_CHARS:
            return stripped
        # Even stripped version too large — keep only essentials
        return {
            '_chart_ready': True,
            '_truncated': True,
            '_tool': tool_name,
            'chart_type': result.get('chart_type', result.get('_tool', tool_name)),
            'title': result.get('title', ''),
            'html_file': _os.path.basename(result.get('html_file', '') or ''),
            'png_path': _os.path.basename(result.get('png_path', '') or ''),
            'data_rows_plotted': result.get('data_rows_plotted'),
            'figures': result.get('figures', []),
        }

    limit = _TOOL_OUTPUT_LIMITS.get(tool_name, _MAX_TOOL_OUTPUT_CHARS)
    serialised = json.dumps(result)
    if len(serialised) <= limit:
        return result
    truncated = serialised[:limit]
    return {
        '_truncated': True,
        '_tool': tool_name,
        '_note': f'Output truncated from {len(serialised):,} to {limit:,} chars to stay within context limits.',
        'data': truncated,
    }


_DB_ENABLED = bool(os.getenv('DATABASE_URL'))
if _DB_ENABLED:
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'sajhamcpserver'))
    from sajha.db import repo as _db_repo  # noqa: E402


async def _log_audit(tool_name: str, duration_ms: float, status: str,
                     tool_args: dict = None, result_summary: str = None):
    """Audit log — dual-write to PostgreSQL (REQ-07) and JSONL fallback."""
    import datetime
    ctx = _worker_ctx.get()
    user_id = ctx.get('user_id', '')
    worker_id = ctx.get('worker_id', '')
    thread_id = ctx.get('thread_id', None)

    # PostgreSQL path — direct await (caller is always async)
    if _DB_ENABLED:
        try:
            await _db_repo.log_tool_call(
                user_id=user_id, worker_id=worker_id, tool_name=tool_name,
                elapsed_ms=round(duration_ms, 1), status=status,
                thread_id=thread_id, tool_args=tool_args,
                result_summary=result_summary,
            )
        except Exception:
            pass

    # JSONL fallback (always write for dual-write safety)
    try:
        _AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'user_id': user_id,
            'worker_id': worker_id,
            'thread_id': thread_id,
            'tool_name': tool_name,
            'duration_ms': round(duration_ms, 1),
            'status': status,
        })
        with open(_AUDIT_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _result_summary(result: dict) -> str:
    """Return a short plain-text summary of a tool result for audit storage."""
    if not isinstance(result, dict):
        return str(result)[:500]
    # Strip large fields; keep top-level keys + short values
    try:
        return json.dumps({k: v for k, v in result.items()
                           if k not in ('html', 'data') and not isinstance(v, (list, dict))
                           or k in ('count', 'total', 'error', 'success', '_truncated')},
                          default=str)[:500]
    except Exception:
        return ''


async def _call_sajha(tool_name: str, args: dict) -> dict:
    t0 = time.time()
    status = 'success'
    result: dict = {}
    timeout = _TOOL_TIMEOUTS.get(tool_name, 30.0)
    # REQ-17: inject worker context inside arguments so upstream tools can read it
    # (upstream's execute() only receives `arguments`, no request access).
    enriched_args = dict(args) if args else {}
    enriched_args['_worker_context'] = _worker_context_for_args()
    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as c:
            r = await c.post(f'{SAJHA_BASE}/api/tools/execute',
                headers=_service_headers(),
                json={'tool': tool_name, 'arguments': enriched_args})
            r.raise_for_status()
            payload = r.json()
            # Legacy fork shape:    {"result": {...}}
            # Upstream v5.0.0 shape: {"success": true, "result": {...}} or {"value": {...}, "error": null}
            result = payload.get('result') if 'result' in payload else payload
            # Upstream StepResult envelope: {value, error, trace, duration, confidence, _composition}
            if isinstance(result, dict) and 'value' in result and ('error' in result or '_composition' in result):
                if result.get('error'):
                    result = {'error': result['error']}
                else:
                    result = result.get('value') or {}
            return _truncate_result(result, tool_name)
    except httpx.TimeoutException:
        status = 'timeout'
        result = {'error': f'{tool_name} timed out after {int(timeout)}s'}
        return result
    except httpx.HTTPStatusError as e:
        status = f'http_{e.response.status_code}'
        result = {'error': f'{tool_name} returned HTTP {e.response.status_code}'}
        return result
    except Exception as e:
        status = 'error'
        result = {'error': f'{tool_name} failed: {str(e)}'}
        return result
    finally:
        # Redact sensitive args before storing (password, api_key, token, secret)
        _safe_args = {k: '[REDACTED]' if any(s in k.lower() for s in ('password', 'api_key', 'token', 'secret')) else v
                      for k, v in args.items()} if args else None
        await _log_audit(tool_name, (time.time() - t0) * 1000, status,
                         tool_args=_safe_args, result_summary=_result_summary(result))


# ================================================================
# Static tools with custom docstrings (the original 6)
# ================================================================

@tool
async def get_counterparty_exposure(counterparty: str, date: str = '') -> dict:
    '''Returns current notional, MTM, PFE and net exposure for a counterparty.
    Use for: current risk snapshot, credit profile, collateral posted.
    counterparty: name or LEI. date: YYYY-MM-DD, defaults to today.
    '''
    return await _call_sajha('get_counterparty_exposure',
                             {'counterparty': counterparty, 'date': date})

@tool
async def get_trade_inventory(counterparty: str, asset_class: str = 'All') -> dict:
    '''Returns all open trade positions for a counterparty.
    Use for: trade-level breakdown, notional by asset class, MTM per position.
    '''
    return await _call_sajha('get_trade_inventory',
                             {'counterparty': counterparty, 'asset_class': asset_class})

@tool
async def get_credit_limits(counterparty: str) -> dict:
    '''Returns approved credit limits and current utilization.
    Use for: limit breach check, headroom analysis, approver details.
    '''
    return await _call_sajha('get_credit_limits', {'counterparty': counterparty})

@tool
async def get_historical_exposure(counterparty: str, date: str) -> dict:
    '''Returns point-in-time exposure snapshot for a specific historical date.
    Use for: QoQ trend analysis — call in parallel with four quarter-end dates.
    '''
    return await _call_sajha('get_historical_exposure',
                             {'counterparty': counterparty, 'date': date})

@tool
async def get_var_contribution(counterparty: str,
                               confidence_level: str = '99%') -> dict:
    '''Returns VaR contribution, marginal VaR, component VaR, and stress loss.
    Use for: portfolio risk contribution, VaR decomposition.
    '''
    return await _call_sajha('get_var_contribution',
                             {'counterparty': counterparty,
                              'confidence_level': confidence_level})

STATIC_TOOLS = [
    get_counterparty_exposure, get_trade_inventory, get_credit_limits,
    get_historical_exposure, get_var_contribution,
]
STATIC_TOOL_NAMES = {t.name for t in STATIC_TOOLS}


# ================================================================
# Dynamic tool discovery from SAJHA
# ================================================================

TYPE_MAP = {
    'string': (str, ''),
    'integer': (int, 0),
    'number': (float, 0.0),
    'boolean': (bool, False),
    'array': (list, []),
    'object': (dict, {}),
}


def _build_pydantic_model(tool_name: str, schema: dict):
    """Build a Pydantic model from a JSON Schema properties dict."""
    props = schema.get('properties', {})
    required = set(schema.get('required', []))
    fields = {}
    for name, prop in props.items():
        # Pydantic v2 rejects leading underscores — strip them (server-injected fields like _worker_context)
        safe_name = name.lstrip('_') or name
        ptype, default = TYPE_MAP.get(prop.get('type', 'string'), (str, ''))
        desc = prop.get('description', name)
        if name in required:
            fields[safe_name] = (ptype, Field(description=desc))
        else:
            ptype = Optional[ptype]
            prop_default = prop.get('default', None)
            fields[safe_name] = (ptype, Field(default=prop_default, description=desc))
    if not fields:
        fields['input'] = (Optional[str], Field(default='', description='Tool input'))
    model_name = tool_name.replace('-', '_').title().replace('_', '') + 'Input'
    return create_model(model_name, **fields)


def _make_dynamic_tool(name: str, description: str, schema: dict):
    """Create a StructuredTool that calls SAJHA for a discovered tool."""
    input_model = _build_pydantic_model(name, schema)
    sajha_name = name  # capture in closure

    async def _run(**kwargs) -> dict:
        args = {k: v for k, v in kwargs.items() if v is not None}
        return await _call_sajha(sajha_name, args)

    return StructuredTool.from_function(
        coroutine=_run,
        name=name,
        description=description,
        args_schema=input_model,
    )


def discover_sajha_tools() -> list:
    """Fetch all tools from SAJHA and create LangChain tool wrappers.

    Retries up to 6 times (with 5-second gaps) so that SAJHA has time to
    finish loading all its tool configs before the agent module is ready.
    This prevents the startup race condition where only a few tools are
    registered when the first tools/list call lands.
    """
    import httpx as _httpx
    import time as _time

    _MIN_EXPECTED_TOOLS = 30  # SAJHA should always serve more than this

    for attempt in range(6):
        try:
            # trust_env=False prevents httpx from picking up system SOCKS/HTTP proxy env vars.
            # Without this, if ALL_PROXY or HTTPS_PROXY is set to a socks5:// URL and the
            # 'socksio' package is not installed, tool discovery fails silently.
            # REQ-17: upstream uses /mcp not /api/mcp, plus JWT or X-API-Key
            if _SAJHA_AUTH_MODE == 'jwt':
                jwt = _get_sajha_jwt()
                disc_headers = {'Authorization': f'Bearer {jwt}'} if jwt else {'X-API-Key': _SAJHA_API_KEY}
                disc_path = '/mcp'
            else:
                disc_headers = {'Authorization': _SAJHA_API_KEY, 'X-API-Key': _SAJHA_API_KEY}
                disc_path = '/api/mcp'
            list_r = _httpx.post(
                f'{SAJHA_BASE}{disc_path}',
                headers=disc_headers,
                json={'jsonrpc': '2.0', 'id': '1', 'method': 'tools/list', 'params': {}},
                timeout=10.0,
                trust_env=False,
            )
            tools_data = list_r.json().get('result', {}).get('tools', [])

            # If SAJHA is still loading its tool registry, retry
            if len(tools_data) < _MIN_EXPECTED_TOOLS and attempt < 5:
                print(f'SAJHA returned only {len(tools_data)} tools on attempt {attempt+1} — retrying in 5s...')
                _time.sleep(5)
                continue

            dynamic_tools = []
            for t in tools_data:
                name = t.get('name', '')
                if name in STATIC_TOOL_NAMES:
                    continue
                desc = t.get('description', f'SAJHA tool: {name}')
                schema = t.get('inputSchema', {})
                try:
                    dynamic_tool = _make_dynamic_tool(name, desc, schema)
                    dynamic_tools.append(dynamic_tool)
                except Exception as e:
                    print(f'Warning: could not create tool wrapper for {name}: {e}')

            print(f'Discovered {len(dynamic_tools)} additional SAJHA tools (attempt {attempt+1})')
            return dynamic_tools

        except Exception as e:
            if attempt < 5:
                print(f'Warning: SAJHA tool discovery failed (attempt {attempt+1}): {e} — retrying in 5s...')
                _time.sleep(5)
            else:
                print(f'Warning: SAJHA tool discovery failed after 6 attempts: {e}')
                print('Falling back to static tools only')
                return []

    return []


# ================================================================
# Build final tool list: static + dynamic
# ================================================================

DYNAMIC_TOOLS = discover_sajha_tools()
AGENT_TOOLS = STATIC_TOOLS + DYNAMIC_TOOLS

# Tool name → tool object index for fast lookup
_TOOL_INDEX: dict = {t.name: t for t in AGENT_TOOLS}


def get_tools_for_worker(enabled_tools: list) -> list:
    """Return the subset of AGENT_TOOLS permitted for a worker's enabled_tools list.

    enabled_tools=['*'] or empty list → all tools (backward compatible).
    Otherwise returns only tools whose name is in the allowlist.
    """
    if not enabled_tools or enabled_tools == ['*']:
        return AGENT_TOOLS
    allowed = set(enabled_tools)
    return [t for t in AGENT_TOOLS if t.name in allowed]
