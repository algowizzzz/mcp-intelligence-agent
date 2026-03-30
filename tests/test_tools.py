import pytest
import asyncio
from agent.tools import (
    get_counterparty_exposure, get_trade_inventory, get_credit_limits,
    get_historical_exposure, get_var_contribution, web_search, AGENT_TOOLS
)

def test_agent_tools_count():
    assert len(AGENT_TOOLS) == 6

def test_tool_names():
    names = {t.name for t in AGENT_TOOLS}
    expected = {'get_counterparty_exposure', 'get_trade_inventory', 'get_credit_limits',
                'get_historical_exposure', 'get_var_contribution', 'web_search'}
    assert names == expected
