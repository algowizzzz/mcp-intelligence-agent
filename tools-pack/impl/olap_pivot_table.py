"""
olap_pivot_table — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_advanced.py
(DuckDBOLAPAdvancedTool._pivot_table).

The original used a semantic-layer dataset abstraction. Here we treat `dataset`
as a DuckDB view name discovered from worker data layers (same auto-discovery
as duckdb_sql / duckdb_list_files), and build pivot SQL directly with the
supplied rows/columns/values/filters.
"""

import logging
import os
import time
from typing import Any, Dict, List

import duckdb

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.worker_ctx import get_data_layers
from tools_pack_impl.duckdb_list_files import scan_duckdb_files, view_name_for

logger = logging.getLogger(__name__)


def _register_views(conn, arguments: Dict[str, Any]) -> Dict[str, str]:
    """Register every CSV/Parquet/JSON file across worker layers as a DuckDB view."""
    registered: Dict[str, str] = {}
    try:
        files = scan_duckdb_files(arguments, 'all')
    except ValueError:
        return registered
    for f in files:
        view = view_name_for(f.get('unique_key', f['filename']))
        if view in registered:
            continue
        fp = f['file_path'].replace("'", "''")
        ft = f['file_type']
        try:
            if ft == 'csv':
                conn.execute(
                    f"CREATE OR REPLACE VIEW {view} AS "
                    f"SELECT * FROM read_csv_auto('{fp}', header=true, sample_size=100)"
                )
            elif ft == 'parquet':
                conn.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{fp}')")
            elif ft == 'json':
                conn.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_json_auto('{fp}')")
            elif ft == 'tsv':
                conn.execute(
                    f"CREATE OR REPLACE VIEW {view} AS "
                    f"SELECT * FROM read_csv_auto('{fp}', header=true, delim='\\t', sample_size=100)"
                )
            registered[view] = fp
        except Exception as exc:
            logger.debug("olap_pivot_table: view %s skipped: %s", view, exc)
    return registered


def _safe_alias(name: str) -> str:
    s = ''.join(c if c.isalnum() else '_' for c in str(name))
    if s and s[0].isdigit():
        s = '_' + s
    return s


def _build_filter_clause(filters: List[Dict]) -> str:
    if not filters:
        return ''
    parts: List[str] = []
    for f in filters:
        col = f.get('dimension') or f.get('column')
        op = (f.get('operator') or '=').upper()
        val = f.get('value')
        if not col:
            continue
        if op == 'IN' or op == 'NOT IN':
            if isinstance(val, list):
                fmt = ', '.join(
                    f"'{v}'" if isinstance(v, str) else str(v) for v in val
                )
            else:
                fmt = f"'{val}'" if isinstance(val, str) else str(val)
            parts.append(f"{col} {op} ({fmt})")
        elif op == 'LIKE':
            parts.append(f"{col} LIKE '{val}'")
        elif op == 'BETWEEN':
            if isinstance(val, list) and len(val) == 2:
                lo, hi = val
                lo_s = f"'{lo}'" if isinstance(lo, str) else str(lo)
                hi_s = f"'{hi}'" if isinstance(hi, str) else str(hi)
                parts.append(f"{col} BETWEEN {lo_s} AND {hi_s}")
        else:
            fmt = f"'{val}'" if isinstance(val, str) else str(val)
            parts.append(f"{col} {op} {fmt}")
    return 'WHERE ' + ' AND '.join(parts) if parts else ''


class OlapPivotTable(BaseMCPTool):
    """Pivot-table aggregation over a DuckDB view sourced from worker data layers."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'dataset':           {'type': 'string', 'description': 'Table/view name (from duckdb_list_files)'},
                'rows':              {'type': 'array', 'items': {'type': 'string'}},
                'columns':           {'type': 'array', 'items': {'type': 'string'}},
                'values':            {'type': 'array', 'description': 'List of {measure, aggregation}'},
                'filters':           {'type': 'array'},
                'include_totals':    {'type': 'boolean', 'default': True},
                'include_subtotals': {'type': 'boolean', 'default': False},
                'limit':             {'type': 'integer'},
            },
            'required': ['dataset', 'rows', 'values'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'data':    {'type': 'array'},
                'columns': {'type': 'array'},
                'sql':     {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        dataset = (arguments.get('dataset') or '').strip()
        rows = list(arguments.get('rows') or [])
        cols = list(arguments.get('columns') or [])
        values = arguments.get('values') or []
        filters = arguments.get('filters') or []
        limit = arguments.get('limit')

        if not dataset:
            return {'success': False, 'error': 'dataset is required'}
        if not rows:
            return {'success': False, 'error': 'rows is required'}
        if not values:
            return {'success': False, 'error': 'values is required'}

        # Normalise dataset (allow either raw view name or a known unique_key form)
        view = _safe_alias(dataset)

        conn = duckdb.connect(':memory:')
        try:
            registered = _register_views(conn, arguments)
            if view not in registered:
                # Fall back to dataset as-is in case caller passed an already-clean name
                if dataset not in registered:
                    return {
                        'success': False,
                        'error':   f"Dataset '{dataset}' not found among worker views.",
                        'available_views': sorted(registered.keys()),
                    }
                view = dataset

            # Build pivot SQL: simple aggregation grouped by rows+columns.
            # (Cross-tab pivoting is left to the caller; we return the long form
            # with both row and column dimensions in GROUP BY.)
            dims = list(rows) + list(cols)
            select_parts = [f"{d} AS {_safe_alias(d)}" for d in dims]
            for v in values:
                measure = v.get('measure', '')
                agg = (v.get('aggregation') or 'SUM').upper()
                if not measure:
                    continue
                alias = _safe_alias(f"{agg.lower()}_{measure}")
                select_parts.append(f"{agg}({measure}) AS {alias}")

            sql = f"SELECT {', '.join(select_parts)} FROM {view}"
            fc = _build_filter_clause(filters)
            if fc:
                sql += f" {fc}"
            if dims:
                sql += f" GROUP BY {', '.join(_safe_alias(d) for d in dims)}"
                sql += f" ORDER BY {', '.join(_safe_alias(d) for d in dims)}"
            if isinstance(limit, int) and limit > 0:
                sql += f" LIMIT {limit}"

            start = time.time()
            res = conn.execute(sql)
            result_cols = [d[0] for d in res.description]
            data_rows = res.fetchall()

            data: List[Dict[str, Any]] = []
            for r in data_rows:
                row_dict = {}
                for i, c in enumerate(result_cols):
                    val = r[i]
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    elif isinstance(val, float):
                        val = round(val, 4)
                    row_dict[c] = val
                data.append(row_dict)

            execution_ms = (time.time() - start) * 1000

            return {
                'success':          True,
                'data':             data,
                'columns':          result_cols,
                'row_count':        len(data),
                'sql':              sql,
                'execution_time_ms': round(execution_ms, 2),
                '_source':          registered.get(view, dataset),
            }
        except Exception as exc:
            logger.error("olap_pivot_table failed: %s", exc)
            return {'success': False, 'error': str(exc), 'dataset': dataset}
        finally:
            conn.close()
