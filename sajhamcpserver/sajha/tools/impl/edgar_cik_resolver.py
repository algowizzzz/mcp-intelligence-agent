"""CIK resolution via direct SEC API call. Cached per process."""
import json
from typing import Optional
from .edgar_tavily_client import direct_sec_json

_cik_cache: dict = {}
TICKERS_URL = 'https://www.sec.gov/files/company_tickers.json'

def resolve_cik(ticker: str) -> str:
    """Resolve ticker symbol to zero-padded 10-digit CIK. Raises ValueError if not found."""
    ticker_upper = ticker.upper()
    if ticker_upper in _cik_cache:
        return _cik_cache[ticker_upper]
    tickers_data = direct_sec_json(TICKERS_URL)
    for entry in tickers_data.values():
        if entry.get('ticker', '').upper() == ticker_upper:
            cik = str(entry['cik_str']).zfill(10)
            _cik_cache[ticker_upper] = cik
            return cik
    raise ValueError(f'Ticker {ticker} not found in SEC company tickers list')
