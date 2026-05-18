"""Shared sandbox runner for python_execute and python_run_script.

Ported from sajhamcpserver/sajha/tools/impl/python_executor.py.

Compliance changes:
- No Flask `g` — worker context comes from arguments['_worker_context'].
- No `sajha.storage` / `sajha.path_resolver` — uses pathlib/open() directly.
- SANDBOX_VENV_PYTHON still points to the fork's python_sandbox_venv since
  this venv lives in our repo (not in upstream); we resolve it as an
  absolute path relative to the repo root.
"""
import ast
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Absolute path to the sandbox venv Python interpreter.
# Resolved relative to this file: tools-pack/impl/_python_sandbox.py
# tools-pack/ sits next to sajhamcpserver/ in the repo root.
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent  # tools-pack/impl/ -> tools-pack/ -> repo root
SANDBOX_VENV_PYTHON = str(_REPO_ROOT / 'sajhamcpserver' / 'python_sandbox_venv' / 'bin' / 'python')


# ---------------------------------------------------------------------------
# Blocked imports — AST-based security scanner
# ---------------------------------------------------------------------------

BLOCKED_IMPORTS = {
    'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib',
    'http', 'ftplib', 'smtplib', 'imaplib', 'poplib',
    'multiprocessing', 'threading', 'ctypes', 'cffi',
    'importlib', '__builtins__', 'builtins',
}


def scan_code(code: str) -> List[str]:
    """Return list of blocked import names found in code (via AST, not regex)."""
    violations: List[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"Syntax error: {exc}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split('.')[0]
                if root in BLOCKED_IMPORTS:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split('.')[0]
                if root in BLOCKED_IMPORTS:
                    violations.append(node.module)
    return violations


SANDBOX_PREAMBLE = r"""
import os as _os, sys as _sys, json as _json, atexit as _atexit

# Memory limit (1.5 GB) — only available on Linux; silently skip on macOS/Windows
try:
    import resource as _resource
    _MEM = 1536 * 1024 * 1024
    _resource.setrlimit(_resource.RLIMIT_AS, (_MEM, _MEM))
except (ImportError, ValueError, _resource.error):
    pass

# Figure tracking
_FIGURES = []
_SANDBOX_DIR = _os.environ.get('SANDBOX_DIR', '/tmp/sandbox')

# DATA_DIR — absolute path to the worker's domain_data directory.
DATA_DIR = _os.environ.get('DATA_DIR', '')

# Matplotlib intercept
try:
    import matplotlib as _mpl
    _mpl.use('Agg')
    import matplotlib.pyplot as _plt
    def _patched_show(*args, **kwargs):
        fname = _os.path.join(_SANDBOX_DIR, f'fig_{len(_FIGURES)}.png')
        _plt.savefig(fname, dpi=150, bbox_inches='tight')
        _FIGURES.append({'type': 'png', 'path': fname})
    _plt.show = _patched_show
except ImportError:
    pass

# Plotly intercept
try:
    import plotly.io as _pio
    def _patched_plotly_show(fig, *args, **kwargs):
        fname = _os.path.join(_SANDBOX_DIR, f'fig_{len(_FIGURES)}.html')
        fig.write_html(fname)
        _FIGURES.append({'type': 'html', 'path': fname})
    _pio.show = _patched_plotly_show
except ImportError:
    pass

# Write figure manifest on exit
def _write_manifest():
    manifest_path = _os.path.join(_SANDBOX_DIR, 'figures.json')
    with open(manifest_path, 'w') as _f:
        _json.dump(_FIGURES, _f)
_atexit.register(_write_manifest)
"""


def run_sandboxed(
    code: str,
    tmpdir: str,
    timeout: int = 60,
    extra_env: Optional[Dict[str, str]] = None,
) -> dict:
    """Write code to tmpdir, execute in sandbox venv, return raw result dict."""
    script_path = os.path.join(tmpdir, 'user_script.py')
    with open(script_path, 'w', encoding='utf-8') as fh:
        fh.write(SANDBOX_PREAMBLE + '\n')
        fh.write(code)

    env: Dict[str, str] = {
        'PATH': os.path.dirname(SANDBOX_VENV_PYTHON),
        'HOME': tmpdir,
        'PYTHONPATH': '',
        'SANDBOX_DIR': tmpdir,
        'NO_PROXY': '*',
        'no_proxy': '*',
        'http_proxy': '',
        'https_proxy': '',
        'HTTP_PROXY': '',
        'HTTPS_PROXY': '',
    }
    if extra_env:
        env.update(extra_env)

    if not os.path.isfile(SANDBOX_VENV_PYTHON):
        return {
            'stdout': '',
            'stderr': (
                f'Sandbox Python interpreter not found: {SANDBOX_VENV_PYTHON}. '
                'Run: python -m venv sajhamcpserver/python_sandbox_venv && '
                'sajhamcpserver/python_sandbox_venv/bin/pip install pandas numpy scipy '
                'matplotlib plotly openpyxl pyarrow statsmodels'
            ),
            'exit_code': -1,
            'elapsed_seconds': 0.0,
            'timed_out': False,
        }

    start = time.monotonic()
    try:
        result = subprocess.run(
            [SANDBOX_VENV_PYTHON, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmpdir,
            env=env,
        )
        elapsed = time.monotonic() - start
        return {
            'stdout': result.stdout[:20_000],
            'stderr': result.stderr[:5_000],
            'exit_code': result.returncode,
            'elapsed_seconds': round(elapsed, 3),
            'timed_out': False,
        }
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return {
            'stdout': '',
            'stderr': f'Execution timed out after {timeout} seconds.',
            'exit_code': -1,
            'elapsed_seconds': round(elapsed, 3),
            'timed_out': True,
        }


def collect_figures(tmpdir: str, charts_dir: str) -> List[Dict[str, str]]:
    """Read figures.json from sandbox tmpdir, copy each into charts_dir."""
    manifest_path = os.path.join(tmpdir, 'figures.json')
    if not os.path.exists(manifest_path):
        return []
    try:
        with open(manifest_path, encoding='utf-8') as fh:
            raw_figures: List[Dict] = json.load(fh)
    except Exception:
        return []

    os.makedirs(charts_dir, exist_ok=True)
    figures: List[Dict[str, str]] = []
    for entry in raw_figures:
        src_path = entry.get('path', '')
        fig_type = entry.get('type', 'png')
        if not src_path or not os.path.exists(src_path):
            continue
        filename = os.path.basename(src_path)
        dest = os.path.join(charts_dir, filename)
        try:
            with open(src_path, 'rb') as src, open(dest, 'wb') as dst:
                dst.write(src.read())
            figures.append({
                'type': fig_type,
                'filename': filename,
                'url': f'/api/fs/charts/{filename}',
            })
        except Exception:
            pass
    return figures


def copy_context_files(context_files: List[str], tmpdir: str, ctx: Dict[str, str]):
    """Copy requested files from worker layers into tmpdir for direct local read."""
    from tools_pack_lib.worker_ctx import get_data_layers
    layers = get_data_layers(ctx, 'all')
    layer_map = {name: path.rstrip('/') for name, path in layers if path}

    for rel_path in context_files:
        rel_path = rel_path.strip().lstrip('/')
        resolved = None

        # Prefix-aware resolution
        if rel_path.startswith('my_data/') and 'my_data' in layer_map:
            inner = rel_path[len('my_data/'):]
            cand = os.path.join(layer_map['my_data'], inner)
            if os.path.exists(cand):
                resolved = cand
        elif rel_path.startswith('domain_data/') and 'domain_data' in layer_map:
            inner = rel_path[len('domain_data/'):]
            cand = os.path.join(layer_map['domain_data'], inner)
            if os.path.exists(cand):
                resolved = cand
        elif rel_path.startswith('common/') and 'common' in layer_map:
            inner = rel_path[len('common/'):]
            cand = os.path.join(layer_map['common'], inner)
            if os.path.exists(cand):
                resolved = cand

        # Bare/relative filename — try every section
        if resolved is None:
            for _, root in layers:
                if not root:
                    continue
                cand = os.path.join(root.rstrip('/'), rel_path)
                if os.path.exists(cand):
                    resolved = cand
                    break

        # Recursive walk fallback
        if resolved is None:
            bare = os.path.basename(rel_path)
            for _, root in layers:
                if not root:
                    continue
                try:
                    for dirpath, _, files in os.walk(root):
                        if bare in files:
                            resolved = os.path.join(dirpath, bare)
                            break
                    if resolved:
                        break
                except OSError:
                    continue

        if resolved:
            dest = os.path.join(tmpdir, os.path.basename(resolved))
            try:
                with open(resolved, 'rb') as src, open(dest, 'wb') as dst:
                    dst.write(src.read())
            except Exception:
                pass


def charts_dir_for(ctx: Dict[str, str]) -> str:
    """Resolve the charts dir for the current user.

    `ctx['my_data_path']` is already user-scoped (agent appends user_id);
    chart files live under `{my_data_path}/charts/`.
    """
    my_data = (ctx.get('my_data_path') or '').strip().rstrip('/')
    if my_data:
        return os.path.join(my_data, 'charts')
    return os.path.join(tempfile.gettempdir(), 'sajha_charts')


def domain_data_dir(ctx: Dict[str, str]) -> str:
    return (ctx.get('domain_data_path') or '').strip().rstrip('/')
