import pytest
from fastapi.testclient import TestClient

def test_app_imports():
    from agent_server import app
    assert app.title == 'MCP Intelligence Agent'
