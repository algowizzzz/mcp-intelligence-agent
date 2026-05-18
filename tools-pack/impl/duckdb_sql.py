"""
duckdb_sql — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_advanced.py
(DuckDBSQLTool).

The original tool looked up customers/orders/products CSVs under a fixed
data_directory (`${data.duckdb.dir}`). In the compliant overlay we anchor on
the worker context's `domain_data_path`/`<worker>/duckdb` subfolder for those
three files, and also auto-register every other CSV/Parquet/JSON file across
all worker layers so general SELECTs still work.
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


FORBIDDEN_KEYWORDS = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'INSERT', 'UPDATE', 'CREATE TABLE']


def _duckdb_root(ctx: Dict[str, str]) -> str:
    """Return the worker's `duckdb/` subdir under domain_data, or '' if none."""
    domain = (ctx.get('domain_data_path') or '').rstrip('/')
    if not domain:
        return ''
    candidate = os.path.join(domain, 'duckdb')
    return candidate if os.path.isdir(candidate) else domain


def _register_named_csv(conn, root: str, name: str) -> bool:
    """Register `<root>/<name>.csv` as table `<name>`. Returns True on success."""
    if not root:
        return False
    fp = os.path.join(root, f"{name}.csv")
    if not os.path.isfile(fp):
        return False
    try:
        conn.execute(
            f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_csv_auto('{fp}')"
        )
        return True
    except Exception as exc:
        logger.debug("duckdb_sql: %s.csv skipped: %s", name, exc)
        return False


def _register_discovered(conn, arguments: Dict[str, Any], skip_names) -> None:
    """Auto-register every file discovered across worker layers, except `skip_names`."""
    try:
        files = scan_duckdb_files(arguments, 'all')
    except ValueError:
        return
    for file_info in files:
        unique_key = file_info.get('unique_key', file_info['filename'])
        view_name = view_name_for(unique_key)
        if view_name in skip_names:
            continue
        fp = file_info['file_path']
        ft = file_info['file_type']
        try:
            if ft == 'csv':
                conn.execute(
                    f"CREATE OR REPLACE VIEW {view_name} AS "
                    f"SELECT * FROM read_csv_auto('{fp}', header=true, sample_size=100)"
                )
            elif ft == 'parquet':
                conn.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{fp}')")
            elif ft == 'json':
                conn.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_json_auto('{fp}')")
            elif ft == 'tsv':
                conn.execute(
                    f"CREATE OR REPLACE VIEW {view_name} AS "
                    f"SELECT * FROM read_csv_auto('{fp}', header=true, delim='\\t', sample_size=100)"
                )
        except Exception as exc:
            logger.debug("duckdb_sql: view '%s' skipped: %s", view_name, exc)


class DuckdbSql(BaseMCPTool):
    """Execute arbitrary SELECT-only SQL against worker-scoped tables (customers/orders/products + auto-views)."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'sql':   {'type': 'string', 'minLength': 1},
                'limit': {'type': 'integer', 'default': 100, 'minimum': 1, 'maximum': 1000},
            },
            'required': ['sql'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'success':           {'type': 'boolean'},
                'columns':           {'type': 'array'},
                'data':              {'type': 'array'},
                'row_count':         {'type': 'integer'},
                'sql':               {'type': 'string'},
                'execution_time_ms': {'type': 'number'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sql = (arguments.get('sql') or '').strip()
        limit = int(arguments.get('limit', 100))

        if not sql:
            return {'success': False, 'error': 'SQL query is required'}

        sql_upper = sql.upper()
        for kw in FORBIDDEN_KEYWORDS:
            if kw in sql_upper:
                return {
                    'success': False,
                    'error':   f'Operation not allowed: {kw}. Only SELECT queries are permitted.',
                }

        if 'LIMIT' not in sql_upper:
            sql = f"{sql.rstrip(';')} LIMIT {limit}"

        ctx = arguments.get('_worker_context') or {}
        root = _duckdb_root(ctx)

        conn = duckdb.connect(':memory:')
        try:
            registered_named = set()
            for name in ('customers', 'orders', 'products'):
                if _register_named_csv(conn, root, name):
                    registered_named.add(name)

            _register_discovered(conn, arguments, skip_names=registered_named)

            start = time.time()
            result = conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()

            data: List[Dict[str, Any]] = []
            for row in rows:
                row_dict: Dict[str, Any] = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    if isinstance(val, float):
                        row_dict[col] = round(val, 2)
                    else:
                        row_dict[col] = val
                data.append(row_dict)

            execution_ms = (time.time() - start) * 1000

            return {
                'success':           True,
                'columns':           columns,
                'data':              data,
                'row_count':         len(data),
                'sql':               sql,
                'execution_time_ms': round(execution_ms, 2),
                'tables_available':  sorted(registered_named) or [],
                '_source':           root or (ctx.get('domain_data_path') or ''),
            }
        except Exception as exc:
            logger.error("duckdb_sql failed: %s", exc)
            return {
                'success': False,
                'error':   str(exc),
                'sql':     sql,
                '_source': root or (ctx.get('domain_data_path') or ''),
            }
        finally:
            conn.close()
