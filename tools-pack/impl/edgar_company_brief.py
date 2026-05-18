"""
EDGAR — One-call company brief (financials + latest filing + news) — compliant port.

Ported from sajhamcpserver/sajha/tools/impl/edgar_tavily_tools.py:EdgarCompanyBriefTool.
"""
from typing import Dict, Any

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._tavily_client import tavily_search
from tools_pack_impl._edgar_helpers import (
    resolve_cik,
    fetch_best_concept,
    filter_and_sort_records,
)
from tools_pack_impl.edgar_find_filing import EdgarFindFiling


class EdgarCompanyBrief(BaseMCPTool):
    """Recent key financials + latest filing info + recent news — single call."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
            },
            'required': ['ticker'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'financials': {'type': 'object'},
                'latest_filing': {'type': 'object'},
                'recent_news': {'type': 'array'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()

        find_tool = EdgarFindFiling(config={'name': 'edgar_find_filing'})
        latest_10q = find_tool.execute({'ticker': ticker, 'form_type': '10-Q', 'limit': 1})
        filings = latest_10q.get('filings', [{}])
        latest_filing = filings[0] if filings else {}

        try:
            cik = resolve_cik(ticker)
            _, rev_records = fetch_best_concept(cik, 'revenue')
            _, eps_records = fetch_best_concept(cik, 'eps diluted')
            rev_filtered = filter_and_sort_records(rev_records, '10-Q', 2)
            eps_filtered = filter_and_sort_records(eps_records, '10-Q', 2)
            financials = {
                'revenue': [
                    {'period_end': r['end'], 'value': r['val'], 'fiscal_period': r.get('fp')}
                    for r in rev_filtered
                ],
                'eps_diluted': [
                    {'period_end': r['end'], 'value': r['val'], 'fiscal_period': r.get('fp')}
                    for r in eps_filtered
                ],
            }
        except Exception as e:
            financials = {'error': str(e)}

        try:
            news_raw = tavily_search(
                f'{ticker} latest earnings financial results news',
                include_domains=['bloomberg.com', 'reuters.com', 'finance.yahoo.com', 'cnbc.com'],
                max_results=3,
                search_depth='basic',
            )
            recent_news = [
                {
                    'title': r.get('title', ''),
                    'url': r.get('url', ''),
                    'snippet': r.get('content', '')[:150],
                }
                for r in news_raw.get('results', [])[:3]
            ]
        except Exception as e:
            recent_news = [{'error': str(e)}]

        return {
            'success': True,
            'ticker': ticker,
            'latest_filing': latest_filing,
            'financials': financials,
            'recent_news': recent_news,
        }
