"""file_read_tool.py — Read any text-based file from domain_data, my_data, or common."""
from pathlib import Path
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator

_TEXT_EXTS = {
    '.md', '.txt', '.csv', '.json', '.jsonl', '.xml', '.html',
    '.yaml', '.yml', '.log', '.tsv', '.rst', '.ini', '.toml',
}
_DEFAULT_MAX_CHARS = 60_000


def _extract_heading(content: str, heading: str) -> tuple:
    """Extract the content block under a matching markdown heading.

    Returns (extracted_text, matched_heading_line) or (None, None) if not found.
    Matching is case-insensitive and partial (query anywhere in heading text).
    """
    import re
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

    # Collect until next heading at same or higher level
    result_lines = [lines[start_idx]]
    for line in lines[start_idx + 1:]:
        m = heading_pat.match(line)
        if m and len(m.group(1)) <= start_level:
            break
        result_lines.append(line)

    return ''.join(result_lines).strip(), matched_title


def _props():
    return PropertiesConfigurator()


def _resolve(path_str):
    p = Path(path_str)
    return p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()


def _domain_root():
    try:
        from flask import g as _g
        r = getattr(_g, 'worker_data_root', None)
        if r:
            return Path(r.rstrip('/')).resolve()
    except RuntimeError:
        pass
    return _resolve(_props().get('data.domain_data.dir', './data/domain_data'))


def _my_data_root():
    try:
        from flask import g as _g
        r = getattr(_g, 'worker_my_data_root', None)
        if r:
            return Path(r.rstrip('/')).resolve()
    except RuntimeError:
        pass
    return _resolve(_props().get('data.my_data.dir', './data/uploads'))


def _common_root():
    try:
        from flask import g as _g
        r = getattr(_g, 'worker_common_root', None)
        if r:
            return Path(r.rstrip('/')).resolve()
    except RuntimeError:
        pass
    return _resolve(_props().get('data.common_data.dir', './data/common'))


class FileReadTool(BaseMCPTool):

    def __init__(self, config=None):
        cfg = {
            'name': 'file_read',
            'description': (
                'Read a text-based file (markdown, txt, csv, json, xml, yaml, etc.) '
                'from domain_data, my_data, or common. '
                'For large markdown filings, pass heading="Risk Factors" (or any section name) '
                'to extract only that section — much faster than reading the whole file. '
                'If the file is truncated, use heading= to target a specific section or '
                'increase max_chars (up to 200,000). '
                'path is relative to the section root, e.g. "report.md" or "gs/10k/GS_10K.md".'
            ),
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            cfg.update(config)
        super().__init__(cfg)

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': (
                        'Relative path to the file within the section root, '
                        'e.g. "report.md", "canvas/notes.md", "prices.csv". '
                        'Do NOT include the section name in the path.'
                    ),
                },
                'section': {
                    'type': 'string',
                    'enum': ['domain_data', 'my_data', 'common'],
                    'description': (
                        'Data layer: "domain_data" (worker knowledge base), '
                        '"my_data" (user uploads and personal files), '
                        '"common" (shared library accessible to all workers). '
                        'OMIT this parameter to auto-search all sections by filename.'
                    ),
                },
                'max_chars': {
                    'type': 'integer',
                    'description': (
                        f'Max characters to return (default {_DEFAULT_MAX_CHARS:,}). '
                        'Increase for large files, up to 200,000.'
                    ),
                },
                'heading': {
                    'type': 'string',
                    'description': (
                        'For markdown files only: extract the section under this heading. '
                        'Case-insensitive partial match, e.g. "Risk Factors" or "MD&A" or '
                        '"Management\'s Discussion". Returns only that section\'s content, '
                        'not the full file — ideal for large filings.'
                    ),
                },
            },
            'required': ['path'],
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, arguments):
        path = arguments.get('path', '').strip()
        section = arguments.get('section', '')
        max_chars = int(arguments.get('max_chars', _DEFAULT_MAX_CHARS))
        heading = (arguments.get('heading') or '').strip()

        roots = {
            'domain_data': _domain_root,
            'my_data':     _my_data_root,
            'common':      _common_root,
        }
        if not path:
            return {'error': 'path is required'}

        # If no section given, auto-search all roots for a bare filename
        if not section:
            bare = Path(path).name
            for sec, root_fn in roots.items():
                root = root_fn()
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
                except (PermissionError, OSError):
                    pass
                if section:
                    break
            if not section:
                return {'error': f'File not found: {path} (searched all sections)'}

        if section not in roots:
            return {'error': f'Unknown section "{section}". Use: domain_data, my_data, common'}

        base = roots[section]()

        # Strip any leading slashes or section prefixes the agent might add
        clean = path.lstrip('/')
        for prefix in ('data/', 'my_data/', 'domain_data/', 'common/'):
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
                break

        target = (base / clean).resolve()

        # Path traversal guard
        try:
            target.relative_to(base)
        except ValueError:
            return {'error': 'Path traversal not allowed'}

        if not target.exists():
            return {'error': f'File not found: {path} (looked in {section}: {base})'}

        if target.is_dir():
            files = sorted(str(f.relative_to(base)) for f in target.iterdir() if f.is_file())
            return {
                'error': f'"{path}" is a directory, not a file.',
                'files_in_dir': files[:30],
            }

        suffix = target.suffix.lower()
        if suffix not in _TEXT_EXTS:
            return {
                'error': (
                    f'"{suffix}" files are not readable as plain text. '
                    f'Supported extensions: {", ".join(sorted(_TEXT_EXTS))}. '
                    'Use pdf_read for .pdf, msdoc_read_word for .docx, '
                    'msdoc_read_excel for .xlsx.'
                )
            }

        try:
            content = target.read_text(encoding='utf-8', errors='replace')
        except Exception as exc:
            return {'error': f'Could not read file: {exc}'}

        # Heading extraction — markdown only
        if heading:
            if suffix != '.md':
                return {'error': f'heading parameter is only supported for .md files, got {suffix}'}
            extracted, matched = _extract_heading(content, heading)
            if extracted is None:
                # List available headings to help the agent retry
                import re
                headings = [
                    l.rstrip() for l in content.splitlines()
                    if re.match(r'^#{1,6}\s+', l)
                ]
                return {
                    'error': f'Heading "{heading}" not found in {path}',
                    'available_headings': headings[:40],
                }
            limit = min(max(max_chars, 1), 200_000)
            truncated = len(extracted) > limit
            result = {
                'path': str(target.relative_to(base)),
                'section': section,
                'matched_heading': matched,
                'size_chars': len(extracted[:limit] if truncated else extracted),
                'content': extracted[:limit] if truncated else extracted,
            }
            if truncated:
                result['truncated'] = True
                result['note'] = f'Section truncated at {limit:,} chars. Pass max_chars={limit * 2} to read more.'
            return result

        limit = min(max(max_chars, 1), 200_000)
        truncated = len(content) > limit
        if truncated:
            content = content[:limit]

        result = {
            'path': str(target.relative_to(base)),
            'section': section,
            'size_chars': len(content),
            'content': content,
        }
        if truncated:
            result['truncated'] = True
            result['note'] = (
                f'File truncated at {limit:,} chars. '
                f'Use heading="<section name>" to read a specific section, '
                f'or pass max_chars={limit * 2} to read more.'
            )
        return result
