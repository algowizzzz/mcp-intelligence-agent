"""
Copyright All rights Reserved 2025-2030, Ashutosh Sinha, Email: ajsinha@gmail.com
Upload Tools — list_uploaded_files MCP Tool Implementation
"""

import os
import datetime
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator


class ListUploadedFilesTool(BaseMCPTool):
    """Lists all files in the SAJHA uploads folder."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'file_type': {
                    'type': 'string',
                    'enum': ['pdf', 'docx', 'xlsx', 'csv', 'txt', 'parquet', 'md', 'json', 'all'],
                    'description': 'Filter by file type. Default: all.'
                },
                'sort_by': {
                    'type': 'string',
                    'enum': ['uploaded_at', 'filename', 'size'],
                    'description': 'Sort order. Default: uploaded_at descending (newest first).'
                },
                'subfolder': {
                    'type': 'string',
                    'description': 'Optional subfolder path within uploads to list (e.g. "123", "exports"). Default: list all subfolders recursively.'
                }
            },
            'required': []
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'files': {'type': 'array'},
                'count': {'type': 'integer'},
                'uploads_dir': {'type': 'string'}
            }
        }

    def execute(self, params: Dict[str, Any]) -> Any:
        props = PropertiesConfigurator()
        uploads_dir = props.get('data.uploads_dir', './data/uploads')
        file_type = params.get('file_type', 'all')
        sort_by = params.get('sort_by', 'uploaded_at')
        subfolder = params.get('subfolder', '').strip().strip('/')

        root = os.path.normpath(uploads_dir)
        if subfolder:
            root = os.path.join(root, subfolder)

        if not os.path.exists(root):
            return {'files': [], 'count': 0, 'uploads_dir': root}

        ALLOWED = {'pdf', 'docx', 'xlsx', 'csv', 'txt', 'parquet', 'pq', 'md', 'json', 'png', 'jpg', 'jpeg'}
        files = []
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
                # Relative path within uploads root for display
                rel = os.path.relpath(fpath, os.path.normpath(uploads_dir))
                stat = os.stat(fpath)
                files.append({
                    'filename': fname,
                    'path': fpath,
                    'relative_path': rel,
                    'subfolder': os.path.dirname(rel) if os.path.dirname(rel) != '.' else '',
                    'file_type': ext,
                    'size_bytes': stat.st_size,
                    'uploaded_at': datetime.datetime.utcfromtimestamp(stat.st_mtime).isoformat() + 'Z'
                })

        sort_key = 'uploaded_at' if sort_by == 'uploaded_at' else ('filename' if sort_by == 'filename' else 'size_bytes')
        files.sort(key=lambda x: x[sort_key], reverse=(sort_by == 'uploaded_at'))
        return {'files': files, 'count': len(files), 'uploads_dir': root}
