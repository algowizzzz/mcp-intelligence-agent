from dotenv import load_dotenv
load_dotenv()

import httpx
import os
import json
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field, create_model
from typing import Any, Optional

SAJHA_BASE = os.getenv('SAJHA_BASE_URL', 'http://localhost:3002')
_sajha_token: str | None = None


async def _get_token() -> str:
    global _sajha_token
    if _sajha_token:
        return _sajha_token
    async with httpx.AsyncClient() as c:
        r = await c.post(f'{SAJHA_BASE}/api/auth/login',
            json={'user_id': 'risk_agent', 'password': os.getenv('SAJHA_PASSWORD')})
        _sajha_token = r.json()['token']
        return _sajha_token


_MAX_TOOL_OUTPUT_CHARS = 12_000  # ~3k tokens per tool — keeps accumulated results well within context


def _truncate_result(result: dict, tool_name: str) -> dict:
    """Truncate oversized tool results before they enter the LangGraph checkpoint."""
    serialised = json.dumps(result)
    if len(serialised) <= _MAX_TOOL_OUTPUT_CHARS:
        return result
    # Return a trimmed JSON string with a clear truncation notice
    truncated = serialised[:_MAX_TOOL_OUTPUT_CHARS]
    # Close the JSON cleanly enough for the LLM to parse what's there
    return {
        '_truncated': True,
        '_tool': tool_name,
        '_note': f'Output truncated from {len(serialised):,} to {_MAX_TOOL_OUTPUT_CHARS:,} chars to stay within context limits.',
        'data': truncated,
    }


async def _call_sajha(tool_name: str, args: dict) -> dict:
    global _sajha_token
    token = await _get_token()
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(f'{SAJHA_BASE}/api/tools/execute',
                headers={'Authorization': f'Bearer {token}'},
                json={'tool': tool_name, 'arguments': args})
            if r.status_code == 401:
                _sajha_token = None
                return await _call_sajha(tool_name, args)
            r.raise_for_status()
            result = r.json()['result']
            return _truncate_result(result, tool_name)
    except httpx.TimeoutException:
        return {'error': f'{tool_name} timed out after 30s'}
    except httpx.HTTPStatusError as e:
        return {'error': f'{tool_name} returned HTTP {e.response.status_code}'}
    except Exception as e:
        return {'error': f'{tool_name} failed: {str(e)}'}


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
        ptype, default = TYPE_MAP.get(prop.get('type', 'string'), (str, ''))
        desc = prop.get('description', name)
        if name in required:
            fields[name] = (ptype, Field(description=desc))
        else:
            ptype = Optional[ptype]
            prop_default = prop.get('default', default)
            fields[name] = (ptype, Field(default=prop_default, description=desc))
    if not fields:
        fields['input'] = (Optional[str], Field(default='', description='Tool input'))
    model_name = tool_name.replace('-', '_').title().replace('_', '') + 'Input'
    return create_model(model_name, **fields)


def _make_dynamic_tool(name: str, description: str, schema: dict):
    """Create a StructuredTool that calls SAJHA for a discovered tool."""
    input_model = _build_pydantic_model(name, schema)
    sajha_name = name  # capture in closure

    async def _run(**kwargs) -> dict:
        # Remove None values
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
        # Login synchronously at import time
        login_r = _httpx.post(
            f'{SAJHA_BASE}/api/auth/login',
            json={'user_id': 'risk_agent', 'password': os.getenv('SAJHA_PASSWORD')},
            timeout=10.0
        )
        token = login_r.json()['token']

        # List all tools via MCP protocol
        list_r = _httpx.post(
            f'{SAJHA_BASE}/api/mcp',
            headers={'Authorization': f'Bearer {token}'},
            json={'jsonrpc': '2.0', 'id': '1', 'method': 'tools/list', 'params': {}},
            timeout=10.0
        )
        tools_data = list_r.json().get('result', {}).get('tools', [])

        dynamic_tools = []
        for t in tools_data:
            name = t.get('name', '')
            # Skip tools we already have static wrappers for
            if name in STATIC_TOOL_NAMES:
                continue
            # (no Tavily tools are skipped — all 4 are exposed directly)
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
