"""
sqlselect_count_rows — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/sqlselect_tool_refactored.py
(SqlSelectCountRowsTool). Worker scope from arguments['_worker_context'].
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._sqlselect_base import build_connection

logger = logging.getLogger(__name__)


class SqlselectCountRows(BaseMCPTool):
    """Count rows in a data source with optional WHERE clause."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'source_name':  {'type': 'string'},
                'where_clause': {'type': 'string'},
            },
            'required': ['source_name'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'success':      {'type': 'boolean'},
                'source_name':  {'type': 'string'},
                'row_count':    {'type': 'integer'},
                'where_clause': {'type': ['string', 'null']},
                'timestamp':    {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        source_name = arguments.get('source_name')
        where_clause = (arguments.get('where_clause') or '').strip()
        if not source_name:
            return {'success': False, 'error': 'source_name is required',
                    'timestamp': datetime.now().isoformat()}

        data_sources = self.config.get('data_sources', {}) or {}
        conn, primary_root, _ = build_connection(arguments, data_sources)
        try:
            sql = f"SELECT COUNT(*) FROM {source_name}"
            if where_clause:
                sql += f" WHERE {where_clause}"
            try:
                count = conn.execute(sql).fetchone()[0]
            except Exception as exc:
                logger.error("sqlselect_count_rows: %s", exc)
                return {
                    'success': False,
                    'error':   f'Failed to count rows: {exc}',
                    'timestamp': datetime.now().isoformat(),
                }

            src_config = data_sources.get(source_name, {})
            file_name = src_config.get('file', '')
            return {
                'success':      True,
                'source_name':  source_name,
                'row_count':    count,
                'where_clause': where_clause or None,
                'timestamp':    datetime.now().isoformat(),
                '_source':      os.path.join(primary_root, file_name) if file_name else primary_root,
            }
        finally:
            conn.close()
