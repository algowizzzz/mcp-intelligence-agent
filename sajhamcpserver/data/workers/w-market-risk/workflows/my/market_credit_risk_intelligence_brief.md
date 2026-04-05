---
name: Market & Credit Risk Intelligence Brief
description: Parallel domain news searches across Bloomberg, Reuters and ratings agencies to produce a per-counterparty signal brief (GREEN/AMBER/RED) and portfolio risk dashboard.
inputs: Comma-separated list of counterparty names
tags: [market-risk, credit-risk, tavily, news, portfolio]
version: "1.0"
---

# **WORKFLOW: Market & Credit Risk Intelligence Brief**
## *For Capital Markets Team — BMO*
---
## **WORKFLOW OVERVIEW**
**Purpose:** Fetch latest market and credit risk intelligence for counterparty list from trusted financial domains (Bloomberg, WSJ, Reuters, FT, S&P Global, Moody's, Fitch) and compile a concise one-page brief per counterparty + portfolio summary.
**Output Format:**
- **Per Counterparty:** 1-paragraph risk summary + 3-5 key links
- **Portfolio Summary:** 1-page high-level risk dashboard
- **Total Length:** 1 page per counterparty + 1 portfolio page (no verbosity)
**Audience:** Market Risk & Credit Risk Officers, Capital Markets Team
---
## **STEP 1 — USER INPUT**
**User provides:** List of counterparty names (comma-separated or line-separated)
**Example:**
```
JP Morgan, Goldman Sachs, Bank of America, RBC, TD Bank
```
**Agent validates:** Confirm counterparty count and proceed.
---
## **STEP 2 — PARALLEL NEWS SEARCHES** *(Execute for each counterparty)*

**Primary tool: `tavily_news_search`** — use this for all 4 queries. Do NOT use `tavily_domain_search` with Bloomberg, WSJ, FT, or S&P as `include_domains` — those sites are paywalled and Tavily cannot index them directly, resulting in zero results. `tavily_news_search` queries Tavily's pre-built financial news index which contains content from all major financial publications including Bloomberg, Reuters, FT, and ratings agencies.

For **each counterparty**, call `tavily_news_search` in parallel with these 4 queries:

### **Query 1: Credit Risk & Ratings**
```
tool: tavily_news_search
query: "{counterparty_name} credit rating downgrade outlook S&P Moody's Fitch 2026"
max_results: 3
```
### **Query 2: Market Risk & Earnings**
```
tool: tavily_news_search
query: "{counterparty_name} earnings guidance capital markets revenue outlook 2026"
max_results: 3
```
### **Query 3: Regulatory & Compliance**
```
tool: tavily_news_search
query: "{counterparty_name} regulatory capital stress test compliance Basel 2026"
max_results: 2
```
### **Query 4: Liquidity & Funding**
```
tool: tavily_news_search
query: "{counterparty_name} liquidity funding debt issuance bond spreads 2026"
max_results: 2
```

**Supplementary (optional):** If news search returns fewer than 2 results for Query 1, also call `tavily_domain_search` with:
```
query: "{counterparty_name} credit rating 2026"
include_domains: [reuters.com, marketwatch.com, cnbc.com]
max_results: 3
```
Reuters, MarketWatch, and CNBC are publicly indexed and serve as reliable fallback sources.

**Fallback:** If fewer than 2 results found across all tools for a query, note "Limited public information available" and move to next counterparty.
---
## **STEP 3 — DATA EXTRACTION & CLASSIFICATION**
For each counterparty, extract:
| Field | Source | Classification |
|-------|--------|-----------------|
| **Credit Signal** | Ratings domains | GREEN / AMBER / RED |
| **Market Signal** | Bloomberg, WSJ, Reuters | POSITIVE / NEUTRAL / NEGATIVE |
| **Regulatory Signal** | Regulatory news | COMPLIANT / WATCH / CONCERN |
| **Liquidity Signal** | Funding news | STRONG / ADEQUATE / TIGHT |
| **Key Links** | All sources | URL + headline |
**Signal Rules:**
- **GREEN:** No downgrades, positive earnings, strong capital, ample liquidity
- **AMBER:** Stable outlook, mixed signals, or watch-list placement
- **RED:** Downgrade, negative guidance, capital concerns, or liquidity stress
---
## **STEP 4 — PER-COUNTERPARTY BRIEF** *(Max 1 paragraph + links)*
**Format:**
```
COUNTERPARTY: [Name]
INTERNAL RATING: [if available from IRIS]
OVERALL SIGNAL: [GREEN / AMBER / RED]
SUMMARY:
[1 paragraph max — 3-4 sentences covering credit, market, regulatory, liquidity]
KEY LINKS:
1. [Headline] — [Domain] — [URL]
2. [Headline] — [Domain] — [URL]
3. [Headline] — [Domain] — [URL]
4. [Headline] — [Domain] — [URL]
5. [Headline] — [Domain] — [URL]
INFO STATUS: ✓ Complete / ⚠ Limited / ✗ Not Found
```
---
## **STEP 5 — PORTFOLIO SUMMARY** *(1 page)*
**Format:**
```
PORTFOLIO RISK DASHBOARD — [Date]
COUNTERPARTY RISK MATRIX:
| Counterparty | Credit Signal | Market Signal | Regulatory | Liquidity | Overall |
|--------------|---------------|---------------|-----------|-----------|---------|
| JPM          | GREEN         | POSITIVE      | COMPLIANT | STRONG    | GREEN   |
| GS           | AMBER         | NEUTRAL       | WATCH     | ADEQUATE  | AMBER   |
| BAC          | AMBER         | NEGATIVE      | COMPLIANT | ADEQUATE  | AMBER   |
| RBC          | GREEN         | POSITIVE      | COMPLIANT | STRONG    | GREEN   |
| TD           | GREEN         | NEUTRAL       | COMPLIANT | STRONG    | GREEN   |
KEY FINDINGS (Bullet points):
• [Finding 1 — reference counterparty + signal]
• [Finding 2 — reference counterparty + signal]
• [Finding 3 — reference counterparty + signal]
• [Finding 4 — reference counterparty + signal]
RISK CONCENTRATION:
- [X counterparties in GREEN]
- [Y counterparties in AMBER]
- [Z counterparties in RED]
RECOMMENDED ACTIONS:
Priority 1 (Immediate): [Action for RED-flagged counterparties]
Priority 2 (This week): [Action for AMBER-flagged counterparties]
Priority 3 (Monitor): [Action for GREEN counterparties]
PREPARED BY: Market & Credit Risk Intelligence Agent | [Date]
```
---
## **STEP 6 — EXECUTION RULES**
### **Parallelization:**
- Execute all 4 domain searches **in parallel** for each counterparty
- Execute all counterparties **in parallel** (no sequential delays)
### **Data Quality:**
- **Only use URLs from trusted domains** (Bloomberg, WSJ, Reuters, FT, S&P, Moody's, Fitch)
- **Discard generic/irrelevant results** (e.g., unrelated company news)
- **Flag missing data:** If <2 results found for a query, note "Limited information"
### **Brevity:**
- **No paragraphs >4 sentences**
- **No bullet points >1 line**
- **No redundant information**
- **Links only — no content excerpts**
### **Timing:**
- Fetch latest news (last 7-30 days)
- Use most recent snapshot date from IRIS (if available)
- Timestamp all outputs
---
## **STEP 7 — OUTPUT DELIVERY**
**Format:** Canvas mode (structured report)
**Structure:**
```
1. Portfolio Summary (1 page)
2. Per-Counterparty Briefs (1 page each)
3. Appendix: All URLs with publication dates
```
**File naming:** `BMO_CCR_Brief_[Date]_[Counterparty_Count]CP.md`
---
## **EXAMPLE INVOCATION**
**User says:**
```
"Create a market and credit risk brief for: JP Morgan, Goldman Sachs, Bank of America"
```
**Agent responds:**
```
Executing workflow for 3 counterparties...
Step 1: Validating input ✓
Step 2: Fetching domain intelligence (parallel) ✓
Step 3: Classifying signals ✓
Step 4: Compiling per-counterparty briefs ✓
Step 5: Building portfolio summary ✓
Step 6: Generating report ✓
[Canvas output with portfolio summary + 3 briefs]
```
---
## **TOOL MAPPING**
| Step | Tool | Parameters |
|------|------|-----------|
| 2 (primary) | `tavily_news_search` | query, max_results |
| 2 (fallback) | `tavily_domain_search` | query, include_domains=[reuters.com, marketwatch.com, cnbc.com], max_results |
| 3 | Manual classification | Signal rules (GREEN/AMBER/RED) |
| 4 | Manual formatting | Per-counterparty template |
| 5 | Manual aggregation | Portfolio matrix + summary |
| 6 | Canvas output | Structured markdown report |
---
## **NOTES FOR AGENT**
1. **Do NOT call IRIS tools** — focus on public domain intelligence only
2. **Do NOT include internal ratings** unless explicitly available from IRIS search
3. **Do NOT synthesize opinions** — report facts + links only
4. **Do NOT exceed 1 page per counterparty** — ruthlessly edit
5. **Do NOT include company descriptions** — assume audience knows the counterparties
6. **Do flag data gaps** — "Limited information available" is acceptable
7. **Timestamp everything** — include publication dates on all links
---
## **SUCCESS CRITERIA**
✓ All counterparties covered
✓ All signals classified (GREEN/AMBER/RED)
✓ All links sourced from trusted domains
✓ Portfolio summary on 1 page
✓ Per-counterparty briefs on 1 page each
✓ No verbosity, no fluff
✓ Ready for Capital Markets team review
---
**Ready to execute. Provide counterparty list.**
