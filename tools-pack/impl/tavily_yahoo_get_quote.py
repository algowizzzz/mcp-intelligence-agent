"""tavily_yahoo_get_quote — fetches latest quote summary via Tavily search of finance.yahoo.com."""
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from tools_pack_impl._tavily_client import tavily_search


class TavilyYahooGetQuote(BaseMCPTool):
    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {'symbol': {'type': 'string'}, '_worker_context': {'type': 'object'}},
            'required': ['symbol'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sym = str(arguments.get('symbol', '')).strip().upper()
        if not sym:
            return {'error': 'symbol is required'}
        try:
            r = tavily_search(
                f'{sym} stock price quote summary',
                include_domains=['finance.yahoo.com'],
                max_results=3,
            )
            return {'symbol': sym, 'results': r}
        except Exception as e:
            return {'error': str(e), 'symbol': sym}
