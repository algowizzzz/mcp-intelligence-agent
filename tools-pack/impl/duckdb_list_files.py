"""
duckdb_list_files — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py
(DuckDbListFilesTool) — see that file for full historical context.

Compliance changes from the original:
- Extends upstream's sajha.tools.base_mcp_tool.BaseMCPTool.
- Worker context comes from arguments['_worker_context']; no Flask `g`.
- Filesystem access via stdlib (os/pathlib); no `sajha.storage` abstraction.
- No PropertiesConfigurator dependency.
"""

import os
import logging
from typing import Any, Dict, List, Optional

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.worker_ctx import get_data_layers

logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {
    'csv':     ['.csv'],
    'parquet': ['.parquet', '.pq'],
    'json':    ['.json', '.jsonl'],
    'tsv':     ['.tsv'],
}


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def _list_prefix(root: str) -> List[str]:
    """Return relative paths of files under root (recursive)."""
    out: List[str] = []
    if not root or not os.path.isdir(root):
        return out
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            abs_p = os.path.join(dirpath, f)
            rel = os.path.relpath(abs_p, root)
            out.append(rel)
    return out


def scan_duckdb_files(arguments: Dict[str, Any], file_type: str = 'all') -> List[Dict]:
    """Scan all data layers (domain_data, my_data, common) for supported file types.

    Looks under each layer's `duckdb/` subdirectory first (mirrors the original
    fork behaviour where the fork's domain_data_path pointed to the worker root
    and `tool.duckdb.data_directory` lived at `<worker_root>/duckdb`). Falls
    back to the layer root if no `duckdb/` exists.

    Returns a list of dicts with filename, unique_key, section, file_type,
    file_path, file_size_bytes, file_size_human.
    """
    ctx = arguments.get('_worker_context') or {}
    layers = get_data_layers(ctx, 'all')

    if not layers:
        raise ValueError(
            "No data directories configured for this worker. "
            "Check X-Worker-Data-Root header."
        )

    # For each layer, try the layer's duckdb subdir, then the root.
    effective_layers: List[tuple] = []
    for section_name, root in layers:
        if not root:
            continue
        duckdb_sub = os.path.join(root.rstrip('/'), 'duckdb')
        if os.path.isdir(duckdb_sub):
            effective_layers.append((section_name, duckdb_sub))
        else:
            effective_layers.append((section_name, root))

    if file_type != 'all':
        extensions = SUPPORTED_EXTENSIONS.get(file_type, [])
    else:
        extensions = [e for exts in SUPPORTED_EXTENSIONS.values() for e in exts]

    files: List[Dict] = []
    seen_keys = set()

    for section_name, data_dir in effective_layers:
        relative_paths = _list_prefix(data_dir)
        for rel_path in relative_paths:
            filename = os.path.basename(rel_path)
            if filename.startswith('.') or filename.endswith('.db'):
                continue

            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in extensions:
                continue

            rel_no_ext = os.path.splitext(rel_path)[0]
            safe_key = (
                rel_no_ext.replace('\\', '/').replace('/', '__')
                .replace(' ', '_').replace('-', '_')
            )
            unique_key = (
                f"{section_name}__{safe_key}" if safe_key in seen_keys else safe_key
            )

            file_path = os.path.join(data_dir, rel_path)

            if file_ext == '.csv':
                ftype = 'csv'
            elif file_ext in ('.parquet', '.pq'):
                ftype = 'parquet'
            elif file_ext in ('.json', '.jsonl'):
                ftype = 'json'
            elif file_ext == '.tsv':
                ftype = 'tsv'
            else:
                continue

            file_info: Dict[str, Any] = {
                'filename':   rel_path,
                'unique_key': unique_key,
                'section':    section_name,
                'file_type':  ftype,
                'file_path':  file_path,
            }
            try:
                size = os.path.getsize(file_path)
                file_info['file_size_bytes'] = size
                file_info['file_size_human'] = _format_file_size(size)
            except OSError:
                pass

            files.append(file_info)
            seen_keys.add(safe_key)

    return files


def view_name_for(unique_key: str) -> str:
    """Sanitise a unique_key into a safe SQL view name."""
    base = os.path.splitext(unique_key)[0]
    return ''.join(c if c.isalnum() or c == '_' else '_' for c in base)


class DuckdbListFiles(BaseMCPTool):
    """List all queryable data files (CSV/Parquet/JSON/TSV) across worker layers."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'file_type': {
                    'type': 'string',
                    'enum': ['all', 'csv', 'parquet', 'json', 'tsv'],
                    'description': 'Optional file-type filter',
                },
            },
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'data_directory': {'type': 'string'},
                'files':          {'type': 'array'},
                'total_files':    {'type': 'integer'},
                'summary':        {'type': 'object'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        file_type = arguments.get('file_type', 'all')

        try:
            files = scan_duckdb_files(arguments, file_type)
        except ValueError as exc:
            return {'error': str(exc), 'files': [], 'total_files': 0}

        # Compute summary
        summary = {
            'csv_count':       len([f for f in files if f['file_type'] == 'csv']),
            'parquet_count':   len([f for f in files if f['file_type'] == 'parquet']),
            'json_count':      len([f for f in files if f['file_type'] == 'json']),
            'tsv_count':       len([f for f in files if f['file_type'] == 'tsv']),
            'total_size_bytes': sum(f.get('file_size_bytes', 0) for f in files),
        }

        # Add view_name (same sanitisation as duckdb_query).
        for file_info in files:
            file_info['view_name'] = view_name_for(
                file_info.get('unique_key', file_info['filename'])
            )

        # Pick domain_data root for _source if available, else first layer.
        ctx = arguments.get('_worker_context') or {}
        layers = get_data_layers(ctx, 'all')
        domain = next((p for n, p in layers if n == 'domain_data'), '')
        data_directory = domain or (layers[0][1] if layers else '')

        return {
            'data_directory': data_directory,
            'files':          files,
            'total_files':    len(files),
            'summary':        summary,
            '_source':        data_directory,
            '_usage':         'Use view_name in SQL: SELECT COUNT(*) FROM <view_name>',
        }
