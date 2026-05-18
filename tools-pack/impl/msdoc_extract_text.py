"""msdoc_extract_text — extract all plain text from a Word/Excel document."""
import os
from typing import Any, Dict

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP


class MsdocExtractText(MsDocBaseTool):
    """Extract all plain text content from a Word or Excel document."""

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

        extension = os.path.splitext(file_path)[1].lower()

        if extension in ['.docx', '.doc']:
            doc_content = self._read_word_document(file_path)
            text = '\n'.join(doc_content['paragraphs'])
        elif extension in ['.xlsx', '.xls', '.xlsm']:
            excel_content = self._read_excel_document(file_path, max_rows=10000)
            text_parts = []
            for row in excel_content['data']:
                text_parts.append('\t'.join(str(cell) if cell else '' for cell in row))
            text = '\n'.join(text_parts)
        else:
            raise ValueError(f"Unsupported file type: {extension}")

        return {
            'filename': filename,
            'text': text,
            'character_count': len(text),
            '_source': str(file_path),
        }
