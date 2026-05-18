"""msdoc_get_excel_metadata — extract metadata from an Excel workbook."""
import io
from typing import Any, Dict

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP


class MsdocGetExcelMetadata(MsDocBaseTool):
    """Get workbook metadata for an Excel .xlsx file."""

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
            wb = load_workbook(io.BytesIO(raw))
            props = wb.properties

            metadata = {
                'creator':  props.creator or '',
                'title':    props.title or '',
                'subject':  props.subject or '',
                'created':  str(props.created) if props.created else '',
                'modified': str(props.modified) if props.modified else '',
            }

            wb.close()
            return {
                'filename': filename,
                'metadata': metadata,
                '_source': str(file_path),
            }
        except ImportError:
            raise ValueError("openpyxl library not installed")
        except Exception as e:
            raise ValueError(f"Failed to get metadata: {str(e)}")
