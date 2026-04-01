"""Shared Tavily client for all EDGAR tools. All SEC/EDGAR HTTP calls go through here."""
import json, os, urllib.request
from typing import List, Dict

TAVILY_API_KEY_ENV = 'TAVILY_API_KEY'

def _get_api_key() -> str:
    key = os.getenv(TAVILY_API_KEY_ENV, '')
    if not key:
        raise ValueError('TAVILY_API_KEY not set in environment')
    return key

def fix_tavily_json(s: str) -> str:
    """Tavily escapes underscores in raw_content. Unescape before json.loads."""
    return s.replace('\\_', '_')

def direct_sec_json(url: str) -> dict:
    """
    Fetch a SEC JSON API endpoint directly via urllib.
    Used for: company_tickers.json, submissions CIK.json, XBRL concept JSON.
    These are all static/structured JSON — no need to route through Tavily.
    """
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'RiskGPT-Agent research@riskgpt.ai'}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def tavily_extract(urls: List[str], query: str = None) -> List[Dict]:
    """
    Fetch specific URLs via Tavily /extract endpoint.
    Use for structured JSON endpoints (XBRL, submissions, company tickers).
    Returns list of {url, raw_content} dicts.
    """
    payload_dict = {
        'api_key': _get_api_key(),
        'urls': urls,
    }
    if query:
        payload_dict['query'] = query
    payload = json.dumps(payload_dict).encode('utf-8')
    req = urllib.request.Request(
        'https://api.tavily.com/extract',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    return data.get('results', [])


def stream_sec_section(filing_url: str, section_marker: str, content_kb: int = 120) -> str:
    """
    Stream a large SEC filing HTML document and extract the section starting at
    section_marker (e.g. 'item 7'). Skips the Table of Contents occurrence and
    returns the actual section body (stripped of HTML tags).

    This is the only reliable method for large 10-K filings (>5 MB) where
    Tavily /extract times out or returns partial/wrong content.

    Args:
        filing_url: Full URL to the SEC Archives HTML document
        section_marker: Section header to find, case-insensitive (e.g. 'item 7')
        content_kb: How many KB of text to return after the marker (default 120 KB)
    """
    import re as _re

    req = urllib.request.Request(
        filing_url,
        headers={
            'User-Agent': 'RiskGPT-Agent research@riskgpt.ai',
            'Accept-Encoding': 'identity',
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            buf = b''
            occurrences = []
            max_scan_bytes = 15 * 1024 * 1024  # scan up to 15 MB

            while len(buf) < max_scan_bytes:
                chunk = r.read(65536)
                if not chunk:
                    break
                buf += chunk

                text = buf.decode('utf-8', errors='ignore')
                marker_pattern = _re.compile(_re.escape(section_marker), _re.IGNORECASE)
                for m in marker_pattern.finditer(text):
                    pos = m.start()
                    if not occurrences or pos - occurrences[-1] > 5000:
                        occurrences.append(pos)

                # After finding 3+ occurrences the third is the real section body
                # (first two are usually Table of Contents entries)
                if len(occurrences) >= 3:
                    actual_pos = occurrences[2]
                    # Read a bit more to get enough content
                    extra_needed = actual_pos + content_kb * 1024 - len(buf)
                    if extra_needed > 0:
                        extra = r.read(min(extra_needed + 65536, 1024 * 1024))
                        buf += extra

                    text = buf.decode('utf-8', errors='ignore')
                    snippet = text[actual_pos: actual_pos + content_kb * 1024]
                    # Strip HTML
                    snippet = _re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', snippet)
                    snippet = _re.sub(r'<[^>]+>', ' ', snippet)
                    snippet = _re.sub(r'&nbsp;', ' ', snippet)
                    snippet = _re.sub(r'&amp;', '&', snippet)
                    snippet = _re.sub(r'&#\d+;', ' ', snippet)
                    snippet = _re.sub(r'\s+', ' ', snippet).strip()
                    return snippet[:content_kb * 1024]

    except Exception:
        return ''

    return ''


def efts_find_section_file(cik: str, accession_no: str, keywords: str) -> str:
    """
    Use EDGAR's EFTS search index to find the specific section file within a filing,
    then extract its content via tavily_extract.

    EFTS returns _id in format 'accession:filename' — this tells us exactly which
    sub-document within the filing contains our section (e.g. MD&A may be in a
    separate exhibit file rather than the massive primary document).

    Returns extracted text content, or '' if not found.
    """
    import urllib.parse, urllib.request

    # Normalise accession to dash format for matching
    acc = accession_no.replace('-', '')
    if len(acc) == 18:
        accession_dash = f'{acc[:10]}-{acc[10:12]}-{acc[12:]}'
    else:
        accession_dash = accession_no

    padded_cik = str(cik).lstrip('0').zfill(10)

    # Search EFTS scoped to this exact accession number via the adsh filter
    query = urllib.parse.quote(f'"{keywords}"')
    efts_url = (
        f'https://efts.sec.gov/LATEST/search-index'
        f'?q={query}&dateRange=custom&startdt=2015-01-01&enddt=2030-01-01'
        f'&_source=ciks,adsh,form,file_date,display_names'
    )

    try:
        req = urllib.request.Request(
            efts_url,
            headers={'User-Agent': 'RiskGPT-Agent research@riskgpt.ai'}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except Exception:
        return ''

    hits = data.get('hits', {}).get('hits', [])

    # Find the hit whose accession matches ours
    matched_file = None
    for hit in hits:
        hit_adsh = hit.get('_source', {}).get('adsh', '').replace('-', '')
        hit_ciks = hit.get('_source', {}).get('ciks', [])
        # Match by accession number OR CIK
        if hit_adsh == acc or any(c.lstrip('0') == cik.lstrip('0') for c in hit_ciks):
            hit_id = hit.get('_id', '')  # format: 'accession:filename'
            if ':' in hit_id:
                _, filename = hit_id.split(':', 1)
                matched_file = filename
                break

    if not matched_file:
        return ''

    # Build the URL for this specific section file
    cik_int = str(int(cik.lstrip('0') or '0'))
    section_url = f'https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}/{matched_file}'

    try:
        results = tavily_extract([section_url])
        if results:
            content = results[0].get('raw_content', '')
            if content and len(content.strip()) > 200:
                return content
    except Exception:
        pass

    return ''

def tavily_search(query: str, include_domains: List[str], max_results: int = 5,
                  include_answer: bool = True, search_depth: str = 'advanced') -> Dict:
    """
    Search via Tavily /search endpoint.
    Use for qualitative text retrieval (MD&A, risk factors, news, filing sections).
    """
    payload = json.dumps({
        'api_key': _get_api_key(),
        'query': query,
        'search_depth': search_depth,
        'include_answer': include_answer,
        'include_domains': include_domains,
        'max_results': max_results,
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.tavily.com/search',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def llm_extract(raw_text: str, extraction_prompt: str, max_tokens: int = 1024) -> Dict:
    """
    Call Anthropic API to extract structured JSON from raw text.
    Uses claude-haiku for cost efficiency.
    """
    import os
    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise ValueError('ANTHROPIC_API_KEY not set')
    model = os.getenv('ANTHROPIC_MODEL', 'claude-haiku-4-5-20251001')
    messages = [{'role': 'user', 'content': f'{extraction_prompt}\n\nContent:\n{raw_text[:6000]}\n\nReturn ONLY valid JSON.'}]
    payload = json.dumps({'model': model, 'max_tokens': max_tokens, 'messages': messages}).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={'Content-Type': 'application/json', 'x-api-key': api_key, 'anthropic-version': '2023-06-01'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    content = resp['content'][0]['text'].strip()
    if content.startswith('```'):
        content = content.split('```')[1]
        if content.startswith('json'):
            content = content[4:]
    return json.loads(content.strip())
