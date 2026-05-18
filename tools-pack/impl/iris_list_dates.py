"""
IRIS CCR — list available snapshot dates.

Ported from sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py
(`IrisListDatesTool`). Reads worker scope from `arguments['_worker_context']`.
"""

from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.iris_base import valid_dates


class IrisListDates(BaseMCPTool):
    """Return the list of snapshot dates available in iris_combined.csv."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                '_worker_context': {'type': 'object', 'description': 'Injected by agent'},
            },
            'required': [],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'dates':  {'type': 'array', 'items': {'type': 'string'}},
                'count':  {'type': 'integer'},
                'latest': {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ctx = arguments.get('_worker_context') or {}
        try:
            dates = valid_dates(ctx)
        except FileNotFoundError as exc:
            return {'error': True, 'error_code': 'NO_DATA', 'message': str(exc),
                    'dates': [], 'count': 0, 'latest': None}
        return {'dates': dates, 'count': len(dates), 'latest': dates[-1] if dates else None}
