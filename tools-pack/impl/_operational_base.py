"""
Shared helpers for operational tools (file_read, pdf_read, search_files, etc.).

Reads worker context from arguments['_worker_context'] and resolves
domain_data/my_data/common roots without Flask or PropertiesConfigurator.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple


def get_roots(arguments: Dict) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """Return (domain_root, my_data_root, common_root) Path objects (or None)."""
    ctx = arguments.get('_worker_context') or {}
    domain = (ctx.get('domain_data_path') or '').strip().rstrip('/')
    my_data = (ctx.get('my_data_path') or '').strip().rstrip('/')
    common = (ctx.get('common_data_path') or '').strip().rstrip('/')
    return (
        Path(domain).resolve() if domain else None,
        Path(my_data).resolve() if my_data else None,
        Path(common).resolve() if common else None,
    )


def safe_path(path_str: str, *allowed_roots: Optional[Path]) -> Optional[Path]:
    """Return Path within one of the allowed roots, or None."""
    if not path_str:
        return None
    try:
        p = Path(path_str).resolve()
    except Exception:
        return None
    for root in allowed_roots:
        if root is None:
            continue
        try:
            p.relative_to(root)
            return p
        except ValueError:
            continue
    return None


def find_file(name: str, *roots: Optional[Path]) -> Optional[Path]:
    """Search bare filename across roots and one level of subdirs."""
    if not name:
        return None
    bare = os.path.basename(name)
    for root in roots:
        if root is None:
            continue
        candidate = root / bare
        if candidate.exists():
            return candidate
        try:
            for sub in root.iterdir():
                if sub.is_dir():
                    c = sub / bare
                    if c.exists():
                        return c
        except (PermissionError, OSError):
            pass
    return None
