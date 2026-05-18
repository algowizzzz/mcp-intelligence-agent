"""
EDGAR Tavily-based tools — T-01, T-02, T-06, T-07, T-08, T-10
Qualitative section extraction and filing discovery via Tavily.
"""
import json
import re
from typing import Dict, Any, List
from sajha.tools.base_mcp_tool import BaseMCPTool
from .edgar_tavily_client import tavily_extract, tavily_search, llm_extract, fix_tavily_json, efts_find_section_file, stream_sec_section, direct_sec_json
from .edgar_cik_resolver import resolve_cik


def _validate_sources(sources: List[Dict], ticker: str, period: str, expected_cik: str = None) -> List[str]:
    """
    Check each source URL for company/period mismatch.
    Returns a list of human-readable warning strings (empty = all clear).
    """
    warnings = []

    # Extract the 4-digit year the caller is asking about
    period_year = None
    m = re.search(r'(20\d{2})', period)
    if m:
        period_year = int(m.group(1))

    for src in sources:
        url = src.get('url', '')
        title = src.get('title', '')

        # ── 1. Wrong company: CIK in URL doesn't match expected ticker CIK ──
        cik_m = re.search(r'/edgar/data/(\d+)/', url)
        if cik_m and expected_cik:
            src_cik = cik_m.group(1).lstrip('0')
            exp_cik = str(expected_cik).lstrip('0')
            if src_cik != exp_cik:
                warnings.append(
                    f"WRONG COMPANY: source CIK {src_cik} does not match {ticker} "
                    f"(CIK {exp_cik}). Source: {url}"
                )

        # ── 2. Stale filing: accession number encodes filing year ──
        # Accession format in URL: 18-digit string where digits [10:12] = 2-digit year filed
        acc_m = re.search(r'/(\d{18})/', url)
        if acc_m and period_year:
            acc = acc_m.group(1)
            filed_yy = int(acc[10:12])
            filed_year = 2000 + filed_yy if filed_yy < 50 else 1900 + filed_yy
            year_diff = abs(filed_year - period_year)
            if year_diff > 1:
                warnings.append(
                    f"STALE FILING: source filed {filed_year} but requested period is "
                    f"{period} (Δ{year_diff}y). Source: {url}"
                )

    return warnings


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


def _resolve_filing_url(cik: str, period: str) -> tuple:
    """
    Use SEC submissions API to find the exact filing URL for a given period.
    Returns (filing_url, filing_date, form_type, accession_no) or (None, None, None, None).
    Period examples: 'Q4 2025', 'FY2024', 'annual 2024', 'latest'.
    """
    import datetime
    padded_cik = str(cik).zfill(10)
    submissions_url = f'https://data.sec.gov/submissions/CIK{padded_cik}.json'

    try:
        data = direct_sec_json(submissions_url)
    except Exception:
        return None, None, None, None

    recent = data.get('filings', {}).get('recent', {})
    forms      = recent.get('form', [])
    dates      = recent.get('filingDate', [])
    accessions = recent.get('accessionNumber', [])
    primary    = recent.get('primaryDocument', [])

    period_upper = period.upper()
    annual = any(x in period_upper for x in ['FY', 'ANNUAL', '10-K'])

    year_m = re.search(r'(20\d{2})', period)
    target_year = int(year_m.group(1)) if year_m else None
    q_m = re.search(r'Q([1-4])', period_upper)
    target_q = int(q_m.group(1)) if q_m else None

    # Q4 is always reported in the 10-K annual filing — no standalone Q4 10-Q exists
    if target_q == 4:
        annual = True
        target_q = None  # Don't filter by quarter month for annual

    target_form = '10-K' if annual else '10-Q'

    candidates = []
    for form, date, acc, doc in zip(forms, dates, accessions, primary):
        if form != target_form:
            continue
        try:
            dt = datetime.date.fromisoformat(date)
        except Exception:
            continue

        if target_year and dt.year not in (target_year, target_year - 1, target_year + 1):
            continue
        if target_year and target_q:
            q_months = {1: (1, 4), 2: (4, 7), 3: (7, 10), 4: (10, 13)}
            lo, hi = q_months.get(target_q, (1, 13))
            if not (lo <= dt.month < hi):
                continue

        acc_clean = acc.replace('-', '')
        filing_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{doc}'
        candidates.append((date, filing_url, form, acc))

    if not candidates:
        # Fall back to most recent matching form type
        for form, date, acc, doc in zip(forms, dates, accessions, primary):
            if form == target_form:
                acc_clean = acc.replace('-', '')
                filing_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{doc}'
                return filing_url, date, form, acc
        return None, None, None, None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0]
    return best[1], best[0], best[2], best[3]


def _extract_from_filing_url(filing_url: str, filing_date: str, form_type: str,
                              ticker: str, period: str, cik: str,
                              prompt: str, fallback_query: str,
                              fallback_domains: List[str] = None,
                              accession_no: str = None,
                              section_keywords: str = None) -> tuple:
    """
    Shared helper: extract filing content using a three-tier strategy:
      1. EFTS full-text search API — JSON endpoint, Tavily-friendly, no large HTML download
      2. tavily_extract on the filing URL — works for smaller filings
      3. tavily_search fallback with _validate_sources gate
    Returns (combined_text, sources, data_quality, warnings).
    """
    if fallback_domains is None:
        fallback_domains = ['sec.gov']

    sources = [{'title': f'{ticker} {form_type} filed {filing_date}', 'url': filing_url}] if filing_url else []

    # ── Tier 1: Stream large SEC Archives HTML directly (most reliable for 10-K/10-Q) ──
    if filing_url and 'sec.gov/Archives' in filing_url and section_keywords:
        # Use first keyword phrase as the section marker to scan for
        marker = section_keywords.split()[0:3]  # e.g. ['management', 'discussion', 'analysis']
        # For MD&A use 'item 7', for risk use 'item 1a', etc.
        section_map = {
            'management': 'item 7',
            'risk': 'item 1a',
            'segment': 'item 7',
            'earnings': 'item 7',
            'guidance': 'item 7',
            'business': 'item 1',
            'audit': 'item 9a',
        }
        first_kw = section_keywords.split()[0].lower()
        item_marker = section_map.get(first_kw, 'item 7')
        try:
            streamed = stream_sec_section(filing_url, item_marker, content_kb=120)
            if streamed and len(streamed.strip()) > 200:
                return streamed, sources, 'OK', []
        except Exception:
            pass

    # ── Tier 2: tavily_extract on the verified filing URL (works for smaller filings) ──
    if filing_url:
        try:
            extract_results = tavily_extract([filing_url])
            content = extract_results[0].get('raw_content', '') if extract_results else ''
        except Exception:
            content = ''

        if content and len(content.strip()) > 200:
            return content, sources, 'OK', []

    # ── Tier 3: keyword search with strict validation gate ──
    raw = tavily_search(fallback_query, include_domains=fallback_domains, max_results=3, include_answer=True)
    results = raw.get('results', [])[:3]
    combined = raw.get('answer', '') + '\n\n' + '\n\n'.join(r.get('content', '') for r in results)
    fallback_sources = [{'title': r.get('title', ''), 'url': r.get('url', '')} for r in results]

    if not combined.strip():
        return '', fallback_sources, 'FAILED', ['No content returned from any source']

    warnings = _validate_sources(fallback_sources, ticker, period, cik)
    if warnings:
        return combined, fallback_sources, 'FAILED', warnings

    return combined, fallback_sources, 'OK', []


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

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        section = arguments.get('section', 'MD&A')
        period = arguments.get('period') or 'latest'

        try:
            cik = resolve_cik(ticker)
        except Exception as e:
            return {'success': False, 'error': f'Could not resolve CIK for {ticker}: {e}'}

        filing_url, filing_date, form_type, accession_no = _resolve_filing_url(cik, period)

        keywords = self.SECTION_QUERIES.get(section, section.lower())
        fallback_query = f'"{ticker}" {keywords} {period} site:sec.gov 10-Q 10-K'
        prompt = self.EXTRACTION_PROMPTS.get(
            section,
            f'Extract key information from this {section} SEC filing section for {ticker}. Return concise JSON summary.'
        )

        content, sources, data_quality, warnings = _extract_from_filing_url(
            filing_url, filing_date, form_type, ticker, period, cik,
            prompt, fallback_query,
            accession_no=accession_no, section_keywords=keywords
        )

        if data_quality == 'FAILED':
            if warnings and warnings[0] == 'No content returned from any source':
                return {'success': False, 'error': f'No content found for {ticker} {section} {period}. Try edgar_find_filing first to locate the exact filing URL.'}
            return {
                'success': False, 'ticker': ticker, 'period': period,
                'sources': sources, 'data_quality': 'FAILED',
                'warnings': warnings,
                'error': (
                    f'Source validation failed for {ticker} {section} {period}. '
                    f'Retrieved documents do not match the requested company or period. '
                    f'Details: ' + ' | '.join(warnings)
                )
            }

        try:
            extracted = llm_extract(content, prompt)
        except Exception:
            extracted = {'raw_summary': content[:1000]}

        extracted.update({
            'success': True, 'ticker': ticker, 'period': period,
            'filing_date': filing_date, 'form_type': form_type,
            'sources': sources, 'data_quality': 'OK',
            '_source': filing_url or (sources[0]['url'] if sources else '')
        })
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

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        # Step 1: Resolve exact filing URL from SEC submissions API
        filing_url, filing_date, form_type, accession_no = _resolve_filing_url(cik, period)

        fallback_query = f'{ticker} earnings {period} revenue EPS results 10-Q 8-K SEC filing'
        prompt = f'Extract a complete earnings brief for {ticker} {period}. Return JSON: {{"ticker":"{ticker}","period":"{period}","key_metrics":{{"revenue":"...","eps":"...","net_income":"...","gross_margin":"..."}},"yoy_change":{{"revenue":"...","eps":"..."}},"management_commentary":"...","guidance":"...","analyst_reaction":"..."}}'

        # Step 2: Extract SEC filing content (EFTS → extract → search fallback)
        sec_text, sec_sources, data_quality, warnings = _extract_from_filing_url(
            filing_url, filing_date, form_type, ticker, period, cik,
            prompt, fallback_query,
            accession_no=accession_no,
            section_keywords='earnings revenue net income EPS management commentary guidance'
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
                )
            }

        # Step 3: News/analyst reaction — /search on news domains is correct usage here
        news_query = f'{ticker} earnings {period} results analyst reaction guidance'
        news_raw = tavily_search(news_query, include_domains=['bloomberg.com', 'reuters.com', 'finance.yahoo.com', 'cnbc.com'], max_results=3)
        news_text = news_raw.get('answer', '') + '\n\n' + '\n\n'.join(r.get('content', '') for r in news_raw.get('results', [])[:3])
        news_sources = [{'title': r.get('title', ''), 'url': r.get('url', '')} for r in news_raw.get('results', [])[:2]]

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

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        filing_url, filing_date, form_type, accession_no = _resolve_filing_url(cik, period)

        fallback_query = f'{ticker} revenue by segment product category operating income {period} 10-Q 10-K SEC'
        prompt = f'Extract business segment data for {ticker} {period}. Return JSON: {{"ticker":"{ticker}","period":"{period}","segments":[{{"name":"...","revenue":"...","operating_income":"...","yoy_change":"..."}}]}}'

        content, sources, data_quality, warnings = _extract_from_filing_url(
            filing_url, filing_date, form_type, ticker, period, cik,
            prompt, fallback_query,
            accession_no=accession_no,
            section_keywords='segment revenue operating income business unit geographic breakdown'
        )

        if data_quality == 'FAILED':
            return {
                'success': False, 'ticker': ticker, 'period': period,
                'sources': sources, 'data_quality': 'FAILED',
                'warnings': warnings,
                'error': (
                    f'Source validation failed for {ticker} segment analysis {period}. '
                    f'Details: ' + ' | '.join(warnings)
                )
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

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        # 10-K is annual — prefix period with FY so _resolve_filing_url picks target_form='10-K'
        fy_period = fiscal_year if fiscal_year.upper().startswith('FY') else f'FY{fiscal_year}'

        filing_url, filing_date, form_type, accession_no = _resolve_filing_url(cik, fy_period)

        fallback_query = f'{ticker} risk factors material risks {fiscal_year} 10-K annual report SEC'
        prompt = f'Extract and categorise risk factors for {ticker} from this 10-K content. Return JSON: {{"ticker":"{ticker}","fiscal_year":"{fiscal_year}","risk_categories":[{{"category":"macro|competitive|regulatory|operational|financial|technology","risks":[{{"title":"...","summary":"..."}}]}}]}}'

        content, sources, data_quality, warnings = _extract_from_filing_url(
            filing_url, filing_date, form_type, ticker, fy_period, cik,
            prompt, fallback_query,
            accession_no=accession_no,
            section_keywords='risk factors material risks regulatory competitive operational financial'
        )

        if data_quality == 'FAILED':
            return {
                'success': False, 'ticker': ticker, 'fiscal_year': fiscal_year,
                'sources': sources, 'data_quality': 'FAILED',
                'warnings': warnings,
                'error': (
                    f'Source validation failed for {ticker} risk summary {fiscal_year}. '
                    f'Details: ' + ' | '.join(warnings)
                )
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
