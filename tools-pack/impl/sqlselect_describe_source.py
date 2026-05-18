"""
sqlselect_describe_source — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/sqlselect_tool_refactored.py
(SqlSelectDescribeSourceTool). Worker scope from arguments['_worker_context'].
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._sqlselect_base import build_connection

logger = logging.getLogger(__name__)


class SqlselectDescribeSource(BaseMCPTool):
    """Describe a single data source (columns + row count)."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'source_name': {'type': 'string'},
            },
            'required': ['source_name'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'success':     {'type': 'boolean'},
                'source_name': {'type': 'string'},
                'row_count':   {'type': 'integer'},
                'columns':     {'type': 'array'},
                'timestamp':   {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        source_name = arguments.get('source_name')
        if not source_name:
            return {'success': False, 'error': 'source_name is required',
                    'timestamp': datetime.now().isoformat()}

        data_sources = self.config.get('data_sources', {}) or {}
        conn, primary_root, _ = build_connection(arguments, data_sources)
        try:
            try:
                result = conn.execute(f"DESCRIBE {source_name}").fetchall()
            except Exception as exc:
                logger.error("sqlselect_describe_source: %s", exc)
                return {
                    'success': False,
                    'error':   f'Data source not found: {source_name}',
                    'timestamp': datetime.now().isoformat(),
                }

            columns = [
                {
                    'column_name': row[0],
                    'data_type':   row[1],
                    'nullable':    row[2] if len(row) > 2 else None,
                    'key':         row[3] if len(row) > 3 else None,
                }
                for row in result
            ]
            try:
                row_count = conn.execute(f"SELECT COUNT(*) FROM {source_name}").fetchone()[0]
            except Exception:
                row_count = 0

            src_config = data_sources.get(source_name, {})
            file_name = src_config.get('file', '')

            return {
                'success':     True,
                'source_name': source_name,
                'file':        file_name,
                'type':        src_config.get('type', 'csv'),
                'description': src_config.get('description', ''),
                'row_count':   row_count,
                'columns':     columns,
                'timestamp':   datetime.now().isoformat(),
                '_source':     os.path.join(primary_root, file_name) if file_name else primary_root,
            }
        finally:
            conn.close()
