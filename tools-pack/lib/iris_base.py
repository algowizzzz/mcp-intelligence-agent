"""IRIS CCR shared helpers — DataFrame loading, validation, and row cleanup.

The 9 IRIS pandas-based tools share a common CSV (`iris/iris_combined.csv`)
that lives somewhere under the worker's data layers. This module centralises:

- locating the CSV via the worker scope dict (`_worker_context`)
- caching the loaded DataFrame per (worker_id, path)
- validating the LEGAL_ENTITY enum and the Date column
- a NaN-safe cell cleaner

Placed under `tools_pack_lib` so individual tool modules can stay self-contained
(no cross-tool imports). Mirrors the behaviour of the original
`IrisBaseTool` in sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py.
"""

import math
import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from tools_pack_lib.worker_ctx import get_data_layers


LEGAL_ENTITY_ENUM = ['BCMC', 'HARRIS BANK', 'BMO', 'BNBI', 'BOMI',
                     'BHIC', 'BMN', 'BCML', 'BLAC', 'BMMC']


# Per-worker cache to prevent different workers sharing the same DataFrame.
# Key: worker_id (str). Value: {'df': pd.DataFrame, 'path': str}
_CACHE: Dict[str, Dict[str, Any]] = {}


def clean(val: Any) -> Any:
    """Replace NaN with None so JSON serialisation works cleanly."""
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def clean_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {k: clean(v) for k, v in row.items()}


def make_limit_key(row: Dict[str, Any]) -> str:
    code = row.get('Customer Code', '')
    fid  = row.get('Facility ID', '')
    le   = row.get('Legal Entity', '')
    prod = row.get('Product', '')
    return f'{code} / {fid} / {le} / {prod}'


def iris_csv_path(ctx: Dict[str, str]) -> Optional[str]:
    """Locate iris/iris_combined.csv across the worker's data layers.

    Preference order: my_data → domain_data → common (mirrors get_data_layers).
    """
    relative = 'iris/iris_combined.csv'
    for _, root in get_data_layers(ctx, 'all'):
        candidate = os.path.join(root, relative)
        if os.path.isfile(candidate):
            return candidate
    # Fallback: the original tool defaulted to a domain_data subfolder when
    # outside a request context. Without _worker_context we can't go anywhere.
    domain_root = (ctx.get('domain_data_path') or '').strip()
    if domain_root:
        return os.path.join(domain_root, relative)
    return None


def get_df(ctx: Dict[str, str]) -> pd.DataFrame:
    """Return the IRIS DataFrame, cached per (worker_id, path)."""
    worker_id = (ctx.get('worker_id') or '').strip()
    path = iris_csv_path(ctx)
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(
            f"IRIS CSV not found at {path or '<none>'} (looked across worker layers)."
        )
    entry = _CACHE.get(worker_id)
    if entry is None or entry['path'] != path:
        df = pd.read_csv(path, encoding='latin1', low_memory=False)
        df['Date'] = df['Date'].astype(str)
        _CACHE[worker_id] = {'df': df, 'path': path}
    return _CACHE[worker_id]['df']


def latest_date(ctx: Dict[str, str]) -> str:
    return get_df(ctx)['Date'].max()


def valid_dates(ctx: Dict[str, str]) -> List[str]:
    return sorted(get_df(ctx)['Date'].unique().tolist())


def validate_legal_entity(le: str) -> Optional[Dict[str, Any]]:
    if le and le not in LEGAL_ENTITY_ENUM:
        return {
            'error': True, 'error_code': 'INVALID_ENUM',
            'message': f'Invalid legal_entity: {le}',
            'valid_options': LEGAL_ENTITY_ENUM,
        }
    return None


def validate_date(ctx: Dict[str, str], date: str) -> Optional[Dict[str, Any]]:
    valid = valid_dates(ctx)
    if date not in valid:
        return {
            'error': True, 'error_code': 'INVALID_DATE',
            'message': f'Date {date} not found in dataset.',
            'valid_options': valid,
        }
    return None
