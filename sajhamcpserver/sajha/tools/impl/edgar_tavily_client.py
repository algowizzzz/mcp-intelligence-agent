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

def tavily_extract(urls: List[str]) -> List[Dict]:
    """
    Fetch specific URLs via Tavily /extract endpoint.
    Use for structured JSON endpoints (XBRL, submissions, company tickers).
    Returns list of {url, raw_content} dicts.
    """
    payload = json.dumps({
        'api_key': _get_api_key(),
        'urls': urls,
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.tavily.com/extract',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    return data.get('results', [])

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
