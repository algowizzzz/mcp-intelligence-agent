"""
duckdb_list_tables — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py
(DuckDbListTablesTool).

Same compliance changes as duckdb_list_files (see that module's docstring).
"""

import logging
import os
from typing import Any, Dict

import duckdb

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl.duckdb_list_files import scan_duckdb_files, view_name_for

logger = logging.getLogger(__name__)


def _register_views(conn, files):
    """Create DuckDB views for the supplied files (best-effort)."""
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
                conn.execute(
                    f"CREATE VIEW {view_name} AS SELECT * FROM read_parquet('{fp}')"
                )
            elif ft == 'json':
                conn.execute(
                    f"CREATE VIEW {view_name} AS SELECT * FROM read_json_auto('{fp}')"
                )
            elif ft == 'tsv':
                conn.execute(
                    f"CREATE VIEW {view_name} AS "
                    f"SELECT * FROM read_csv_auto('{fp}', header=true, delim='\\t', sample_size=100)"
                )
        except Exception as exc:
            logger.debug("duckdb_list_tables: view '%s' skipped: %s", view_name, exc)


class DuckdbListTables(BaseMCPTool):
    """List all DuckDB tables and views (auto-created from worker data files)."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'include_system_tables': {'type': 'boolean', 'default': False},
            },
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'tables':       {'type': 'array'},
                'total_count':  {'type': 'integer'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        include_system = arguments.get('include_system_tables', False)

        try:
            files = scan_duckdb_files(arguments, 'all')
        except ValueError as exc:
            return {'error': str(exc), 'tables': [], 'total_count': 0}

        conn = duckdb.connect(':memory:')
        try:
            _register_views(conn, files)

            query = """
                SELECT
                    table_name as name,
                    table_type as type,
                    'main' as schema
                FROM information_schema.tables
            """
            if not include_system:
                query += " WHERE table_schema = 'main'"

            result = conn.execute(query).fetchall()
            tables = []
            for row in result:
                info = {
                    'name':   row[0],
                    'type':   'view' if row[1].lower() == 'view' else 'table',
                    'schema': row[2],
                }
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {row[0]}").fetchone()
                    info['row_count'] = count[0] if count else 0
                except Exception:
                    info['row_count'] = None
                tables.append(info)

            return {
                'tables': tables,
                'total_count': len(tables),
                '_note': 'view_name is the SQL identifier (e.g. SELECT * FROM iris__iris_combined)',
            }
        finally:
            conn.close()
