"""
uat_framework.py
================
Shared infrastructure for RiskGPT UAT test suites.

Provides:
  - UATResult dataclass
  - UATReporter  — records results, saves JSON + Markdown after every test
  - req()        — typed HTTP helper
  - login()      — returns JWT or ''
  - run_agent()  — SSE streaming helper; returns text + tool_names called
  - timed()      — wraps a callable, returns (result, duration_ms)
"""

import os, json, time, pathlib, datetime, traceback
from dataclasses import dataclass, asdict
import httpx

BASE        = os.getenv('AGENT_BASE', 'http://localhost:8000')
TIMEOUT     = float(os.getenv('UAT_TIMEOUT', '20'))
RESULTS_DIR = pathlib.Path('UAT_RESULTS')

STATUS_SYM = {'PASS': '✓', 'FAIL': '✗', 'SKIP': '○', 'ERROR': '!'}


# ── Result dataclass ───────────────────────────────────────────────────���──────

@dataclass
class UATResult:
    id: str           # e.g. "A-01"
    module: str       # e.g. "1 - Authentication"
    scenario: str     # short description
    status: str       # PASS | FAIL | SKIP | ERROR
    detail: str = ''
    duration_ms: float = 0.0
    timestamp: str = ''


# ── Reporter ─────────────────────────────────────────────────────────────���────

class UATReporter:
    def __init__(self, phase: str):
        self.phase = phase
        self.results: list = []
        ts = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.run_id = f'{phase}_{ts}'
        RESULTS_DIR.mkdir(exist_ok=True)

    # ── Recording ─────────────────────────────────────────────────────────────

    def section(self, title: str):
        print(f'\n{"─"*70}')
        print(f'  {title}')
        print(f'{"─"*70}')

    def record(self, result: UATResult):
        if not result.timestamp:
            result.timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
        self.results.append(result)
        sym    = STATUS_SYM.get(result.status, '?')
        suffix = f'  [{result.detail[:120]}]' if result.detail and result.status != 'PASS' else ''
        print(f'  {sym} [{result.id}] {result.scenario}{suffix}')
        self._save_json()  # incremental save after every result

    def ok(self, id_, module, scenario, duration_ms=0.0):
        self.record(UATResult(id_, module, scenario, 'PASS', duration_ms=duration_ms))

    def fail(self, id_, module, scenario, detail='', duration_ms=0.0):
        self.record(UATResult(id_, module, scenario, 'FAIL', detail=detail, duration_ms=duration_ms))

    def skip(self, id_, module, scenario, reason=''):
        self.record(UATResult(id_, module, scenario, 'SKIP', detail=reason))

    def error(self, id_, module, scenario, detail='', duration_ms=0.0):
        self.record(UATResult(id_, module, scenario, 'ERROR', detail=detail, duration_ms=duration_ms))

    # ── Helpers ───────────────────────────────────────────────────────────��───

    def assert_test(self, id_, module, scenario, condition: bool, detail: str = '', duration_ms=0.0):
        """Record PASS if condition is True, FAIL otherwise."""
        if condition:
            self.ok(id_, module, scenario, duration_ms=duration_ms)
        else:
            self.fail(id_, module, scenario, detail=detail, duration_ms=duration_ms)
        return condition

    # ── Persistence ───────────────────────────────────────────────────────────

    def _summary_dict(self) -> dict:
        by_status: dict = {}
        for r in self.results:
            by_status[r.status] = by_status.get(r.status, 0) + 1
        return {
            'total': len(self.results),
            'pass':  by_status.get('PASS',  0),
            'fail':  by_status.get('FAIL',  0),
            'skip':  by_status.get('SKIP',  0),
            'error': by_status.get('ERROR', 0),
        }

    def _save_json(self):
        try:
            path = RESULTS_DIR / f'{self.run_id}.json'
            path.write_text(json.dumps({
                'run_id':       self.run_id,
                'phase':        self.phase,
                'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
                'summary':      self._summary_dict(),
                'results':      [asdict(r) for r in self.results],
            }, indent=2))
        except Exception:
            pass

    def save(self) -> tuple:
        """Write final JSON + Markdown; copy to LATEST_<phase>.* files."""
        data = {
            'run_id':       self.run_id,
            'phase':        self.phase,
            'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'summary':      self._summary_dict(),
            'results':      [asdict(r) for r in self.results],
        }
        json_txt = json.dumps(data, indent=2)
        md_txt   = self._build_markdown()

        json_path = RESULTS_DIR / f'{self.run_id}.json'
        md_path   = RESULTS_DIR / f'{self.run_id}.md'
        json_path.write_text(json_txt)
        md_path.write_text(md_txt)

        # Always overwrite LATEST so CI/CD or manual review can grab one file
        (RESULTS_DIR / f'LATEST_{self.phase}.json').write_text(json_txt)
        (RESULTS_DIR / f'LATEST_{self.phase}.md').write_text(md_txt)

        return json_path, md_path

    def _build_markdown(self) -> str:
        s   = self._summary_dict()
        pct = round(s['pass'] / s['total'] * 100) if s['total'] else 0
        now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        lines = [
            f'# UAT Results — {self.phase}',
            f'',
            f'**Run ID:** `{self.run_id}`  ',
            f'**Generated:** {now} UTC  ',
            f'',
            f'## Summary',
            f'',
            f'| Status | Count |',
            f'|--------|-------|',
            f'| ✓ PASS  | {s["pass"]}  |',
            f'| ✗ FAIL  | {s["fail"]}  |',
            f'| ○ SKIP  | {s["skip"]}  |',
            f'| ! ERROR | {s["error"]} |',
            f'| **Total** | **{s["total"]}** |',
            f'',
            f'**Pass rate: {pct}% ({s["pass"]}/{s["total"]})**',
            f'',
        ]

        # Group by module
        modules: dict = {}
        for r in self.results:
            modules.setdefault(r.module, []).append(r)

        for mod_name, mod_results in modules.items():
            mod_pass = sum(1 for r in mod_results if r.status == 'PASS')
            lines += [
                f'## {mod_name}',
                f'',
                f'| ID | Scenario | Status | Detail | ms |',
                f'|----|----------|--------|--------|----|',
            ]
            for r in mod_results:
                sym    = STATUS_SYM.get(r.status, '?')
                detail = (r.detail[:80].replace('|', '/')) if r.detail else ''
                dur    = f'{r.duration_ms:.0f}' if r.duration_ms else ''
                lines.append(
                    f'| {r.id} | {r.scenario[:55]} | {sym} {r.status} | {detail} | {dur} |'
                )
            lines += [f'', f'*{mod_pass}/{len(mod_results)} passed*', f'']

        # Failures appendix
        failures = [r for r in self.results if r.status in ('FAIL', 'ERROR')]
        if failures:
            lines += [f'## Failures & Errors', f'']
            for r in failures:
                lines += [
                    f'### [{r.id}] {r.scenario}',
                    f'- **Status:** {r.status}',
                    f'- **Detail:** `{r.detail}`',
                    f'- **Timestamp:** {r.timestamp}',
                    f'',
                ]

        return '\n'.join(lines)

    def print_final_summary(self):
        s   = self._summary_dict()
        pct = round(s['pass'] / s['total'] * 100) if s['total'] else 0
        print(f'\n{"="*70}')
        print(f'  {self.phase} — {s["pass"]}/{s["total"]} PASSED ({pct}%)')
        if s['fail']:  print(f'  FAIL:  {s["fail"]}')
        if s['error']: print(f'  ERROR: {s["error"]}')
        if s['skip']:  print(f'  SKIP:  {s["skip"]}')
        print(f'{"="*70}')


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def req(method: str, path: str, token: str = '', timeout: float = TIMEOUT, **kwargs) -> tuple:
    headers = kwargs.pop('headers', {})
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        r = httpx.request(method, f'{BASE}{path}', headers=headers, timeout=timeout, **kwargs)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {'_text': r.text[:500]}
    except Exception as e:
        return 0, {'_error': str(e)}


def login(user_id: str, password: str) -> str:
    s, body = req('POST', '/api/auth/login', json={'user_id': user_id, 'password': password})
    return body.get('token', '') if s == 200 else ''


def timed(fn) -> tuple:
    """Call fn() and return (result, duration_ms)."""
    t0 = time.monotonic()
    result = fn()
    return result, round((time.monotonic() - t0) * 1000, 1)


# ── SSE agent runner ──────────────────────────────────────────────────────────

def run_agent(query: str, worker_id: str, token: str,
              thread_id: str = '', timeout: float = 120.0) -> dict:
    """
    POST /api/agent/run and stream SSE until [DONE].

    Returns dict:
      text        str   — full concatenated text response
      tool_names  list  — names of tools called (tool_start events)
      tools       list  — [{name, input, output}] with tool_end outputs filled
      error       str|None
      thread_id   str
    """
    tools: dict   = {}   # run_id → {name, input, output}
    text_chunks   = []
    error         = None
    session_tid   = ''

    payload: dict = {'query': query, 'worker_id': worker_id}
    if thread_id:
        payload['thread_id'] = thread_id

    try:
        with httpx.stream(
            'POST', f'{BASE}/api/agent/run',
            headers={'Authorization': f'Bearer {token}'},
            json=payload,
            timeout=timeout,
        ) as r:
            if r.status_code != 200:
                return {'text': '', 'tool_names': [], 'tools': [], 'error': f'HTTP {r.status_code}', 'thread_id': ''}
            for line in r.iter_lines():
                if not line:
                    continue
                if '[DONE]' in line:
                    break
                if line.startswith('data:'):
                    try:
                        ev    = json.loads(line[5:].strip())
                        etype = ev.get('type', '')
                        if etype == 'session':
                            session_tid = ev.get('thread_id', '')
                        elif etype == 'text':
                            text_chunks.append(ev.get('text', ''))
                        elif etype == 'tool_start':
                            rid = ev.get('run_id', '')
                            tools[rid] = {
                                'name':   ev.get('name', ''),
                                'input':  ev.get('input'),
                                'output': None,
                            }
                        elif etype == 'tool_end':
                            rid = ev.get('run_id', '')
                            if rid in tools:
                                tools[rid]['output'] = ev.get('output')
                        elif etype == 'error':
                            error = ev.get('message', 'unknown error')
                        elif etype == 'replace_text':
                            # Replace accumulated text with final summary
                            text_chunks = [ev.get('text', '')]
                    except Exception:
                        pass
    except Exception as e:
        error = str(e)

    tool_list = list(tools.values())
    return {
        'text':       ''.join(text_chunks),
        'tool_names': [t['name'] for t in tool_list],
        'tools':      tool_list,
        'error':      error,
        'thread_id':  session_tid or thread_id,
    }
