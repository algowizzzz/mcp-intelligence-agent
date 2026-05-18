"""data_export — Export structured data to CSV/Parquet. REQ-17 compliant version (upstream BaseMCPTool)."""
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


class DataExport(BaseMCPTool):
    """Export structured data to CSV/Parquet."""

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
        return _do_execute_data_export(arguments)


# Tool-specific implementation below the class so each is small and isolated.

def _do_execute_data_export(arguments):
    src = str(arguments.get('source', '')).strip()
    fmt = str(arguments.get('format', 'csv')).lower()
    if not src:
        return {'error': 'source is required'}
    full = _resolve(arguments, src)
    if not full:
        return {'error': f'source not found: {src}'}
    try:
        import pandas as pd
        df = pd.read_csv(full) if full.endswith('.csv') else pd.read_parquet(full)
        layers = _layer_roots(arguments)
        my = next((r for n,r in layers if n == 'my_data'), None) or os.path.dirname(full)
        os.makedirs(my, exist_ok=True)
        base = os.path.splitext(os.path.basename(full))[0]
        if fmt == 'csv':
            out = os.path.join(my, base + '_export.csv'); df.to_csv(out, index=False)
        elif fmt == 'parquet':
            out = os.path.join(my, base + '_export.parquet'); df.to_parquet(out, index=False)
        else:
            return {'error': f'unsupported format {fmt}'}
        return {'source': full, 'output': out, 'rows': len(df)}
    except Exception as e:
        return {'error': str(e), 'source': full}
