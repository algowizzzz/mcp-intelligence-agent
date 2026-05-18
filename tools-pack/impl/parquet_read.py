"""
parquet_read — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/data_transform_tools.py
(ParquetReadTool). Worker scope from arguments['_worker_context'].
"""

import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._operational_base import get_roots, safe_path, find_file

logger = logging.getLogger(__name__)


def _pq_to_df(path: str):
    import pyarrow.parquet as pq_mod
    import pandas as pd
    with open(path, 'rb') as fh:
        buf = io.BytesIO(fh.read())
    table = pq_mod.read_table(buf)
    data = {}
    for i, col in enumerate(table.schema.names):
        arr = table.column(i)
        try:
            data[col] = arr.to_pylist()
        except Exception:
            data[col] = [None] * len(arr)
    return pd.DataFrame(data)


def _load_df(file_path: str):
    import pandas as pd
    ext = Path(file_path).suffix.lower()
    if ext in ('.parquet', '.pq'):
        return _pq_to_df(file_path), 'parquet'
    if ext == '.csv':
        with open(file_path, 'rb') as fh:
            return pd.read_csv(io.BytesIO(fh.read()), sep=None, engine='python'), 'csv'
    if ext == '.tsv':
        with open(file_path, 'rb') as fh:
            return pd.read_csv(io.BytesIO(fh.read()), sep='\t'), 'tsv'
    raise ValueError(f'Unsupported extension: {ext}')


def _df_schema(df) -> List[Dict[str, Any]]:
    return [
        {
            'column':   col,
            'dtype':    str(df[col].dtype),
            'nullable': bool(df[col].isna().any()),
        }
        for col in df.columns
    ]


def _df_stats(df, columns: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    import pandas as pd
    cols = columns if columns else list(df.columns)
    stats: Dict[str, Dict[str, Any]] = {}
    for col in cols:
        if col not in df.columns:
            continue
        s = df[col]
        entry: Dict[str, Any] = {
            'null_count':   int(s.isna().sum()),
            'unique_count': int(s.nunique()),
        }
        if pd.api.types.is_numeric_dtype(s):
            entry['min'] = float(s.min()) if not s.empty else None
            entry['max'] = float(s.max()) if not s.empty else None
            entry['mean'] = float(s.mean()) if not s.empty else None
        stats[col] = entry
    return stats


def _safe_val(v: Any) -> Any:
    if hasattr(v, 'item'):
        try:
            return v.item()
        except Exception:
            return v
    return v


def _rows_to_list(df, limit: int = 500) -> List[Dict[str, Any]]:
    return [
        {k: _safe_val(v) for k, v in row.items()}
        for _, row in df.head(limit).iterrows()
    ]


class ParquetRead(BaseMCPTool):
    """Inspect and preview a Parquet/CSV/TSV file: schema, row count, sample, per-column stats."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'file_path':     {'type': 'string'},
                'sample_rows':   {'type': 'integer', 'default': 10},
                'include_stats': {'type': 'boolean', 'default': True},
                'columns':       {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['file_path'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        file_path = arguments.get('file_path', '')
        sample_rows = min(int(arguments.get('sample_rows', 10)), 100)
        include_stats = arguments.get('include_stats', True)
        columns = arguments.get('columns') or None

        domain, my_data, common = get_roots(arguments)
        safe = safe_path(file_path, domain, my_data, common)
        if not safe or not safe.exists():
            safe = find_file(file_path, domain, my_data, common)
        if not safe or not safe.exists():
            return {'error': f'File not found or access denied: {file_path}'}
        ext = safe.suffix.lower()
        if ext not in ('.parquet', '.pq', '.csv', '.tsv'):
            return {'error': 'parquet_read supports .parquet, .pq, .csv, .tsv only.'}

        try:
            size_bytes = safe.stat().st_size
        except OSError:
            size_bytes = 0
        large_file = size_bytes > 500 * 1024 * 1024

        try:
            if large_file and ext in ('.parquet', '.pq'):
                import pyarrow.parquet as pq
                pf = pq.read_metadata(str(safe))
                row_count = pf.num_rows
                schema_arrow = pq.read_schema(str(safe))
                col_names = schema_arrow.names
                schema = [
                    {'column': n, 'dtype': str(schema_arrow.field(n).type), 'nullable': True}
                    for n in col_names
                ]
                df_sample = _pq_to_df(str(safe)).head(sample_rows)
                df = df_sample  # placeholder
            else:
                df, _ = _load_df(str(safe))
                row_count = len(df)
                if columns:
                    missing = [c for c in columns if c not in df.columns]
                    if missing:
                        return {'error': f'Columns not found: {missing}. Available: {list(df.columns)}'}
                    df = df[columns]
                schema = _df_schema(df)
                df_sample = df.head(sample_rows)
        except Exception as exc:
            return {'error': f'Could not read file: {exc}'}

        fmt = 'parquet' if ext in ('.parquet', '.pq') else ext.lstrip('.')
        result: Dict[str, Any] = {
            'filename':     safe.name,
            'format':       fmt,
            'row_count':    int(row_count),
            'column_count': len(schema),
            'size_bytes':   size_bytes,
            'schema':       schema,
            'sample':       _rows_to_list(df_sample, sample_rows),
            '_source':      str(safe),
        }
        if large_file:
            result['large_file'] = True
        if include_stats and not large_file:
            result['stats'] = _df_stats(df, columns)
        return result
