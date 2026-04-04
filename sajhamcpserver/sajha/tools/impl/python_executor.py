"""
Python Execution Tools — REQ-04a
Sandboxed Python execution with figure capture for matplotlib and Plotly.
"""

import ast
import json
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.path_resolver import resolve as path_resolve

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Absolute path to the sandbox venv Python interpreter.
# Resolved relative to *this* file so it works regardless of CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
# sajhamcpserver/sajha/tools/impl -> up 3 levels -> sajhamcpserver/
_SAJHA_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..'))
SANDBOX_VENV_PYTHON = os.path.join(_SAJHA_ROOT, 'python_sandbox_venv', 'bin', 'python')

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


# ---------------------------------------------------------------------------
# Sandbox preamble — injected before every user script
# ---------------------------------------------------------------------------

SANDBOX_PREAMBLE = r"""
import os as _os, sys as _sys, json as _json, atexit as _atexit

# Memory limit (512 MB) — only available on Linux; silently skip on macOS/Windows
try:
    import resource as _resource
    _MEM = 512 * 1024 * 1024
    _resource.setrlimit(_resource.RLIMIT_AS, (_MEM, _MEM))
except (ImportError, ValueError, _resource.error):
    pass

# Figure tracking
_FIGURES = []
_SANDBOX_DIR = _os.environ.get('SANDBOX_DIR', '/tmp/sandbox')

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

del _os, _sys, _json, _atexit
"""


# ---------------------------------------------------------------------------
# Worker context helper
# ---------------------------------------------------------------------------

def _get_worker_ctx() -> dict:
    try:
        from flask import g as _g
        return getattr(_g, 'worker_ctx', {}) or {}
    except RuntimeError:
        return {}


def _get_user_id() -> Optional[str]:
    try:
        from flask import g as _g
        return getattr(_g, 'user_id', None)
    except RuntimeError:
        return None


# ---------------------------------------------------------------------------
# Core sandbox runner
# ---------------------------------------------------------------------------

def _run_sandboxed(
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
        'PATH': os.path.join(os.path.dirname(SANDBOX_VENV_PYTHON)),
        'HOME': tmpdir,
        'PYTHONPATH': '',
        'SANDBOX_DIR': tmpdir,
        # Block network proxies
        'NO_PROXY': '*',
        'no_proxy': '*',
        'http_proxy': '',
        'https_proxy': '',
        'HTTP_PROXY': '',
        'HTTPS_PROXY': '',
    }
    if extra_env:
        env.update(extra_env)

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


def _collect_figures(tmpdir: str, charts_dir: str) -> List[Dict[str, str]]:
    """
    Read figures.json from the sandbox temp dir, copy each figure to charts_dir,
    and return a list of figure dicts with 'type', 'filename', and 'url' fields.
    """
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
            shutil.copy2(src_path, dest)
            figures.append({
                'type': fig_type,
                'filename': filename,
                'url': f'/api/fs/charts/{filename}',
            })
        except Exception:
            pass
    return figures


def _copy_context_files(context_files: List[str], tmpdir: str, worker_ctx: dict, user_id: Optional[str]):
    """
    Copy requested context files from domain_data or my_data into tmpdir
    so user code can read them as local files.
    """
    for rel_path in context_files:
        rel_path = rel_path.strip().lstrip('/')
        resolved = None

        # Try my_data first (prefix 'my_data/')
        if rel_path.startswith('my_data/'):
            inner = rel_path[len('my_data/'):]
            if worker_ctx and user_id:
                try:
                    base = path_resolve('my_data', worker_ctx, user_id=user_id)
                    candidate = os.path.join(base, inner)
                    if os.path.isfile(candidate):
                        resolved = candidate
                except Exception:
                    pass
        elif rel_path.startswith('domain_data/'):
            inner = rel_path[len('domain_data/'):]
            if worker_ctx:
                try:
                    base = path_resolve('domain_data', worker_ctx)
                    candidate = os.path.join(base, inner)
                    if os.path.isfile(candidate):
                        resolved = candidate
                except Exception:
                    pass

        # Fallback: treat as bare filename and search both sections
        if resolved is None and worker_ctx:
            for section in ('my_data', 'domain_data'):
                try:
                    kw = {'user_id': user_id} if section == 'my_data' and user_id else {}
                    base = path_resolve(section, worker_ctx, **kw)
                    candidate = os.path.join(base, rel_path)
                    if os.path.isfile(candidate):
                        resolved = candidate
                        break
                except Exception:
                    pass

        if resolved:
            dest = os.path.join(tmpdir, os.path.basename(resolved))
            try:
                shutil.copy2(resolved, dest)
            except Exception:
                pass


def _charts_dir(worker_ctx: dict, user_id: Optional[str]) -> str:
    """Return the charts directory path for the current user."""
    if worker_ctx and user_id:
        try:
            my_data_base = path_resolve('my_data', worker_ctx, user_id=user_id)
            return os.path.join(my_data_base, 'charts')
        except Exception:
            pass
    return os.path.join(tempfile.gettempdir(), 'sajha_charts')


# ---------------------------------------------------------------------------
# PythonExecuteTool
# ---------------------------------------------------------------------------

class PythonExecuteTool(BaseMCPTool):
    """Execute ad-hoc Python code in a sandboxed subprocess environment."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'code': {
                    'type': 'string',
                    'description': (
                        'Python code to execute. Available libraries: '
                        'pandas, numpy, scipy, matplotlib, plotly, openpyxl, '
                        'pyarrow, statsmodels.'
                    ),
                },
                'context_files': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': (
                        'Optional list of file paths from domain_data or my_data '
                        'to make available in the sandbox as local files. '
                        'Prefix with "my_data/" or "domain_data/".'
                    ),
                },
                'timeout_seconds': {
                    'type': 'integer',
                    'default': 60,
                    'maximum': 90,
                    'description': 'Execution timeout in seconds (max 90).',
                },
            },
            'required': ['code'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'stdout': {'type': 'string'},
                'stderr': {'type': 'string'},
                'exit_code': {'type': 'integer'},
                'elapsed_seconds': {'type': 'number'},
                'figures': {'type': 'array'},
                'error': {'type': ['string', 'null']},
                '_python_ready': {'type': 'boolean'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Any:
        code: str = arguments.get('code', '').strip()
        context_files: List[str] = arguments.get('context_files') or []
        timeout: int = min(int(arguments.get('timeout_seconds', 60)), 90)

        if not code:
            return {
                'stdout': '', 'stderr': '', 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': 'No code provided.', '_python_ready': False,
            }

        # --- Security scan ---
        try:
            violations = scan_code(code)
        except ValueError as exc:
            return {
                'stdout': '', 'stderr': str(exc), 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': str(exc), '_python_ready': False,
            }

        if violations:
            msg = (
                f"Blocked import(s) detected: {', '.join(violations)}. "
                "Network access and system-level modules are not permitted in the sandbox."
            )
            return {
                'stdout': '', 'stderr': msg, 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': msg, '_python_ready': False,
            }

        worker_ctx = _get_worker_ctx()
        user_id = _get_user_id()

        with tempfile.TemporaryDirectory(prefix='sajha_sandbox_') as tmpdir:
            # Copy requested context files into the sandbox working dir
            if context_files:
                _copy_context_files(context_files, tmpdir, worker_ctx, user_id)

            # Execute
            run_result = _run_sandboxed(code, tmpdir, timeout=timeout)

            # Collect figures
            c_dir = _charts_dir(worker_ctx, user_id)
            figures = _collect_figures(tmpdir, c_dir)

        error: Optional[str] = None
        if run_result['timed_out']:
            error = f"Execution timed out after {timeout} seconds."
        elif run_result['exit_code'] != 0 and run_result['stderr']:
            error = run_result['stderr'][:500]

        return {
            'stdout': run_result['stdout'],
            'stderr': run_result['stderr'],
            'exit_code': run_result['exit_code'],
            'elapsed_seconds': run_result['elapsed_seconds'],
            'figures': figures,
            'error': error,
            '_python_ready': True,
        }


# ---------------------------------------------------------------------------
# PythonRunScriptTool
# ---------------------------------------------------------------------------

class PythonRunScriptTool(BaseMCPTool):
    """Run a .py script from domain_data or my_data in the sandboxed environment."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'script_path': {
                    'type': 'string',
                    'description': (
                        "Path to a .py script relative to the section root "
                        "(e.g. 'scripts/analyse.py')."
                    ),
                },
                'section': {
                    'type': 'string',
                    'enum': ['domain_data', 'my_data'],
                    'description': 'Section containing the script.',
                },
                'args': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Command-line arguments passed to the script via sys.argv.',
                },
                'timeout_seconds': {
                    'type': 'integer',
                    'default': 60,
                    'maximum': 90,
                    'description': 'Execution timeout in seconds (max 90).',
                },
            },
            'required': ['script_path', 'section'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'stdout': {'type': 'string'},
                'stderr': {'type': 'string'},
                'exit_code': {'type': 'integer'},
                'elapsed_seconds': {'type': 'number'},
                'figures': {'type': 'array'},
                'error': {'type': ['string', 'null']},
                '_python_ready': {'type': 'boolean'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Any:
        script_path: str = arguments.get('script_path', '').strip().lstrip('/')
        section: str = arguments.get('section', 'my_data')
        args: List[str] = arguments.get('args') or []
        timeout: int = min(int(arguments.get('timeout_seconds', 60)), 90)

        if not script_path:
            return {
                'stdout': '', 'stderr': '', 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': 'No script_path provided.', '_python_ready': False,
            }

        if not script_path.endswith('.py'):
            return {
                'stdout': '', 'stderr': '', 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': 'Only .py scripts are supported.', '_python_ready': False,
            }

        worker_ctx = _get_worker_ctx()
        user_id = _get_user_id()

        # Resolve script location
        try:
            if section == 'my_data':
                if not user_id:
                    return {
                        'stdout': '', 'stderr': '', 'exit_code': 1,
                        'elapsed_seconds': 0.0, 'figures': [],
                        'error': 'User context not available for my_data section.',
                        '_python_ready': False,
                    }
                section_root = path_resolve('my_data', worker_ctx, user_id=user_id)
            else:
                section_root = path_resolve('domain_data', worker_ctx)
        except Exception as exc:
            return {
                'stdout': '', 'stderr': str(exc), 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': f'Path resolution failed: {exc}', '_python_ready': False,
            }

        abs_script = os.path.normpath(os.path.join(section_root, script_path))

        # Security: prevent path traversal outside section root
        if not abs_script.startswith(os.path.normpath(section_root)):
            return {
                'stdout': '', 'stderr': '', 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': 'Path traversal outside section root is not permitted.',
                '_python_ready': False,
            }

        if not os.path.isfile(abs_script):
            return {
                'stdout': '', 'stderr': '', 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': f'Script not found: {script_path}', '_python_ready': False,
            }

        # Read script source
        try:
            with open(abs_script, encoding='utf-8') as fh:
                code = fh.read()
        except Exception as exc:
            return {
                'stdout': '', 'stderr': str(exc), 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': f'Failed to read script: {exc}', '_python_ready': False,
            }

        # Security scan
        try:
            violations = scan_code(code)
        except ValueError as exc:
            return {
                'stdout': '', 'stderr': str(exc), 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': str(exc), '_python_ready': False,
            }

        if violations:
            msg = (
                f"Blocked import(s) detected in script: {', '.join(violations)}. "
                "Network access and system-level modules are not permitted in the sandbox."
            )
            return {
                'stdout': '', 'stderr': msg, 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': msg, '_python_ready': False,
            }

        # Inject sys.argv if args provided
        if args:
            argv_repr = json.dumps([os.path.basename(abs_script)] + args)
            argv_injection = f"import sys as _sys_argv; _sys_argv.argv = {argv_repr}\n"
            code = argv_injection + code

        with tempfile.TemporaryDirectory(prefix='sajha_sandbox_') as tmpdir:
            run_result = _run_sandboxed(code, tmpdir, timeout=timeout)

            c_dir = _charts_dir(worker_ctx, user_id)
            figures = _collect_figures(tmpdir, c_dir)

        error: Optional[str] = None
        if run_result['timed_out']:
            error = f"Execution timed out after {timeout} seconds."
        elif run_result['exit_code'] != 0 and run_result['stderr']:
            error = run_result['stderr'][:500]

        return {
            'stdout': run_result['stdout'],
            'stderr': run_result['stderr'],
            'exit_code': run_result['exit_code'],
            'elapsed_seconds': run_result['elapsed_seconds'],
            'figures': figures,
            'error': error,
            '_python_ready': True,
        }
