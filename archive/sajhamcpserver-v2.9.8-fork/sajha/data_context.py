"""
data_context.py — Standardized multi-layer data access for all operational tools.

All tools that read, list, or write files should use this module instead of
building their own path resolution logic.

Layers (in priority order):
  my_data     — per-user files (user uploads, reports, scripts)
  domain_data — per-worker curated data (CSVs, docs, SQL sources)
  common      — platform-wide shared reference data (read-only for users)

The my_data_path stored in g.worker_ctx is already user-scoped
(user_id appended by agent_server before the request reaches SAJHA).
Do NOT call path_resolve('my_data', ctx, user_id=...) — that would
double-append the user_id.
"""

import os
import logging

from sajha.storage import storage

_logger = logging.getLogger(__name__)


def get_data_layers(section: str = 'all') -> list:
    """Return [(layer_name, root_path), ...] for the requested scope.

    Priority order: my_data → domain_data → common.
    Only layers with a non-empty path are returned.

    FIX 4: When called outside a Flask request context (RuntimeError), falls back
    to reading paths from PropertiesConfigurator instead of returning an empty dict.
    FIX 8: Logs a warning when X-Worker-Data-Root is missing from the request context.

    Args:
        section: 'all' | 'my_data' | 'domain_data' | 'common'
    """
    ctx = {}
    try:
        from flask import g as _g
        ctx = getattr(_g, 'worker_ctx', {}) or {}
        # FIX 8: warn when domain_data header is absent inside a request context
        if not ctx.get('domain_data_path', '').strip():
            _logger.warning(
                "X-Worker-Data-Root header missing — tool will search no domain_data files"
            )
    except RuntimeError:
        # FIX 4: Outside Flask request context — fall back to PropertiesConfigurator
        try:
            from sajha.core.properties_configurator import PropertiesConfigurator
            _props = PropertiesConfigurator()
            ctx = {
                'domain_data_path': _props.get('data.domain_data.dir', ''),
                'my_data_path':     _props.get('data.my_data.dir',     ''),
                'common_data_path': _props.get('data.common_data.dir', ''),
            }
        except Exception:
            ctx = {}

    # my_data_path is already user-scoped (user_id appended by agent_server)
    layers = [
        ('my_data',     ctx.get('my_data_path',     '').strip()),
        ('domain_data', ctx.get('domain_data_path', '').strip()),
        ('common',      ctx.get('common_data_path', '').strip()),
    ]

    if section == 'all':
        return [(n, p) for n, p in layers if p]
    return [(n, p) for n, p in layers if n == section and p]


def resolve_file(filename: str, section: str = 'all') -> tuple:
    """Find a file across data layers.

    Returns (full_path, layer_name) for the first match found.
    Raises FileNotFoundError if not found in any searched layer.

    Args:
        filename: relative filename or path, e.g. 'report.csv' or 'iris/iris_combined.csv'
        section:  'all' | 'my_data' | 'domain_data' | 'common'
    """
    # Strip any leading layer prefix the agent might include
    clean = filename.strip().lstrip('/')
    for prefix in ('my_data/', 'domain_data/', 'common/', 'data/'):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
            break

    layers = get_data_layers(section)
    for layer, root in layers:
        candidate = root.rstrip('/') + '/' + clean
        if storage.exists(candidate):
            return candidate, layer

    searched = [n for n, _ in layers]
    raise FileNotFoundError(
        f"'{filename}' not found in section='{section}' "
        f"(layers searched: {searched})"
    )


def list_files(section: str = 'all', extensions: set = None) -> list:
    """List files across data layers.

    Returns list of dicts:
      {path, layer, name, rel, ext}

    Args:
        section:    'all' | 'my_data' | 'domain_data' | 'common'
        extensions: set of extensions to include, e.g. {'csv', 'parquet'}.
                    None means all extensions.
    """
    ext_set = {e.lower().lstrip('.') for e in extensions} if extensions else None
    results = []

    for layer, root in get_data_layers(section):
        root = root.rstrip('/')
        try:
            for rel in storage.list_prefix(root):
                fname = os.path.basename(rel)
                if not fname or fname.startswith('.') or fname.startswith('_'):
                    continue
                if any(p.startswith('.') for p in rel.replace('\\', '/').split('/')):
                    continue
                ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
                if ext_set and ext not in ext_set:
                    continue
                results.append({
                    'path':  root + '/' + rel,
                    'layer': layer,
                    'name':  fname,
                    'rel':   rel,
                    'ext':   ext,
                })
        except Exception:
            pass

    return results
