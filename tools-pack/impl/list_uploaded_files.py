"""
list_uploaded_files — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/upload_tools.py
(ListUploadedFilesTool). Worker scope from arguments['_worker_context'].
"""

import logging
import os
from collections import defaultdict
from typing import Any, Dict, List

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.worker_ctx import get_data_layers

logger = logging.getLogger(__name__)


ALLOWED_EXTS = {
    'pdf', 'docx', 'xlsx', 'csv', 'txt', 'parquet', 'pq',
    'md', 'json', 'png', 'jpg', 'jpeg', 'py',
}


class ListUploadedFiles(BaseMCPTool):
    """List files across worker data layers as a compact markdown tree."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'section':   {'type': 'string', 'enum': ['all', 'my_data', 'domain_data', 'common']},
                'file_type': {'type': 'string'},
                'subfolder': {'type': 'string'},
            },
            'required': [],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'output': {'type': 'string'},
                'count':  {'type': 'integer'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        section = arguments.get('section', 'all')
        file_type = arguments.get('file_type', 'all')
        subfolder = (arguments.get('subfolder') or '').strip().strip('/')

        ctx = arguments.get('_worker_context') or {}
        layers = get_data_layers(ctx, section if section in ('my_data', 'domain_data', 'common') else 'all')

        files: List[Dict[str, Any]] = []
        for section_name, base_path in layers:
            root = base_path.rstrip('/')
            if subfolder:
                root = os.path.join(root, subfolder)
            if not os.path.isdir(root):
                continue
            for dirpath, _, filenames in os.walk(root):
                rel_dir = os.path.relpath(dirpath, root) if dirpath != root else ''
                # Skip hidden directories
                if any(part.startswith('.') for part in rel_dir.replace('\\', '/').split('/')):
                    continue
                for fname in filenames:
                    if fname.startswith('.') or fname.startswith('_'):
                        continue
                    ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                    if ext not in ALLOWED_EXTS:
                        continue
                    if file_type != 'all' and ext != file_type:
                        continue
                    fpath = os.path.join(dirpath, fname)
                    rel = os.path.join(rel_dir, fname) if rel_dir and rel_dir != '.' else fname
                    sub = rel_dir if rel_dir and rel_dir != '.' else ''
                    files.append({
                        'filename':      fname,
                        'relative_path': rel,
                        'file_path':     fpath,
                        'section':       section_name,
                        'subfolder':     sub,
                        'file_type':     ext,
                    })

        files.sort(key=lambda x: (x['section'], x['subfolder'], x['filename']))
        return self._render_markdown(files)

    def _render_markdown(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not files:
            return {'output': '_No files found._', 'count': 0}

        tree: Dict[str, Any] = {}
        for f in files:
            sec = f['section']
            sub = f['subfolder'] or ''
            tree.setdefault(sec, defaultdict(list))[sub].append(f)

        lines = [f'**{len(files)} file(s) found**\n']
        for sec, folders in sorted(tree.items()):
            sec_count = sum(len(v) for v in folders.values())
            lines.append(f'### {sec}  ({sec_count} files)')
            for sub in sorted(folders.keys()):
                entries = sorted(folders[sub], key=lambda x: x['filename'])
                if sub:
                    lines.append(f'\n**{sub}/**')
                    for f in entries:
                        lines.append(f'  {f["filename"]}  →  `{f["file_path"]}`')
                else:
                    for f in entries:
                        lines.append(f'  {f["filename"]}  →  `{f["file_path"]}`')
            lines.append('')

        return {'output': '\n'.join(lines), 'count': len(files)}
