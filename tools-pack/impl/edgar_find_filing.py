"""
EDGAR — Find a specific SEC filing (10-K, 10-Q, 8-K, DEF14A) — compliant port.

Ported from sajhamcpserver/sajha/tools/impl/edgar_tavily_tools.py:EdgarFindFilingTool
of our pre-migration fork.

Compliance changes from the original:
- Extends upstream's `sajha.tools.base_mcp_tool.BaseMCPTool`.
- Tavily API key + SEC HTTP calls are routed through `_tavily_client` (no
  PropertiesConfigurator).
- No Flask `g` usage — this tool does not need worker context.
"""
from typing import Dict, Any

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._tavily_client import direct_sec_json
from tools_pack_impl._edgar_helpers import resolve_cik


class EdgarFindFiling(BaseMCPTool):
    """Find a specific SEC filing for a company via EDGAR submissions API."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'form_type': {
                    'type': 'string',
                    'description': 'Filing type',
                    'enum': ['10-K', '10-Q', '8-K', 'DEF14A'],
                    'default': '10-K',
                },
                'limit': {'type': 'integer', 'description': 'Max filings to return', 'default': 5},
            },
            'required': ['ticker'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'filings': {'type': 'array'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        form_type = arguments.get('form_type') or '10-K'
        limit = min(int(arguments.get('limit') or 5), 10)

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        submissions_url = f'https://data.sec.gov/submissions/CIK{cik}.json'
        try:
            data = direct_sec_json(submissions_url)
        except Exception as e:
            return {'success': False, 'error': f'Could not fetch EDGAR submissions: {e}'}

        recent = data.get('filings', {}).get('recent', {})
        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        accns = recent.get('accessionNumber', [])
        docs = recent.get('primaryDocument', [])

        filings = []
        for i, form in enumerate(forms):
            if form == form_type.upper():
                accn_clean = accns[i].replace('-', '')
                cik_int = str(int(cik))
                filings.append({
                    'form': form,
                    'filed': dates[i],
                    'accession': accns[i],
                    'primary_doc': docs[i],
                    'url': f'https://www.sec.gov/Archives/edgar/data/{cik_int}/{accn_clean}/{docs[i]}',
                })
            if len(filings) >= limit:
                break

        return {'success': True, 'ticker': ticker, 'form_type': form_type, 'filings': filings}
