"""
Copyright All rights Reserved 2025-2030, Ashutosh Sinha, Email: ajsinha@gmail.com
Upload Tools — list_uploaded_files MCP Tool Implementation
"""

import os
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator
from sajha.storage import storage
from sajha.data_context import get_data_layers


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

    def _resolve_roots(self, section: str) -> list:
        """Return list of (section_name, root_path) tuples for the requested section(s)."""
        return get_data_layers(section)

    def _render_markdown(self, files: list) -> dict:
        """Render file list as a compact grouped markdown tree."""
        if not files:
            return {'output': '_No files found._', 'count': 0}

        # Group: section -> subfolder -> [{filename, file_path}]
        from collections import defaultdict
        tree = {}
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

    def execute(self, params: Dict[str, Any]) -> Any:
        section = params.get('section', 'all')
        file_type = params.get('file_type', 'all')
        subfolder = params.get('subfolder', '').strip().strip('/')

        roots = self._resolve_roots(section)

        ALLOWED = {'pdf', 'docx', 'xlsx', 'csv', 'txt', 'parquet', 'pq', 'md', 'json', 'png', 'jpg', 'jpeg', 'py'}
        files = []
        searched_dirs = []

        for section_name, base_path in roots:
            # Avoid os.path.normpath — it corrupts s3:// URIs (converts // to /)
            root = base_path.rstrip('/')
            if subfolder:
                root = root + '/' + subfolder
            searched_dirs.append(root)

            for rel_key in storage.list_prefix(root):
                fname = os.path.basename(rel_key)
                if fname.startswith('.') or fname.startswith('_'):
                    continue
                # Skip entries inside hidden directories
                if any(part.startswith('.') for part in rel_key.replace('\\', '/').split('/')):
                    continue
                ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                if ext not in ALLOWED:
                    continue
                if file_type != 'all' and ext != file_type:
                    continue
                fpath = root + '/' + rel_key
                sub = os.path.dirname(rel_key)
                files.append({
                    'filename': fname,
                    'relative_path': rel_key,
                    'file_path': fpath,
                    'section': section_name,
                    'subfolder': sub if sub != '.' else '',
                    'file_type': ext,
                })

        files.sort(key=lambda x: (x['section'], x['subfolder'], x['filename']))
        return self._render_markdown(files)
