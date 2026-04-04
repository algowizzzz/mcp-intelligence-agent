"""
conftest.py — pytest fixture wiring for test_multiworker_platform.py

The test module was originally designed as a standalone runner where
test_authentication() returns (super_tok, admin_tok, user_tok) and passes
them to each subsequent function.  Pytest cannot wire function return values
as fixtures.  This conftest bridges the gap by creating session-scoped
fixtures that perform the same logins once and share the tokens.
"""
import pytest
import httpx
import os

BASE = os.getenv('AGENT_BASE', 'http://localhost:8000')
TIMEOUT = 15.0

SUPER_ADMIN_CREDS = ('risk_agent', 'RiskAgent2025!')
ADMIN_CREDS       = ('admin',      'Admin2025!')
USER_CREDS        = ('test_user',  'TestUser2025!')


def _login(user_id: str, password: str) -> str:
    try:
        r = httpx.post(f'{BASE}/api/auth/login',
                       json={'user_id': user_id, 'password': password},
                       timeout=TIMEOUT)
        return r.json().get('token', '') if r.status_code == 200 else ''
    except Exception:
        return ''


@pytest.fixture(scope='session')
def super_tok():
    tok = _login(*SUPER_ADMIN_CREDS)
    if not tok:
        pytest.skip('super_admin login failed — server may not be running')
    return tok


@pytest.fixture(scope='session')
def admin_tok():
    return _login(*ADMIN_CREDS)


@pytest.fixture(scope='session')
def user_tok():
    return _login(*USER_CREDS)
