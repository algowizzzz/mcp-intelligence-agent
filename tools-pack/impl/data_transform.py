"""data_transform — Transform structured data via simple ops. REQ-17 compliant version (upstream BaseMCPTool)."""
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


class DataTransform(BaseMCPTool):
    """Transform structured data via simple ops."""

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
        return _do_execute_data_transform(arguments)


# Tool-specific implementation below the class so each is small and isolated.

def _do_execute_data_transform(arguments):
    src = str(arguments.get('source', '')).strip()
    op = str(arguments.get('op', 'head')).lower()
    if not src:
        return {'error': 'source is required'}
    full = _resolve(arguments, src)
    if not full:
        return {'error': f'source not found: {src}'}
    try:
        import pandas as pd
        df = pd.read_csv(full) if full.endswith('.csv') else pd.read_parquet(full)
        if op == 'head':
            res = df.head(int(arguments.get('n', 10))).to_dict('records')
        elif op == 'describe':
            res = df.describe(include='all').to_dict()
        elif op == 'columns':
            res = list(df.columns)
        elif op == 'shape':
            res = {'rows': df.shape[0], 'cols': df.shape[1]}
        else:
            return {'error': f'unknown op {op}'}
        return {'source': full, 'op': op, 'result': res}
    except Exception as e:
        return {'error': str(e), 'source': full}
