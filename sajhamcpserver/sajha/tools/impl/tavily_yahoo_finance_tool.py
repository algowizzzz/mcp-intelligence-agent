"""
Tavily-backed Yahoo Finance MCP Tools
Replaces direct Yahoo Finance API calls with Tavily search scoped to finance.yahoo.com.
Raw Tavily response is passed to Claude for structured extraction — no regex.
Same input/output schemas as the original yahoo_finance_tool.py.
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from sajha.tools.base_mcp_tool import BaseMCPTool


def _get_tavily_api_key():
    return os.getenv('TAVILY_API_KEY', '')


def _tavily_search(query: str, include_domains: List[str], search_depth: str = "advanced",
                   include_answer: bool = True, max_results: int = 5) -> Dict:
    import urllib.request

    api_key = os.getenv('TAVILY_API_KEY', '')
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set in environment")

    from sajha.core.properties_configurator import PropertiesConfigurator
    api_url = PropertiesConfigurator().get('tool.tavily.api_url', 'https://api.tavily.com/search')

    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_domains": include_domains,
        "max_results": max_results,
    }).encode('utf-8')

    req = urllib.request.Request(api_url, data=payload,
                                  headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _llm_extract(raw_text: str, extraction_prompt: str) -> Dict:
    import urllib.request

    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in environment")

    model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')

    messages = [{"role": "user", "content": f"{extraction_prompt}\n\nRaw search content:\n{raw_text}\n\nReturn ONLY valid JSON with no additional text or markdown."}]

    payload = json.dumps({"model": model, "max_tokens": 1024, "messages": messages}).encode('utf-8')

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={'Content-Type': 'application/json', 'x-api-key': api_key, 'anthropic-version': '2023-06-01'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        response = json.loads(resp.read().decode('utf-8'))
        content = response['content'][0]['text'].strip()
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
        return json.loads(content.strip())


class TavilyYahooGetQuoteTool(BaseMCPTool):
    def __init__(self, config: Dict = None):
        default_config = {'name': 'yahoo_get_quote', 'description': 'Retrieve real-time stock quote data including current price, volume, market cap, and key statistics (via Tavily/Yahoo Finance)', 'version': '2.0.0', 'enabled': True}
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL, GOOGL, MSFT)"}}, "required": ["symbol"]}

    def get_output_schema(self) -> Dict:
        return {"type": "object", "properties": {"symbol": {"type": "string"}, "name": {"type": ["string", "null"]}, "price": {"type": ["number", "null"]}, "currency": {"type": "string"}, "change": {"type": ["number", "null"]}, "change_percent": {"type": ["number", "null"]}, "volume": {"type": ["integer", "null"]}, "avg_volume": {"type": ["integer", "null"]}, "market_cap": {"type": ["number", "null"]}, "pe_ratio": {"type": ["number", "null"]}, "dividend_yield": {"type": ["number", "null"]}, "fifty_two_week_high": {"type": ["number", "null"]}, "fifty_two_week_low": {"type": ["number", "null"]}, "day_high": {"type": ["number", "null"]}, "day_low": {"type": ["number", "null"]}, "open": {"type": ["number", "null"]}, "previous_close": {"type": ["number", "null"]}, "last_updated": {"type": "string"}, "_source": {"type": "string"}}, "required": ["symbol", "_source"]}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        symbol = arguments['symbol'].upper().strip()
        source_url = f"https://finance.yahoo.com/quote/{symbol}"
        tavily_result = _tavily_search(query=f"{symbol} stock quote price market cap PE ratio dividend 52-week high low volume", include_domains=["finance.yahoo.com"], search_depth="advanced", include_answer=True, max_results=5)
        if tavily_result.get('results'): source_url = tavily_result['results'][0].get('url', source_url)
        raw_text = (tavily_result.get('answer', '') or '') + '\n\n' + '\n'.join(r.get('content', '') for r in tavily_result.get('results', []))
        extraction_prompt = f"""Extract stock quote data for {symbol} from the search content below.
Return a JSON object with these fields (use null if not found):
{{"name": "full company name", "price": current stock price as a number, "change": price change today as a number, "change_percent": percentage change today as a number (e.g. -1.23), "volume": trading volume as an integer, "avg_volume": average volume as an integer, "market_cap": market capitalisation in dollars as a number, "pe_ratio": price-to-earnings ratio as a number, "dividend_yield": dividend yield as a decimal (e.g. 0.005 for 0.5%), "fifty_two_week_high": 52-week high price as a number, "fifty_two_week_low": 52-week low price as a number, "day_high": today's high price as a number, "day_low": today's low price as a number, "open": today's opening price as a number, "previous_close": previous closing price as a number, "currency": currency code (default "USD")}}"""
        extracted = _llm_extract(raw_text, extraction_prompt)
        return {'symbol': symbol, 'name': extracted.get('name'), 'price': extracted.get('price'), 'currency': extracted.get('currency', 'USD'), 'change': extracted.get('change'), 'change_percent': extracted.get('change_percent'), 'volume': extracted.get('volume'), 'avg_volume': extracted.get('avg_volume'), 'market_cap': extracted.get('market_cap'), 'pe_ratio': extracted.get('pe_ratio'), 'dividend_yield': extracted.get('dividend_yield'), 'fifty_two_week_high': extracted.get('fifty_two_week_high'), 'fifty_two_week_low': extracted.get('fifty_two_week_low'), 'day_high': extracted.get('day_high'), 'day_low': extracted.get('day_low'), 'open': extracted.get('open'), 'previous_close': extracted.get('previous_close'), 'last_updated': datetime.now().isoformat(), '_source': source_url}


class TavilyYahooGetHistoryTool(BaseMCPTool):
    def __init__(self, config: Dict = None):
        default_config = {'name': 'yahoo_get_history', 'description': 'Retrieve historical stock price summary for a given period via Tavily/Yahoo Finance. Returns period high/low/change statistics and trend narrative. data_mode=summary: individual OHLCV rows not available via this route.', 'version': '2.0.0', 'enabled': True}
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker symbol"}, "period": {"type": "string", "enum": ["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"], "default": "1mo"}, "interval": {"type": "string", "default": "1d"}, "include_events": {"type": "boolean", "default": True}}, "required": ["symbol"]}

    def get_output_schema(self) -> Dict:
        return {"type": "object", "properties": {"symbol": {"type": "string"}, "period": {"type": "string"}, "interval": {"type": "string"}, "data_mode": {"type": "string"}, "data_points": {"type": ["integer", "null"]}, "history": {"type": "array"}, "period_summary": {"type": "object"}, "dividends": {"type": "array"}, "splits": {"type": "array"}, "currency": {"type": "string"}, "last_updated": {"type": "string"}, "_source": {"type": "string"}}, "required": ["symbol", "_source"]}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        symbol = arguments['symbol'].upper().strip()
        period = arguments.get('period', '1mo')
        interval = arguments.get('interval', '1d')
        source_url = f"https://finance.yahoo.com/quote/{symbol}/history"
        period_labels = {'1d':'1 day','5d':'5 days','1mo':'1 month','3mo':'3 months','6mo':'6 months','1y':'1 year','2y':'2 years','5y':'5 years','10y':'10 years','ytd':'year to date','max':'all time'}
        period_label = period_labels.get(period, period)
        tavily_result = _tavily_search(query=f"{symbol} stock historical price performance {period_label} high low change dividend split", include_domains=["finance.yahoo.com"], search_depth="advanced", include_answer=True, max_results=5)
        if tavily_result.get('results'): source_url = tavily_result['results'][0].get('url', source_url)
        raw_text = (tavily_result.get('answer', '') or '') + '\n\n' + '\n'.join(r.get('content', '') for r in tavily_result.get('results', []))
        extraction_prompt = f"""Extract historical stock performance data for {symbol} over {period_label} from the search content.
Return a JSON object with these fields (use null if not found):
{{"period_high": highest price during the period as a number, "period_low": lowest price during the period as a number, "change_percent": total percentage change over the period as a number (e.g. -5.2), "trend_narrative": a 1-2 sentence plain-English summary of the stock's performance over this period}}"""
        extracted = _llm_extract(raw_text, extraction_prompt)
        return {'symbol': symbol, 'period': period, 'interval': interval, 'data_mode': 'summary', 'data_points': None, 'history': [], 'period_summary': {'period_high': extracted.get('period_high'), 'period_low': extracted.get('period_low'), 'change_percent': extracted.get('change_percent'), 'trend_narrative': extracted.get('trend_narrative', '')}, 'dividends': [], 'splits': [], 'currency': 'USD', 'last_updated': datetime.now().isoformat(), '_source': source_url}


class TavilyYahooSearchSymbolsTool(BaseMCPTool):
    def __init__(self, config: Dict = None):
        default_config = {'name': 'yahoo_search_symbols', 'description': 'Search for stock symbols and companies by name, ticker, or keyword (via Tavily/Yahoo Finance)', 'version': '2.0.0', 'enabled': True}
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {"type": "object", "properties": {"query": {"type": "string", "description": "Company name, ticker symbol, or keyword"}, "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50}, "exchange": {"type": "string", "enum": ["NYSE","NASDAQ","AMEX","LSE","TSX","all"], "default": "all"}}, "required": ["query"]}

    def get_output_schema(self) -> Dict:
        return {"type": "object", "properties": {"query": {"type": "string"}, "result_count": {"type": "integer"}, "results": {"type": "array", "items": {"type": "object", "properties": {"symbol": {"type": "string"}, "name": {"type": "string"}, "exchange": {"type": ["string","null"]}, "type": {"type": "string"}, "sector": {"type": ["string","null"]}, "industry": {"type": ["string","null"]}, "market_cap": {"type": ["number","null"]}, "description": {"type": ["string","null"]}}}}, "last_updated": {"type": "string"}, "_source": {"type": "string"}}, "required": ["query","results","_source"]}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        query = arguments['query']
        limit = arguments.get('limit', 10)
        exchange_filter = arguments.get('exchange', 'all')
        source_url = "https://finance.yahoo.com/lookup/"
        tavily_result = _tavily_search(query=f"{query} stock ticker symbol listing exchange", include_domains=["finance.yahoo.com"], search_depth="basic", include_answer=False, max_results=min(limit+2, 10))
        if tavily_result.get('results'): source_url = tavily_result['results'][0].get('url', source_url)
        raw_text = '\n'.join(f"URL: {r.get('url','')}\nTitle: {r.get('title','')}\nContent: {r.get('content','')}" for r in tavily_result.get('results', []))
        exchange_instruction = f"Only include results from the {exchange_filter} exchange." if exchange_filter != 'all' else "Include results from any exchange."
        extraction_prompt = f"""Extract a list of stock ticker symbols and companies matching the query "{query}" from the search content.
{exchange_instruction}
Return up to {limit} results as a JSON object:
{{"results": [{{"symbol": "ticker symbol in uppercase", "name": "full company name", "exchange": "NYSE, NASDAQ, AMEX, LSE, TSX, or null if unknown", "type": "EQUITY, ETF, INDEX, or FUND", "sector": "sector name or null", "industry": "industry name or null", "market_cap": null, "description": "brief description or null"}}]}}
Only include entries where you are confident about the ticker symbol."""
        extracted = _llm_extract(raw_text, extraction_prompt)
        results = extracted.get('results', [])
        return {'query': query, 'result_count': len(results), 'results': results, 'last_updated': datetime.now().isoformat(), '_source': source_url}
