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


def get_system_prompt(worker_id: str) -> str:
    """Load the system_prompt for a specific worker at call time (not cached).
    Called per-request so admin prompt updates take effect immediately.
    Falls back to the default worker prompt if not found.
    """
    try:
        data = json.loads(_WORKERS_FILE.read_text())
        for w in data.get('workers', []):
            if w.get('worker_id') == worker_id and w.get('enabled', True):
                prompt = w.get('system_prompt', '').strip()
                if prompt:
                    return prompt
    except Exception:
        pass
    return _load_prompt_from_workers()


SYSTEM_PROMPT = _load_prompt_from_workers()

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
