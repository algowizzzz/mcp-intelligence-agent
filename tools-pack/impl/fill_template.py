"""fill_template — Fill placeholder values into a template file. REQ-17 compliant version (upstream BaseMCPTool)."""
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


class FillTemplate(BaseMCPTool):
    """Fill placeholder values into a template file."""

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
        return _do_execute_fill_template(arguments)


# Tool-specific implementation below the class so each is small and isolated.

def _do_execute_fill_template(arguments):
    name = str(arguments.get('template', arguments.get('name', ''))).strip()
    vars_ = arguments.get('variables') or {}
    if not name:
        return {'error': 'template is required'}
    # Look for templates under each layer's templates/ subfolder
    candidate = None
    for _, root in _layer_roots(arguments):
        for sub in ('templates', ''):
            p = os.path.join(root, sub, name) if sub else os.path.join(root, name)
            if os.path.exists(p):
                candidate = p; break
        if candidate: break
    if not candidate:
        return {'error': f'template not found: {name}'}
    try:
        with open(candidate, 'r', encoding='utf-8') as f:
            tpl = f.read()
        for k, v in (vars_ or {}).items():
            tpl = tpl.replace('{{' + k + '}}', str(v))
            tpl = tpl.replace('{' + k + '}', str(v))
        return {'template': name, 'rendered': tpl, 'variables_applied': list((vars_ or {}).keys())}
    except Exception as e:
        return {'error': str(e), 'template': name}
