"""
pdf_read — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/operational_tools.py (PdfReadTool).
Worker scope from arguments['_worker_context'].
"""

import io
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._operational_base import get_roots, safe_path, find_file

logger = logging.getLogger(__name__)


def _parse_pages(pages_arg: str, total: int) -> List[int]:
    if not pages_arg or pages_arg == 'all':
        return list(range(total))
    m = re.match(r"^(\d+)-(\d+)$", pages_arg.strip())
    if m:
        a, b = int(m.group(1)) - 1, int(m.group(2)) - 1
        return list(range(max(0, a), min(total, b + 1)))
    m2 = re.match(r"^(\d+)$", pages_arg.strip())
    if m2:
        i = int(m2.group(1)) - 1
        return [i] if 0 <= i < total else []
    return list(range(total))


class PdfRead(BaseMCPTool):
    """Extract text (and tables) from a PDF file, with optional heading-section extraction."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'file_path':      {'type': 'string'},
                'pages':          {'type': 'string'},
                'extract_tables': {'type': 'boolean'},
                'max_chars':      {'type': 'integer'},
                'heading':        {'type': 'string'},
            },
            'required': ['file_path'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        file_path = arguments.get('file_path', '')
        pages_arg = arguments.get('pages', 'all')
        extract_tables = arguments.get('extract_tables', True)
        max_chars = int(arguments.get('max_chars', 50000))
        heading = (arguments.get('heading') or '').strip()

        domain, my_data, common = get_roots(arguments)
        safe = safe_path(file_path, domain, my_data, common)
        if not safe or not os.path.exists(str(safe)):
            safe = find_file(file_path, domain, my_data, common)
        if not safe or not os.path.exists(str(safe)):
            return {'error': f'File not found or access denied: {file_path}'}
        if safe.suffix.lower() != '.pdf':
            return {'error': 'pdf_read only accepts .pdf files.'}

        # Prefer PyMuPDF for heading detection, fall back to pdfplumber.
        try:
            import fitz  # PyMuPDF
        except ImportError:
            fitz = None

        try:
            with open(str(safe), 'rb') as fh:
                raw = fh.read()
        except Exception as exc:
            return {'error': f'PDF could not be read: {exc}'}

        if fitz is not None:
            try:
                doc = fitz.open(stream=io.BytesIO(raw), filetype='pdf')
            except Exception as exc:
                return {'error': f'PDF could not be parsed: {exc}'}

            if doc.is_encrypted:
                return {'error': 'PDF is encrypted. Cannot extract without password.'}

            total_pages = len(doc)
            page_indices = _parse_pages(pages_arg, total_pages)

            if heading:
                return self._extract_pdf_section(doc, page_indices, heading, safe, total_pages)

            text_parts: List[str] = []
            tables: List[Dict[str, Any]] = []
            for i in page_indices:
                page = doc[i]
                text_parts.append(page.get_text())
                if extract_tables:
                    try:
                        for tab in page.find_tables():
                            rows = tab.extract()
                            headers = getattr(tab.header, 'names', []) if hasattr(tab, 'header') else []
                            if rows:
                                if not headers:
                                    headers = rows[0]
                                    rows = rows[1:]
                                tables.append({'page': i + 1, 'headers': headers, 'rows': rows})
                    except Exception:
                        pass

            full_text = '\n'.join(text_parts)
            truncated = len(full_text) > max_chars
            if truncated:
                full_text = full_text[:max_chars]

            result = {
                'filename':        safe.name,
                'pages_extracted': len(page_indices),
                'total_pages':     total_pages,
                'char_count':      len(full_text),
                'truncated':       truncated,
                'text':            full_text,
                '_source':         str(safe),
            }
            if extract_tables:
                result['tables'] = tables
            if not full_text.strip():
                result['warning'] = 'No text layer detected. PDF may be image-only.'
            return result

        # pdfplumber fallback
        try:
            import pdfplumber
        except ImportError:
            return {'error': 'Neither PyMuPDF nor pdfplumber is installed.'}
        try:
            pdf = pdfplumber.open(io.BytesIO(raw))
        except Exception as exc:
            return {'error': f'PDF could not be parsed: {exc}'}
        total_pages = len(pdf.pages)
        page_indices = _parse_pages(pages_arg, total_pages)
        text_parts = []
        tables = []
        for i in page_indices:
            page = pdf.pages[i]
            text = page.extract_text() or ''
            text_parts.append(text)
            if extract_tables:
                for tab in (page.extract_tables() or []):
                    if tab:
                        headers = [str(c) if c else '' for c in tab[0]]
                        rows = [[str(c) if c else '' for c in row] for row in tab[1:]]
                        tables.append({'page': i + 1, 'headers': headers, 'rows': rows})
        pdf.close()
        full_text = '\n'.join(text_parts)
        truncated = len(full_text) > max_chars
        if truncated:
            full_text = full_text[:max_chars]
        result = {
            'filename':        safe.name,
            'pages_extracted': len(page_indices),
            'total_pages':     total_pages,
            'char_count':      len(full_text),
            'truncated':       truncated,
            'text':            full_text,
            'tables':          tables,
            '_source':         str(safe),
        }
        if not full_text.strip():
            result['warning'] = 'No text layer detected. PDF may be image-only.'
        return result

    def _detect_pdf_headings(self, doc, page_indices):
        from collections import Counter
        page_line_items: Dict[int, List] = {}
        for page_idx in page_indices:
            items = []
            page = doc[page_idx]
            d = page.get_text('dict')
            for block in d.get('blocks', []):
                if block.get('type') != 0:
                    continue
                for line in block.get('lines', []):
                    parts, max_size, bold = [], 0.0, False
                    for span in line.get('spans', []):
                        t = span.get('text', '')
                        if t.strip():
                            parts.append(t)
                        sz = span.get('size', 0.0)
                        if sz > max_size:
                            max_size = sz
                        if span.get('flags', 0) & 16:
                            bold = True
                    line_text = ''.join(parts).strip()
                    if line_text:
                        items.append((max_size, bold, line_text))
            page_line_items[page_idx] = items

        all_line_items = [
            (p + 1, sz, bold, txt)
            for p, items in page_line_items.items()
            for sz, bold, txt in items
        ]
        if not all_line_items:
            return [], ''
        body_size = Counter(round(it[1]) for it in all_line_items).most_common(1)[0][0]
        n_pages = len(page_indices)
        text_page_count: Counter = Counter()
        for _, _, _, txt in all_line_items:
            text_page_count[re.sub(r'\s+', ' ', txt.lower()[:40])] += 1
        running_threshold = max(2, int(n_pages * 0.30))
        running_texts = {k for k, v in text_page_count.items() if v >= running_threshold}

        full_text = '\n'.join(doc[p].get_text() for p in page_indices)
        headings: List[Dict[str, Any]] = []
        search_from = 0
        for page, size, bold, text in all_line_items:
            norm_key = re.sub(r'\s+', ' ', text.lower()[:40])
            is_large = size > body_size * 1.15
            is_bold_hdr = bold and len(text) < 120 and size >= body_size * 0.95
            is_toc_line = bool(re.search(r'\.{3,}', text))
            is_numeric = bool(re.match(r'^[\d\s\.\,\-\$\%]+$', text))
            is_running = norm_key in running_texts
            too_long = len(text) > 200
            too_short = len(text) < 3
            if (is_large or is_bold_hdr) and not any(
                [is_toc_line, is_numeric, is_running, too_long, too_short]
            ):
                pos = full_text.lower().find(text.lower()[:40], search_from)
                if pos == -1:
                    pos = full_text.lower().find(text.lower()[:40])
                if pos != -1:
                    search_from = pos + 1
                    headings.append({'text': text, 'page': page, 'char_offset': pos})
        return headings, full_text

    def _extract_pdf_section(self, doc, page_indices, heading_query, safe, total_pages):
        headings, full_text = self._detect_pdf_headings(doc, page_indices)
        if not headings:
            return {
                'error':    'No headings detected in this PDF.',
                'filename': safe.name,
                '_source':  str(safe),
            }
        query = heading_query.strip().lower()
        match_idx = None
        for i, h in enumerate(headings):
            if query in h['text'].lower():
                match_idx = i
                break
        available = [h['text'] for h in headings]
        if match_idx is None:
            return {
                'error':              f'Heading "{heading_query}" not found in {safe.name}',
                'available_headings': available[:50],
                'filename':           safe.name,
                'total_pages':        total_pages,
                '_source':            str(safe),
            }

        all_heading_offsets = sorted(h['char_offset'] for h in headings)
        matching_headings = [(i, h) for i, h in enumerate(headings) if query in h['text'].lower()]

        best_text = ''
        best_matched_text = headings[match_idx]['text']
        best_start_page = headings[match_idx]['page']
        for _, candidate_h in matching_headings:
            start_off = candidate_h['char_offset']
            next_boundary = len(full_text)
            for hoff in all_heading_offsets:
                if hoff > start_off + len(candidate_h['text']):
                    next_boundary = hoff
                    break
            candidate_text = full_text[start_off:next_boundary].strip()
            if len(candidate_text) > len(best_text):
                best_text = candidate_text
                best_matched_text = candidate_h['text']
                best_start_page = candidate_h['page']

        section_text = best_text
        max_chars = 60_000
        truncated = len(section_text) > max_chars
        if truncated:
            section_text = section_text[:max_chars]
        return {
            'filename':           safe.name,
            'matched_heading':    best_matched_text,
            'start_page':         best_start_page,
            'total_pages':        total_pages,
            'char_count':         len(section_text),
            'truncated':          truncated,
            'content':            section_text,
            'available_headings': available[:50],
            '_source':            str(safe),
        }
