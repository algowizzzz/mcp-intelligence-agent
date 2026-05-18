"""
EDGAR — Earnings brief (metrics + commentary + guidance + news) — compliant port.

Ported from sajhamcpserver/sajha/tools/impl/edgar_tavily_tools.py:EdgarEarningsBriefTool.
"""
from typing import Dict, Any

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._tavily_client import tavily_search, llm_extract
from tools_pack_impl._edgar_helpers import resolve_cik
from tools_pack_impl._edgar_filing_helpers import (
    resolve_filing_url,
    extract_from_filing_url,
)


class EdgarEarningsBrief(BaseMCPTool):
    """One-call earnings brief: key metrics + management commentary + guidance + news."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'period': {
                    'type': 'string',
                    'description': 'Quarter/period e.g. "Q1 2026", "Q3 FY2025", "latest"',
                },
            },
            'required': ['ticker', 'period'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'period': {'type': 'string'},
                'key_metrics': {'type': 'object'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        period = arguments.get('period', 'latest')

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        filing_url, filing_date, form_type, accession_no = resolve_filing_url(cik, period)

        fallback_query = f'{ticker} earnings {period} revenue EPS results 10-Q 8-K SEC filing'
        prompt = (
            f'Extract a complete earnings brief for {ticker} {period}. Return JSON: '
            f'{{"ticker":"{ticker}","period":"{period}",'
            f'"key_metrics":{{"revenue":"...","eps":"...","net_income":"...","gross_margin":"..."}},'
            f'"yoy_change":{{"revenue":"...","eps":"..."}},'
            f'"management_commentary":"...","guidance":"...","analyst_reaction":"..."}}'
        )

        sec_text, sec_sources, data_quality, warnings = extract_from_filing_url(
            filing_url, filing_date, form_type, ticker, period, cik,
            prompt, fallback_query,
            accession_no=accession_no,
            section_keywords='earnings revenue net income EPS management commentary guidance',
        )

        if data_quality == 'FAILED':
            return {
                'success': False, 'ticker': ticker, 'period': period,
                'sources': sec_sources, 'data_quality': 'FAILED',
                'warnings': warnings,
                'error': (
                    f'Source validation failed for {ticker} earnings {period}. '
                    f'Retrieved documents do not match the requested company or period. '
                    f'Details: ' + ' | '.join(warnings)
                ),
            }

        news_query = f'{ticker} earnings {period} results analyst reaction guidance'
        news_raw = tavily_search(
            news_query,
            include_domains=['bloomberg.com', 'reuters.com', 'finance.yahoo.com', 'cnbc.com'],
            max_results=3,
        )
        news_text = news_raw.get('answer', '') + '\n\n' + '\n\n'.join(
            r.get('content', '') for r in news_raw.get('results', [])[:3]
        )
        news_sources = [
            {'title': r.get('title', ''), 'url': r.get('url', '')}
            for r in news_raw.get('results', [])[:2]
        ]

        combined = f'SEC FILING DATA:\n{sec_text}\n\nNEWS & ANALYST COMMENTARY:\n{news_text}'
        try:
            result = llm_extract(combined, prompt)
        except Exception:
            result = {'raw_summary': sec_text[:800]}

        result['success'] = True
        result['data_quality'] = 'OK'
        result['sources'] = sec_sources + news_sources
        if filing_url:
            result['_source'] = filing_url
        return result
