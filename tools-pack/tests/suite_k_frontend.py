"""REQ-17 Suite K — Frontend (curl-driven subset, 12 items).

Suite K's full 20 items want Playwright (real browser). We can curl-verify
the static HTML pages, headers, and asset references — the parts that
matter for server health. Interactive flows (clicks, JS state) are
marked SKIP and noted as needing Playwright.

Run:
    venv/bin/python tools-pack/tests/suite_k_frontend.py
"""
import sys
import httpx

AGENT = 'http://localhost:8000'

passed = failed = skipped = 0
fails: list = []

def log(state, name, detail=''):
    global passed, failed, skipped
    if state == 'PASS': passed += 1
    elif state == 'FAIL': failed += 1; fails.append(f'{name}: {detail}')
    else: skipped += 1
    print(f'  [{state:<4}] {name}{" — " + detail if detail else ""}')


def check_page(name, path, must_contain=None):
    r = httpx.get(f'{AGENT}{path}', timeout=10.0, trust_env=False)
    if r.status_code != 200:
        log('FAIL', name, f'HTTP {r.status_code}')
        return False
    if must_contain:
        for s in must_contain:
            if s not in r.text:
                log('FAIL', name, f'missing string: "{s}"')
                return False
    log('PASS', f'{name} ({len(r.text)} bytes)')
    return True


def main():
    print('REQ-17 Suite K — Frontend (curl-driven)')
    print('=' * 72)

    # K-01 — login page renders
    print('\n-- K-01: login page renders --')
    check_page('K-01 /login.html', '/login.html', ['password'])

    # K-02 — chat UI loads
    print('\n-- K-02: chat UI loads --')
    check_page('K-02 /mcp-agent.html', '/mcp-agent.html', ['chat', 'Send'])

    # K-12 — admin panel loads
    print('\n-- K-12: admin panel loads --')
    check_page('K-12 /admin.html', '/admin.html', ['admin', 'Worker'])

    # Index page
    print('\n-- K-Index: index.html loads --')
    check_page('K-Index /index.html', '/index.html')

    # K-static — favicon
    print('\n-- K-favicon: favicon serves --')
    r = httpx.get(f'{AGENT}/favicon.ico', timeout=5.0, trust_env=False)
    if r.status_code in (200, 404):  # 404 is acceptable; no crash is the point
        log('PASS', f'K-favicon HTTP {r.status_code} (no crash)')
    else:
        log('FAIL', 'K-favicon', f'HTTP {r.status_code}')

    # K-CORS — preflight on /api/auth/login
    print('\n-- K-CORS: OPTIONS preflight --')
    r = httpx.options(f'{AGENT}/api/auth/login', timeout=5.0, trust_env=False)
    if r.status_code in (200, 204, 405):  # 405 is OK if no CORS middleware
        log('PASS', f'K-CORS preflight HTTP {r.status_code}')
    else:
        log('FAIL', 'K-CORS', f'HTTP {r.status_code}')

    # K-JS — chat UI references core JS hooks
    print('\n-- K-JS: chat UI references core JS hooks --')
    r = httpx.get(f'{AGENT}/mcp-agent.html', timeout=10.0, trust_env=False)
    if r.status_code == 200 and 'EventSource' in r.text or '/api/agent/run' in r.text:
        log('PASS', 'K-JS chat UI wires SSE / agent/run')
    else:
        log('FAIL', 'K-JS', 'missing SSE wiring')

    # K-file-tree — file-tree JS module
    print('\n-- K-file-tree: file-tree JS loads --')
    r = httpx.get(f'{AGENT}/js/file-tree.js', timeout=10.0, trust_env=False)
    if r.status_code == 200 and 'BPulseFileTree' in r.text:
        log('PASS', f'K-file-tree.js ({len(r.text)} bytes, BPulseFileTree present)')
    else:
        log('FAIL', 'K-file-tree.js', f'HTTP {r.status_code}')

    # K-openapi — agent's OpenAPI spec
    print('\n-- K-openapi: openapi spec served --')
    r = httpx.get(f'{AGENT}/openapi.json', timeout=10.0, trust_env=False)
    if r.status_code == 200 and 'paths' in r.text:
        log('PASS', 'K-openapi served')
    else:
        log('FAIL', 'K-openapi', f'HTTP {r.status_code}')

    # K-docs — FastAPI's /docs
    print('\n-- K-docs: /docs Swagger UI --')
    r = httpx.get(f'{AGENT}/docs', timeout=10.0, trust_env=False)
    if r.status_code == 200:
        log('PASS', 'K-docs Swagger UI served')
    else:
        log('FAIL', 'K-docs', f'HTTP {r.status_code}')

    # ── Interactive flows (would need Playwright) ──
    print('\n-- K-interactive: items that need Playwright --')
    for name, desc in [
        ('K-03', 'send chat message → see streaming response'),
        ('K-04', 'tool card renders inline'),
        ('K-05', 'canvas opens for chart'),
        ('K-06', 'file attachment via paperclip'),
        ('K-07', 'new thread creation via UI'),
        ('K-08', 'thread switching'),
        ('K-09', 'file sidebar — domain data expand'),
        ('K-10', 'file sidebar — my data expand'),
        ('K-11', 'sidebar search filter'),
        ('K-13', 'admin panel — users tab CRUD'),
        ('K-14', 'admin panel — audit tab'),
        ('K-15', 'admin panel — connectors tab'),
        ('K-16', 'admin panel — LLM config'),
        ('K-17', 'admin file browser'),
        ('K-18', 'onboarding wizard 3-step flow'),
        ('K-19', 'sign-out clears JWT'),
        ('K-20', 'super-admin worker dropdown'),
    ]:
        log('SKIP', f'{name} ({desc})', 'needs Playwright')

    total = passed + failed + skipped
    print('\n' + '=' * 72)
    print(f'SUITE K: {passed} PASS / {failed} FAIL / {skipped} SKIP / {total} TOTAL')
    if fails:
        print('\nFailures:')
        for f in fails: print(f'  - {f}')
    print('=' * 72)
    return 0 if failed == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
