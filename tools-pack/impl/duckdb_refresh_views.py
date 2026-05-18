"""
duckdb_refresh_views — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py
(DuckDbRefreshViewsTool).

In the compliant overlay each DuckDB call uses a fresh per-request in-memory
connection (no persistent shared state), so 'refresh' simply rescans the
filesystem and validates that each candidate view is queryable.
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
            logger.debug("duckdb_refresh_views: view '%s' skipped: %s", view_name, exc)


class DuckdbRefreshViews(BaseMCPTool):
    """Rescan worker data layers and validate each candidate view is queryable."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'view_name':             {'type': 'string'},
                'reload_external_files': {'type': 'boolean', 'default': False},
            },
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'refreshed_views':         {'type': 'array'},
                'total_refreshed':         {'type': 'integer'},
                'external_files_reloaded': {'type': 'boolean'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        target_view = arguments.get('view_name')
        reload_external = bool(arguments.get('reload_external_files', False))

        try:
            files = scan_duckdb_files(arguments, 'all')
        except ValueError as exc:
            return {'error': str(exc)}

        conn = duckdb.connect(':memory:')
        try:
            _register_views(conn, files)

            # Pick the views to refresh
            if target_view:
                views_to_check = [target_view]
            else:
                rows = conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
                ).fetchall()
                views_to_check = [r[0] for r in rows]

            refreshed = []
            for view in views_to_check:
                try:
                    start = time.time()
                    cr = conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()
                    row_count = cr[0] if cr else 0
                    refresh_ms = (time.time() - start) * 1000
                    refreshed.append({
                        'view_name':       view,
                        'status':          'success',
                        'row_count':       row_count,
                        'refresh_time_ms': round(refresh_ms, 2),
                    })
                except Exception as exc:
                    refreshed.append({
                        'view_name':     view,
                        'status':        'failed',
                        'error_message': str(exc),
                    })

            return {
                'refreshed_views':          refreshed,
                'total_refreshed':          len([v for v in refreshed if v['status'] == 'success']),
                'external_files_reloaded':  reload_external,
            }
        finally:
            conn.close()
