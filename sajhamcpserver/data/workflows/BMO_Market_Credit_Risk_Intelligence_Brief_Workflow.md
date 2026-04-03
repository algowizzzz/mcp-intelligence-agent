# BMO Capital Markets — Market & Credit Risk Intelligence Brief
## Workflow Specification

*Version 1.0 · April 2026 · MCP Agent Workflow*
*Audience: Market Risk Officers · Credit Risk Officers · Capital Markets Team*

---

## Workflow Overview

| Property | Specification |
|---|---|
| **Purpose** | Fetch latest market and credit risk intelligence for a counterparty list from trusted financial domains and compile a concise brief per counterparty plus a portfolio-level summary. |
| **Trusted domains** | Bloomberg, WSJ, Reuters, FT, S&P Global, Moody's, Fitch Ratings |
| **Output — per counterparty** | 1-paragraph risk summary + 3–5 key links. Maximum 1 page. |
| **Output — portfolio summary** | 1-page risk dashboard with signal matrix, key findings, concentration breakdown, and recommended actions. |
| **Audience** | Market Risk Officers, Credit Risk Officers, Capital Markets Team |
| **Delivery** | Canvas mode — structured markdown report |
| **File naming** | `BMO_CCR_Brief_[Date]_[N]CP.md` |
| **MCP tools used** | `tavily_domain_search` (Step 2), `iris_search_counterparties` (optional Step 4) |

---

## Step 1 — User Input

The user provides a list of counterparty names, comma-separated or line-separated. The agent validates the count and confirms before proceeding.

```
Example input:
JP Morgan, Goldman Sachs, Bank of America, RBC, TD Bank

Agent response:
Confirmed — 5 counterparties. Proceeding with parallel domain searches.
```

---

## Step 2 — Parallel Domain Searches

For each counterparty, execute 4 `tavily_domain_search` calls in parallel. All counterparties are also processed in parallel — no sequential delays.

| # | Topic | Query string | Domains | Max results |
|---|---|---|---|---|
| Query 1 | Credit Risk & Ratings | `"{counterparty} credit rating downgrade default risk 2026"` | spglobal.com, fitchratings.com, moodys.com | 3 |
| Query 2 | Market Risk & Earnings | `"{counterparty} earnings guidance capital markets outlook 2026"` | bloomberg.com, wsj.com, reuters.com, ft.com | 3 |
| Query 3 | Regulatory & Compliance | `"{counterparty} regulatory capital stress test compliance 2026"` | bloomberg.com, reuters.com, ft.com | 2 |
| Query 4 | Liquidity & Funding | `"{counterparty} liquidity funding debt issuance 2026"` | bloomberg.com, wsj.com, reuters.com | 2 |

**Fallback:** If no results are found for any query, note "Limited public information available" and continue to next counterparty.

---

## Step 3 — Data Extraction & Signal Classification

For each counterparty, extract and classify four signals from the search results:

| Signal | Source domains | Values | Classification rule |
|---|---|---|---|
| **Credit Signal** | S&P, Fitch, Moody's | GREEN / AMBER / RED | GREEN = no downgrade, stable/positive outlook. AMBER = watch-list or mixed signals. RED = downgrade, negative outlook, or default risk elevated. |
| **Market Signal** | Bloomberg, WSJ, Reuters, FT | POSITIVE / NEUTRAL / NEGATIVE | POSITIVE = beat estimates, raised guidance. NEUTRAL = in-line, no major news. NEGATIVE = missed, lowered guidance, or macro headwinds cited. |
| **Regulatory Signal** | Bloomberg, Reuters, FT | COMPLIANT / WATCH / CONCERN | COMPLIANT = no regulatory action. WATCH = under review, pending stress test. CONCERN = enforcement action, capital shortfall, or remediation order. |
| **Liquidity Signal** | Bloomberg, WSJ, Reuters | STRONG / ADEQUATE / TIGHT | STRONG = ample liquidity, active issuance at favourable spreads. ADEQUATE = normal conditions. TIGHT = spread widening, constrained issuance, or liquidity facility drawdowns. |

**Overall signal:** Take the worst signal across all four dimensions. One RED dimension = RED overall. All GREEN = GREEN overall.

---

## Step 4 — Per-Counterparty Brief

Compile one brief per counterparty using the template below. Maximum 1 paragraph (3–4 sentences). Links only — no content excerpts.

```
COUNTERPARTY: [Name]
INTERNAL RATING: [from IRIS if available — omit if not]
OVERALL SIGNAL: [GREEN / AMBER / RED]

SUMMARY:
[1 paragraph, max 4 sentences — credit, market, regulatory, liquidity]

KEY LINKS:
1. [Headline] — [Domain] — [URL] — [Publication date]
2. [Headline] — [Domain] — [URL] — [Publication date]
3. [Headline] — [Domain] — [URL] — [Publication date]
4. [Headline] — [Domain] — [URL] — [Publication date]
5. [Headline] — [Domain] — [URL] — [Publication date]

INFO STATUS: ✓ Complete / ⚠ Limited / ✗ Not Found
```

---

## Step 5 — Portfolio Summary

Aggregate all counterparty signals into a one-page portfolio risk dashboard.

```
PORTFOLIO RISK DASHBOARD — [Date]

COUNTERPARTY RISK MATRIX:
| Counterparty | Credit | Market   | Regulatory | Liquidity | Overall |
|--------------|--------|----------|------------|-----------|---------|
| JPM          | GREEN  | POSITIVE | COMPLIANT  | STRONG    | GREEN   |
| GS           | AMBER  | NEUTRAL  | WATCH      | ADEQUATE  | AMBER   |
| BAC          | AMBER  | NEGATIVE | COMPLIANT  | ADEQUATE  | AMBER   |
| RBC          | GREEN  | POSITIVE | COMPLIANT  | STRONG    | GREEN   |
| TD           | GREEN  | NEUTRAL  | COMPLIANT  | STRONG    | GREEN   |

KEY FINDINGS:
• [Finding 1 — reference counterparty + signal]
• [Finding 2 — reference counterparty + signal]
• [Finding 3 — reference counterparty + signal]
• [Finding 4 — reference counterparty + signal]

RISK CONCENTRATION:
- [X] counterparties GREEN
- [Y] counterparties AMBER
- [Z] counterparties RED

RECOMMENDED ACTIONS:
Priority 1 (Immediate): [Action for RED-flagged counterparties]
Priority 2 (This week): [Action for AMBER-flagged counterparties]
Priority 3 (Monitor):   [Action for GREEN counterparties]

PREPARED BY: Market & Credit Risk Intelligence Agent | [Date]
```

---

## Step 6 — Execution Rules

| Rule | Specification |
|---|---|
| **Parallelization** | Execute all 4 domain searches in parallel per counterparty. Execute all counterparties in parallel. No sequential delays. |
| **Source trust** | Only use URLs from: bloomberg.com, wsj.com, reuters.com, ft.com, spglobal.com, fitchratings.com, moodys.com. Discard all other domains. |
| **Missing data** | If fewer than 2 results returned for a query, flag "Limited information" for that signal dimension. |
| **Brevity** | No paragraph >4 sentences. No bullet point >1 line. No redundant information. Links only — no content excerpts. |
| **Recency** | Fetch latest news from last 7–30 days. Timestamp all links with publication date. |
| **No opinion** | Report facts and links only. Do not synthesize opinions or draw forward-looking conclusions beyond what sources state. |
| **No descriptions** | Do not include company background or descriptions. Assume audience knows the counterparties. |

---

## Step 7 — Output Delivery

| Property | Specification |
|---|---|
| **Mode** | Canvas output (structured markdown report) |
| **Structure** | 1. Portfolio Summary (1 page) · 2. Per-Counterparty Briefs (1 page each) · 3. Appendix: all URLs with publication dates |
| **File naming** | `BMO_CCR_Brief_[YYYY-MM-DD]_[N]CP.md` e.g. `BMO_CCR_Brief_2026-04-01_5CP.md` |

---

## Tool Mapping

| Step | Tool | Parameters | Notes |
|---|---|---|---|
| 2 | `tavily_domain_search` | query, include_domains, max_results | 4 calls per counterparty, all parallel |
| 4 (optional) | `iris_search_counterparties` | counterparty_name | Fetch internal rating only if available; omit if not found |
| 3, 4, 5 | *(LLM)* | Signal rules (GREEN/AMBER/RED) | Classification and formatting — no additional tool calls |
| 7 | Canvas output | Structured markdown | Report rendered directly in canvas panel |

---

## Agent Constraints

1. Do NOT call IRIS tools proactively — only call `iris_search_counterparties` if the user explicitly requests internal ratings.
2. Do NOT synthesize opinions — report facts and source links only.
3. Do NOT exceed 1 page per counterparty — ruthlessly edit.
4. Do NOT include company background descriptions.
5. Do flag data gaps — "Limited information available" is an acceptable and expected output.
6. Timestamp everything — include publication dates on all links.
7. Only use URLs from the trusted domain list — discard all others silently.

---

## Example Invocation

**User input:**
```
"Create a market and credit risk brief for: JP Morgan, Goldman Sachs, Bank of America"
```

**Agent execution log:**
```
Executing workflow for 3 counterparties...
Step 1: Input validated — 3 counterparties confirmed ✓
Step 2: Launching 12 parallel domain searches (4 queries × 3 counterparties) ✓
Step 3: Classifying signals for JPM, GS, BAC ✓
Step 4: Compiling per-counterparty briefs ✓
Step 5: Building portfolio summary ✓
Step 6: Rules check — all links from trusted domains, timestamps present ✓
Step 7: Generating canvas output → BMO_CCR_Brief_2026-04-01_3CP.md ✓
```

---

## Success Criteria

| # | Criterion | Pass condition |
|---|---|---|
| SC-01 | Coverage | All counterparties in the input list have a brief. |
| SC-02 | Signal completeness | All four signals (Credit, Market, Regulatory, Liquidity) classified for each counterparty. |
| SC-03 | Source trust | Every URL in the output is from one of the 7 trusted domains. |
| SC-04 | Brevity | No counterparty brief exceeds 1 page (4 sentences + 5 links). |
| SC-05 | Portfolio summary | Portfolio summary fits on 1 page — matrix + findings + concentration + actions. |
| SC-06 | Timestamps | Every link includes a publication date. |
| SC-07 | No verbosity | No company descriptions, no background paragraphs, no opinion text. |
| SC-08 | Data gap flagging | Any signal with <2 sources shows "Limited information" rather than a fabricated classification. |

---

*Confidential · BMO Capital Markets · Market & Credit Risk Intelligence Agent*
