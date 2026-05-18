"""msdoc_read_excel_sheet — read a specific sheet from an Excel workbook."""
from typing import Any, Dict

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP


class MsdocReadExcelSheet(MsDocBaseTool):
    """Read data from a specific Excel worksheet."""

    def get_input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "sheet_name": {"type": "string"},
                "sheet_index": {"type": "integer", "minimum": 0},
                "max_rows": {"type": "integer", "default": 100, "minimum": 1, "maximum": 10000},
                "section": SECTION_PROP,
            },
            "required": ["filename"],
        }

    def get_output_schema(self) -> Dict:
        return {"type": "object"}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ctx = arguments.get('_worker_context') or {}
        filename = arguments['filename']
        section = arguments.get('section', 'domain_data')
        file_path = self._get_file_path(ctx, filename, section)

        if not self._exists(file_path):
            raise ValueError(f"File not found: {filename}")

        result = self._read_excel_document(
            file_path,
            arguments.get('sheet_name'),
            arguments.get('sheet_index'),
            arguments.get('max_rows', 100),
            False,
        )
        result['_source'] = str(file_path)
        return result
