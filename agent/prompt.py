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
        # Prefer the default worker, then fall back to the first enabled one
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


SYSTEM_PROMPT = _load_prompt_from_workers()

SUMMARISE_PROMPT = '''You are a context compressor for a financial risk intelligence session.
Summarise the messages below in 500 words or fewer. Preserve exactly:
- Every counterparty name and its exposure / limit / credit rating figures
- Every specific number (notional, MTM, PFE, VaR, utilisation %)
- Every tool that was called, what it returned, and the source cited in _source
- Any limit breaches, credit alerts, or action items raised
Omit greetings, repeated boilerplate, and tool schema details.
Output only the summary text, no preamble.
'''
