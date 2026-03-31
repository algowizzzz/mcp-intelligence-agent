"""
POC: T-01 edgar_find_filing
Tests Tavily filing discovery on efts.sec.gov.
Query: "Find Apple 10-K for FY2024"
"""
import json, os, urllib.request
from dotenv import load_dotenv
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

def tavily_search(query: str, include_domains: list, max_results: int = 5) -> dict:
    payload = json.dumps({
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "include_domains": include_domains,
        "max_results": max_results,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def edgar_find_filing(ticker: str, form_type: str = "10-K", period: str = "") -> dict:
    """
    Locate a specific SEC filing using Tavily on efts.sec.gov.
    Returns filing metadata: accession number, filing date, document URL.
    """
    query_parts = [ticker, form_type]
    if period:
        query_parts.append(period)
    query = " ".join(query_parts) + " SEC filing"

    raw = tavily_search(
        query=query,
        include_domains=["efts.sec.gov", "sec.gov"],
        max_results=5
    )

    results = raw.get("results", [])
    filings = []
    for r in results:
        url = r.get("url", "")
        title = r.get("title", "")
        content = r.get("content", "")

        # Extract accession number if present (format: XXXXXXXXXX-YY-ZZZZZZ)
        import re
        accn_match = re.search(r'(\d{10}-\d{2}-\d{6})', url + content)
        accession = accn_match.group(1) if accn_match else None

        # Only include results that look like actual filings
        if any(ft in title.upper() or ft in url.upper() for ft in [form_type, "EDGAR", "SEC"]):
            filings.append({
                "title":          title,
                "url":            url,
                "accession_number": accession,
                "snippet":        content[:200],
            })

    return {
        "ticker":    ticker.upper(),
        "form_type": form_type,
        "period":    period,
        "query":     query,
        "filings":   filings[:3],
        "_total_raw_results": len(results),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("TEST 1: Find Apple 10-K for FY2024")
    print("=" * 60)
    result = edgar_find_filing("AAPL", "10-K", "FY2024")
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print("TEST 2: Find Microsoft latest 10-Q")
    print("=" * 60)
    result = edgar_find_filing("MSFT", "10-Q", "")
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print("TEST 3: Find Apple 8-K earnings release 2026")
    print("=" * 60)
    result = edgar_find_filing("AAPL", "8-K", "2026")
    print(json.dumps(result, indent=2))
