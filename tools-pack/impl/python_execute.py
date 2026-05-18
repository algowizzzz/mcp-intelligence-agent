"""python_execute — sandboxed Python execution (REQ-04a)."""
import tempfile
from typing import Any, Dict, List, Optional

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._python_sandbox import (
    scan_code,
    run_sandboxed,
    collect_figures,
    copy_context_files,
    charts_dir_for,
    domain_data_dir,
)


class PythonExecute(BaseMCPTool):
    """Execute ad-hoc Python code in a sandboxed subprocess."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'code': {
                    'type': 'string',
                    'description': (
                        'Python code to execute. Available libraries: '
                        'pandas, numpy, scipy, matplotlib, plotly, openpyxl, '
                        'pyarrow, statsmodels, arch, riskfolio, sklearn, networkx, xarray. '
                        'DATA_DIR is pre-set to the worker domain_data path.'
                    ),
                },
                'context_files': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Optional: copy specific files into the sandbox working directory.',
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
        code: str = (arguments.get('code') or '').strip()
        context_files: List[str] = arguments.get('context_files') or []
        timeout: int = min(int(arguments.get('timeout_seconds', 60)), 90)

        if not code:
            return {
                'stdout': '', 'stderr': '', 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': 'No code provided.', '_python_ready': False,
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
                f"Blocked import(s) detected: {', '.join(violations)}. "
                "Network access and system-level modules are not permitted in the sandbox."
            )
            return {
                'stdout': '', 'stderr': msg, 'exit_code': 1,
                'elapsed_seconds': 0.0, 'figures': [],
                'error': msg, '_python_ready': False,
            }

        ctx = arguments.get('_worker_context') or {}

        extra_env: Dict[str, str] = {}
        data_dir = domain_data_dir(ctx)
        if data_dir:
            extra_env['DATA_DIR'] = data_dir

        with tempfile.TemporaryDirectory(prefix='sajha_sandbox_') as tmpdir:
            if context_files:
                copy_context_files(context_files, tmpdir, ctx)

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
