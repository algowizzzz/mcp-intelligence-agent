"""msdoc_list_files — list Word/Excel files across worker data layers."""
from typing import Any, Dict, List

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP
from tools_pack_lib.worker_ctx import get_data_layers


class MsdocListFiles(MsDocBaseTool):
    """List Word/Excel files in worker data layers (recursive)."""

    def get_input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "file_type": {
                    "type": "string",
                    "enum": ["all", "word", "excel"],
                    "default": "all",
                },
                "section": SECTION_PROP,
            },
        }

    def get_output_schema(self) -> Dict:
        return {"type": "object"}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ctx = arguments.get('_worker_context') or {}
        section = arguments.get('section', 'domain_data')
        file_type = arguments.get('file_type', 'all')

        # When listing domain_data, scan all layers to discover files regardless of location.
        if section == 'domain_data':
            dirs_to_scan: List[str] = []
            for _, path in get_data_layers(ctx, 'all'):
                if path:
                    dirs_to_scan.append(path.rstrip('/'))

            seen = set()
            all_files: List[Dict] = []
            for d in dirs_to_scan:
                for f in self._list_files_by_type(file_type, d):
                    key = f['path']
                    if key not in seen:
                        seen.add(key)
                        all_files.append(f)

            return {
                'directory': dirs_to_scan[0] if dirs_to_scan else '',
                'section': section,
                'file_type': file_type,
                'count': len(all_files),
                'files': all_files,
                '_source': ', '.join(dirs_to_scan),
            }

        # my_data / common — single directory
        docs_dir = self._resolve_docs_dir(ctx, section)
        files = self._list_files_by_type(file_type, docs_dir)
        return {
            'directory': docs_dir,
            'section': section,
            'file_type': file_type,
            'count': len(files),
            'files': files,
            '_source': docs_dir,
        }
