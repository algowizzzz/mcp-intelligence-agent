"""
fill_template — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/operational_tools.py (FillTemplateTool).
Worker scope from arguments['_worker_context'].
"""

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._operational_base import get_roots, safe_path, find_file
from tools_pack_impl.md_save import MdSave
from tools_pack_impl.md_to_docx import MdToDocx

logger = logging.getLogger(__name__)


class FillTemplate(BaseMCPTool):
    """Read a template, substitute placeholders, save the result."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'template_path':    {'type': 'string'},
                'data':             {'type': 'object'},
                'output_filename':  {'type': 'string'},
                'output_subfolder': {'type': 'string'},
                'versioning':       {'type': 'boolean'},
                'convert_to_docx':  {'type': 'boolean'},
            },
            'required': ['template_path', 'data'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        template_path = arguments.get('template_path', '')
        data = arguments.get('data', {}) or {}
        output_subfolder = arguments.get('output_subfolder', 'reports')
        versioning = arguments.get('versioning', True)
        convert_to_docx = arguments.get('convert_to_docx', False)

        domain, my_data, common = get_roots(arguments)
        # Templates can live under <domain>/templates or <common>/templates
        templates_roots = []
        if domain:
            templates_roots.append(domain / 'templates')
        if common:
            templates_roots.append(common / 'templates')
        # Allow any root if the agent passes a full path
        all_roots = [r for r in [domain, my_data, common, *templates_roots] if r is not None]

        safe = safe_path(template_path, *all_roots)
        if not safe or not safe.exists():
            safe = find_file(template_path, *all_roots)
        if not safe or not safe.exists():
            return {'error': f'Template not found or access denied: {template_path}'}
        if safe.suffix.lower() != '.md':
            return {'error': 'fill_template only accepts .md template files.'}

        content = safe.read_text(encoding='utf-8', errors='replace')

        # Strip YAML frontmatter
        fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if fm_match:
            content = content[fm_match.end():]

        # Substitute placeholders
        filled = content
        for key, value in data.items():
            filled = filled.replace('{{' + str(key) + '}}', str(value))

        remaining = re.findall(r'\{\{(\w+)\}\}', filled)
        missing = sorted(set(remaining))

        # Determine output filename
        output_filename = arguments.get('output_filename')
        if not output_filename:
            ts = datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')
            output_filename = f"{safe.stem}_filled_{ts}.md"

        saver = MdSave({'name': 'md_save'})
        save_result = saver.execute({
            '_worker_context': arguments.get('_worker_context'),
            'content':         filled,
            'filename':        output_filename,
            'subfolder':       output_subfolder,
            'versioning':      versioning,
        })

        result = {
            'template_used':        safe.name,
            'output_md_path':       save_result.get('path'),
            'output_docx_path':     None,
            'placeholders_filled':  len(data) - len(missing),
            'placeholders_missing': missing,
            'versioned':            save_result.get('versioned', False),
            'archived_as':          save_result.get('archived_as'),
            '_source':              save_result.get('path'),
        }

        if convert_to_docx and save_result.get('path'):
            converter = MdToDocx({'name': 'md_to_docx'})
            docx_result = converter.execute({
                '_worker_context': arguments.get('_worker_context'),
                'file_path':       save_result['path'],
            })
            if 'output_docx' in docx_result:
                result['output_docx_path'] = docx_result['output_docx']

        return result
