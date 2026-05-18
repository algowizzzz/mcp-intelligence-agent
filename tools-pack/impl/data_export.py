"""
data_export — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/data_transform_tools.py
(DataExportTool). Worker scope from arguments['_worker_context'].
"""

import io
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._operational_base import get_roots

logger = logging.getLogger(__name__)


def _df_to_pq(df, dest, compression: str = 'snappy'):
    import pyarrow as pa, pyarrow.parquet as pq_mod
    arrays, fields = [], []
    for col in df.columns:
        vals = df[col].tolist()
        try:
            arr = pa.array(vals)
        except Exception:
            arr = pa.array([str(v) if v is not None else None for v in vals], type=pa.string())
        arrays.append(arr)
        fields.append(pa.field(str(col), arr.type))
    table = pa.table(arrays, schema=pa.schema(fields))
    pq_mod.write_table(table, dest, compression=compression)


class DataExport(BaseMCPTool):
    """Save a data_transform result as CSV or Parquet in my_data/."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'data':          {'type': 'object'},
                'filename':      {'type': 'string'},
                'subfolder':     {'type': 'string'},
                'format':        {'type': 'string', 'enum': ['csv', 'parquet']},
                'versioning':    {'type': 'boolean'},
                'include_index': {'type': 'boolean'},
            },
            'required': ['data', 'filename'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        import pandas as pd

        data = arguments.get('data', {})
        filename = Path(arguments.get('filename', 'export.csv')).name
        subfolder = arguments.get('subfolder', 'exports')
        versioning = arguments.get('versioning', True)
        include_index = arguments.get('include_index', False)

        ext = Path(filename).suffix.lower()
        fmt = arguments.get('format')
        if not fmt:
            fmt = 'parquet' if ext in ('.parquet', '.pq') else 'csv'

        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get('data', [])
        else:
            rows = []
        if not rows:
            return {'error': 'data is empty — nothing to export.'}

        df = pd.DataFrame(rows)

        _, my_data, _ = get_roots(arguments)
        if not my_data:
            return {'error': 'my_data layer not available on worker context'}

        folder = my_data / subfolder if subfolder else my_data
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / filename

        archived_as = None
        if dest.exists() and versioning:
            ts = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d_%H%M%S')
            archive_name = f"{dest.stem}_{ts}{dest.suffix}"
            shutil.copy2(str(dest), str(folder / archive_name))
            dest.unlink()
            archived_as = archive_name

        try:
            if fmt == 'parquet':
                buf = io.BytesIO()
                _df_to_pq(df, buf)
                with open(dest, 'wb') as fh:
                    fh.write(buf.getvalue())
                size_bytes = len(buf.getvalue())
            else:
                csv_buf = io.StringIO()
                df.to_csv(csv_buf, index=include_index, encoding='utf-8')
                csv_text = csv_buf.getvalue()
                with open(dest, 'w', encoding='utf-8') as fh:
                    fh.write(csv_text)
                size_bytes = len(csv_text.encode('utf-8'))
        except Exception as exc:
            return {'error': f'Export failed: {exc}'}

        return {
            'path':        str(dest),
            'filename':    filename,
            'format':      fmt,
            'rows_written': len(df),
            'size_bytes':  size_bytes,
            'versioned':   archived_as is not None,
            'archived_as': archived_as,
            'written_at':  datetime.now(tz=timezone.utc).isoformat(),
            '_source':     str(dest),
        }
