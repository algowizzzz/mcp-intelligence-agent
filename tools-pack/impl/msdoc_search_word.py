"""msdoc_search_word — search for text within Word documents."""
from typing import Any, Dict

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP


class MsdocSearchWord(MsDocBaseTool):
    """Search for text within a Word .docx document."""

    def get_input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "search_term": {"type": "string"},
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
        section = arguments.get('section', 'domain_data')
        file_path = self._get_file_path(ctx, filename, section)

        if not self._exists(file_path):
            raise ValueError(f"File not found: {filename}")

        doc_content = self._read_word_document(file_path)

        matches = []
        for i, paragraph in enumerate(doc_content['paragraphs']):
            if search_term in paragraph.lower():
                matches.append({
                    'paragraph_index': i,
                    'text': paragraph,
                })

        return {
            'filename': filename,
            'search_term': search_term,
            'matches': matches,
            'match_count': len(matches),
            '_source': str(file_path),
        }
