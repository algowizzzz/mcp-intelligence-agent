"""msdoc_search_excel — search for text within Excel spreadsheets."""
from typing import Any, Dict

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP


class MsdocSearchExcel(MsDocBaseTool):
    """Search for text within an Excel .xlsx spreadsheet."""

    def get_input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "search_term": {"type": "string"},
                "sheet_name": {"type": "string"},
                "section": SECTION_PROP,
            },
            "required": ["filename", "search_term"],
        }

    def get_output_schema(self) -> Dict:
        return {"type": "object"}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ctx = arguments.get('_worker_context') or {}
        filename = arguments['filename']
        search_term = arguments['search_term'].lower()
        sheet_name = arguments.get('sheet_name')
        section = arguments.get('section', 'domain_data')
        file_path = self._get_file_path(ctx, filename, section)

        if not self._exists(file_path):
            raise ValueError(f"File not found: {filename}")

        excel_content = self._read_excel_document(
            file_path,
            sheet_name=sheet_name,
            max_rows=10000,
        )

        matches = []
        for row_idx, row in enumerate(excel_content['data']):
            for col_idx, cell in enumerate(row):
                if cell and search_term in str(cell).lower():
                    matches.append({
                        'row_index': row_idx,
                        'column_index': col_idx,
                        'value': str(cell),
                    })

        return {
            'filename': filename,
            'sheet_name': excel_content['sheet_name'],
            'search_term': search_term,
            'matches': matches,
            'match_count': len(matches),
            '_source': str(file_path),
        }
