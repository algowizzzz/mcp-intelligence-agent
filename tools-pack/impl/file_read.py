"""
file_read — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/file_read_tool.py.
Worker scope from arguments['_worker_context'].
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._operational_base import get_roots

logger = logging.getLogger(__name__)


_TEXT_EXTS = {
    '.md', '.txt', '.csv', '.json', '.jsonl', '.xml', '.html',
    '.yaml', '.yml', '.log', '.tsv', '.rst', '.ini', '.toml',
}
_DEFAULT_MAX_CHARS = 60_000


def _extract_heading(content: str, heading: str) -> Tuple[Optional[str], Optional[str]]:
    lines = content.splitlines(keepends=True)
    heading_pat = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)
    query = heading.strip().lower()

    start_idx = None
    start_level = None
    matched_title = None

    for i, line in enumerate(lines):
        m = heading_pat.match(line)
        if m and query in m.group(2).lower():
            start_idx = i
            start_level = len(m.group(1))
            matched_title = line.rstrip()
            break

    if start_idx is None:
        return None, None

    result_lines = [lines[start_idx]]
    for line in lines[start_idx + 1:]:
        m = heading_pat.match(line)
        if m and len(m.group(1)) <= start_level:
            break
        result_lines.append(line)

    return ''.join(result_lines).strip(), matched_title


class FileRead(BaseMCPTool):
    """Read a text-based file from domain_data / my_data / common."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'path':      {'type': 'string'},
                'section':   {'type': 'string', 'enum': ['domain_data', 'my_data', 'common']},
                'max_chars': {'type': 'integer'},
                'heading':   {'type': 'string'},
            },
            'required': ['path'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        path = (arguments.get('path') or '').strip()
        section = (arguments.get('section') or '').strip()
        max_chars = int(arguments.get('max_chars') or _DEFAULT_MAX_CHARS)
        heading = (arguments.get('heading') or '').strip()

        if not path:
            return {'error': 'path is required'}

        domain, my_data, common = get_roots(arguments)
        roots = {'domain_data': domain, 'my_data': my_data, 'common': common}

        if not section:
            bare = Path(path).name
            for sec, root in roots.items():
                if root is None:
                    continue
                candidate = root / bare
                if candidate.exists():
                    section = sec
                    break
                try:
                    for sub in root.iterdir():
                        if sub.is_dir() and (sub / bare).exists():
                            section = sec
                            path = str((sub / bare).relative_to(root))
                            break
                    if section:
                        break
                except (PermissionError, OSError):
                    pass
            if not section:
                return {'error': f'File not found: {path} (searched all sections)'}

        if section not in roots:
            return {'error': f'Unknown section "{section}". Use: domain_data, my_data, common'}

        base = roots[section]
        if base is None:
            return {'error': f'Section "{section}" not configured on worker context'}

        clean = path.lstrip('/')
        for prefix in ('data/', 'my_data/', 'domain_data/', 'common/'):
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
                break

        target = (base / clean).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            return {'error': 'Path traversal not allowed'}

        if not target.exists():
            return {'error': f'File not found: {path} (looked in {section}: {base})'}

        if target.is_dir():
            files = sorted(str(f.relative_to(base)) for f in target.iterdir() if f.is_file())
            return {
                'error':         f'"{path}" is a directory, not a file.',
                'files_in_dir':  files[:30],
            }

        suffix = target.suffix.lower()
        if suffix not in _TEXT_EXTS:
            return {
                'error': (
                    f'"{suffix}" files are not readable as plain text. '
                    f'Supported: {", ".join(sorted(_TEXT_EXTS))}. '
                    'Use pdf_read for .pdf, msdoc_read_word for .docx, '
                    'msdoc_read_excel for .xlsx.'
                )
            }

        try:
            content = target.read_text(encoding='utf-8', errors='replace')
        except Exception as exc:
            return {'error': f'Could not read file: {exc}'}

        if heading:
            if suffix != '.md':
                return {'error': f'heading parameter is only supported for .md files, got {suffix}'}
            extracted, matched = _extract_heading(content, heading)
            if extracted is None:
                headings_found = [
                    l.rstrip() for l in content.splitlines()
                    if re.match(r'^#{1,6}\s+', l)
                ]
                return {
                    'error':              f'Heading "{heading}" not found in {path}',
                    'available_headings': headings_found[:40],
                }
            limit = min(max(max_chars, 1), 200_000)
            truncated = len(extracted) > limit
            result = {
                'path':            str(target.relative_to(base)),
                'section':         section,
                'matched_heading': matched,
                'size_chars':      len(extracted[:limit] if truncated else extracted),
                'content':         extracted[:limit] if truncated else extracted,
            }
            if truncated:
                result['truncated'] = True
                result['note'] = f'Section truncated at {limit:,} chars.'
            return result

        limit = min(max(max_chars, 1), 200_000)
        truncated = len(content) > limit
        if truncated:
            content = content[:limit]

        result = {
            'path':       str(target.relative_to(base)),
            'section':    section,
            'size_chars': len(content),
            'content':    content,
        }
        if truncated:
            result['truncated'] = True
            result['note'] = f'File truncated at {limit:,} chars.'
        return result
