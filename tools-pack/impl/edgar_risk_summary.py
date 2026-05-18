"""
EDGAR — Risk factor extraction and categorisation from a 10-K — compliant port.

Ported from sajhamcpserver/sajha/tools/impl/edgar_tavily_tools.py:EdgarRiskSummaryTool.
"""
from typing import Dict, Any

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._tavily_client import llm_extract
from tools_pack_impl._edgar_helpers import resolve_cik
from tools_pack_impl._edgar_filing_helpers import (
    resolve_filing_url,
    extract_from_filing_url,
)


class EdgarRiskSummary(BaseMCPTool):
    """Extract and categorise risk factors from a company's 10-K."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'fiscal_year': {
                    'type': 'string',
                    'description': 'Fiscal year e.g. "FY2024", "2024"',
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
                'risk_categories': {'type': 'array'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        fiscal_year = arguments.get('fiscal_year') or 'latest'

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        fy_period = fiscal_year if fiscal_year.upper().startswith('FY') else f'FY{fiscal_year}'

        filing_url, filing_date, form_type, accession_no = resolve_filing_url(cik, fy_period)

        fallback_query = (
            f'{ticker} risk factors material risks {fiscal_year} 10-K annual report SEC'
        )
        prompt = (
            f'Extract and categorise risk factors for {ticker} from this 10-K content. Return JSON: '
            f'{{"ticker":"{ticker}","fiscal_year":"{fiscal_year}",'
            f'"risk_categories":[{{"category":"macro|competitive|regulatory|operational|financial|technology",'
            f'"risks":[{{"title":"...","summary":"..."}}]}}]}}'
        )

        content, sources, data_quality, warnings = extract_from_filing_url(
            filing_url, filing_date, form_type, ticker, fy_period, cik,
            prompt, fallback_query,
            accession_no=accession_no,
            section_keywords='risk factors material risks regulatory competitive operational financial',
        )

        if data_quality == 'FAILED':
            return {
                'success': False, 'ticker': ticker, 'fiscal_year': fiscal_year,
                'sources': sources, 'data_quality': 'FAILED',
                'warnings': warnings,
                'error': (
                    f'Source validation failed for {ticker} risk summary {fiscal_year}. '
                    f'Details: ' + ' | '.join(warnings)
                ),
            }

        try:
            result = llm_extract(content, prompt)
        except Exception as e:
            result = {'risk_categories': [], 'note': str(e)}

        result['success'] = True
        result['data_quality'] = 'OK'
        result['sources'] = sources
        if filing_url:
            result['_source'] = filing_url
        return result
