"""
Shared helpers for sqlselect_* tools — compliant with upstream SAJHA.

Mirrors the logic in
  sajhamcpserver/sajha/tools/impl/sqlselect_tool_refactored.py
but:
  - Reads worker scope from arguments['_worker_context'] via worker_ctx.get_data_layers
  - Uses stdlib filesystem ops (os/pathlib); no sajha.storage abstraction
  - No PropertiesConfigurator dependency — falls back to '<domain_data>/sqlselect'
"""

import logging
import os
from typing import Any, Dict, List, Tuple

import duckdb

from tools_pack_lib.worker_ctx import get_data_layers

logger = logging.getLogger(__name__)


def sqlselect_root(ctx: Dict[str, str]) -> str:
    """Return the worker's `sqlselect/` directory under domain_data, or domain itself."""
    domain = (ctx.get('domain_data_path') or '').rstrip('/')
    if not domain:
        return ''
    candidate = os.path.join(domain, 'sqlselect')
    return candidate if os.path.isdir(candidate) else domain


def list_files_under(root: str) -> List[str]:
    """Return relative file paths under root, recursive."""
    out: List[str] = []
    if not root or not os.path.isdir(root):
        return out
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            rel = os.path.relpath(os.path.join(dirpath, f), root)
            out.append(rel)
    return out


def build_connection(arguments: Dict[str, Any], data_sources: Dict[str, Dict]) -> Tuple[duckdb.DuckDBPyConnection, str, List[str]]:
    """Build an in-memory DuckDB connection and register configured + discovered tables.

    Returns (conn, primary_root, registered_static_sources).
    """
    ctx = arguments.get('_worker_context') or {}
    primary_root = sqlselect_root(ctx)

    conn = duckdb.connect(':memory:')

    # Pass 1: register configured static sources (resolve under primary_root).
    registered_static: List[str] = []
    for source_name, source_config in (data_sources or {}).items():
        try:
            file_name = source_config.get('file', '')
            file_type = (source_config.get('type', 'csv') or 'csv').lower()
            if not primary_root or not file_name:
                continue
            file_path = os.path.join(primary_root, file_name)
            if not os.path.isfile(file_path):
                logger.debug("sqlselect: static source missing %s", file_path)
                continue
            safe = file_path.replace("'", "''")
            if file_type == 'csv':
                conn.execute(
                    f"CREATE OR REPLACE TABLE {source_name} AS "
                    f"SELECT * FROM read_csv_auto('{safe}')"
                )
            elif file_type == 'parquet':
                conn.execute(
                    f"CREATE OR REPLACE TABLE {source_name} AS "
                    f"SELECT * FROM read_parquet('{safe}')"
                )
            elif file_type == 'json':
                conn.execute(
                    f"CREATE OR REPLACE TABLE {source_name} AS "
                    f"SELECT * FROM read_json_auto('{safe}')"
                )
            else:
                continue
            registered_static.append(source_name)
        except Exception as exc:
            logger.warning("sqlselect: failed to register %s: %s", source_name, exc)

    # Pass 2: auto-discover CSV/Parquet/JSON across all 3 data layers as VIEWs.
    layers = get_data_layers(ctx, 'all')
    static_files = {cfg.get('file', '') for cfg in (data_sources or {}).values()}
    seen_names = set(registered_static)

    for section_name, data_dir in layers:
        for rel_key in list_files_under(data_dir):
            fname = os.path.basename(rel_key)
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ('.csv', '.parquet', '.pq', '.json', '.jsonl'):
                continue
            if rel_key in static_files or fname in static_files:
                continue
            name_no_ext = os.path.splitext(rel_key)[0]
            table_name = (
                name_no_ext.replace(os.sep, '__').replace('/', '__')
                .replace(' ', '_').replace('-', '_')
            )
            table_name = '__'.join(p.lstrip('.') for p in table_name.split('__') if p.lstrip('.'))
            if not table_name:
                continue
            if table_name in seen_names:
                table_name = f"{section_name}__{table_name}"
            seen_names.add(table_name)
            abs_path = os.path.join(data_dir, rel_key).replace("'", "''")
            try:
                if ext == '.csv':
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {table_name} AS "
                        f"SELECT * FROM read_csv_auto('{abs_path}', header=true, sample_size=100)"
                    )
                elif ext in ('.parquet', '.pq'):
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {table_name} AS "
                        f"SELECT * FROM read_parquet('{abs_path}')"
                    )
                elif ext in ('.json', '.jsonl'):
                    conn.execute(
                        f"CREATE OR REPLACE VIEW {table_name} AS "
                        f"SELECT * FROM read_json_auto('{abs_path}')"
                    )
            except Exception as exc:
                logger.debug("sqlselect: auto-register skipped %s: %s", rel_key, exc)

    return conn, primary_root, registered_static
