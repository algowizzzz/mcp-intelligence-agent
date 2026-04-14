"""
Copyright All rights Reserved 2025-2030, Ashutosh Sinha, Email: ajsinha@gmail.com
Upload Tools — list_uploaded_files MCP Tool Implementation
"""

import os
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator
from sajha.storage import storage
from sajha.path_resolver import resolve as path_resolve


def _get_worker_ctx():
    try:
        from flask import g as _g
        return getattr(_g, 'worker_ctx', {}) or {}
    except RuntimeError:
        return {}


class ListUploadedFilesTool(BaseMCPTool):
    """Lists files across all data layers (my_data, domain_data, common) or a specific layer."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'section': {
                    'type': 'string',
                    'enum': ['all', 'my_data', 'domain_data', 'common'],
                    'description': 'Data layer to list. Default: all (searches my_data, domain_data, and common).'
                },
                'file_type': {
                    'type': 'string',
                    'enum': ['pdf', 'docx', 'xlsx', 'csv', 'txt', 'parquet', 'md', 'json', 'py', 'all'],
                    'description': 'Filter by file type. Default: all.'
                },
                'subfolder': {
                    'type': 'string',
                    'description': 'Optional subfolder path within a section to list (e.g. "123", "exports"). Default: list all subfolders recursively.'
                }
            },
            'required': []
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'output': {'type': 'string', 'description': 'Compact markdown tree of files grouped by subfolder.'},
                'count': {'type': 'integer'},
            }
        }

    def _resolve_roots(self, section: str, worker_ctx: dict, user_id, props) -> list:
        """Return list of (section_name, root_path) tuples for the requested section(s)."""
        roots = []

        def _my_data_root():
            if worker_ctx:
                try:
                    uid = user_id or '_shared'
                    return path_resolve('my_data', worker_ctx, user_id=uid)
                except Exception:
                    pass
            try:
                from flask import g as _g
                my_data_root = getattr(_g, 'worker_my_data_root', '') or ''
            except RuntimeError:
                my_data_root = ''
            return my_data_root.strip() or props.get('data.uploads_dir', './data/uploads')

        def _domain_data_root():
            if worker_ctx:
                try:
                    return path_resolve('domain_data', worker_ctx)
                except Exception:
                    pass
            # Fallback: X-Worker-Data-Root header injected by agent server (G-04)
            try:
                from flask import g as _g
                wr = getattr(_g, 'worker_data_root', '') or ''
                if wr:
                    return wr.strip()
            except RuntimeError:
                pass
            return ''

        def _common_root():
            if worker_ctx:
                try:
                    return path_resolve('common_data', worker_ctx)
                except Exception:
                    pass
            return props.get('data.common_dir', './data/common')

        if section == 'all':
            for name, fn in [('my_data', _my_data_root), ('domain_data', _domain_data_root), ('common', _common_root)]:
                p = fn()
                if p:
                    roots.append((name, p))
        elif section == 'my_data':
            p = _my_data_root()
            if p:
                roots.append(('my_data', p))
        elif section == 'domain_data':
            p = _domain_data_root()
            if p:
                roots.append(('domain_data', p))
        elif section == 'common':
            p = _common_root()
            if p:
                roots.append(('common', p))
        return roots

    def _render_markdown(self, files: list) -> dict:
        """Render file list as a compact grouped markdown tree."""
        if not files:
            return {'output': '_No files found._', 'count': 0}

        # Group: section -> subfolder -> [filename]
        from collections import defaultdict
        tree = {}
        for f in files:
            sec = f['section']
            sub = f['subfolder'] or ''
            tree.setdefault(sec, defaultdict(list))[sub].append(f['filename'])

        lines = [f'**{len(files)} file(s) found**\n']
        for sec, folders in sorted(tree.items()):
            sec_count = sum(len(v) for v in folders.values())
            lines.append(f'### {sec}  ({sec_count} files)')
            for sub in sorted(folders.keys()):
                fnames = sorted(folders[sub])
                if sub:
                    lines.append(f'\n**{sub}/**')
                    for fname in fnames:
                        lines.append(f'  {sub}/{fname}')
                else:
                    for fname in fnames:
                        lines.append(f'  {fname}')
            lines.append('')

        return {'output': '\n'.join(lines), 'count': len(files)}

    def execute(self, params: Dict[str, Any]) -> Any:
        props = PropertiesConfigurator()
        worker_ctx = _get_worker_ctx()
        user_id = None
        try:
            from flask import g as _g
            user_id = getattr(_g, 'user_id', None)
        except RuntimeError:
            pass

        section = params.get('section', 'all')
        file_type = params.get('file_type', 'all')
        subfolder = params.get('subfolder', '').strip().strip('/')

        roots = self._resolve_roots(section, worker_ctx, user_id, props)

        ALLOWED = {'pdf', 'docx', 'xlsx', 'csv', 'txt', 'parquet', 'pq', 'md', 'json', 'png', 'jpg', 'jpeg', 'py'}
        files = []
        searched_dirs = []

        for section_name, base_path in roots:
            root = os.path.normpath(base_path)
            if subfolder:
                root = os.path.join(root, subfolder)
            searched_dirs.append(root)

            if not os.path.exists(root):
                continue

            for dirpath, dirnames, fnames in os.walk(root):
                # Skip hidden dirs
                dirnames[:] = [d for d in dirnames if not d.startswith('.')]
                for fname in fnames:
                    if fname.startswith('.') or fname.startswith('_'):
                        continue
                    ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                    if ext not in ALLOWED:
                        continue
                    if file_type != 'all' and ext != file_type:
                        continue
                    fpath = os.path.join(dirpath, fname)
                    rel = os.path.relpath(fpath, os.path.normpath(base_path))
                    sub = os.path.dirname(rel)
                    files.append({
                        'filename': fname,
                        'relative_path': rel,
                        'file_path': os.path.abspath(fpath),
                        'section': section_name,
                        'subfolder': sub if sub != '.' else '',
                        'file_type': ext,
                    })

        files.sort(key=lambda x: (x['section'], x['subfolder'], x['filename']))
        return self._render_markdown(files)
