"""
Shared Tavily client used by the EDGAR Tavily-based tools and Yahoo Finance tools.

Ported from sajhamcpserver/sajha/tools/impl/edgar_tavily_client.py (pre-migration fork).

Compliance changes from the original:
- No dependency on the old fork's PropertiesConfigurator — Tavily API URL is hard-coded
  with optional override via the TAVILY_API_URL environment variable.
- TAVILY_API_KEY and ANTHROPIC_API_KEY are read from environment.
"""
import json
import os
import urllib.request
from typing import List, Dict, Optional


TAVILY_API_KEY_ENV = 'TAVILY_API_KEY'
DEFAULT_TAVILY_SEARCH_URL = 'https://api.tavily.com/search'
DEFAULT_TAVILY_EXTRACT_URL = 'https://api.tavily.com/extract'
SEC_USER_AGENT = 'RiskGPT-Agent research@riskgpt.ai'


def _get_api_key() -> str:
    key = os.getenv(TAVILY_API_KEY_ENV, '')
    if not key:
        raise ValueError('TAVILY_API_KEY not set in environment')
    return key


def _tavily_search_url() -> str:
    return os.getenv('TAVILY_API_URL', DEFAULT_TAVILY_SEARCH_URL)


def _tavily_extract_url() -> str:
    return os.getenv('TAVILY_EXTRACT_URL', DEFAULT_TAVILY_EXTRACT_URL)


def fix_tavily_json(s: str) -> str:
    """Tavily escapes underscores in raw_content. Unescape before json.loads."""
    return s.replace('\\_', '_')


def direct_sec_json(url: str) -> dict:
    """
    Fetch a SEC JSON API endpoint directly via urllib.
    Used for: company_tickers.json, submissions CIK.json, XBRL concept JSON.
    """
    req = urllib.request.Request(url, headers={'User-Agent': SEC_USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def tavily_extract(urls: List[str], query: Optional[str] = None) -> List[Dict]:
    """Fetch specific URLs via Tavily /extract endpoint."""
    payload_dict = {
        'api_key': _get_api_key(),
        'urls': urls,
    }
    if query:
        payload_dict['query'] = query
    payload = json.dumps(payload_dict).encode('utf-8')
    req = urllib.request.Request(
        _tavily_extract_url(),
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    return data.get('results', [])


def stream_sec_section(filing_url: str, section_marker: str, content_kb: int = 120) -> str:
    """
    Stream a large SEC filing HTML document and extract the section starting at
    section_marker (e.g. 'item 7'). Returns stripped text up to content_kb bytes.
    """
    import re as _re

    req = urllib.request.Request(
        filing_url,
        headers={
            'User-Agent': SEC_USER_AGENT,
            'Accept-Encoding': 'identity',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as r:
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

                if len(occurrences) >= 3:
                    actual_pos = occurrences[2]
                    extra_needed = actual_pos + content_kb * 1024 - len(buf)
                    if extra_needed > 0:
                        extra = r.read(min(extra_needed + 65536, 1024 * 1024))
                        buf += extra

                    text = buf.decode('utf-8', errors='ignore')
                    snippet = text[actual_pos: actual_pos + content_kb * 1024]
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
    Use EDGAR's EFTS search index to find a specific section file within a filing,
    then extract its content via tavily_extract. Returns extracted text or ''.
    """
    import urllib.parse

    acc = accession_no.replace('-', '')
    if len(acc) == 18:
        accession_dash = f'{acc[:10]}-{acc[10:12]}-{acc[12:]}'
    else:
        accession_dash = accession_no

    query = urllib.parse.quote(f'"{keywords}"')
    efts_url = (
        f'https://efts.sec.gov/LATEST/search-index'
        f'?q={query}&dateRange=custom&startdt=2015-01-01&enddt=2030-01-01'
        f'&_source=ciks,adsh,form,file_date,display_names'
    )

    try:
        req = urllib.request.Request(efts_url, headers={'User-Agent': SEC_USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except Exception:
        return ''

    hits = data.get('hits', {}).get('hits', [])
    matched_file = None
    for hit in hits:
        hit_adsh = hit.get('_source', {}).get('adsh', '').replace('-', '')
        hit_ciks = hit.get('_source', {}).get('ciks', [])
        if hit_adsh == acc or any(c.lstrip('0') == cik.lstrip('0') for c in hit_ciks):
            hit_id = hit.get('_id', '')
            if ':' in hit_id:
                _, filename = hit_id.split(':', 1)
                matched_file = filename
                break

    if not matched_file:
        return ''

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


def tavily_search(query: str, include_domains: Optional[List[str]] = None,
                  max_results: int = 5, include_answer: bool = True,
                  search_depth: str = 'advanced',
                  topic: Optional[str] = None,
                  include_raw_content: bool = False,
                  include_images: bool = False,
                  exclude_domains: Optional[List[str]] = None) -> Dict:
    """Search via Tavily /search endpoint."""
    payload_dict: Dict[str, object] = {
        'api_key': _get_api_key(),
        'query': query,
        'search_depth': search_depth,
        'include_answer': include_answer,
        'max_results': max_results,
        'include_raw_content': include_raw_content,
        'include_images': include_images,
    }
    if include_domains is not None:
        payload_dict['include_domains'] = include_domains
    if exclude_domains is not None:
        payload_dict['exclude_domains'] = exclude_domains
    if topic is not None:
        payload_dict['topic'] = topic

    payload = json.dumps(payload_dict).encode('utf-8')
    req = urllib.request.Request(
        _tavily_search_url(),
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def llm_extract(raw_text: str, extraction_prompt: str, max_tokens: int = 1024) -> Dict:
    """Call Anthropic API to extract structured JSON from raw text."""
    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise ValueError('ANTHROPIC_API_KEY not set')
    model = os.getenv('ANTHROPIC_MODEL', 'claude-haiku-4-5-20251001')
    messages = [{
        'role': 'user',
        'content': f'{extraction_prompt}\n\nContent:\n{raw_text[:6000]}\n\nReturn ONLY valid JSON.',
    }]
    payload = json.dumps({'model': model, 'max_tokens': max_tokens, 'messages': messages}).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    content = resp['content'][0]['text'].strip()
    if content.startswith('```'):
        content = content.split('```')[1]
        if content.startswith('json'):
            content = content[4:]
    return json.loads(content.strip())
