"""
duckdb_get_stats — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py
(DuckDbGetStatsTool).
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
            logger.debug("duckdb_get_stats: view '%s' skipped: %s", view_name, exc)


class DuckdbGetStats(BaseMCPTool):
    """Compute statistical summaries for table columns (count, mean, std, min, max, percentiles)."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'table_name':          {'type': 'string', 'minLength': 1},
                'columns':             {'type': 'array', 'items': {'type': 'string'}},
                'include_percentiles': {'type': 'boolean', 'default': True},
            },
            'required': ['table_name'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'table_name':        {'type': 'string'},
                'total_rows':        {'type': 'integer'},
                'column_statistics': {'type': 'object'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        table_name = arguments['table_name']
        columns = arguments.get('columns', []) or []
        include_percentiles = arguments.get('include_percentiles', True)

        try:
            files = scan_duckdb_files(arguments, 'all')
        except ValueError as exc:
            return {'error': str(exc)}

        conn = duckdb.connect(':memory:')
        try:
            _register_views(conn, files)

            if not columns:
                describe = conn.execute(f"DESCRIBE {table_name}").fetchall()
                all_columns = [row[0] for row in describe]
            else:
                all_columns = columns

            total_rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            column_statistics: Dict[str, Any] = {}
            for col in all_columns:
                stats_parts = [
                    f"COUNT({col}) as count",
                    f"COUNT(*) - COUNT({col}) as null_count",
                    f"MIN({col}) as min",
                    f"MAX({col}) as max",
                    f"COUNT(DISTINCT {col}) as unique_count",
                ]
                # Try numeric stats
                try:
                    numeric_stats = [
                        f"AVG({col}) as mean",
                        f"STDDEV({col}) as std_dev",
                    ]
                    if include_percentiles:
                        numeric_stats.extend([
                            f"PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {col}) as p25",
                            f"PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {col}) as median",
                            f"PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {col}) as p75",
                        ])

                    stats_sql = (
                        f"SELECT {', '.join(stats_parts + numeric_stats)} FROM {table_name}"
                    )
                    stats = conn.execute(stats_sql).fetchone()
                    column_statistics[col] = {
                        'count':        stats[0],
                        'null_count':   stats[1],
                        'min':          stats[2],
                        'max':          stats[3],
                        'unique_count': stats[4],
                        'mean':         float(stats[5]) if stats[5] is not None else None,
                        'std_dev':      float(stats[6]) if stats[6] is not None else None,
                        'data_type':    'numeric',
                    }
                    if include_percentiles:
                        column_statistics[col].update({
                            'percentile_25': float(stats[7]) if stats[7] is not None else None,
                            'median':        float(stats[8]) if stats[8] is not None else None,
                            'percentile_75': float(stats[9]) if stats[9] is not None else None,
                        })
                except Exception:
                    # Non-numeric column: fall back to basic stats
                    try:
                        stats_sql = f"SELECT {', '.join(stats_parts)} FROM {table_name}"
                        stats = conn.execute(stats_sql).fetchone()
                        column_statistics[col] = {
                            'count':        stats[0],
                            'null_count':   stats[1],
                            'min':          stats[2],
                            'max':          stats[3],
                            'unique_count': stats[4],
                            'data_type':    'non-numeric',
                        }
                    except Exception as inner_exc:
                        logger.warning("get_stats: column '%s' skipped: %s", col, inner_exc)
                        continue

            return {
                'table_name':        table_name,
                'total_rows':        total_rows,
                'column_statistics': column_statistics,
            }
        except Exception as exc:
            logger.error("duckdb_get_stats failed: %s", exc)
            return {'error': str(exc)}
        finally:
            conn.close()
