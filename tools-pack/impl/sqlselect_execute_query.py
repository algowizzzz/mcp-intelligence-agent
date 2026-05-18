"""
sqlselect_execute_query — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/sqlselect_tool_refactored.py
(SqlSelectExecuteQueryTool). Worker scope from arguments['_worker_context'].
"""

import logging
from datetime import datetime
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._sqlselect_base import build_connection

logger = logging.getLogger(__name__)


FORBIDDEN_KEYWORDS = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 'TRUNCATE']


class SqlselectExecuteQuery(BaseMCPTool):
    """Execute a SELECT-only SQL query against worker data sources."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'query': {'type': 'string'},
                'limit': {'type': 'integer', 'default': 100, 'minimum': 1, 'maximum': 10000},
            },
            'required': ['query'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'success':   {'type': 'boolean'},
                'columns':   {'type': 'array'},
                'rows':      {'type': 'array'},
                'row_count': {'type': 'integer'},
                'query':     {'type': 'string'},
                'timestamp': {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get('query', '')
        limit = int(arguments.get('limit', 100))

        if not query:
            return {'success': False, 'error': 'query is required', 'timestamp': datetime.now().isoformat()}

        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            return {'success': False, 'error': 'Only SELECT queries are allowed', 'timestamp': datetime.now().isoformat()}

        for kw in FORBIDDEN_KEYWORDS:
            if kw in query_upper:
                return {
                    'success': False,
                    'error':   f'Query contains forbidden keyword: {kw}',
                    'timestamp': datetime.now().isoformat(),
                }

        if 'LIMIT' not in query_upper:
            query = f"{query.strip().rstrip(';')} LIMIT {limit}"

        data_sources = self.config.get('data_sources', {}) or {}
        conn, primary_root, _ = build_connection(arguments, data_sources)
        try:
            result = conn.execute(query).fetchall()
            columns = [desc[0] for desc in conn.description]

            data = [dict(zip(columns, row)) for row in result]

            return {
                'success':   True,
                'columns':   columns,
                'rows':      data,
                'row_count': len(data),
                'query':     query,
                'timestamp': datetime.now().isoformat(),
                '_source':   primary_root,
            }
        except Exception as exc:
            logger.error("sqlselect_execute_query failed: %s", exc)
            return {
                'success':   False,
                'error':     f'Query execution failed: {exc}',
                'query':     query,
                'timestamp': datetime.now().isoformat(),
            }
        finally:
            conn.close()
