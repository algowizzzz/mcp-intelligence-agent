"""
Credit Limits Tool — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/credit_limits_tool.py.
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


class CreditLimitsTool(BaseMCPTool):
    """Retrieve credit limits and utilization data."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'counterparty': {
                    'type': 'string',
                    'description': 'Filter by counterparty name (optional). Returns all limit records if omitted.'
                },
            },
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'limits':  {'type': 'array'},
                '_source': {'type': 'string'},
            },
            'required': ['limits', '_source'],
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ctx = arguments.get('_worker_context') or {}
        relative_path = 'counterparties/credit_limits.json'
        try:
            data, source = _load_json(ctx, relative_path)
        except FileNotFoundError as exc:
            return {'limits': [], '_source': '', 'error': str(exc)}

        counterparty_filter = arguments.get('counterparty')
        if counterparty_filter:
            data = [
                r for r in data
                if str(r.get('counterparty', '')).lower() == counterparty_filter.lower()
            ]
        return {'limits': data, '_source': source}
