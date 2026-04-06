"""file_read_tool.py — Read any text-based file from domain_data, my_data, or common."""
from pathlib import Path
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator

_TEXT_EXTS = {
    '.md', '.txt', '.csv', '.json', '.jsonl', '.xml', '.html',
    '.yaml', '.yml', '.log', '.tsv', '.rst', '.ini', '.toml',
}
_DEFAULT_MAX_CHARS = 40_000


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
                'Read the full content of a text-based file (markdown, txt, csv, json, '
                'xml, yaml, html, etc.) from domain_data, my_data, or common (shared '
                'library). Returns the raw file content as a string. '
                'Use section="domain_data" for domain knowledge files, '
                'section="my_data" for user-uploaded/personal files, '
                'section="common" for shared library files. '
                'path is relative to the section root, e.g. "report.md" or "canvas/notes.md".'
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
                        '"common" (shared library accessible to all workers).'
                    ),
                },
                'max_chars': {
                    'type': 'integer',
                    'description': (
                        f'Max characters to return (default {_DEFAULT_MAX_CHARS:,}). '
                        'Increase for large files, up to 200,000.'
                    ),
                },
            },
            'required': ['path', 'section'],
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, arguments):
        path = arguments.get('path', '').strip()
        section = arguments.get('section', '')
        max_chars = int(arguments.get('max_chars', _DEFAULT_MAX_CHARS))

        roots = {
            'domain_data': _domain_root,
            'my_data':     _my_data_root,
            'common':      _common_root,
        }
        if section not in roots:
            return {'error': f'Unknown section "{section}". Use: domain_data, my_data, common'}
        if not path:
            return {'error': 'path is required'}

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
                f'Pass max_chars={limit * 2} to read more.'
            )
        return result
