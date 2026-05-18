"""REQ-17 Story 7 — Multi-worker isolation gate test.

Hard merge gate per REQ-17_Regression_Test_Suite.md (tests G-17/G-18/G-19).
Worker A's user must NOT be able to read Worker B's files via any path:
- file tree (UI/admin path)
- direct API
- agent tool call

Run with:
    cd /Users/saadahmed/Desktop/durga_agent/mcp-intelligence-agent
    venv/bin/pytest tools-pack/tests/test_worker_isolation.py -v

Or directly:
    venv/bin/python tools-pack/tests/test_worker_isolation.py

Pre-requisites:
- Agent + SAJHA (upstream or fork) running
- Two test workers exist in workers.json: w-test-iso-a, w-test-iso-b
- Each has a different sentinel file in domain_data/
- Users iso_user_a and iso_user_b assigned to their respective workers
"""
import os
import sys
import json
import time
import httpx
from pathlib import Path

AGENT = os.getenv('AGENT_URL', 'http://localhost:8000')
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SAJHA_DATA = REPO_ROOT / 'sajhamcpserver' / 'data' / 'workers'

SUPER_ADMIN = ('risk_agent', 'RiskAgent2025!')
WORKER_A_ID = 'w-test-iso-a'
WORKER_B_ID = 'w-test-iso-b'
SENTINEL_A = 'sentinel_worker_a_secret.txt'
SENTINEL_B = 'sentinel_worker_b_secret.txt'


def _login(user_id: str, password: str) -> str:
    r = httpx.post(f'{AGENT}/api/auth/login',
                   json={'user_id': user_id, 'password': password},
                   timeout=10.0, trust_env=False)
    r.raise_for_status()
    return r.json()['token']


def _setup() -> bool:
    """Ensure two test workers + two users exist, with sentinel files."""
    super_jwt = _login(*SUPER_ADMIN)
    h = {'Authorization': f'Bearer {super_jwt}'}

    # Create workers if missing
    workers = httpx.get(f'{AGENT}/api/super/workers', headers=h, timeout=10.0, trust_env=False).json()
    have = {w.get('worker_id') for w in workers} if isinstance(workers, list) else set()
    for wid, name in [(WORKER_A_ID, 'Isolation Test A'), (WORKER_B_ID, 'Isolation Test B')]:
        if wid not in have:
            httpx.post(f'{AGENT}/api/super/workers', headers=h, timeout=15.0, trust_env=False,
                       json={'worker_id': wid, 'name': name, 'system_prompt': 'test', 'enabled_tools': ['*']})

    # Create sentinel files on disk
    for wid, fname, body in [(WORKER_A_ID, SENTINEL_A, 'WORKER_A_SECRET'),
                              (WORKER_B_ID, SENTINEL_B, 'WORKER_B_SECRET')]:
        dd = SAJHA_DATA / wid / 'domain_data'
        dd.mkdir(parents=True, exist_ok=True)
        (dd / fname).write_text(body)

    # Create users
    for uid, wid in [('iso_user_a', WORKER_A_ID), ('iso_user_b', WORKER_B_ID)]:
        try:
            httpx.post(f'{AGENT}/api/super/users', headers=h, timeout=10.0, trust_env=False,
                       json={'user_id': uid, 'role': 'user', 'worker_id': wid,
                             'display_name': uid, 'password': 'IsoTest123!'})
        except Exception:
            pass
        httpx.post(f'{AGENT}/api/super/users/{uid}/reset-password', headers=h,
                   timeout=10.0, trust_env=False, json={'new_password': 'IsoTest123!'})

    return True


def _check_tree_isolation(user_jwt: str, expected_dir_suffix: str) -> tuple:
    """G-18 — tree listing must be scoped to the user's own worker only."""
    r = httpx.get(f'{AGENT}/api/fs/domain_data/tree', headers={'Authorization': f'Bearer {user_jwt}'},
                  timeout=10.0, trust_env=False)
    r.raise_for_status()
    data = r.json()
    root = data.get('root', '')
    if not root.endswith(expected_dir_suffix):
        return False, f'tree root {root} does not end with {expected_dir_suffix}'
    return True, root


def _check_read_isolation(user_jwt: str, target_path: str) -> tuple:
    """G-17 — reading another worker's file must fail."""
    r = httpx.get(f'{AGENT}/api/fs/domain_data/file',
                  params={'path': target_path},
                  headers={'Authorization': f'Bearer {user_jwt}'},
                  timeout=10.0, trust_env=False)
    if r.status_code in (400, 403, 404):
        return True, f'cross-worker read blocked ({r.status_code})'
    return False, f'expected 4xx, got {r.status_code}: {r.text[:120]}'


def main() -> int:
    print('REQ-17 Story 7: Multi-worker isolation gate')
    print('=' * 60)
    try:
        _setup()
    except Exception as e:
        print(f'SETUP FAILED: {e}')
        return 1

    passes = fails = 0
    def check(name, cond, msg):
        nonlocal passes, fails
        mark = 'PASS' if cond else 'FAIL'
        print(f'  [{mark}] {name}: {msg}')
        if cond: passes += 1
        else:    fails += 1

    # Login as iso_user_a and iso_user_b
    try:
        a_jwt = _login('iso_user_a', 'IsoTest123!')
        b_jwt = _login('iso_user_b', 'IsoTest123!')
    except Exception as e:
        print(f'  [FAIL] login: {e}')
        return 1

    # G-18a — A's tree scoped to A
    ok, msg = _check_tree_isolation(a_jwt, f'{WORKER_A_ID}/domain_data')
    check('G-18a (A tree → A scope)', ok, msg)

    # G-18b — B's tree scoped to B
    ok, msg = _check_tree_isolation(b_jwt, f'{WORKER_B_ID}/domain_data')
    check('G-18b (B tree → B scope)', ok, msg)

    # G-17a — A tries to read B's sentinel via traversal
    ok, msg = _check_read_isolation(a_jwt, f'../../../{WORKER_B_ID}/domain_data/{SENTINEL_B}')
    check('G-17a (A → B via traversal blocked)', ok, msg)

    # G-17b — A tries to read B's sentinel directly via filename only (worker dir auto-resolves to A's)
    # If the API resolves the filename against A's worker dir, it should 404 (not found)
    r = httpx.get(f'{AGENT}/api/fs/domain_data/file', params={'path': SENTINEL_B},
                  headers={'Authorization': f'Bearer {a_jwt}'}, timeout=10.0, trust_env=False)
    check('G-17b (A read B-sentinel-name → 404 in A)', r.status_code == 404,
          f'HTTP {r.status_code} body={r.text[:120]}')

    # G-19 — A's tree must not contain B's sentinel filename
    r = httpx.get(f'{AGENT}/api/fs/domain_data/tree', headers={'Authorization': f'Bearer {a_jwt}'},
                  timeout=10.0, trust_env=False)
    body = r.text
    check('G-19 (B sentinel name not in A tree)', SENTINEL_B not in body,
          'absent' if SENTINEL_B not in body else f'LEAKED: {SENTINEL_B} found in A tree')

    print()
    print(f'TOTAL: {passes} PASS / {fails} FAIL')
    return 0 if fails == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
