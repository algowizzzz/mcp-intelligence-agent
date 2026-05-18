"""tavily_yahoo_get_history — historical price summary via Tavily search."""
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from tools_pack_impl._tavily_client import tavily_search


class TavilyYahooGetHistory(BaseMCPTool):
    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'symbol': {'type': 'string'},
                'period': {'type': 'string', 'default': '1y'},
                '_worker_context': {'type': 'object'},
            },
            'required': ['symbol'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sym = str(arguments.get('symbol', '')).strip().upper()
        period = arguments.get('period', '1y')
        if not sym:
            return {'error': 'symbol is required'}
        try:
            r = tavily_search(
                f'{sym} stock historical price chart {period}',
                include_domains=['finance.yahoo.com'],
                max_results=5,
            )
            return {'symbol': sym, 'period': period, 'results': r}
        except Exception as e:
            return {'error': str(e), 'symbol': sym}
