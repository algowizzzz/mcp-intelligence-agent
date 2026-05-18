"""
list_versions — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/operational_tools.py (ListVersionsTool).
Worker scope from arguments['_worker_context'].
"""

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._operational_base import get_roots

logger = logging.getLogger(__name__)


class ListVersions(BaseMCPTool):
    """List canonical + archived versions of a filename stem under my_data/."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'filename':  {'type': 'string'},
                'subfolder': {'type': 'string'},
            },
            'required': ['filename'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        filename = (arguments.get('filename') or '').strip()
        subfolder = (arguments.get('subfolder') or '').strip()
        if not filename:
            return {'error': 'filename is required'}

        _, my_data, _ = get_roots(arguments)
        if not my_data:
            return {'error': 'my_data layer not available'}

        search_root = my_data / subfolder if subfolder else my_data
        if not search_root.exists():
            return {
                'canonical':     None,
                'versions':      [],
                'version_count': 0,
                '_source':       str(search_root),
            }

        stem = Path(filename).stem
        ext = Path(filename).suffix
        version_pattern = re.compile(
            r'^' + re.escape(stem) + r'_(\d{4}-\d{2}-\d{2}_\d{6})' + re.escape(ext) + r'$',
            re.IGNORECASE,
        )

        canonical = None
        versions: List[Dict[str, Any]] = []
        for dirpath, _, filenames in os.walk(str(search_root)):
            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(fp)
                    mtime = datetime.fromtimestamp(os.path.getmtime(fp), tz=timezone.utc)
                except OSError:
                    size = 0
                    mtime = datetime.now(tz=timezone.utc)

                if fname.lower() == filename.lower():
                    canonical = {
                        'filename':    fname,
                        'path':        fp,
                        'modified_at': mtime.isoformat(),
                        'size_bytes':  size,
                    }
                else:
                    m = version_pattern.match(fname)
                    if m:
                        versions.append({
                            'filename':    fname,
                            'path':        fp,
                            'archived_at': m.group(1),
                            'size_bytes':  size,
                            '_ts':         m.group(1),
                        })

        versions.sort(key=lambda v: v['_ts'], reverse=True)
        for v in versions:
            del v['_ts']

        if not canonical and versions:
            canonical = dict(versions[0])
            canonical['note'] = 'No canonical file found; showing most recent version.'

        return {
            'canonical':     canonical,
            'versions':      versions,
            'version_count': len(versions),
            '_source':       str(search_root),
        }
