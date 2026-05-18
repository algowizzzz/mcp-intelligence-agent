"""pdf_read — Extract text from a PDF. REQ-17 compliant version (upstream BaseMCPTool)."""
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


class PdfRead(BaseMCPTool):
    """Extract text from a PDF."""

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
        return _do_execute_pdf_read(arguments)


# Tool-specific implementation below the class so each is small and isolated.

def _do_execute_pdf_read(arguments):
    p = str(arguments.get('path', '')).strip()
    if not p:
        return {'error': 'path is required'}
    full = _resolve(arguments, p)
    if not full:
        return {'error': f'pdf not found: {p}'}
    try:
        import pdfplumber
        chunks = []
        with pdfplumber.open(full) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ''
                if t.strip():
                    chunks.append(t)
        return {'path': full, 'page_count': len(chunks), 'content': '\n'.join(chunks)}
    except Exception as e:
        return {'error': str(e), 'path': full}
