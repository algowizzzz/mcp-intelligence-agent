import json
import pathlib

_WORKERS_FILE = pathlib.Path('sajhamcpserver/config/workers.json')
_DEFAULT_WORKER_ID = 'w-market-risk'

_FALLBACK_PROMPT = '''You are a sophisticated financial risk intelligence agent.'''


def _load_prompt_from_workers() -> str:
    """Load system_prompt from the first enabled worker in workers.json.
    Falls back to _FALLBACK_PROMPT if the file is missing or the prompt is blank.
    """
    try:
        data = json.loads(_WORKERS_FILE.read_text())
        workers = data.get('workers', [])
        for w in workers:
            if w.get('worker_id') == _DEFAULT_WORKER_ID and w.get('enabled', True):
                prompt = w.get('system_prompt', '').strip()
                if prompt:
                    return prompt
        for w in workers:
            if w.get('enabled', True):
                prompt = w.get('system_prompt', '').strip()
                if prompt:
                    return prompt
    except Exception:
        pass
    return _FALLBACK_PROMPT


_PYTHON_ADDENDUM = """
## Python Execution (REQ-04a)

You have access to two Python execution tools:

- `python_execute`: Run ad-hoc Python code in a sandboxed environment.
- `python_run_script`: Run a .py script from domain_data or my_data. Before running a script, use `list_uploaded_files` with `file_type: "py"` to discover available scripts — always pass `file_type: "py"` when listing scripts to avoid truncation of large directories.

Available libraries: pandas, numpy, scipy, matplotlib, plotly, openpyxl, pyarrow, statsmodels.

Best practices:
- Use pandas for tabular data operations.
- Use plotly for charts — plotly charts render interactively in the canvas panel.
- Call `fig.show()` or `plt.show()` to capture figures; they are auto-saved and displayed.
- Do not attempt to access the network, file system outside provided context_files, or import blocked modules (os, sys, subprocess, socket, requests).
- For large datasets, load from context_files rather than embedding data in code.
- Summarise numeric results in your response — do not rely solely on stdout.

## Extended Quantitative Finance Libraries (REQ-04b)
Additional libraries available in the sandbox:
- scikit-learn: ML models (LinearRegression, PCA, KMeans, RandomForest), dimensionality reduction, clustering
- arch: GARCH/EGARCH volatility modelling — `from arch import arch_model`
- riskfolio-lib: Portfolio optimisation — mean-variance, CVaR, HRP — `import riskfolio as rp`
- QuantLib: Interest rate curves, bond pricing, derivatives (if available for runtime Python version)
- xarray: Multi-dimensional labelled arrays for scenario grids and stress tests
- networkx: Counterparty network graphs, contagion and centrality analysis
"""


_CANVAS_ADDENDUM = """

## Canvas Panel — Direct Streaming

**RULE: Canvas is ONLY for your FINAL response. Never open canvas before all tool calls are complete.**

You MUST complete all tool calls and have real data in hand before writing any [CANVAS] output.
- NEVER open canvas with placeholder, TBD, or "to be populated" content
- NEVER pre-write a report template before tools have returned
- NEVER emit [CANVAS] mid-reasoning or as a "I'm about to fetch this" message
- If you need to call tools, call them first. Canvas comes AFTER.

Correct order:
  1. Call all required tools
  2. Receive and process tool results
  3. Write your final response — THEN open [CANVAS] if the output warrants it

When your FINAL response is a report, detailed analysis, policy write-up, or structured document (>200 words with headers/tables):

Start your final response with exactly:
  [CANVAS]Your Report Title Here

Everything AFTER that line streams directly into the canvas panel.
Keep any text BEFORE [CANVAS] to one or two sentences (the chat summary).

Example (correct — tools already called, data in hand):
  Here is the latest news report on RBC.
  [CANVAS]RBC Latest News — April 2026
  ## Summary
  Royal Bank of Canada is currently...
  | Date | Headline | Source |
  |------|----------|--------|
  | Apr 6 | SpaceX IPO ... | Reuters |

Do NOT use {"summary":..., "canvas":...} JSON format.
Skip [CANVAS] entirely for short direct answers (< 3 sentences, no structure needed).
"""


_MULTI_AGENT_ADDENDUM = """

=== MULTI-AGENT ORCHESTRATION ===
You have access to a `task` tool that spawns specialised sub-agents in parallel.
Each sub-agent is a clone of you with a focused task prompt and access to the
same worker data and tools (or a tool subset you specify).

FREESTYLE MODE (no workflow file in context):
  Use task() when:
  - The query requires 3+ independent data sources
  - "Full picture", "comprehensive analysis", "complete review" requests
  - Independent sub-tasks that can run in parallel
  Do NOT use task() for:
  - Simple factual questions answerable with 1-2 tools
  - Follow-up questions in an ongoing conversation
  - Queries already focused on one data source
  How to call task():
    task(description="CCR exposure lookup",
         prompt="Get the counterparty exposure, credit limits and VaR
                 from IRIS. Return structured table with net MTM, limit util %.",
         tools=["iris_*", "get_counterparty_*"])   # optional — omit for all tools
  Multiple task() calls in one response run in parallel.
  Sub-agents cannot call task() — no recursion.

WORKFLOW-GUIDED MODE (workflow file attached with agent_mode: multi in frontmatter):
  Read the YAML frontmatter from the workflow file.
  Execute agents[] in order, respecting order and depends_on fields.
  Substitute {id.result_summary} placeholders with completed agent results.
  Do not deviate from the workflow plan unless an agent fails.
  After all agents complete, synthesise results into the final answer.
"""


def _augment_prompt(prompt: str, agent_mode: str = 'single') -> str:
    """Append platform addenda to a worker system prompt."""
    result = prompt + _PYTHON_ADDENDUM + _CANVAS_ADDENDUM
    if agent_mode == 'multi':
        result += _MULTI_AGENT_ADDENDUM
    return result


SYSTEM_PROMPT = _augment_prompt(_load_prompt_from_workers())


def get_system_prompt(worker_id: str, agent_mode: str = 'single') -> str:
    """Load the system_prompt for a specific worker at call time (not cached).
    Called per-request so admin prompt updates take effect immediately.
    Appends platform addenda (Python guidance etc.) to the worker prompt.
    Falls back to the default worker prompt if not found.
    """
    try:
        data = json.loads(_WORKERS_FILE.read_text())
        for w in data.get('workers', []):
            if w.get('worker_id') == worker_id and w.get('enabled', True):
                prompt = w.get('system_prompt', '').strip()
                if prompt:
                    return _augment_prompt(prompt, agent_mode)
    except Exception:
        pass
    return _augment_prompt(_load_prompt_from_workers(), agent_mode)


SUMMARISE_PROMPT = """You are a context compressor for a financial risk intelligence session on the B-Pulse platform.

Compress the conversation history below into a precise, information-dense summary.

MANDATORY PRESERVATION — include ALL of the following if present:
- Every counterparty name with its exposure, limit, rating, and any breaches
- Every specific figure: notional amounts, MTM values, PFE, VaR, utilization percentages, dates
- Every file or workflow referenced (exact filenames, section paths)
- Every tool call and its key output: what was asked, what was returned, what source was cited
- Any decisions made, action items, or unresolved questions raised by the user
- Any errors, 404s, or data gaps the agent reported

OMIT entirely:
- Greetings, pleasantries, filler phrases
- Repeated boilerplate from tool schemas or error messages
- Intermediate reasoning steps that did not produce a final answer

FORMAT REQUIREMENTS:
- Plain prose paragraphs (no markdown headers)
- Maximum {max_tokens} tokens
- Third-person past tense ("The user asked...", "The agent retrieved...", "The analysis found...")
- Conclude with: "PENDING: [any unresolved questions or action items]"

Output only the summary text, no preamble."""
