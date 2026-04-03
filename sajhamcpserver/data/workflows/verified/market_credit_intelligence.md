# Workflow: Market & Credit Intelligence Brief

## Combines live market data, news, and EDGAR financials to produce a 1-2 page sector or single-name credit and market intelligence brief for a CCR or financial analyst.

## Inputs:
- ticker: Primary stock ticker e.g. "TD" or "GS" (required)
- company_name: Full company name e.g. "The Toronto-Dominion Bank" (required)
- sector: Sector for peer context e.g. "Canadian Banks" or "US Investment Banks" (optional)
- peer_tickers: Comma-separated peer tickers e.g. "BNS,RY,BMO" (optional)
- horizon: Forward horizon for risk view e.g. "3M" or "12M" (optional — default "3M")

## Step 1 — Market & News Pulse (all parallel)

```
tool: tavily_yahoo_get_quote
params: { "ticker": "{ticker}" }
```

```
tool: tavily_yahoo_get_history
params: { "ticker": "{ticker}", "period": "6mo", "interval": "1mo" }
```

```
tool: tavily_news_search
params: { "query": "{company_name} credit outlook earnings capital {horizon}", "max_results": 5 }
```

```
tool: tavily_research_search
params: { "query": "{sector} credit risk outlook {horizon} analyst view", "max_results": 3 }
```

If peer_tickers provided, also in parallel:
```
tool: tavily_yahoo_get_quote
params: { "ticker": "{peer_ticker_1}" }
```
[repeat for each peer, max 3 peers]

## Step 2 — Fundamental Check (parallel)

```
tool: edgar_find_filing
params: { "company_name": "{company_name}", "filing_type": "10-K", "year": "latest" }
```

```
tool: ir_get_latest_earnings
params: { "company_name": "{company_name}" }
```

## Step 3 — Financials (parallel, using accession from Step 2 if found)

If EDGAR filing found:
```
tool: edgar_calculate_ratios
params: { "accession_number": "{accession}" }
```

```
tool: edgar_risk_summary
params: { "accession_number": "{accession}" }
```

## Step 4 — Price Chart (after Step 1)

```
tool: generate_chart
params: {
  "data": "{price_history_rows}",
  "chart_type": "line",
  "x": "date",
  "y": "close",
  "title": "{ticker} — 6-Month Price History",
  "theme": "riskgpt",
  "save_png": true
}
```

## Step 5 — Intelligence Brief

Determine overall credit and market signal:
- CONSTRUCTIVE: Stable/improving fundamentals, positive market momentum, no material news risk
- NEUTRAL: Mixed signals — some credit concerns offset by market resilience or vice versa
- CAUTIOUS: Deteriorating ratios, negative news flow, widening credit spreads or price weakness
- NEGATIVE: Multiple concurrent risk factors — fundamental, market, and news all negative

Write in exactly this format. Under 400 words.

---
**MARKET & CREDIT INTELLIGENCE BRIEF**
**{company_name}** ({ticker}) | Horizon: {horizon} | {today}

**SIGNAL:** CONSTRUCTIVE / NEUTRAL / CAUTIOUS / NEGATIVE

**MARKET SNAPSHOT**
| Metric | Value |
|--------|-------|
| Current Price | |
| 52-Week Range | |
| 6M Price Change | |
| Market Cap | |
| P/B Ratio | |
| Analyst Consensus | |

**CREDIT FUNDAMENTALS** (from latest filing — state period)
| Ratio | Value | Assessment |
|-------|-------|------------|
| CET1 / Tier 1 Capital | | |
| ROE | | |
| NIM / ROAA | | |
| NPL / Loan Loss Ratio | | |

**PEER POSITION** [Only if peers provided]
| Name | Price 6M Chg | Key Ratio | vs {ticker} |
|------|-------------|-----------|-------------|
[one row per peer]

**NEWS & SENTIMENT** (last 30 days)
- [Top news item 1 — source — date — credit/market implication]
- [Top news item 2 — source — date — credit/market implication]
- [Sector theme from research search — 1 sentence]

**KEY RISKS** [Top 2 from EDGAR risk summary or news — 1 line each]

**EARNINGS COMMENTARY** [1 sentence from IR tool on management tone and guidance]

**ANALYST VIEW**
[CONSTRUCTIVE / CAUTIOUS / NEGATIVE] on {horizon} horizon — [2 sentences: primary reason + key watchpoint]

---

Save with:
```
tool: md_save
params: { "content": "{brief}", "filename": "mci_{ticker}_{today}.md", "subfolder": "reports" }
```

## Notes for Agent
- Steps 1 and 2 run in parallel. Step 3 depends on Step 2 (need accession). Step 4 depends on Step 1 (need price history). Step 5 is LLM-only synthesis.
- Canadian banks (TD, BNS, RY, BMO, CM) file 6-K on EDGAR — if 10-K not found, use IR tools only and note this in the brief.
- For tickers without EDGAR filings, skip Step 3 and mark credit fundamentals as "N/A — IR data only."
- Do not extrapolate or interpolate financial metrics. Only report what tool results return.
- Wrap final output in canvas mode.
