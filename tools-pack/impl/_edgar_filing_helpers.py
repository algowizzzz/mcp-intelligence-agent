"""
Shared filing-resolution and section-extraction helpers used by the EDGAR
Tavily-based tools (edgar_extract_section, edgar_earnings_brief,
edgar_segment_analysis, edgar_risk_summary).

Ported from sajhamcpserver/sajha/tools/impl/edgar_tavily_tools.py module-level
helpers (_validate_sources, _resolve_filing_url, _extract_from_filing_url).
"""
import re
from typing import List, Dict, Optional, Tuple

from tools_pack_impl._tavily_client import (
    tavily_extract,
    tavily_search,
    stream_sec_section,
    direct_sec_json,
)


def validate_sources(sources: List[Dict], ticker: str, period: str,
                     expected_cik: Optional[str] = None) -> List[str]:
    """
    Check each source URL for company/period mismatch.
    Returns a list of human-readable warning strings (empty = all clear).
    """
    warnings: List[str] = []

    period_year = None
    m = re.search(r'(20\d{2})', period)
    if m:
        period_year = int(m.group(1))

    for src in sources:
        url = src.get('url', '')

        cik_m = re.search(r'/edgar/data/(\d+)/', url)
        if cik_m and expected_cik:
            src_cik = cik_m.group(1).lstrip('0')
            exp_cik = str(expected_cik).lstrip('0')
            if src_cik != exp_cik:
                warnings.append(
                    f"WRONG COMPANY: source CIK {src_cik} does not match {ticker} "
                    f"(CIK {exp_cik}). Source: {url}"
                )

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


def resolve_filing_url(cik: str, period: str) -> Tuple:
    """
    Use SEC submissions API to find the exact filing URL for a given period.
    Returns (filing_url, filing_date, form_type, accession_no) or (None,)*4.
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

    if target_q == 4:
        annual = True
        target_q = None

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
        for form, date, acc, doc in zip(forms, dates, accessions, primary):
            if form == target_form:
                acc_clean = acc.replace('-', '')
                filing_url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{doc}'
                return filing_url, date, form, acc
        return None, None, None, None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0]
    return best[1], best[0], best[2], best[3]


def extract_from_filing_url(filing_url: Optional[str], filing_date: Optional[str],
                             form_type: Optional[str], ticker: str, period: str,
                             cik: str, prompt: str, fallback_query: str,
                             fallback_domains: Optional[List[str]] = None,
                             accession_no: Optional[str] = None,
                             section_keywords: Optional[str] = None) -> Tuple:
    """
    Three-tier extraction:
      1. stream_sec_section for large SEC Archives HTML
      2. tavily_extract on the filing URL
      3. tavily_search fallback with source validation
    Returns (combined_text, sources, data_quality, warnings).
    """
    if fallback_domains is None:
        fallback_domains = ['sec.gov']

    sources = (
        [{'title': f'{ticker} {form_type} filed {filing_date}', 'url': filing_url}]
        if filing_url else []
    )

    if filing_url and 'sec.gov/Archives' in filing_url and section_keywords:
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

    if filing_url:
        try:
            extract_results = tavily_extract([filing_url])
            content = extract_results[0].get('raw_content', '') if extract_results else ''
        except Exception:
            content = ''

        if content and len(content.strip()) > 200:
            return content, sources, 'OK', []

    raw = tavily_search(
        fallback_query,
        include_domains=fallback_domains,
        max_results=3,
        include_answer=True,
    )
    results = raw.get('results', [])[:3]
    combined = raw.get('answer', '') + '\n\n' + '\n\n'.join(r.get('content', '') for r in results)
    fallback_sources = [{'title': r.get('title', ''), 'url': r.get('url', '')} for r in results]

    if not combined.strip():
        return '', fallback_sources, 'FAILED', ['No content returned from any source']

    warnings = validate_sources(fallback_sources, ticker, period, cik)
    if warnings:
        return combined, fallback_sources, 'FAILED', warnings

    return combined, fallback_sources, 'OK', []
