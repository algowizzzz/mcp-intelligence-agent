"""msdoc_read_word — read Word document content (paragraphs and tables)."""
import io
from typing import Any, Dict

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP


class MsdocReadWord(MsDocBaseTool):
    """Read and extract content from a Word .docx document."""

    def get_input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Word file to read"},
                "heading": {
                    "type": "string",
                    "description": (
                        "Extract only the section under this heading "
                        "(case-insensitive partial match against Heading styles)."
                    ),
                },
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
        heading = (arguments.get('heading') or '').strip()
        file_path = self._get_file_path(ctx, filename, section)

        if not self._exists(file_path):
            raise ValueError(f"File not found: {filename}")

        if heading:
            from docx import Document
            raw = self._read_bytes(file_path)
            doc = Document(io.BytesIO(raw))
            text, matched_title, all_headings = self._extract_word_heading(doc, heading)

            if text is None:
                if not all_headings:
                    return {
                        'error': (
                            f'No Word heading styles found in {filename}. '
                            'The document may not use standard Heading styles.'
                        ),
                        'filename': filename,
                        '_source': file_path,
                    }
                return {
                    'error': f'Heading "{heading}" not found in {filename}',
                    'available_headings': all_headings[:40],
                    'filename': filename,
                    '_source': file_path,
                }

            return {
                'filename': filename,
                'matched_heading': matched_title,
                'size_chars': len(text),
                'content': text,
                'available_headings': all_headings[:40],
                '_source': file_path,
            }

        result = self._read_word_document(file_path)
        result['_source'] = str(file_path)
        return result
