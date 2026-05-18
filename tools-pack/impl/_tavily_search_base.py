"""Shared Tavily search base — used by web/news/research/domain search tools.

These tools all call Tavily's /search endpoint with different topic/include hints.
"""
from typing import Dict, Any, List, Optional

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._tavily_client import tavily_search


class _TavilySearchBase(BaseMCPTool):
    """Common scaffold for tavily_*_search tools."""

    _TOPIC: Optional[str] = None  # subclasses override

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'query':           {'type': 'string'},
                'max_results':     {'type': 'integer', 'default': 5},
                'include_domains': {'type': 'array', 'items': {'type': 'string'}},
                'exclude_domains': {'type': 'array', 'items': {'type': 'string'}},
                '_worker_context': {'type': 'object'},
            },
            'required': ['query'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def _do_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = str(arguments.get('query', '')).strip()
        if not query:
            return {'error': 'query is required'}
        try:
            res = tavily_search(
                query,
                include_domains=arguments.get('include_domains'),
                exclude_domains=arguments.get('exclude_domains'),
                max_results=int(arguments.get('max_results', 5)),
                topic=self._TOPIC,
            )
            return {'query': query, 'topic': self._TOPIC, 'results': res}
        except Exception as e:
            return {'error': str(e), 'query': query}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._do_search(arguments)
