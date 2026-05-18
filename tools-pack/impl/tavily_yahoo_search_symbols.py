"""tavily_yahoo_search_symbols — symbol lookup via Tavily search."""
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from tools_pack_impl._tavily_client import tavily_search


class TavilyYahooSearchSymbols(BaseMCPTool):
    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {'query': {'type': 'string'}, '_worker_context': {'type': 'object'}},
            'required': ['query'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        q = str(arguments.get('query', '')).strip()
        if not q:
            return {'error': 'query is required'}
        try:
            r = tavily_search(
                f'stock ticker symbol for {q} on Yahoo Finance',
                include_domains=['finance.yahoo.com'],
                max_results=5,
            )
            return {'query': q, 'results': r}
        except Exception as e:
            return {'error': str(e), 'query': q}
