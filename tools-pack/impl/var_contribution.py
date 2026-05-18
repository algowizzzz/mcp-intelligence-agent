"""
VaR Contribution Tool — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/var_contribution_tool.py.
Worker scope comes from arguments['_worker_context']; data lookup walks the
worker data layers (my_data → domain_data → common).
"""

import json
import os
from typing import Any, Dict, List, Optional

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.worker_ctx import get_data_layers


def _resolve_relative(ctx: Dict[str, str], relative_path: str) -> Optional[str]:
    for _, root in get_data_layers(ctx, 'all'):
        candidate = os.path.join(root, relative_path)
        if os.path.isfile(candidate):
            return candidate
    return None


def _load_json(ctx: Dict[str, str], relative_path: str) -> (List[Dict], str):
    abs_path = _resolve_relative(ctx, relative_path)
    if abs_path is None:
        raise FileNotFoundError(
            f"Data file not found across worker layers: {relative_path}"
        )
    with open(abs_path, 'r', encoding='utf-8') as fh:
        return json.load(fh), abs_path


class VarContributionTool(BaseMCPTool):
    """Retrieve Value-at-Risk contribution data per counterparty."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'counterparty': {
                    'type': 'string',
                    'description': 'Filter by counterparty name (optional). Returns all VaR records if omitted.'
                },
            },
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'var_data': {'type': 'array'},
                '_source':  {'type': 'string'},
            },
            'required': ['var_data', '_source'],
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ctx = arguments.get('_worker_context') or {}
        relative_path = 'counterparties/var.json'
        try:
            data, source = _load_json(ctx, relative_path)
        except FileNotFoundError as exc:
            return {'var_data': [], '_source': '', 'error': str(exc)}

        counterparty_filter = arguments.get('counterparty')
        if counterparty_filter:
            data = [
                r for r in data
                if str(r.get('counterparty', '')).lower() == counterparty_filter.lower()
            ]
        return {'var_data': data, '_source': source}
