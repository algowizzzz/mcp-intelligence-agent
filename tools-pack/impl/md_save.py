"""
md_save — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/operational_tools.py (MdSaveTool).
Worker scope from arguments['_worker_context'].
"""

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._operational_base import get_roots

logger = logging.getLogger(__name__)


class MdSave(BaseMCPTool):
    """Save Markdown content to my_data/ with automatic versioning."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'content':    {'type': 'string'},
                'filename':   {'type': 'string'},
                'subfolder':  {'type': 'string'},
                'versioning': {'type': 'boolean'},
                'overwrite':  {'type': 'boolean'},
            },
            'required': ['content', 'filename'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        content = arguments.get('content', '')
        filename = Path(arguments.get('filename', 'output.md')).name
        if not filename.endswith('.md'):
            filename += '.md'
        subfolder = arguments.get('subfolder', '')
        versioning = arguments.get('versioning', True)
        overwrite = arguments.get('overwrite', False)

        _, my_data, _ = get_roots(arguments)
        if not my_data:
            return {'error': 'my_data layer not available on worker context'}

        folder = my_data / subfolder if subfolder else my_data
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / filename
        archived_as = None

        if dest.exists() and not overwrite:
            if versioning:
                ts = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d_%H%M%S')
                archive_name = f"{dest.stem}_{ts}.md"
                archive_path = folder / archive_name
                shutil.copy2(str(dest), str(archive_path))
                dest.unlink()
                archived_as = archive_name

        with open(dest, 'w', encoding='utf-8') as fh:
            fh.write(content)
        size_bytes = dest.stat().st_size if dest.exists() else len(content.encode('utf-8'))

        return {
            'path':        str(dest),
            'filename':    filename,
            'subfolder':   subfolder,
            'size_bytes':  size_bytes,
            'versioned':   archived_as is not None,
            'archived_as': archived_as,
            'written_at':  datetime.now(tz=timezone.utc).isoformat(),
            '_source':     str(dest),
        }
