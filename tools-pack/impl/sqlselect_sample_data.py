"""
sqlselect_sample_data — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/sqlselect_tool_refactored.py
(SqlSelectSampleDataTool). Worker scope from arguments['_worker_context'].
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._sqlselect_base import build_connection

logger = logging.getLogger(__name__)


class SqlselectSampleData(BaseMCPTool):
    """Return sample rows from a data source (preview)."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'source_name': {'type': 'string'},
                'limit':       {'type': 'integer', 'default': 10, 'minimum': 1, 'maximum': 1000},
            },
            'required': ['source_name'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'success':     {'type': 'boolean'},
                'source_name': {'type': 'string'},
                'columns':     {'type': 'array'},
                'rows':        {'type': 'array'},
                'row_count':   {'type': 'integer'},
                'timestamp':   {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        source_name = arguments.get('source_name')
        limit = int(arguments.get('limit', 10))
        if not source_name:
            return {'success': False, 'error': 'source_name is required',
                    'timestamp': datetime.now().isoformat()}

        data_sources = self.config.get('data_sources', {}) or {}
        conn, primary_root, _ = build_connection(arguments, data_sources)
        try:
            try:
                result = conn.execute(f"SELECT * FROM {source_name} LIMIT {limit}").fetchall()
                columns = [desc[0] for desc in conn.description]
            except Exception as exc:
                logger.error("sqlselect_sample_data: %s", exc)
                return {
                    'success': False,
                    'error':   f'Failed to get sample data: {exc}',
                    'timestamp': datetime.now().isoformat(),
                }

            data = [dict(zip(columns, row)) for row in result]
            src_config = data_sources.get(source_name, {})
            file_name = src_config.get('file', '')

            return {
                'success':     True,
                'source_name': source_name,
                'columns':     columns,
                'rows':        data,
                'row_count':   len(data),
                'timestamp':   datetime.now().isoformat(),
                '_source':     os.path.join(primary_root, file_name) if file_name else primary_root,
            }
        finally:
            conn.close()
