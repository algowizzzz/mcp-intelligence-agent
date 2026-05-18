"""
duckdb_query — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py
(DuckDbQueryTool).
"""

import logging
import time
from typing import Any, Dict

import duckdb

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl.duckdb_list_files import scan_duckdb_files, view_name_for

logger = logging.getLogger(__name__)

FORBIDDEN_KEYWORDS = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'INSERT', 'UPDATE']


def _register_views(conn, files):
    for file_info in files:
        unique_key = file_info.get('unique_key', file_info['filename'])
        view_name = view_name_for(unique_key)
        fp = file_info['file_path']
        ft = file_info['file_type']
        try:
            if ft == 'csv':
                conn.execute(
                    f"CREATE VIEW {view_name} AS "
                    f"SELECT * FROM read_csv_auto('{fp}', header=true, sample_size=100)"
                )
            elif ft == 'parquet':
                conn.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_parquet('{fp}')")
            elif ft == 'json':
                conn.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_json_auto('{fp}')")
            elif ft == 'tsv':
                conn.execute(
                    f"CREATE VIEW {view_name} AS "
                    f"SELECT * FROM read_csv_auto('{fp}', header=true, delim='\\t', sample_size=100)"
                )
        except Exception as exc:
            logger.debug("duckdb_query: view '%s' skipped: %s", view_name, exc)


class DuckdbQuery(BaseMCPTool):
    """Execute SELECT-only SQL queries against worker-scoped DuckDB views."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'sql_query':     {'type': 'string', 'minLength': 1},
                'limit':         {'type': 'integer', 'default': 100, 'minimum': 1, 'maximum': 10000},
                'output_format': {'type': 'string', 'enum': ['json', 'csv', 'table'], 'default': 'json'},
            },
            'required': ['sql_query'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'query':             {'type': 'string'},
                'columns':           {'type': 'array'},
                'rows':              {'type': 'array'},
                'row_count':         {'type': 'integer'},
                'execution_time_ms': {'type': 'number'},
                'limited':           {'type': 'boolean'},
                'success':           {'type': 'boolean'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sql_query = arguments['sql_query']
        limit = int(arguments.get('limit', 100))

        query_upper = sql_query.upper()
        for kw in FORBIDDEN_KEYWORDS:
            if kw in query_upper:
                return {
                    'error':   f'Forbidden operation: {kw}. Only SELECT queries allowed.',
                    'success': False,
                }

        # Append LIMIT if not present and not an aggregation/COUNT query
        if 'LIMIT' not in query_upper and 'COUNT(' not in query_upper:
            sql_query = f"{sql_query.rstrip(';')} LIMIT {limit}"

        try:
            files = scan_duckdb_files(arguments, 'all')
        except ValueError as exc:
            return {'error': str(exc), 'success': False}

        conn = duckdb.connect(':memory:')
        try:
            _register_views(conn, files)

            start = time.time()
            df = conn.execute(sql_query).fetchdf()
            execution_ms = (time.time() - start) * 1000

            return {
                'query':              sql_query,
                'columns':            list(df.columns),
                'rows':               df.to_dict(orient='records'),
                'row_count':          len(df),
                'execution_time_ms':  round(execution_ms, 2),
                'limited':            'LIMIT' in sql_query.upper() and len(df) >= limit,
                'success':            True,
            }
        except Exception as exc:
            logger.error("duckdb_query failed: %s", exc)
            return {'error': str(exc), 'success': False, 'query': sql_query}
        finally:
            conn.close()
