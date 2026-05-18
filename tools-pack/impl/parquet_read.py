"""parquet_read — Read a parquet file. REQ-17 compliant version (upstream BaseMCPTool)."""
import io
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from sajha.tools.base_mcp_tool import BaseMCPTool
from tools_pack_lib.worker_ctx import get_data_layers


def _layer_roots(arguments: Dict[str, Any]) -> List[tuple]:
    return get_data_layers(arguments.get('_worker_context') or {}, 'all')


def _resolve(arguments: Dict[str, Any], rel: str) -> Optional[str]:
    """Find a file across layers by relative path; return first absolute match or None."""
    rel = (rel or '').lstrip('/')
    for _, root in _layer_roots(arguments):
        full = os.path.join(root, rel)
        if os.path.exists(full):
            return full
    return None


class ParquetRead(BaseMCPTool):
    """Read a parquet file."""

    def get_input_schema(self) -> Dict[str, Any]:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'path': {'type': 'string', 'description': 'Relative path to file'},
                '_worker_context': {'type': 'object'},
            },
            'required': [],
        })

    def get_output_schema(self) -> Dict[str, Any]:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return _do_execute_parquet_read(arguments)


# Tool-specific implementation below the class so each is small and isolated.

def _do_execute_parquet_read(arguments):
    src = str(arguments.get('path', '')).strip()
    if not src:
        return {'error': 'path is required'}
    full = _resolve(arguments, src)
    if not full:
        return {'error': f'parquet not found: {src}'}
    try:
        import pandas as pd
        df = pd.read_parquet(full)
        n = int(arguments.get('limit', 100))
        return {'path': full, 'rows': df.shape[0], 'columns': list(df.columns), 'sample': df.head(n).to_dict('records')}
    except Exception as e:
        return {'error': str(e), 'path': full}
