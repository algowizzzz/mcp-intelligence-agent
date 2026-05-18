"""msdoc_read_excel — read data from Excel spreadsheets."""
from typing import Any, Dict

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP


class MsdocReadExcel(MsDocBaseTool):
    """Read and extract data from an Excel .xlsx workbook."""

    def get_input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Excel file to read"},
                "sheet_name": {"type": "string"},
                "sheet_index": {"type": "integer", "minimum": 0},
                "max_rows": {"type": "integer", "default": 100, "minimum": 1, "maximum": 10000},
                "include_formulas": {"type": "boolean", "default": False},
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
            arguments.get('include_formulas', False),
        )
        result['_source'] = str(file_path)
        return result
