"""
duckdb_aggregate — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py
(DuckDbAggregateTool).
"""

import logging
import time
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
            logger.debug("duckdb_aggregate: view '%s' skipped: %s", view_name, exc)


class DuckdbAggregate(BaseMCPTool):
    """Perform aggregation operations (SUM/AVG/COUNT/MIN/MAX) with GROUP BY/HAVING/ORDER BY."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'table_name':   {'type': 'string', 'minLength': 1},
                'aggregations': {'type': 'object'},
                'group_by':     {'type': 'array', 'items': {'type': 'string'}},
                'having':       {'type': 'string'},
                'order_by':     {'type': 'array'},
                'limit':        {'type': 'integer', 'default': 100},
            },
            'required': ['table_name', 'aggregations'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'table_name':           {'type': 'string'},
                'aggregations_applied': {'type': 'object'},
                'grouped_by':           {'type': 'array'},
                'results':              {'type': 'array'},
                'row_count':            {'type': 'integer'},
                'execution_time_ms':    {'type': 'number'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        table_name = arguments['table_name']
        aggregations: Dict[str, str] = arguments['aggregations']
        group_by = arguments.get('group_by', []) or []
        having = arguments.get('having')
        order_by = arguments.get('order_by', []) or []
        limit = int(arguments.get('limit', 100))

        try:
            files = scan_duckdb_files(arguments, 'all')
        except ValueError as exc:
            return {'error': str(exc)}

        # Build aggregation expressions
        agg_expressions = []
        for col, func in aggregations.items():
            func_upper = func.upper()
            if func_upper in ('SUM', 'AVG', 'COUNT', 'MIN', 'MAX'):
                agg_expressions.append(f"{func_upper}({col}) as {func}_{col}")
            elif func_upper == 'COUNT_DISTINCT':
                agg_expressions.append(f"COUNT(DISTINCT {col}) as count_distinct_{col}")

        if group_by:
            select_clause = f"SELECT {', '.join(group_by)}, {', '.join(agg_expressions)}"
        else:
            select_clause = f"SELECT {', '.join(agg_expressions)}"

        query = f"{select_clause} FROM {table_name}"
        if group_by:
            query += f" GROUP BY {', '.join(group_by)}"
        if having:
            query += f" HAVING {having}"
        if order_by:
            order_clauses = []
            for order in order_by:
                col = order.get('column')
                direction = order.get('direction', 'asc').upper()
                order_clauses.append(f"{col} {direction}")
            query += f" ORDER BY {', '.join(order_clauses)}"
        query += f" LIMIT {limit}"

        conn = duckdb.connect(':memory:')
        try:
            _register_views(conn, files)

            start = time.time()
            df = conn.execute(query).fetchdf()
            execution_ms = (time.time() - start) * 1000

            return {
                'table_name':           table_name,
                'aggregations_applied': aggregations,
                'grouped_by':           group_by,
                'results':              df.to_dict(orient='records'),
                'row_count':            len(df),
                'execution_time_ms':    round(execution_ms, 2),
            }
        except Exception as exc:
            logger.error("duckdb_aggregate failed: %s", exc)
            return {'error': str(exc), 'query': query}
        finally:
            conn.close()
