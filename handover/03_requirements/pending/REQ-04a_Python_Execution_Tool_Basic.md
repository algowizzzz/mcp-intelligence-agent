# REQ-04a — Python Execution Tool (Basic Libraries)
**Status:** Pending Implementation
**Version:** 1.0 (2026-04-04)
**Scope:** Sandboxed Python execution environment with core data science libraries. Heavy quantitative finance libraries (QuantLib, riskfolio-lib, arch, scikit-learn) are tracked separately in REQ-04b and implemented after this is stable.

---

## 1. Background

The platform has no Python code execution capability. All tools are pre-defined MCP tools. This requirement adds:

1. **Ad-hoc Python execution** — agent composes and runs code dynamically in chat
2. **Script execution from file tree** — upload `.py` scripts to Domain Data or My Data and run them
3. **Python file preview** — `.py` files render with syntax highlighting (read-only, no execution from preview)
4. **Output + figure capture** — stdout/stderr returned to agent; matplotlib/Plotly figures auto-saved and displayed in canvas panel

---

## 2. Architecture

```
Agent (LLM)
    │
    │  Tool call: python_execute(code="...", context_files=[...])
    ▼
MCP Tool: PythonExecuteTool
    (sajhamcpserver/sajha/tools/impl/python_executor.py)
    │
    │  Submits code to sandboxed subprocess
    ▼
Execution Sandbox
    │  Isolated venv: sajhamcpserver/python_sandbox_venv/
    │  Timeout: 60s CPU / 90s wall clock
    │  Memory limit: 512 MB (ulimit)
    │  No network access (iptables/subprocess env)
    │  Filesystem write: /tmp/sandbox/{session_id}/ only
    ▼
Result: { stdout, stderr, exit_code, figures, elapsed_seconds }
    │
    ▼
Agent Server: Figure detection → canvas SSE event
    │
    ▼
Frontend: Output in tool card + canvas panel for figures
```

---

## 3. Sandbox Requirements

### 3.1 Isolation Model

**Subprocess-based isolation** (not `eval`/`exec` in-process):

```python
import subprocess, sys, tempfile, os

def run_sandboxed(code: str, timeout: int = 60) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        script = os.path.join(tmpdir, 'user_script.py')
        with open(script, 'w') as f:
            f.write(SANDBOX_PREAMBLE + '\n' + code)

        result = subprocess.run(
            [SANDBOX_VENV_PYTHON, script],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmpdir,
            env={
                'PATH': os.path.join(SANDBOX_VENV, 'bin'),
                'HOME': tmpdir,
                'PYTHONPATH': '',
                'NO_PROXY': '*',         # block proxy
                'http_proxy': '',
                'https_proxy': '',
            }
        )
        return {
            'stdout': result.stdout[:20_000],
            'stderr': result.stderr[:5_000],
            'exit_code': result.returncode,
        }
```

`SANDBOX_PREAMBLE` sets up figure capture (see section 3.3).

### 3.2 Resource Limits

| Limit | Value | Enforcement |
|---|---|---|
| CPU timeout | 60 seconds | `subprocess.run(timeout=60)` |
| Wall clock timeout | 90 seconds | `subprocess.run(timeout=90)` |
| Memory | 512 MB | `resource.setrlimit(RLIMIT_AS)` in preamble |
| Stdout capture | 20 KB | Truncated before returning |
| Stderr capture | 5 KB | Truncated before returning |
| Disk writes | `/tmp/sandbox/{session}/` only | Enforced by sandbox preamble |
| Network | Blocked | Empty proxy env + network namespace (Linux) |

### 3.3 Figure Capture Preamble

The sandbox preamble auto-intercepts matplotlib and Plotly figure saves:

```python
# SANDBOX_PREAMBLE — injected before every user script
import os, sys, resource, json

# Memory limit
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))

# Figure tracking
_FIGURES = []
_SANDBOX_DIR = os.environ.get('SANDBOX_DIR', '/tmp/sandbox')

# Matplotlib intercept
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    _orig_show = plt.show
    def _patched_show(*args, **kwargs):
        fname = os.path.join(_SANDBOX_DIR, f'fig_{len(_FIGURES)}.png')
        plt.savefig(fname, dpi=150, bbox_inches='tight')
        _FIGURES.append({'type': 'png', 'path': fname})
    plt.show = _patched_show
except ImportError:
    pass

# Plotly intercept
try:
    import plotly.io as pio
    _orig_show = pio.show
    def _patched_plotly_show(fig, *args, **kwargs):
        fname = os.path.join(_SANDBOX_DIR, f'fig_{len(_FIGURES)}.html')
        fig.write_html(fname)
        _FIGURES.append({'type': 'html', 'path': fname})
    pio.show = _patched_plotly_show
except ImportError:
    pass

# Write figure manifest on exit
import atexit
def _write_manifest():
    with open(os.path.join(_SANDBOX_DIR, 'figures.json'), 'w') as f:
        json.dump(_FIGURES, f)
atexit.register(_write_manifest)
```

### 3.4 Code Security Scan (Static, Pre-Execution)

Before executing any code, scan for blocked imports using AST parsing (not regex):

```python
import ast

BLOCKED_IMPORTS = {
    'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib',
    'http', 'ftplib', 'smtplib', 'imaplib', 'poplib',
    'multiprocessing', 'threading', 'ctypes', 'cffi',
    'importlib', '__builtins__', 'builtins',
}

def scan_code(code: str) -> list[str]:
    """Return list of blocked import names found in code."""
    violations = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error: {e}")
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
```

If violations found, return immediately with a clear error message — do not execute.

---

## 4. MCP Tool Specifications

### 4.1 `python_execute` Tool

**File:** `sajhamcpserver/sajha/tools/impl/python_executor.py`

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "string",
      "description": "Python code to execute. Available libraries: pandas, numpy, scipy, matplotlib, plotly, openpyxl, pyarrow, statsmodels."
    },
    "context_files": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Optional list of file paths from domain_data or my_data to make available in the sandbox as local files."
    },
    "timeout_seconds": {
      "type": "integer",
      "default": 60,
      "maximum": 90,
      "description": "Execution timeout in seconds."
    }
  },
  "required": ["code"]
}
```

**Output schema:**
```json
{
  "stdout": "string (≤20KB)",
  "stderr": "string (≤5KB)",
  "exit_code": "integer",
  "elapsed_seconds": "number",
  "figures": [
    { "type": "png|html", "filename": "fig_0.png", "url": "/api/fs/charts/fig_0.png" }
  ],
  "error": "string or null"
}
```

### 4.2 `python_run_script` Tool

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "script_path": {
      "type": "string",
      "description": "Path to a .py script in domain_data or my_data (e.g. 'scripts/analyse.py')."
    },
    "section": {
      "type": "string",
      "enum": ["domain_data", "my_data"],
      "description": "Section containing the script."
    },
    "args": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Command-line arguments to pass to the script via sys.argv."
    },
    "timeout_seconds": {
      "type": "integer",
      "default": 60,
      "maximum": 90
    }
  },
  "required": ["script_path", "section"]
}
```

**Behaviour:** Reads the `.py` file from the worker's section directory, applies the same security scan, then executes in the sandbox.

---

## 5. Sandbox Virtual Environment

### 5.1 Location

```
sajhamcpserver/python_sandbox_venv/
```

Added to `.gitignore` (do not commit the venv itself). The setup script is committed.

### 5.2 Basic Library Set (REQ-04a)

```
pandas>=2.0
numpy>=1.26
scipy>=1.12
matplotlib>=3.8
plotly>=5.19
openpyxl>=3.1
pyarrow>=14.0
statsmodels>=0.14
```

### 5.3 Setup Script

**File:** `sajhamcpserver/setup_sandbox_venv.sh`

```bash
#!/bin/bash
set -e
VENV_DIR="$(dirname "$0")/python_sandbox_venv"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install \
    pandas>=2.0 \
    numpy>=1.26 \
    scipy>=1.12 \
    matplotlib>=3.8 \
    plotly>=5.19 \
    openpyxl>=3.1 \
    pyarrow>=14.0 \
    statsmodels>=0.14
echo "Sandbox venv created at $VENV_DIR"
```

### 5.4 Tool JSON Config

**File:** `sajhamcpserver/config/tools/python_execute.json`

```json
{
  "name": "python_execute",
  "description": "Execute Python code in a sandboxed environment. Available libraries: pandas, numpy, scipy, matplotlib, plotly, openpyxl, pyarrow, statsmodels. No network access. Timeout: 60s.",
  "version": "1.0.0",
  "enabled": true,
  "implementation": "sajha.tools.impl.python_executor.PythonExecuteTool"
}
```

**File:** `sajhamcpserver/config/tools/python_run_script.json` (same pattern)

---

## 6. Agent Server Integration

### 6.1 Figure Detection and Canvas Event

In `agent_server.py`, in the `on_tool_end` handler — detect figure output and emit a canvas SSE event (same pattern as FIX-VIZ-003 in REQ-03):

```python
if tool_name in ('python_execute', 'python_run_script'):
    figures = output.get('figures', [])
    if figures:
        first_fig = figures[0]
        yield f"data: {json.dumps({'type': 'canvas', 'title': 'Python Output', 'canvas_type': 'chart', 'chart_url': first_fig['url']})}\n\n"
```

---

## 7. Frontend: `.py` File Preview

**File:** `public/js/file-tree.js` — `BPulseFilePreview`

When a `.py` file is clicked in the file tree, render it in the canvas panel with syntax highlighting:

```javascript
// In BPulseFilePreview.render()
if (ext === 'py') {
    var pre = document.createElement('pre');
    var code = document.createElement('code');
    code.className = 'language-python';
    code.textContent = content;
    pre.appendChild(code);
    container.appendChild(pre);
    if (window.hljs) hljs.highlightElement(code);

    // "Run Script" button for writable sections
    if (opts.writable && opts.onRunScript) {
        var btn = document.createElement('button');
        btn.className = 'py-run-btn';
        btn.textContent = '▶ Run Script';
        btn.onclick = function() {
            showRunConfirmModal(section, path, opts.onRunScript);
        };
        container.insertBefore(btn, pre);
    }
    return;
}
```

**Run confirmation modal:**
- Shows script name and path
- Input for optional arguments
- "Run" and "Cancel" buttons
- On Run: calls `python_run_script` tool via agent chat prompt (not directly)

---

## 8. System Prompt Additions

Add to `agent/prompt.py` (or equivalent system prompt file):

```
## Python Execution

You have access to two Python execution tools:

- `python_execute`: Run ad-hoc Python code. Use for data analysis, calculations, and chart generation.
- `python_run_script`: Run a .py script from domain_data or my_data.

Available libraries: pandas, numpy, scipy, matplotlib, plotly, openpyxl, pyarrow, statsmodels.

Best practices:
- Always use pandas for tabular data operations.
- Use plotly for charts (not matplotlib) as plotly charts render interactively in the canvas panel.
- Call plt.show() or fig.show() to trigger figure capture — figures are auto-saved and displayed.
- Do not attempt to access the network, file system outside provided context_files, or import blocked modules.
- For large datasets, load from context_files rather than embedding data in code.
- Summarise numeric results in your response — do not rely solely on stdout.
```

---

## 9. Testing Plan

### PY-TEST-001 — Basic Code Execution

Prompt: `"Calculate the mean and standard deviation of [1.2, 3.4, 5.6, 7.8, 9.0] using numpy"`

Expected:
- `python_execute` tool called with correct numpy code
- stdout shows mean and std
- exit_code = 0
- No JavaScript errors

### PY-TEST-002 — Blocked Import Rejected

Prompt: `"Write Python code to make an HTTP request to example.com"`

Expected:
- Code scanner detects `import requests` or `import urllib`
- Returns error: "Blocked import: requests. Network access is not permitted in the sandbox."
- Agent informs user execution was blocked

### PY-TEST-003 — Matplotlib Figure Capture

Prompt: `"Plot a simple bar chart using matplotlib with values [10, 20, 15, 25] and labels A, B, C, D"`

Expected:
- Figure auto-saved to charts directory
- Canvas SSE event emitted
- Canvas panel opens with the PNG figure

### PY-TEST-004 — Plotly Figure Capture

Prompt: `"Create a Plotly bar chart from this data: categories=[Q1,Q2,Q3,Q4], values=[120,145,110,180]"`

Expected:
- Plotly HTML saved to charts directory
- Canvas panel opens with interactive Plotly chart in iframe

### PY-TEST-005 — Script Execution from My Data

Upload a `.py` script to My Data, then prompt: `"Run my script [filename.py] from my data"`

Expected:
- `python_run_script` tool called with correct path and section
- stdout returned in tool card
- No errors if script is valid

### PY-TEST-006 — Timeout Enforcement

Prompt: `"Run this Python code: import time; time.sleep(120)"`

Expected:
- Execution terminates at 60-second timeout
- Error returned: "Execution timed out after 60 seconds"
- Agent informs user

### PY-TEST-007 — Context File Access

Upload `data.csv` to My Data, then prompt: `"Use Python to calculate the average of the 'exposure' column in my data.csv file"`

Expected:
- `python_execute` called with `context_files=['my_data/data.csv']`
- File made available in sandbox directory
- Script reads and calculates correctly

### PY-TEST-008 — Syntax Error Handling

Prompt: `"Run this Python code: def broken(:"`

Expected:
- AST parse fails before execution
- Clear error returned: "Syntax error: invalid syntax"
- No subprocess spawned

---

## 10. Acceptance Criteria

- [ ] PY-TEST-001 through PY-TEST-008 all pass
- [ ] Blocked imports (os, sys, subprocess, socket, requests) are rejected via AST scan before execution
- [ ] Timeout kills subprocess at configured limit
- [ ] Matplotlib and Plotly figures auto-captured and available in canvas panel
- [ ] `.py` files preview with syntax highlighting in canvas panel
- [ ] Run Script button appears for writable sections (My Data, My Workflows)
- [ ] Confirmation modal shown before execution
- [ ] stdout/stderr truncated at 20KB/5KB
- [ ] No sandbox escape possible (verified by running blocked import tests)
- [ ] `setup_sandbox_venv.sh` creates working venv with all basic libraries
- [ ] Tool configs in `sajhamcpserver/config/tools/`
- [ ] System prompt updated with Python tool guidance

---

## Out of Scope (See REQ-04b)

- QuantLib
- riskfolio-lib
- arch (GARCH models)
- scikit-learn
- Any library not in the basic set defined in section 5.2
