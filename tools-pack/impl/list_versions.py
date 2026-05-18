"""list_versions — List versioned files in my_data. REQ-17 compliant version (upstream BaseMCPTool)."""
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


class ListVersions(BaseMCPTool):
    """List versioned files in my_data."""

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
        return _do_execute_list_versions(arguments)


# Tool-specific implementation below the class so each is small and isolated.

def _do_execute_list_versions(arguments):
    name = str(arguments.get('name', '')).strip()
    versions = []
    for layer, root in _layer_roots(arguments):
        if not root or not os.path.isdir(root):
            continue
        for r, _, files in os.walk(root):
            for fn in files:
                if not name or name in fn:
                    versions.append({'layer': layer, 'name': fn, 'path': os.path.join(r, fn)})
    return {'filter': name, 'versions': versions[:200], 'count': len(versions)}
