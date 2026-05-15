"""
POC: T-03 edgar_get_metric
Tests the XBRL filtered numeric layer.
Query: "AAPL EPS diluted last 4 quarters"
"""
import urllib.request, json, sys

USER_AGENT = "Sajha-POC saad@example.com"

CONCEPT_MAP = {
    "eps":               ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
    "eps diluted":       ["EarningsPerShareDiluted"],
    "eps basic":         ["EarningsPerShareBasic"],
    "revenue":           ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                          "SalesRevenueNet"],
    "net income":        ["NetIncomeLoss", "NetIncomeLossAttributableToParent"],
    "gross profit":      ["GrossProfit"],
    "operating income":  ["OperatingIncomeLoss"],
    "total assets":      ["Assets"],
    "total debt":        ["LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"],
    "cash":              ["CashAndCashEquivalentsAtCarryingValue", "Cash"],
    "operating cash flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex":             ["PaymentsToAcquirePropertyPlantAndEquipment"],
}

def resolve_cik(ticker: str) -> str:
    url = "https://www.sec.gov/files/company_tickers.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"] == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"Ticker {ticker} not found in company_tickers.json")

def fetch_concept(cik: str, concept: str) -> list:
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    units = data.get("units", {})
    # EPS uses USD/shares, most others use USD
    for key in ["USD/shares", "USD", "shares"]:
        if key in units:
            return units[key]
    return []

def edgar_get_metric(ticker: str, metric: str, periods: int = 4, form_type: str = "10-Q") -> dict:
    metric_lower = metric.lower().strip()
    concepts = CONCEPT_MAP.get(metric_lower)
    if not concepts:
        # Try partial match
        for k, v in CONCEPT_MAP.items():
            if metric_lower in k or k in metric_lower:
                concepts = v
                break
    if not concepts:
        return {"error": f"Unknown metric '{metric}'. Known metrics: {list(CONCEPT_MAP.keys())}"}

    cik = resolve_cik(ticker)

    records = []
    used_concept = None
    for concept in concepts:
        records = fetch_concept(cik, concept)
        if records:
            used_concept = concept
            break

    if not records:
        return {"error": f"No XBRL data found for {ticker} metric '{metric}'"}

    # Filter by form_type
    if form_type and form_type.upper() != "BOTH":
        records = [r for r in records if r.get("form", "") == form_type.upper()]

    # Remove duplicates by period end date (keep the latest filing for each period)
    seen = {}
    for r in records:
        end = r.get("end", "")
        if end not in seen or r.get("filed", "") > seen[end].get("filed", ""):
            seen[end] = r
    records = list(seen.values())

    # Sort by end date descending, take top N
    records.sort(key=lambda x: x.get("end", ""), reverse=True)
    records = records[:min(periods, 20)]

    # Clean up output
    result_records = []
    for r in records:
        result_records.append({
            "period_end":    r.get("end"),
            "period_start":  r.get("start"),
            "value":         r.get("val"),
            "fiscal_year":   r.get("fy"),
            "fiscal_period": r.get("fp"),
            "form":          r.get("form"),
            "filed":         r.get("filed"),
        })

    import json as _json
    response = {
        "ticker":       ticker.upper(),
        "metric":       metric,
        "xbrl_concept": used_concept,
        "form_type":    form_type,
        "periods":      len(result_records),
        "records":      result_records,
    }
    size_kb = len(_json.dumps(response)) / 1024
    response["_size_kb"] = round(size_kb, 1)
    return response


if __name__ == "__main__":
    print("=" * 60)
    print("TEST 1: AAPL EPS diluted last 4 quarters (10-Q)")
    print("=" * 60)
    result = edgar_get_metric("AAPL", "eps diluted", periods=4, form_type="10-Q")
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print("TEST 2: MSFT revenue last 6 quarters")
    print("=" * 60)
    result = edgar_get_metric("MSFT", "revenue", periods=6, form_type="10-Q")
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print("TEST 3: AAPL annual EPS (10-K) last 3 years")
    print("=" * 60)
    result = edgar_get_metric("AAPL", "eps diluted", periods=3, form_type="10-K")
    print(json.dumps(result, indent=2))
