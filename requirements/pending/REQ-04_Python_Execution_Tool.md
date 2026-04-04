# REQ-04 — Python Execution Tool
**Status:** Pending Implementation
**Version:** 1.0
**Date:** 2026-04-04
**Scope:** A sandboxed Python execution environment exposed as an MCP tool, with script preview and execution from Domain Data and My Data file trees, and integration with the quant finance ecosystem.

---

## 1. Background

The platform currently has no Python code execution capability. All tools are pre-defined MCP tools with fixed signatures. The user wants to:

1. **Write and execute Python ad-hoc** in the chat (agent composes and runs code dynamically)
2. **Upload Python scripts** to Domain Data or My Data and execute them from the file tree
3. **Preview `.py` files** in the canvas panel with syntax highlighting (read-only preview)
4. **Access financial data libraries** — pandas, numpy, scipy, and quantitative finance libraries

There is an existing `script_tool_generator.py` in the studio module, but it generates tool *definitions*, not runtime code. No sandboxed execution environment exists.

---

## 2. Architecture Overview

```
Agent (LLM)
    │
    │  Tool call: python_execute(code="...", context_files=[...])
    ▼
MCP Tool: PythonExecuteTool (sajhamcpserver/sajha/tools/impl/python_executor.py)
    │
    │  Submits code to sandboxed subprocess
    ▼
Execution Sandbox (RestrictedPython or subprocess + venv)
    │
    │  Runs in isolated venv with allowlisted libraries
    │  Timeout: 60 seconds
    │  Memory limit: 512 MB
    │  No network access
    │  No filesystem write outside /tmp/sandbox/{session_id}/
    ▼
Result: {stdout, stderr, return_value, figures, elapsed_seconds}
    │
    ▼
Agent Server: Chart/figure detection → canvas event
    │
    ▼
Frontend: Output in tool card + canvas panel for figures
```

---

## 3. Execution Sandbox Requirements

### 3.1 Isolation Model

The Python sandbox must use **subprocess-based isolation** (not `eval`/`exec` in-process):

```python
# Implementation approach:
import subprocess
import sys

result = subprocess.run(
    [venv_python_path, '-c', user_code],
    capture_output=True,
    text=True,
    timeout=60,
    cwd=sandbox_dir,
    env={
        'PATH': venv_bin_path,
        'PYTHONPATH': '',
        'HOME': sandbox_dir,
        # NO network, NO system access beyond venv
    }
)
```

**Alternative (preferred if containerization available):** Run in a `nsjail`-wrapped process or Docker container for stronger isolation. For initial implementation, subprocess-based is acceptable.

### 3.2 Dedicated Virtualenv

Create a dedicated virtualenv at `sajhamcpserver/data/python_sandbox/venv/` with only the allowlisted packages. This venv is separate from the main application venv.

**Required packages (must be pre-installed in sandbox venv):**

```
# Core data science
pandas>=2.0.0
numpy>=1.26.0
scipy>=1.12.0
matplotlib>=3.8.0
plotly>=5.18.0

# Quantitative finance
quantlib-python>=1.33
QuantLib>=1.33
pyportfolioopt>=1.5.5
riskfolio-lib>=5.1.0
arch>=6.3.0            # GARCH models
statsmodels>=0.14.0
scikit-learn>=1.4.0

# Data handling
openpyxl>=3.1.0        # Excel read/write
xlrd>=2.0.1            # Legacy Excel read
python-docx>=1.1.0     # Word documents
pyarrow>=14.0.0        # Parquet
fastparquet>=2023.10.0

# Financial data (offline only — no API calls from sandbox)
yfinance>=0.2.36       # Allowed only for data already cached

# Utilities
tabulate>=0.9.0        # Table formatting
humanize>=4.9.0        # Number formatting
python-dateutil>=2.9.0
pytz>=2024.1

# Jupyter-compatible output
IPython>=8.21.0        # For rich output support
```

**Blocked:** `requests`, `httpx`, `urllib`, `socket`, `subprocess`, `os.system`, `shutil.rmtree`, any package not in the allowlist above.

### 3.3 Resource Limits

| Resource | Limit | Enforcement |
|---|---|---|
| CPU time | 60 seconds | `subprocess.run(timeout=60)` |
| Wall clock | 90 seconds | Separate timeout wrapper |
| Memory | 512 MB | `resource.setrlimit(RLIMIT_AS)` before exec |
| Disk write | 50 MB | Sandbox working directory only, quota enforced |
| Network | None | No `requests`/`httpx` in venv; no network namespace |
| File system | Read: domain_data only; Write: /tmp/sandbox/{id}/ | Enforced by symlinks and chroot-style restriction |

### 3.4 Output Capture

The sandbox captures:
- **stdout** (print statements) → returned as `stdout` string
- **stderr** (tracebacks, warnings) → returned as `stderr` string
- **Figures:** Matplotlib figures auto-saved as PNG; Plotly figures auto-saved as HTML
- **Return value:** Last expression result, serialized to JSON if possible

**Figure detection pattern:**

```python
# Injected wrapper code that runs AFTER user code:
import matplotlib.pyplot as plt
import plotly.io as pio

_figures = []
for fig_num in plt.get_fignums():
    fig = plt.figure(fig_num)
    fig_path = f'/tmp/sandbox/{session_id}/fig_{fig_num}.png'
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    _figures.append({'type': 'matplotlib', 'path': fig_path})

# Plotly figures detected via globals
import plotly.graph_objects as go
for var_name, var_val in globals().items():
    if isinstance(var_val, go.Figure):
        html_path = f'/tmp/sandbox/{session_id}/{var_name}.html'
        pio.write_html(var_val, html_path, full_html=True)
        _figures.append({'type': 'plotly', 'path': html_path, 'name': var_name})
```

---

## 4. MCP Tool Specification

### 4.1 `python_execute` Tool

**Config file:** `sajhamcpserver/config/tools/python_execute.json`

```json
{
  "name": "python_execute",
  "description": "Execute Python code in a secure sandbox with pandas, numpy, scipy, QuantLib, and financial analysis libraries pre-installed. Returns stdout, stderr, and any generated charts or data frames. Use this for data analysis, financial calculations, risk modeling, and chart generation from uploaded data files.",
  "version": "1.0.0",
  "enabled": true,
  "connector_id": null,
  "implementation": "sajha.tools.impl.python_executor.PythonExecuteTool",
  "metadata": {
    "category": "data_analysis",
    "access": "write",
    "confirmation_required": false,
    "execution_environment": "sandboxed_python"
  },
  "inputSchema": {
    "type": "object",
    "properties": {
      "code": {
        "type": "string",
        "description": "Python code to execute. Keep under 10,000 characters. Use print() to output results. Assign Plotly or Matplotlib figures to variables to have them captured."
      },
      "context_files": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Optional list of file paths from domain_data or uploads to mount as readable files in the sandbox. Paths are relative to the section root (e.g. ['counterparties/trades.json', 'my_data/user_file.csv'])."
      },
      "context_sections": {
        "type": "array",
        "items": { "type": "string", "enum": ["domain_data", "uploads", "my_workflows", "my_data"] },
        "description": "Sections to make available for reading. Files from these sections are mounted as /data/{section}/ in the sandbox."
      },
      "timeout_seconds": {
        "type": "integer",
        "default": 60,
        "minimum": 5,
        "maximum": 120,
        "description": "Maximum execution time. Default 60 seconds."
      }
    },
    "required": ["code"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "stdout": { "type": "string", "description": "Print output from the code" },
      "stderr": { "type": "string", "description": "Error output and warnings" },
      "exit_code": { "type": "integer", "description": "0 = success, non-zero = error" },
      "elapsed_seconds": { "type": "number" },
      "figures": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "type": { "type": "string", "enum": ["matplotlib", "plotly"] },
            "filename": { "type": "string" },
            "chart_url": { "type": "string" }
          }
        }
      },
      "return_value": { "type": "string", "description": "JSON-serialized last expression" },
      "_code_ready": { "type": "boolean", "description": "Internal flag for agent server" }
    }
  }
}
```

### 4.2 `python_run_script` Tool

For running scripts stored in the file system (Domain Data or My Data):

**Config file:** `sajhamcpserver/config/tools/python_run_script.json`

```json
{
  "name": "python_run_script",
  "description": "Run a .py script file from Domain Data, My Data, or My Workflows in the secure Python sandbox. The script has read access to all files in the same section.",
  "version": "1.0.0",
  "enabled": true,
  "implementation": "sajha.tools.impl.python_executor.PythonRunScriptTool",
  "metadata": {
    "category": "data_analysis",
    "access": "write",
    "confirmation_required": true
  },
  "inputSchema": {
    "type": "object",
    "properties": {
      "script_path": {
        "type": "string",
        "description": "Path to the .py file relative to its section root (e.g. 'analysis/portfolio_var.py')"
      },
      "script_section": {
        "type": "string",
        "enum": ["domain_data", "uploads", "my_data", "my_workflows"],
        "description": "Section containing the script"
      },
      "args": {
        "type": "object",
        "description": "Optional dictionary of arguments passed to the script as environment variables (SCRIPT_ARG_*)"
      },
      "timeout_seconds": { "type": "integer", "default": 120, "maximum": 300 }
    },
    "required": ["script_path", "script_section"]
  }
}
```

### 4.3 Implementation File: `sajhamcpserver/sajha/tools/impl/python_executor.py`

```python
import subprocess
import tempfile
import shutil
import resource
import json
import time
from pathlib import Path

SANDBOX_VENV = Path(__file__).parent.parent.parent.parent / 'data' / 'python_sandbox' / 'venv'
PYTHON_BIN = SANDBOX_VENV / 'bin' / 'python'

_BLOCKED_IMPORTS = [
    'import os', 'import sys', 'import subprocess', 'import socket',
    'import requests', 'import httpx', 'import urllib', 'from os ',
    '__import__', 'eval(', 'exec(', 'compile(',
]

class PythonExecuteTool:
    name = 'python_execute'

    def execute(self, params: dict) -> dict:
        code = params.get('code', '')
        context_files = params.get('context_files', [])
        context_sections = params.get('context_sections', [])
        timeout = min(params.get('timeout_seconds', 60), 120)
        worker_ctx = params.get('_worker_context', {})

        # Security: scan for blocked patterns
        for blocked in _BLOCKED_IMPORTS:
            if blocked in code:
                return {
                    'stdout': '',
                    'stderr': f'Security error: "{blocked}" is not allowed in sandbox code.',
                    'exit_code': 1,
                    'elapsed_seconds': 0,
                    'figures': [],
                }

        # Create temporary sandbox directory
        session_dir = tempfile.mkdtemp(prefix='bpulse_py_')
        try:
            # Mount context files as symlinks (read-only via os.chmod)
            self._mount_context(session_dir, context_files, context_sections, worker_ctx)

            # Write user code to file
            code_file = Path(session_dir) / 'user_code.py'
            wrapped = self._wrap_code(code, session_dir)
            code_file.write_text(wrapped)

            # Execute
            start = time.time()
            result = subprocess.run(
                [str(PYTHON_BIN), str(code_file)],
                capture_output=True, text=True,
                timeout=timeout,
                cwd=session_dir,
                env={'PATH': str(SANDBOX_VENV / 'bin'), 'HOME': session_dir},
            )
            elapsed = round(time.time() - start, 2)

            # Collect figures
            figures = self._collect_figures(session_dir, worker_ctx)

            return {
                'stdout': result.stdout[:20000],  # Cap at 20KB
                'stderr': result.stderr[:5000],
                'exit_code': result.returncode,
                'elapsed_seconds': elapsed,
                'figures': figures,
                '_code_ready': True,
            }
        except subprocess.TimeoutExpired:
            return {'stdout': '', 'stderr': f'Execution timed out after {timeout}s', 'exit_code': -1, 'elapsed_seconds': timeout, 'figures': []}
        finally:
            shutil.rmtree(session_dir, ignore_errors=True)
```

---

## 5. Frontend Requirements

### 5.1 Python Script Preview in File Tree

When a `.py` file is clicked in any file tree section, the canvas panel should open with:
- File name in panel header
- Syntax-highlighted Python source code (using `highlight.js` or Prism.js with `python` language pack)
- Line numbers in gutter
- A "Run Script" button in the panel toolbar (visible only if section is My Data, My Workflows, or Domain Data and user has execution permission)

```javascript
// In ftPreviewFile() and adminPreviewFile() — add .py handling:
case 'py':
    panel.innerHTML = '<pre class="code-preview language-python"><code id="py-code-content"></code></pre>' +
                      '<div class="preview-actions">' +
                        '<button onclick="runScript(\'' + section + '\', \'' + path + '\')">' +
                          '▶ Run Script' +
                        '</button>' +
                      '</div>';
    // Fetch and display
    fetch(fileUrl, { headers: _ftHeaders() })
        .then(r => r.text())
        .then(src => {
            $('py-code-content').textContent = src;
            if (window.hljs) hljs.highlightElement($('py-code-content'));
        });
    break;
```

**Add `highlight.js` CDN** to `mcp-agent.html` and `admin.html` head:
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
```

### 5.2 Run Script from Preview Panel

When the user clicks "Run Script" in the `.py` preview panel:

1. A confirmation modal appears:
   ```
   Run script: portfolio_var.py

   This will execute the script in a secure Python sandbox.
   Execution timeout: 120 seconds.

   [Cancel]  [Run Script]
   ```

2. After confirmation, the chat sends a message automatically:
   ```javascript
   function runScript(section, path) {
       var fname = path.split('/').pop();
       sendChatMessage('Please run the script "' + fname + '" from my ' + section + ' section.');
   }
   ```
   The agent then invokes `python_run_script` with the appropriate parameters.

3. Output appears in the chat as a tool result card showing stdout, stderr, and any generated figures.

### 5.3 Execution Result Rendering in Chat

The `python_execute` and `python_run_script` tool cards must render execution output clearly:

```
┌─────────────────────────────────────────────────────────┐
│ ⚙ python_execute                              ✓ 2.3s   │
├─────────────────────────────────────────────────────────┤
│ stdout:                                                  │
│ ┌────────────────────────────────────────────────────┐  │
│ │ Portfolio VaR (95%): $2,847,391                    │  │
│ │ Portfolio VaR (99%): $4,123,847                    │  │
│ │ Largest contributor: Counterparty ABC (31.2%)      │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ [📊 Chart 1: VaR Distribution] [Open]                   │
│                                                          │
│ stderr: (collapsed by default if empty)                  │
└─────────────────────────────────────────────────────────┘
```

- stdout rendered in a monospace `<pre>` block, max height 400px with scroll
- stderr shown in a collapsible section with yellow/red highlight if non-empty
- Each figure shows as a clickable chip that opens the chart in canvas panel
- Elapsed time shown in header
- Error exit code shown in red

---

## 6. System Prompt Integration

The agent's system prompt must be updated (in `agent/prompt.py`) to include guidance on when and how to use the Python tool:

```
## Python Execution
You have access to a secure Python sandbox via the python_execute tool. Use it when:
- A user uploads a CSV/Excel file and asks for analysis or calculations
- Complex financial calculations are needed (VaR, Greeks, portfolio optimization)
- The user provides a script and asks you to run it
- Data manipulation is needed before visualization

Available libraries: pandas, numpy, scipy, QuantLib, PyPortfolioOpt, arch (GARCH), statsmodels, matplotlib, plotly, scikit-learn, openpyxl, pyarrow.

When writing code:
- Always check if files exist before reading: `import os; os.path.exists('/data/domain_data/file.csv')`
- Use pandas for data manipulation; QuantLib for derivatives pricing and curves
- Assign matplotlib or plotly figures to named variables (they are auto-captured)
- Limit output to key results; avoid printing full dataframes (use .head(10) or .describe())
- Handle errors gracefully with try/except and print informative error messages
```

---

## 7. Quant Finance Library Guide (Reference for Agent Prompt)

The following quant finance capabilities are available:

| Library | Key Capabilities | Example Use Case |
|---|---|---|
| `QuantLib` | Yield curves, bond pricing, swaps, options (Black-Scholes, SABR), credit models | Price an interest rate swap, bootstrap yield curve |
| `PyPortfolioOpt` | Mean-variance optimization, efficient frontier, Black-Litterman | Optimize portfolio weights given covariance matrix |
| `riskfolio-lib` | Risk parity, CVaR optimization, factor models | Risk parity portfolio construction |
| `arch` | GARCH(p,q) models, conditional volatility, DCC-GARCH | Model equity/FX volatility |
| `statsmodels` | OLS/GLS regression, VAR, ARIMA, cointegration tests | Factor model regression, Johansen cointegration |
| `scipy` | Numerical optimization, integration, statistical distributions | Option pricing via Monte Carlo integration |
| `scikit-learn` | PCA, clustering, regression, feature importance | Risk factor identification, PCA on yield curve |

---

## 8. Sandbox Venv Setup Script

This setup script must be run once during deployment:

```bash
#!/bin/bash
# setup_python_sandbox.sh

VENV_DIR="sajhamcpserver/data/python_sandbox/venv"

# Create isolated venv (no system packages)
python3 -m venv --without-pip "$VENV_DIR"

# Bootstrap pip
"$VENV_DIR/bin/python" -m ensurepip --upgrade

# Install allowlisted packages only
"$VENV_DIR/bin/pip" install \
    pandas numpy scipy matplotlib plotly \
    QuantLib pyportfolioopt riskfolio-lib arch statsmodels \
    scikit-learn openpyxl xlrd python-docx pyarrow fastparquet \
    tabulate humanize python-dateutil pytz IPython \
    highlight-io  # For code highlighting in output

# Verify installs
"$VENV_DIR/bin/python" -c "
import pandas, numpy, scipy, matplotlib, plotly, QuantLib
import sklearn, statsmodels, arch, openpyxl, pyarrow
print('All packages verified')
"

echo "Python sandbox venv created at: $VENV_DIR"
```

---

## 9. Security Requirements

**SEC-PY-001 — Code scanning before execution**
Block any code containing: `import os`, `import sys`, `import subprocess`, `import socket`, `import requests`, `import httpx`, `__import__`, `eval(`, `exec(`, `compile(`, `open(`, `shutil`, `pickle.loads`.

**SEC-PY-002 — Filesystem isolation**
The sandbox working directory is a fresh temporary directory per execution. It has no access to the application codebase, configuration files, or credential stores.

**SEC-PY-003 — No network access**
The sandbox venv does not include `requests`, `httpx`, or `urllib3`. No outbound network connections are possible from user code.

**SEC-PY-004 — Resource limits enforced**
Use `resource.setrlimit()` to enforce memory limits before subprocess spawn. Use `subprocess.run(timeout=N)` for CPU time.

**SEC-PY-005 — Audit logging**
All `python_execute` and `python_run_script` calls must be logged to `data/audit/tool_calls.jsonl` with the full code submitted (truncated at 5,000 characters), user_id, worker_id, exit_code, and elapsed time.

**SEC-PY-006 — Output sanitization**
stdout and stderr are sanitized before display: ANSI escape codes stripped, maximum 20KB captured (excess truncated with note).

---

## 10. Acceptance Criteria

- [ ] `python_execute` tool executes pandas, numpy, QuantLib code correctly in sandbox
- [ ] Output (stdout) appears in chat tool card within 2 seconds of completion
- [ ] Matplotlib and Plotly figures generated in code are captured and appear as "Open Chart" chips in tool card
- [ ] Charts open in canvas panel (reuses FIX-VIZ-004 from REQ-03)
- [ ] `.py` files render with syntax highlighting in canvas preview panel
- [ ] "Run Script" button from preview panel triggers agent to execute the script
- [ ] Sandbox cannot access application config files or credential stores
- [ ] Code containing `import os` or `import subprocess` is rejected with SEC-PY-001 error before execution
- [ ] Execution timeout enforced: code running >60s is killed and error returned
- [ ] All executions logged in audit trail
- [ ] Sandbox venv setup script runs without errors on a clean Ubuntu 22.04 environment

---

## 11. Out of Scope

- Jupyter notebook rendering (`.ipynb` files) — separate feature
- Interactive REPL (persistent session between tool calls)
- GPU-accelerated computation
- R or Julia execution
- Package installation at runtime (only pre-installed packages available)
