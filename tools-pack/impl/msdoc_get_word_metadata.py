"""msdoc_get_word_metadata — extract metadata from a Word document."""
import io
from typing import Any, Dict

from tools_pack_impl._msdoc_base import MsDocBaseTool, SECTION_PROP


class MsdocGetWordMetadata(MsDocBaseTool):
    """Get core metadata and properties for a Word .docx document."""

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
            from docx import Document
            raw = self._read_bytes(file_path)
            doc = Document(io.BytesIO(raw))
            core_props = doc.core_properties

            return {
                'filename': filename,
                'metadata': {
                    'author':   core_props.author or '',
                    'title':    core_props.title or '',
                    'subject':  core_props.subject or '',
                    'created':  str(core_props.created) if core_props.created else '',
                    'modified': str(core_props.modified) if core_props.modified else '',
                },
                '_source': str(file_path),
            }
        except ImportError:
            raise ValueError("python-docx library not installed")
        except Exception as e:
            raise ValueError(f"Failed to get metadata: {str(e)}")
