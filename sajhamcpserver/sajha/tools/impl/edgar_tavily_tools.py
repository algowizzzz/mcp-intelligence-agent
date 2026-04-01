"""
EDGAR Tavily-based tools — T-01, T-02, T-06, T-07, T-08, T-10
Qualitative section extraction and filing discovery via Tavily.
"""
import json
from typing import Dict, Any
from sajha.tools.base_mcp_tool import BaseMCPTool
from .edgar_tavily_client import tavily_extract, tavily_search, llm_extract, fix_tavily_json
from .edgar_cik_resolver import resolve_cik


class EdgarFindFilingTool(BaseMCPTool):
    """T-01: Find a specific SEC filing using EDGAR submissions API via Tavily."""

    def __init__(self, config: Dict = None):
        default_config = {'name': 'edgar_find_filing', 'description': 'Find a specific SEC filing (10-K, 10-Q, 8-K) for a company. Returns filing URL, accession number, and filing date. Use this first when you need to access a specific filing document.', 'version': '1.0.0', 'enabled': True}
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'form_type': {'type': 'string', 'description': 'Filing type', 'enum': ['10-K', '10-Q', '8-K', 'DEF14A'], 'default': '10-K'},
                'limit': {'type': 'integer', 'description': 'Max filings to return (default 5)', 'default': 5},
            },
            'required': ['ticker']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'ticker': {'type': 'string'}, 'filings': {'type': 'array'}}}

    SEDAR_FILERS = {'TD', 'RY', 'BMO', 'BNS', 'CM', 'NA', 'CWB', 'EQB',
                    'SU', 'CNQ', 'ABX', 'WPM', 'MFC', 'SLF', 'GWO', 'POW'}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        form_type = arguments.get('form_type') or '10-K'
        limit = min(int(arguments.get('limit') or 5), 10)

        if ticker in self.SEDAR_FILERS:
            return {'success': False, 'filings': [],
                    'error': f'{ticker} files with SEDAR (Canadian regulator), not SEC. Use edgar_extract_section or edgar_earnings_brief which support SEDAR/IR searches.',
                    'suggestion': 'edgar_extract_section'}

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        submissions_url = f'https://data.sec.gov/submissions/CIK{cik}.json'
        results = tavily_extract([submissions_url])
        if not results:
            return {'success': False, 'error': 'Could not fetch EDGAR submissions'}

        raw = fix_tavily_json(results[0].get('raw_content', ''))
        try:
            data = json.loads(raw)
        except Exception:
            return {'success': False, 'error': 'Failed to parse EDGAR submissions response'}

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


class EdgarExtractSectionTool(BaseMCPTool):
    """T-02: Extract a specific section from a 10-K or 10-Q using Tavily + LLM."""

    def __init__(self, config: Dict = None):
        default_config = {'name': 'edgar_extract_section', 'description': 'Extract and summarise a specific section (MD&A, Risk Factors, Business, Guidance, Segment Revenue) from a 10-K or 10-Q filing. Returns structured text analysis. Use for qualitative analyst queries about management commentary, risks, or strategy.', 'version': '1.0.0', 'enabled': True}
        if config: default_config.update(config)
        super().__init__(default_config)

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

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'section': {'type': 'string', 'description': 'Section to extract', 'enum': ['MD&A', 'Risk_Factors', 'Business', 'Guidance', 'Segment_Revenue', 'Notes', 'Audit']},
                'period': {'type': 'string', 'description': 'Period hint e.g. "Q1 2026", "FY2024", "latest" (optional)', 'default': 'latest'},
            },
            'required': ['ticker', 'section']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'section': {'type': 'string'}, 'ticker': {'type': 'string'}, 'key_points': {'type': 'array'}}}

    # Canadian bank tickers and their company names for better search queries
    CANADIAN_BANKS = {
        'TD': 'TD Bank Toronto-Dominion', 'RY': 'RBC Royal Bank Canada',
        'BMO': 'BMO Bank of Montreal', 'BNS': 'Scotiabank Bank of Nova Scotia',
        'CM': 'CIBC Canadian Imperial Bank', 'NA': 'National Bank Canada',
        'CWB': 'Canadian Western Bank', 'EQB': 'EQ Bank Equitable',
    }
    # Other non-US filers by ticker prefix patterns
    CANADIAN_TICKERS = set(CANADIAN_BANKS.keys())

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        section = arguments.get('section', 'MD&A')
        period = arguments.get('period') or 'latest'

        keywords = self.SECTION_QUERIES.get(section, section.lower())
        is_canadian = ticker in self.CANADIAN_TICKERS

        if is_canadian:
            # Canadian banks file with SEDAR/SEDAR+, not SEC.
            # Search their IR pages and sedarplus directly.
            company_name = self.CANADIAN_BANKS.get(ticker, ticker)
            query = f'{company_name} {keywords} {period} annual report quarterly results management discussion'
            domains = ['sedarplus.ca', 'sedar.com', 'td.com', 'rbc.com', 'bmo.com',
                       'scotiabank.com', 'cibc.com', 'nbc.ca', 'sec.gov']
            raw = tavily_search(query, include_domains=domains, max_results=5, include_answer=True)
        else:
            query = f'{ticker} {keywords} {period} 10-Q OR 10-K SEC annual quarterly report'
            raw = tavily_search(query, include_domains=['sec.gov'], max_results=3, include_answer=True)

        combined = (raw.get('answer', '') + '\n\n' + '\n\n'.join(r.get('content', '') for r in raw.get('results', [])[:3]))
        sources = [{'title': r.get('title', ''), 'url': r.get('url', '')} for r in raw.get('results', [])[:5]]

        if not combined.strip():
            return {'success': False, 'error': f'No content retrieved for {ticker} {section}'}

        prompt = self.EXTRACTION_PROMPTS.get(section, f'Extract key information from this {section} section for {ticker}. Return concise JSON summary.')
        try:
            extracted = llm_extract(combined, prompt)
        except Exception as e:
            extracted = {'raw_summary': combined[:1000]}

        extracted.update({'success': True, 'ticker': ticker, 'period': period,
                          'sources': sources, 'filing_regime': 'SEDAR' if is_canadian else 'SEC'})
        return extracted


class EdgarEarningsBriefTool(BaseMCPTool):
    """T-06: Complete earnings brief — metrics + commentary + guidance + analyst reaction."""

    def __init__(self, config: Dict = None):
        default_config = {'name': 'edgar_earnings_brief', 'description': 'Get a complete earnings brief for a company and quarter: key metrics, management commentary, guidance, and analyst reaction. Replaces a 5-tool chain for earnings queries like "How did Apple do in Q1 2026?"', 'version': '1.0.0', 'enabled': True}
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'period': {'type': 'string', 'description': 'Quarter/period e.g. "Q1 2026", "Q3 FY2025", "latest"'},
            },
            'required': ['ticker', 'period']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'ticker': {'type': 'string'}, 'period': {'type': 'string'}, 'key_metrics': {'type': 'object'}}}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        period = arguments.get('period', 'latest')

        # Search SEC for filing metrics
        sec_query = f'{ticker} earnings {period} revenue EPS results 10-Q 8-K SEC filing'
        sec_raw = tavily_search(sec_query, include_domains=['sec.gov'], max_results=3)
        sec_text = (sec_raw.get('answer', '') + '\n\n' + '\n\n'.join(r.get('content', '') for r in sec_raw.get('results', [])[:3]))

        # Search news for analyst reaction
        news_query = f'{ticker} earnings {period} results analyst reaction guidance'
        news_raw = tavily_search(news_query, include_domains=['bloomberg.com', 'reuters.com', 'finance.yahoo.com', 'cnbc.com'], max_results=3)
        news_text = (news_raw.get('answer', '') + '\n\n' + '\n\n'.join(r.get('content', '') for r in news_raw.get('results', [])[:3]))

        combined = f'SEC FILING DATA:\n{sec_text}\n\nNEWS & ANALYST COMMENTARY:\n{news_text}'
        prompt = f'Extract a complete earnings brief for {ticker} {period}. Return JSON: {{"ticker":"{ticker}","period":"{period}","key_metrics":{{"revenue":"...","eps":"...","net_income":"...","gross_margin":"..."}},"yoy_change":{{"revenue":"...","eps":"..."}},"management_commentary":"...","guidance":"...","analyst_reaction":"..."}}'
        try:
            result = llm_extract(combined, prompt)
        except Exception as e:
            result = {'raw_summary': sec_text[:800]}

        result['success'] = True
        result['sources'] = [{'title': r.get('title', ''), 'url': r.get('url', '')} for r in sec_raw.get('results', [])[:2] + news_raw.get('results', [])[:2]]
        return result


class EdgarSegmentAnalysisTool(BaseMCPTool):
    """T-07: Revenue and operating income by business segment."""

    def __init__(self, config: Dict = None):
        default_config = {'name': 'edgar_segment_analysis', 'description': 'Get revenue breakdown by business segment (e.g. Apple: iPhone/Services/Mac/iPad/Wearables, or Microsoft: Cloud/Productivity/Gaming). Segment data is extracted from 10-Q/10-K filings.', 'version': '1.0.0', 'enabled': True}
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'period': {'type': 'string', 'description': 'Period e.g. "latest", "Q1 2026"', 'default': 'latest'},
            },
            'required': ['ticker']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'ticker': {'type': 'string'}, 'segments': {'type': 'array'}}}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        period = arguments.get('period') or 'latest'

        query = f'{ticker} revenue by segment product category operating income {period} 10-Q 10-K SEC'
        raw = tavily_search(query, include_domains=['sec.gov'], max_results=3, include_answer=True)
        combined = raw.get('answer', '') + '\n\n' + '\n\n'.join(r.get('content', '') for r in raw.get('results', [])[:3])
        sources = [{'title': r.get('title', ''), 'url': r.get('url', '')} for r in raw.get('results', [])[:3]]

        prompt = f'Extract business segment data for {ticker} {period}. Return JSON: {{"ticker":"{ticker}","period":"{period}","segments":[{{"name":"...","revenue":"...","operating_income":"...","yoy_change":"..."}}]}}'
        try:
            result = llm_extract(combined, prompt)
        except Exception as e:
            result = {'segments': [], 'note': str(e)}

        result['success'] = True
        result['sources'] = sources
        return result


class EdgarRiskSummaryTool(BaseMCPTool):
    """T-08: Extract and categorise risk factors from 10-K."""

    def __init__(self, config: Dict = None):
        default_config = {'name': 'edgar_risk_summary', 'description': 'Extract and categorise risk factors from a company 10-K annual report. Can compare risks between two years to identify new or removed risks.', 'version': '1.0.0', 'enabled': True}
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'fiscal_year': {'type': 'string', 'description': 'Fiscal year e.g. "FY2024", "2024"', 'default': 'latest'},
            },
            'required': ['ticker']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'ticker': {'type': 'string'}, 'risk_categories': {'type': 'array'}}}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        fiscal_year = arguments.get('fiscal_year') or 'latest'

        query = f'{ticker} risk factors material risks {fiscal_year} 10-K annual report SEC'
        raw = tavily_search(query, include_domains=['sec.gov'], max_results=3, include_answer=True)
        combined = raw.get('answer', '') + '\n\n' + '\n\n'.join(r.get('content', '') for r in raw.get('results', [])[:3])
        sources = [{'title': r.get('title', ''), 'url': r.get('url', '')} for r in raw.get('results', [])[:3]]

        prompt = f'Extract and categorise risk factors for {ticker} from this 10-K content. Return JSON: {{"ticker":"{ticker}","fiscal_year":"{fiscal_year}","risk_categories":[{{"category":"macro|competitive|regulatory|operational|financial|technology","risks":[{{"title":"...","summary":"..."}}]}}]}}'
        try:
            result = llm_extract(combined, prompt)
        except Exception as e:
            result = {'risk_categories': [], 'note': str(e)}

        result['success'] = True
        result['sources'] = sources
        return result


class EdgarCompanyBriefTool(BaseMCPTool):
    """T-10: One-call company snapshot — financials + latest filing + recent news."""

    def __init__(self, config: Dict = None):
        default_config = {'name': 'edgar_company_brief', 'description': 'Get a comprehensive company brief: recent key financials (revenue, EPS, margins), latest filing info, and recent news. Use as the starting point for any new company analysis before drilling into specifics.', 'version': '1.0.0', 'enabled': True}
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
            },
            'required': ['ticker']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'ticker': {'type': 'string'}, 'financials': {'type': 'object'}, 'latest_filing': {'type': 'object'}, 'recent_news': {'type': 'array'}}}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()

        # Get latest filing
        find_tool = EdgarFindFilingTool()
        latest_10q = find_tool.execute({'ticker': ticker, 'form_type': '10-Q', 'limit': 1})
        filings = latest_10q.get('filings', [{}])
        latest_filing = filings[0] if filings else {}

        # Get key metrics (revenue + EPS last 2 quarters)
        from .edgar_concept_map import fetch_best_concept, filter_and_sort_records
        try:
            cik = resolve_cik(ticker)
            _, rev_records = fetch_best_concept(cik, 'revenue')
            _, eps_records = fetch_best_concept(cik, 'eps diluted')
            rev_filtered = filter_and_sort_records(rev_records, '10-Q', 2)
            eps_filtered = filter_and_sort_records(eps_records, '10-Q', 2)
            financials = {
                'revenue': [{'period_end': r['end'], 'value': r['val'], 'fiscal_period': r.get('fp')} for r in rev_filtered],
                'eps_diluted': [{'period_end': r['end'], 'value': r['val'], 'fiscal_period': r.get('fp')} for r in eps_filtered],
            }
        except Exception as e:
            financials = {'error': str(e)}

        # Recent news
        news_raw = tavily_search(f'{ticker} latest earnings financial results news', include_domains=['bloomberg.com', 'reuters.com', 'finance.yahoo.com', 'cnbc.com'], max_results=3, search_depth='basic')
        recent_news = [{'title': r.get('title', ''), 'url': r.get('url', ''), 'snippet': r.get('content', '')[:150]} for r in news_raw.get('results', [])[:3]]

        return {
            'success': True,
            'ticker': ticker,
            'latest_filing': latest_filing,
            'financials': financials,
            'recent_news': recent_news,
        }
