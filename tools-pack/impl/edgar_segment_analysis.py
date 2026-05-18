"""
EDGAR — Revenue and operating income by business segment — compliant port.

Ported from sajhamcpserver/sajha/tools/impl/edgar_tavily_tools.py:EdgarSegmentAnalysisTool.
"""
from typing import Dict, Any

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._tavily_client import llm_extract
from tools_pack_impl._edgar_helpers import resolve_cik
from tools_pack_impl._edgar_filing_helpers import (
    resolve_filing_url,
    extract_from_filing_url,
)


class EdgarSegmentAnalysis(BaseMCPTool):
    """Extract business segment revenue and operating income from a 10-Q/10-K."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'period': {
                    'type': 'string',
                    'description': 'Period e.g. "latest", "Q1 2026"',
                    'default': 'latest',
                },
            },
            'required': ['ticker'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'segments': {'type': 'array'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        period = arguments.get('period') or 'latest'

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        filing_url, filing_date, form_type, accession_no = resolve_filing_url(cik, period)

        fallback_query = (
            f'{ticker} revenue by segment product category operating income {period} 10-Q 10-K SEC'
        )
        prompt = (
            f'Extract business segment data for {ticker} {period}. Return JSON: '
            f'{{"ticker":"{ticker}","period":"{period}","segments":'
            f'[{{"name":"...","revenue":"...","operating_income":"...","yoy_change":"..."}}]}}'
        )

        content, sources, data_quality, warnings = extract_from_filing_url(
            filing_url, filing_date, form_type, ticker, period, cik,
            prompt, fallback_query,
            accession_no=accession_no,
            section_keywords='segment revenue operating income business unit geographic breakdown',
        )

        if data_quality == 'FAILED':
            return {
                'success': False, 'ticker': ticker, 'period': period,
                'sources': sources, 'data_quality': 'FAILED',
                'warnings': warnings,
                'error': (
                    f'Source validation failed for {ticker} segment analysis {period}. '
                    f'Details: ' + ' | '.join(warnings)
                ),
            }

        try:
            result = llm_extract(content, prompt)
        except Exception as e:
            result = {'segments': [], 'note': str(e)}

        result['success'] = True
        result['data_quality'] = 'OK'
        result['sources'] = sources
        if filing_url:
            result['_source'] = filing_url
        return result
