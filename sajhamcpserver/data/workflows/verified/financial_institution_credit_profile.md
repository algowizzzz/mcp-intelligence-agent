# Workflow: Financial Institution Credit Profile

## Pulls EDGAR financials, key ratios, IR earnings commentary, and market news for any public financial institution. Produces a 2-page analyst credit note.

## Inputs:
- company_name: Full company name e.g. JPMorgan Chase (required)
- ticker: Stock ticker e.g. JPM (required)
- fiscal_year: Four-digit year e.g. 2024 (optional — defaults to latest)
- peer_tickers: Comma-separated peer tickers for comparison e.g. BAC,C,WFC (optional)

## Step 1 — Data Pull (all in parallel)

```
tool: edgar_find_filing
params: { "company_name": "{company_name}", "filing_type": "10-K", "year": "{fiscal_year}" }
```

```
tool: tavily_yahoo_get_quote
params: { "ticker": "{ticker}" }
```

```
tool: tavily_news_search
params: { "query": "{company_name} earnings credit quality capital ratio {fiscal_year}", "max_results": 5 }
```

```
tool: ir_get_latest_earnings
params: { "company_name": "{company_name}" }
```

## Step 2 — Financials & Ratios (parallel, using filing accession from Step 1)

```
tool: edgar_get_statements
params: { "accession_number": "{accession}", "statement_type": "income" }
```

```
tool: edgar_calculate_ratios
params: { "accession_number": "{accession}" }
```

```
tool: edgar_risk_summary
params: { "accession_number": "{accession}" }
```

If peer_tickers provided:
```
tool: edgar_peer_comparison
params: { "ticker": "{ticker}", "peers": "{peer_tickers}", "year": "{fiscal_year}" }
```

## Step 3 — Credit Note

Write in exactly this format. Every metric must reference a tool result. Under 400 words.

---
**CREDIT PROFILE NOTE**
**{company_name}** ({ticker}) | FY{fiscal_year} | Credit Intelligence Agent

**SIGNAL:** INVESTMENT GRADE / WATCH / DISTRESSED

| Metric | Value | YoY |
|--------|-------|-----|
| Revenue | | |
| Net Income | | |
| CET1 / Tier 1 Capital | | |
| ROE | | |
| NIM | | |
| NPL Ratio | | |
| Market Cap | | |
| P/B | | |

**CREDIT STRENGTHS** (max 3 bullets — 1 data point each)
**CREDIT CONCERNS** (max 3 bullets — 1 data point each)

**PEER POSITION** [Only if peers provided: 1 sentence on where company ranks vs peers on key ratio]

**KEY RISK FACTORS** [Top 2 from EDGAR risk summary — 1 line each]

**EARNINGS COMMENTARY** [1 sentence from IR tool on management tone]

**MARKET SIGNAL** [{ticker} price, 52w range, analyst consensus if available]

**RECOMMENDATION**
[Hold / Reduce / Watch] — [1 sentence rationale with data]

---

Save with:
```
tool: md_save
params: { "content": "{note}", "filename": "credit_profile_{ticker}_{fiscal_year}.md", "subfolder": "credit_notes" }
```

## Notes for Agent
- Steps 1 and 2 are sequential (need accession from Step 1). Within each step, all calls parallel.
- If 10-K not found, fall back to 10-Q. If EDGAR returns no data for Canadian firms, note they file 6-K and use IR tools instead.
- Do not hallucinate financial metrics — only report what tool results return.
- Wrap final output in canvas mode.
