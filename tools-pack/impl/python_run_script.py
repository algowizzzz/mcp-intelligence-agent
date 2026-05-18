"""python_run_script — run a .py script from worker data layers in the sandbox."""
import json
import os
import tempfile
from typing import Any, Dict, List, Optional

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._python_sandbox import (
    scan_code,
    run_sandboxed,
    collect_figures,
    charts_dir_for,
    domain_data_dir,
)
from tools_pack_lib.worker_ctx import get_data_layers


class PythonRunScript(BaseMCPTool):
    """Run a .py script (from any data layer) in the sandboxed environment."""

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
                    'enum': ['domain_data', 'my_data', 'common'],
                    'description': 'Data layer containing the script. Default: domain_data.',
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
        script_path: str = (arguments.get('script_path') or '').strip().lstrip('/')
        section: str = arguments.get('section', 'domain_data')
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

        ctx = arguments.get('_worker_context') or {}
        layers = get_data_layers(ctx, 'all')
        layer_map = {name: path.rstrip('/') for name, path in layers if path}

        # Resolve script location — requested section first, then fall back to others
        all_sections = ['domain_data', 'my_data', 'common']
        sections_to_try = [section] + [s for s in all_sections if s != section]

        abs_script: Optional[str] = None
        resolve_errors: List[str] = []

        for try_section in sections_to_try:
            root = layer_map.get(try_section)
            if not root:
                resolve_errors.append(f'{try_section}: not configured')
                continue
            candidate = os.path.normpath(os.path.join(root, script_path))
            if not candidate.startswith(os.path.normpath(root)):
                resolve_errors.append(f'{try_section}: path traversal blocked')
                continue
            if os.path.exists(candidate):
                abs_script = candidate
                break
            resolve_errors.append(f'{try_section}: not found')

        if abs_script is None:
            return {
                'stdout': '', 'stderr': '', 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': f'Script not found: {script_path} (searched: {", ".join(resolve_errors)})',
                '_python_ready': False,
            }

        # Read script source
        try:
            with open(abs_script, 'r', encoding='utf-8') as fh:
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

        extra_env: Dict[str, str] = {}
        data_dir = domain_data_dir(ctx)
        if data_dir:
            extra_env['DATA_DIR'] = data_dir

        with tempfile.TemporaryDirectory(prefix='sajha_sandbox_') as tmpdir:
            run_result = run_sandboxed(code, tmpdir, timeout=timeout, extra_env=extra_env or None)
            c_dir = charts_dir_for(ctx)
            figures = collect_figures(tmpdir, c_dir)

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
