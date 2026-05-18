"""msdoc_get_excel_sheets — list all sheets in an Excel workbook."""
import io
from typing import Any, Dict

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP


class MsdocGetExcelSheets(MsDocBaseTool):
    """List all worksheets in an Excel .xlsx workbook."""

    def get_input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
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

        try:
            from openpyxl import load_workbook
            raw = self._read_bytes(file_path)
            wb = load_workbook(io.BytesIO(raw), read_only=True)
            sheets = [
                {'index': i, 'name': sheet.title}
                for i, sheet in enumerate(wb.worksheets)
            ]
            wb.close()

            return {
                'filename': filename,
                'sheets': sheets,
                'count': len(sheets),
                '_source': str(file_path),
            }
        except ImportError:
            raise ValueError("openpyxl library not installed")
        except Exception as e:
            raise ValueError(f"Failed to get sheets: {str(e)}")
