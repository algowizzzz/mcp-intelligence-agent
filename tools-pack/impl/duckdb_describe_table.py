"""
duckdb_describe_table — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py
(DuckDbDescribeTableTool).
"""

import logging
from typing import Any, Dict

import duckdb

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl.duckdb_list_files import scan_duckdb_files, view_name_for

logger = logging.getLogger(__name__)


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
            logger.debug("duckdb_describe_table: view '%s' skipped: %s", view_name, exc)


class DuckdbDescribeTable(BaseMCPTool):
    """Describe a DuckDB table or view (column types, row count, optional sample)."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'table_name':          {'type': 'string'},
                'include_sample_data': {'type': 'boolean', 'default': False},
                'sample_size':         {'type': 'integer', 'default': 5},
            },
            'required': ['table_name'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'table_name': {'type': 'string'},
                'table_type': {'type': 'string'},
                'columns':    {'type': 'array'},
                'row_count':  {'type': 'integer'},
                'sample_data': {'type': 'array'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        table_name = arguments['table_name']
        include_sample = arguments.get('include_sample_data', False)
        sample_size = int(arguments.get('sample_size', 5))

        try:
            files = scan_duckdb_files(arguments, 'all')
        except ValueError as exc:
            return {'error': str(exc)}

        conn = duckdb.connect(':memory:')
        try:
            _register_views(conn, files)

            tt_row = conn.execute(
                "SELECT table_type FROM information_schema.tables WHERE table_name = ?",
                [table_name],
            ).fetchone()
            table_type = 'view' if tt_row and tt_row[0].lower() == 'view' else 'table'

            describe = conn.execute(f"DESCRIBE {table_name}").fetchall()
            columns = []
            for row in describe:
                col = {
                    'column_name':    row[0],
                    'data_type':      row[1],
                    'nullable':       row[2] == 'YES' if len(row) > 2 else True,
                    'is_primary_key': False,
                }
                if len(row) > 3 and row[3]:
                    col['default_value'] = str(row[3])
                columns.append(col)

            row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            result: Dict[str, Any] = {
                'table_name': table_name,
                'table_type': table_type,
                'columns':    columns,
                'row_count':  row_count,
            }

            if include_sample:
                sample_df = conn.execute(
                    f"SELECT * FROM {table_name} LIMIT {sample_size}"
                ).fetchdf()
                result['sample_data'] = sample_df.to_dict(orient='records')

            return result
        finally:
            conn.close()
