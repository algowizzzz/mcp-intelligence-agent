"""CIK resolution via Tavily extract. Cached per process."""
import json
from typing import Optional
from .edgar_tavily_client import tavily_extract, fix_tavily_json

_cik_cache: dict = {}
TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'

def resolve_cik(ticker: str) -> str:
    """Resolve ticker symbol to zero-padded 10-digit CIK. Raises ValueError if not found."""
    ticker_upper = ticker.upper()
    if ticker_upper in _cik_cache:
        return _cik_cache[ticker_upper]
    results = tavily_extract([TICKERS_URL])
    if not results:
        raise ValueError(f'Could not fetch company tickers from SEC')
    raw = fix_tavily_json(results[0].get('raw_content', ''))
    tickers_data = json.loads(raw)
    for entry in tickers_data.values():
        if entry.get('ticker', '').upper() == ticker_upper:
            cik = str(entry['cik_str']).zfill(10)
            _cik_cache[ticker_upper] = cik
            return cik
    raise ValueError(f'Ticker {ticker} not found in SEC company tickers list')
