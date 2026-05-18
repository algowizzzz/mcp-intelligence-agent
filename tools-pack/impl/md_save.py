"""md_save — Save markdown content to my_data. REQ-17 compliant version (upstream BaseMCPTool)."""
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


class MdSave(BaseMCPTool):
    """Save markdown content to my_data."""

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
        return _do_execute_md_save(arguments)


# Tool-specific implementation below the class so each is small and isolated.

def _do_execute_md_save(arguments):
    name = str(arguments.get('filename', arguments.get('name',''))).strip()
    content = str(arguments.get('content', ''))
    if not name or not content:
        return {'error': 'filename and content are required'}
    if not name.endswith('.md'):
        name += '.md'
    layers = _layer_roots(arguments)
    my = next((r for n,r in layers if n == 'my_data'), None)
    if not my:
        return {'error': 'my_data layer not available'}
    os.makedirs(my, exist_ok=True)
    full = os.path.join(my, name)
    try:
        with open(full, 'w', encoding='utf-8') as f:
            f.write(content)
        return {'path': full, 'size_bytes': len(content)}
    except Exception as e:
        return {'error': str(e), 'path': full}
