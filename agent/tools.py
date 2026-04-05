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

# Per-request worker context — set by agent_server before each agent invocation.
# Carries user_id, worker_id, domain_data_path, common_data_path for SAJHA headers + audit.
_worker_ctx: ContextVar[dict] = ContextVar('worker_ctx', default={})

_AUDIT_FILE = pathlib.Path('sajhamcpserver/data/audit/tool_calls.jsonl')


def _service_headers() -> dict:
    """Build SAJHA request headers, injecting worker context for path scoping and audit."""
    ctx = _worker_ctx.get()
    headers = {'Authorization': _SAJHA_API_KEY}
    if ctx:
        if ctx.get('worker_id'):
            headers['X-Worker-Id'] = ctx['worker_id']
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
    return headers


# Keep _get_token for any legacy callers — delegates to API key path
async def _get_token() -> str:
    return _SAJHA_API_KEY


_MAX_TOOL_OUTPUT_CHARS = 12_000  # ~3k tokens per tool — keeps accumulated results well within context

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

    serialised = json.dumps(result)
    if len(serialised) <= _MAX_TOOL_OUTPUT_CHARS:
        return result
    truncated = serialised[:_MAX_TOOL_OUTPUT_CHARS]
    return {
        '_truncated': True,
        '_tool': tool_name,
        '_note': f'Output truncated from {len(serialised):,} to {_MAX_TOOL_OUTPUT_CHARS:,} chars to stay within context limits.',
        'data': truncated,
    }


def _log_audit(tool_name: str, duration_ms: float, status: str):
    """Append one structured JSONL audit log line. Non-blocking best-effort."""
    try:
        import datetime
        ctx = _worker_ctx.get()
        _AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'user_id': ctx.get('user_id', ''),
            'worker_id': ctx.get('worker_id', ''),
            'tool_name': tool_name,
            'duration_ms': round(duration_ms, 1),
            'status': status,
        })
        with open(_AUDIT_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


async def _call_sajha(tool_name: str, args: dict) -> dict:
    t0 = time.time()
    status = 'success'
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as c:
            r = await c.post(f'{SAJHA_BASE}/api/tools/execute',
                headers=_service_headers(),
                json={'tool': tool_name, 'arguments': args})
            r.raise_for_status()
            result = r.json()['result']
            return _truncate_result(result, tool_name)
    except httpx.TimeoutException:
        status = 'timeout'
        return {'error': f'{tool_name} timed out after 30s'}
    except httpx.HTTPStatusError as e:
        status = f'http_{e.response.status_code}'
        return {'error': f'{tool_name} returned HTTP {e.response.status_code}'}
    except Exception as e:
        status = 'error'
        return {'error': f'{tool_name} failed: {str(e)}'}
    finally:
        _log_audit(tool_name, (time.time() - t0) * 1000, status)


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
    """Fetch all tools from SAJHA and create LangChain tool wrappers."""
    import httpx as _httpx

    try:
        # trust_env=False prevents httpx from picking up system SOCKS/HTTP proxy env vars.
        # Without this, if ALL_PROXY or HTTPS_PROXY is set to a socks5:// URL and the
        # 'socksio' package is not installed, tool discovery fails silently.
        list_r = _httpx.post(
            f'{SAJHA_BASE}/api/mcp',
            headers={'Authorization': _SAJHA_API_KEY},
            json={'jsonrpc': '2.0', 'id': '1', 'method': 'tools/list', 'params': {}},
            timeout=10.0,
            trust_env=False,
        )
        tools_data = list_r.json().get('result', {}).get('tools', [])

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

        print(f'Discovered {len(dynamic_tools)} additional SAJHA tools')
        return dynamic_tools

    except Exception as e:
        print(f'Warning: SAJHA tool discovery failed: {e}')
        print('Falling back to static tools only')
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
