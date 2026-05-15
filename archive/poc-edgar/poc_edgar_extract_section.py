"""
POC: T-02 edgar_extract_section
Tests Tavily fetch + LLM extraction of a 10-K/10-Q section.
Query: "What did Apple say about iPhone demand in their latest 10-Q?"
"""
import json, os, urllib.request
from dotenv import load_dotenv
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

SECTION_QUERIES = {
    "MD&A":               "management discussion analysis results operations",
    "Risk_Factors":       "risk factors",
    "Business":           "business overview description",
    "Financial_Statements": "financial statements condensed consolidated",
    "Notes":              "notes to financial statements",
    "Audit":              "auditor opinion internal controls",
    "Segment_Revenue":    "segment revenue operating income geographic",
    "Guidance":           "outlook guidance forward looking fiscal year",
}

def tavily_fetch(url: str, query: str) -> dict:
    payload = json.dumps({
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "include_domains": ["sec.gov"],
        "max_results": 3,
        "include_raw_content": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def llm_extract(raw_text: str, section: str, ticker: str) -> dict:
    extraction_prompts = {
        "MD&A": f"Extract the key points from this {ticker} Management Discussion & Analysis section. Return JSON: {{\"section\": \"MD&A\", \"key_points\": [\"...\"], \"revenue_commentary\": \"...\", \"outlook\": \"...\", \"risks_mentioned\": [\"...\"]}}",
        "Risk_Factors": f"Extract and categorise the main risk factors from this {ticker} SEC filing. Return JSON: {{\"section\": \"Risk_Factors\", \"risk_categories\": [{{\"category\": \"...\", \"summary\": \"...\"}}]}}",
        "Guidance": f"Extract any forward guidance or outlook statements from this {ticker} SEC filing. Return JSON: {{\"section\": \"Guidance\", \"fiscal_year\": \"...\", \"revenue_guidance\": \"...\", \"eps_guidance\": \"...\", \"commentary\": \"...\", \"key_statements\": [\"...\"]}}",
        "Segment_Revenue": f"Extract business segment revenue data from this {ticker} SEC filing. Return JSON: {{\"section\": \"Segment_Revenue\", \"segments\": [{{\"name\": \"...\", \"revenue\": \"...\", \"yoy_change\": \"...\"}}]}}",
    }
    prompt = extraction_prompts.get(section,
        f"Extract the key information from this {section} section of a {ticker} SEC filing. Return a concise JSON summary with the most important points.")

    messages = [{"role": "user", "content": f"{prompt}\n\nFiling content:\n{raw_text[:6000]}\n\nReturn ONLY valid JSON."}]
    payload = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "messages": messages
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        resp = json.loads(r.read())
    content = resp["content"][0]["text"].strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())

def edgar_extract_section(ticker: str, section: str, period: str = "latest") -> dict:
    """
    Find the relevant SEC filing section for a ticker and extract structured content.
    section: MD&A | Risk_Factors | Business | Guidance | Segment_Revenue | Notes | Audit
    """
    section_keywords = SECTION_QUERIES.get(section, section.lower())
    query = f"{ticker} {section_keywords} {period} 10-Q OR 10-K SEC filing site:sec.gov"

    raw = tavily_fetch(url="", query=query)

    results = raw.get("results", [])
    answer = raw.get("answer", "")

    # Combine answer + top results content for extraction
    combined_text = answer + "\n\n"
    sources = []
    for r in results[:3]:
        combined_text += r.get("content", "") + "\n\n"
        sources.append({"title": r.get("title", ""), "url": r.get("url", "")})

    if not combined_text.strip():
        return {"error": "No content retrieved from SEC filing"}

    print(f"  → Retrieved {len(combined_text)} chars from {len(results)} sources, extracting...")
    extracted = llm_extract(combined_text, section, ticker)
    extracted["ticker"] = ticker.upper()
    extracted["period"] = period
    extracted["sources"] = sources
    extracted["_raw_chars"] = len(combined_text)

    import json as _json
    extracted["_size_kb"] = round(len(_json.dumps(extracted)) / 1024, 1)
    return extracted


if __name__ == "__main__":
    print("=" * 60)
    print("TEST 1: Apple MD&A from latest 10-Q")
    print("=" * 60)
    result = edgar_extract_section("AAPL", "MD&A", "latest 2026")
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print("TEST 2: Apple Guidance / Outlook")
    print("=" * 60)
    result = edgar_extract_section("AAPL", "Guidance", "Q1 FY2026")
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print("TEST 3: Apple Segment Revenue breakdown")
    print("=" * 60)
    result = edgar_extract_section("AAPL", "Segment_Revenue", "latest")
    print(json.dumps(result, indent=2))
