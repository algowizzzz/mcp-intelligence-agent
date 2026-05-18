"""worker_ctx — read per-request worker context from upstream's HTTP request.

Mirrors the X-Worker-* headers that our agent (agent/tools.py:_service_headers)
already sends to SAJHA. Upstream sees the headers and passes the request to
the tool's execute(); we extract context here.

Usage (inside a tool's execute()):

    from tools_pack.lib.worker_ctx import get_worker_ctx
    ctx = get_worker_ctx(self.request)   # request is injected by BaseMCPTool
    worker_id = ctx['worker_id']
    my_data_root = ctx['my_data_path']
"""
from typing import Dict, Any, Optional


HEADER_MAP = {
    'worker_id':            'X-Worker-Id',
    'user_id':              'X-User-Id',
    'domain_data_path':     'X-Worker-Data-Root',
    'common_data_path':     'X-Worker-Common-Root',
    'my_data_path':         'X-Worker-My-Data-Root',   # already user-scoped (agent appends user_id)
    'workflows_path':       'X-Worker-Verified-Workflows',
    'my_workflows_path':    'X-Worker-My-Workflows',
}


def get_worker_ctx(request: Any = None, fallback_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Return a dict with worker scope from request headers, with empty-string defaults."""
    headers: Dict[str, str] = {}
    if request is not None:
        try:
            headers = {k: request.headers.get(v, '') for k, v in HEADER_MAP.items()}
        except Exception:
            headers = {}
    if not any(headers.values()) and fallback_headers:
        headers = {k: fallback_headers.get(v, '') for k, v in HEADER_MAP.items()}
    if not headers:
        headers = {k: '' for k in HEADER_MAP}
    return headers


def get_data_layers(ctx: Dict[str, str], section: str = 'all') -> list:
    """Return [(layer_name, root_path), ...] for the requested scope.
    Mirrors the API of sajha/data_context.py:get_data_layers in our old fork,
    but takes context as a dict argument instead of reading Flask g."""
    layers = [
        ('my_data',     ctx.get('my_data_path', '').strip()),
        ('domain_data', ctx.get('domain_data_path', '').strip()),
        ('common',      ctx.get('common_data_path', '').strip()),
    ]
    if section == 'all':
        return [(n, p) for n, p in layers if p]
    return [(n, p) for n, p in layers if n == section and p]
