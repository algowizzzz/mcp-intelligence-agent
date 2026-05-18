"""
EDGAR — Extract a specific section (MD&A, Risk Factors, etc.) from a 10-K/10-Q.

Ported from sajhamcpserver/sajha/tools/impl/edgar_tavily_tools.py:EdgarExtractSectionTool.

Compliance changes from the original:
- Extends upstream's `sajha.tools.base_mcp_tool.BaseMCPTool`.
- Shared Tavily/SEC client lives in `_tavily_client`; shared filing helpers in
  `_edgar_filing_helpers`. No PropertiesConfigurator, no Flask `g`.
"""
from typing import Dict, Any

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._tavily_client import llm_extract
from tools_pack_impl._edgar_helpers import resolve_cik
from tools_pack_impl._edgar_filing_helpers import (
    resolve_filing_url,
    extract_from_filing_url,
)


SECTION_QUERIES = {
    'MD&A': 'management discussion analysis results operations revenue',
    'Risk_Factors': 'risk factors material risks business',
    'Business': 'business overview description products services',
    'Guidance': 'outlook guidance forward looking fiscal year expectations',
    'Segment_Revenue': 'segment revenue operating income geographic breakdown',
    'Notes': 'notes to financial statements accounting policies',
    'Audit': 'auditor opinion internal controls over financial reporting',
}

EXTRACTION_PROMPTS = {
    'MD&A': 'Extract key points from this Management Discussion & Analysis. Return JSON: {"section":"MD&A","key_points":["..."],"revenue_commentary":"...","outlook":"...","risks_mentioned":["..."]}',
    'Risk_Factors': 'Extract and categorise main risk factors. Return JSON: {"section":"Risk_Factors","risk_categories":[{"category":"...","summary":"..."}]}',
    'Guidance': 'Extract forward guidance and outlook statements. Return JSON: {"section":"Guidance","fiscal_year":"...","revenue_guidance":"...","eps_guidance":"...","key_statements":["..."]}',
    'Segment_Revenue': 'Extract business segment data. Return JSON: {"section":"Segment_Revenue","segments":[{"name":"...","revenue":"...","yoy_change":"..."}]}',
    'Business': 'Summarise the business description. Return JSON: {"section":"Business","description":"...","key_products":["..."],"competitive_position":"..."}',
    'Notes': 'Extract key accounting policies and notable items. Return JSON: {"section":"Notes","key_policies":["..."],"notable_items":["..."]}',
    'Audit': 'Extract audit opinion and internal control findings. Return JSON: {"section":"Audit","opinion":"...","material_weaknesses":[],"key_findings":["..."]}',
}


class EdgarExtractSection(BaseMCPTool):
    """Extract and summarise a section from a 10-K/10-Q via Tavily + LLM."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'section': {
                    'type': 'string',
                    'description': 'Section to extract',
                    'enum': list(SECTION_QUERIES.keys()),
                },
                'period': {
                    'type': 'string',
                    'description': 'Period hint e.g. "Q1 2026", "FY2024", "latest"',
                    'default': 'latest',
                },
            },
            'required': ['ticker', 'section'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'section': {'type': 'string'},
                'ticker': {'type': 'string'},
                'key_points': {'type': 'array'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        section = arguments.get('section', 'MD&A')
        period = arguments.get('period') or 'latest'

        try:
            cik = resolve_cik(ticker)
        except Exception as e:
            return {'success': False, 'error': f'Could not resolve CIK for {ticker}: {e}'}

        filing_url, filing_date, form_type, accession_no = resolve_filing_url(cik, period)

        keywords = SECTION_QUERIES.get(section, section.lower())
        fallback_query = f'"{ticker}" {keywords} {period} site:sec.gov 10-Q 10-K'
        prompt = EXTRACTION_PROMPTS.get(
            section,
            f'Extract key information from this {section} SEC filing section for {ticker}. Return concise JSON summary.',
        )

        content, sources, data_quality, warnings = extract_from_filing_url(
            filing_url, filing_date, form_type, ticker, period, cik,
            prompt, fallback_query,
            accession_no=accession_no, section_keywords=keywords,
        )

        if data_quality == 'FAILED':
            if warnings and warnings[0] == 'No content returned from any source':
                return {
                    'success': False,
                    'error': (
                        f'No content found for {ticker} {section} {period}. '
                        f'Try edgar_find_filing first to locate the exact filing URL.'
                    ),
                }
            return {
                'success': False, 'ticker': ticker, 'period': period,
                'sources': sources, 'data_quality': 'FAILED',
                'warnings': warnings,
                'error': (
                    f'Source validation failed for {ticker} {section} {period}. '
                    f'Retrieved documents do not match the requested company or period. '
                    f'Details: ' + ' | '.join(warnings)
                ),
            }

        try:
            extracted = llm_extract(content, prompt)
        except Exception:
            extracted = {'raw_summary': content[:1000]}

        extracted.update({
            'success': True, 'ticker': ticker, 'period': period,
            'filing_date': filing_date, 'form_type': form_type,
            'sources': sources, 'data_quality': 'OK',
            '_source': filing_url or (sources[0]['url'] if sources else ''),
        })
        return extracted
