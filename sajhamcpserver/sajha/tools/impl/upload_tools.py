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
                    'enum': ['pdf', 'docx', 'xlsx', 'csv', 'txt', 'all'],
                    'description': 'Filter by file type. Default: all.'
                },
                'sort_by': {
                    'type': 'string',
                    'enum': ['uploaded_at', 'filename', 'size'],
                    'description': 'Sort order. Default: uploaded_at descending (newest first).'
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
        uploads_dir = props.get('data.uploads_dir', './CCR_data/uploads')
        file_type = params.get('file_type', 'all')
        sort_by = params.get('sort_by', 'uploaded_at')

        if not os.path.exists(uploads_dir):
            return {'files': [], 'count': 0, 'uploads_dir': uploads_dir}

        ALLOWED = {'pdf', 'docx', 'xlsx', 'csv', 'txt'}
        files = []
        for fname in os.listdir(uploads_dir):
            if fname.startswith('.'):
                continue
            ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
            if ext not in ALLOWED:
                continue
            if file_type != 'all' and ext != file_type:
                continue
            fpath = os.path.join(uploads_dir, fname)
            stat = os.stat(fpath)
            files.append({
                'filename': fname,
                'path': fpath,
                'file_type': ext,
                'size_bytes': stat.st_size,
                'uploaded_at': datetime.datetime.utcfromtimestamp(stat.st_mtime).isoformat() + 'Z'
            })

        files.sort(key=lambda x: x[sort_by], reverse=(sort_by == 'uploaded_at'))
        return {'files': files, 'count': len(files), 'uploads_dir': uploads_dir}
