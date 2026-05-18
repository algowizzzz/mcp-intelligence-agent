"""md_to_docx — Convert markdown to Word docx. REQ-17 compliant version (upstream BaseMCPTool)."""
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


class MdToDocx(BaseMCPTool):
    """Convert markdown to Word docx."""

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
        return _do_execute_md_to_docx(arguments)


# Tool-specific implementation below the class so each is small and isolated.

def _do_execute_md_to_docx(arguments):
    src = str(arguments.get('source', arguments.get('path',''))).strip()
    if not src:
        return {'error': 'source is required'}
    full = _resolve(arguments, src)
    if not full:
        return {'error': f'source not found: {src}'}
    try:
        from docx import Document as _D
        with open(full, 'r', encoding='utf-8') as f:
            md = f.read()
        doc = _D()
        for line in md.splitlines():
            doc.add_paragraph(line)
        out = full.replace('.md', '.docx')
        doc.save(out)
        return {'source': full, 'output': out}
    except Exception as e:
        return {'error': str(e), 'source': full}
