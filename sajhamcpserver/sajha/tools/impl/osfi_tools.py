"""
Copyright All rights Reserved 2025-2030, Ashutosh Sinha, Email: ajsinha@gmail.com
OSFI Regulatory Intelligence Tools — MCP Tool Implementations
"""

import os
import datetime
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator


class OsfiBaseTool(BaseMCPTool):
    """Shared base for OSFI tools."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {'type': 'object', 'properties': {}, 'required': []})

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def _get_osfi_dir(self) -> str:
        return PropertiesConfigurator().get('data.osfi_docs_dir', './CCR_data/osfi')

    def _get_chunk_size(self) -> int:
        return int(PropertiesConfigurator().get('data.osfi_chunk_size_chars', '8000'))

    def _get_max_chunks(self) -> int:
        return int(PropertiesConfigurator().get('data.osfi_max_chunks_per_call', '3'))

    def _list_md_files(self, osfi_dir: str):
        files = []
        for root, dirs, fnames in os.walk(osfi_dir):
            for fname in fnames:
                if fname.endswith('.md') and fname != 'README.md':
                    fpath = os.path.join(root, fname)
                    rel = os.path.relpath(fpath, osfi_dir)
                    stat = os.stat(fpath)
                    parts = fname.replace('.md', '').split('_')
                    code = parts[0] if parts else ''
                    year = ''
                    for p in parts:
                        if p.isdigit() and len(p) == 4:
                            year = p
                            break
                    files.append({
                        'filename': fname,
                        'path': fpath,
                        'relative_path': rel,
                        'size_bytes': stat.st_size,
                        'guideline_code': code,
                        'year': year,
                        'description': fname.replace('.md', '').replace('_', ' ')
                    })
        return files

    def execute(self, params: Dict[str, Any]) -> Any:
        raise NotImplementedError("Subclasses must implement execute()")


class OsfiListDocsTool(OsfiBaseTool):
    """Lists all OSFI guideline documents available locally."""

    def execute(self, params: Dict[str, Any]) -> Any:
        osfi_dir = self._get_osfi_dir()
        category = params.get('category', 'all')

        if not os.path.exists(osfi_dir):
            return {'files': [], 'count': 0, 'osfi_docs_dir': osfi_dir,
                    'error': f'OSFI docs directory not found: {osfi_dir}'}

        files = self._list_md_files(osfi_dir)

        if category and category != 'all':
            files = [f for f in files if category.lower() in f['filename'].lower()]

        return {'files': files, 'count': len(files), 'osfi_docs_dir': osfi_dir}


class OsfiSearchGuidanceTool(OsfiBaseTool):
    """Search across OSFI guideline documents for a keyword or topic."""

    def execute(self, params: Dict[str, Any]) -> Any:
        keyword = params.get('keyword', '')
        doc_filter = params.get('doc_filter', '')
        max_results = int(params.get('max_results', 5))

        if not keyword:
            return {'error': True, 'error_code': 'MISSING_PARAM', 'message': 'keyword is required'}

        osfi_dir = self._get_osfi_dir()
        if not os.path.exists(osfi_dir):
            return {'matches': [], 'total_matches': 0, 'keyword_used': keyword}

        all_files = self._list_md_files(osfi_dir)
        if doc_filter:
            all_files = [f for f in all_files
                         if doc_filter.lower() in f['filename'].lower()
                         or doc_filter.lower() in f['guideline_code'].lower()]

        matches = []
        kw = keyword.lower()
        for f in all_files:
            try:
                file_matches = self._search_file(f['path'], kw)
                for m in file_matches:
                    matches.append({
                        'doc': f['filename'],
                        'path': f['path'],
                        'heading': m['heading'],
                        'excerpt': m['excerpt'],
                        'char_offset': m['char_offset']
                    })
            except Exception:
                continue

        matches = matches[:max_results]
        return {'matches': matches, 'total_matches': len(matches), 'keyword_used': keyword}

    def _search_file(self, filepath: str, keyword: str):
        matches = []
        current_heading = ''
        offset = 0
        with open(filepath, 'r', encoding='utf-8') as fh:
            for line in fh:
                if line.startswith('#'):
                    current_heading = line.strip()
                elif keyword in line.lower() and len(line.strip()) > 20:
                    matches.append({
                        'heading': current_heading,
                        'excerpt': line.strip()[:200],
                        'char_offset': offset
                    })
                offset += len(line.encode('utf-8'))
        return matches


class OsfiReadDocumentTool(OsfiBaseTool):
    """Read a targeted chunk from a specific OSFI guideline document."""

    def execute(self, params: Dict[str, Any]) -> Any:
        filename = params.get('filename', '')
        chapter = params.get('chapter', '')
        keyword = params.get('keyword', '')
        char_offset = params.get('char_offset', None)
        max_chars = int(params.get('max_chars', self._get_chunk_size()))

        if not filename:
            return {'error': True, 'error_code': 'MISSING_PARAM', 'message': 'filename is required'}

        osfi_dir = self._get_osfi_dir()
        all_files = self._list_md_files(osfi_dir)
        matched = [f for f in all_files if f['filename'] == filename]
        if not matched:
            return {'error': True, 'error_code': 'NO_DATA',
                    'message': f'File not found: {filename}',
                    'available': [f['filename'] for f in all_files]}

        fpath = matched[0]['path']
        with open(fpath, 'r', encoding='utf-8') as fh:
            content = fh.read()

        total_chars = len(content)
        max_chunks = self._get_max_chunks()
        effective_max = min(max_chars, self._get_chunk_size() * max_chunks)

        start = 0
        if char_offset is not None:
            start = int(char_offset)
        elif chapter:
            chapter_lower = chapter.lower()
            lines = content.split('\n')
            pos = 0
            for line in lines:
                if line.startswith('#') and chapter_lower in line.lower():
                    start = pos
                    break
                pos += len(line.encode('utf-8')) + 1
        elif keyword:
            idx = content.lower().find(keyword.lower())
            if idx >= 0:
                start = max(0, idx - 200)

        chunk_text = content[start:start + effective_max]
        char_end = start + len(chunk_text)
        has_more = char_end < total_chars

        heading = ''
        for line in content[:start].split('\n')[::-1]:
            if line.startswith('#'):
                heading = line.strip()
                break

        return {
            'chunks': [{
                'text': chunk_text,
                'heading': heading,
                'char_start': start,
                'char_end': char_end,
                'doc': filename
            }],
            'chunks_returned': 1,
            'total_doc_chars': total_chars,
            'has_more': has_more,
            'next_char_offset': char_end if has_more else None
        }


class OsfiFetchAnnouncementsTool(OsfiBaseTool):
    """Fetch latest content from live OSFI announcement and guidance pages using Tavily."""

    def execute(self, params: Dict[str, Any]) -> Any:
        category = params.get('category', 'news')
        max_items = params.get('max_items', None)

        # Get URLs from the tool config (populated when loaded from JSON)
        urls = self.config.get('urls', [])
        if not urls:
            # Fallback hardcoded list
            urls = [
                {'name': 'News & Announcements', 'url': 'https://www.osfi-bsif.gc.ca/en/news',
                 'category': 'news', 'description': 'OSFI main news and announcements page'},
                {'name': 'Guidance Library', 'url': 'https://www.osfi-bsif.gc.ca/en/guidance/guidance-library',
                 'category': 'guidance_library', 'description': 'Full OSFI guidance library'},
                {'name': 'Annual Risk Outlook', 'url': 'https://www.osfi-bsif.gc.ca/en/supervision/annual-risk-outlook',
                 'category': 'risk_outlook', 'description': 'Annual risk outlook'},
            ]

        if category and category != 'all':
            urls = [u for u in urls if u.get('category') == category]

        if max_items:
            urls = urls[:int(max_items)]

        results = []
        failed = []
        for u in urls:
            try:
                result = self._fetch_url(u)
                results.append(result)
            except Exception as e:
                failed.append({'url': u.get('url', ''), 'error': str(e)})

        return {'results': results, 'total_fetched': len(results), 'failed': failed}

    def _fetch_url(self, url_entry: Dict) -> Dict:
        """Fetch URL content via Tavily /extract (exact URL); fall back to URL reference."""
        target_url = url_entry['url']
        content = f"[Direct URL: {target_url}]"
        try:
            from .edgar_tavily_client import tavily_extract
            results = tavily_extract([target_url])
            if results:
                raw = results[0].get('raw_content', '')
                if raw and len(raw.strip()) > 100:
                    content = raw
        except Exception:
            pass

        return {
            'url_name': url_entry.get('name', ''),
            'url': target_url,
            'category': url_entry.get('category', ''),
            'content': content,
            'fetched_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'status': 'ok'
        }
