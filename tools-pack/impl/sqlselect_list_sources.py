"""
sqlselect_list_sources — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/sqlselect_tool_refactored.py
(SqlSelectListSourcesTool). Worker scope from arguments['_worker_context'].
"""

import logging
from datetime import datetime
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._sqlselect_base import build_connection

logger = logging.getLogger(__name__)


class SqlselectListSources(BaseMCPTool):
    """List all available data sources (static + auto-discovered) for SQL Select."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {},
            'additionalProperties': False,
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'success':   {'type': 'boolean'},
                'sources':   {'type': 'array'},
                'count':     {'type': 'integer'},
                'timestamp': {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        data_sources = self.config.get('data_sources', {}) or {}
        conn, primary_root, registered_static = build_connection(arguments, data_sources)
        try:
            sources = []
            static_names = set()
            for source_name, source_config in data_sources.items():
                sources.append({
                    'name':        source_name,
                    'file':        source_config.get('file', ''),
                    'type':        source_config.get('type', 'csv'),
                    'description': source_config.get('description', ''),
                })
                static_names.add(source_name)

            try:
                rows = conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
                ).fetchall()
                for (tname,) in rows:
                    if tname not in static_names:
                        sources.append({
                            'name':        tname,
                            'file':        '',
                            'type':        'view',
                            'description': 'auto-discovered',
                        })
            except Exception as exc:
                logger.warning("sqlselect_list_sources: could not list auto-discovered: %s", exc)

            return {
                'success':   True,
                'sources':   sources,
                'count':     len(sources),
                'timestamp': datetime.now().isoformat(),
                '_source':   primary_root,
            }
        finally:
            conn.close()
