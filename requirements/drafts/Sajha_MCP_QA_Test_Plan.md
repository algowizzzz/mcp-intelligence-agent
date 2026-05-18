# SAJHA MCP SERVER

> **Source:** Converted from `Sajha_MCP_QA_Test_Plan.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**SAJHA MCP SERVER**

**QA Test Plan & Tool Acceptance Criteria**

Version 1.0 \| March 2026 \| Confidential

|                |                                     |
|----------------|-------------------------------------|
| **Attribute**  | **Value**                           |
| Document Owner | Sajha Engineering / QA              |
| Scope          | All active MCP tools (post-cleanup) |
| Tool Count     | ~76 tools across 8 categories       |
| Environment    | Staging → Production                |

**1. Overview**

This document defines acceptance test cases for every active tool in the Sajha MCP Server. Each tool must pass all Happy Path tests before being declared production-ready. Edge and Negative tests must be acknowledged (pass or documented waiver).

**1.1 Test Type Legend**

|  |  |
|----|----|
| **Type** | **Definition** |
| Happy Path | Canonical valid input. Tool must return correct, well-formed output. |
| Edge Case | Valid but unusual input (e.g., maximum limits, special characters, zero results). |
| Negative | Invalid or missing input. Tool must return a descriptive error, not crash. |
| Boundary | Input at schema minimum/maximum. Tool must honour declared schema limits. |

**1.2 Universal Pass Criteria**

All tools must additionally satisfy the following regardless of test type:

• Response time \< 30 seconds for external API tools; \< 2 seconds for in-memory/data tools.

• Output is valid JSON conforming to the declared outputSchema.

• No unhandled Python exceptions are surfaced to the caller.

• Errors return a JSON object with at minimum: { "error": "...", "success": false }.

• Disabled tools (yahoo_get_quote.json.disabled etc.) must not appear in the tool list.

**SECTION 2 — SEC / EDGAR Tools**

**2.1 SEC Abstracted Layer (7 tools)**

These tools wrap the raw EDGAR REST API with a simplified interface. They share the base URL data.sec.gov and require no API key.

**TC-SEC-001 — sec_search_company**

Search SEC EDGAR by company name or ticker. Returns CIK, ticker, exchange.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SEC-001-01 | Happy Path | Search by well-known ticker | search_term: "AAPL" | result_count \>= 1; company with ticker "AAPL" and cik present | **cik is 10-digit string** |
| TC-SEC-001-02 | Happy Path | Search by company name | search_term: "Microsoft" | result_count \>= 1; name contains "Microsoft" | **cik non-empty** |
| TC-SEC-001-03 | Edge Case | Search with limit = 1 | search_term: "Apple", limit: 1 | companies array length === 1 | **Limit honoured exactly** |
| TC-SEC-001-04 | Boundary | Max limit = 100 | search_term: "Bank", limit: 100 | companies.length \<= 100 | **No schema violation** |
| TC-SEC-001-05 | Negative | Empty search term | search_term: "" | error or result_count === 0 | **No unhandled exception** |
| TC-SEC-001-06 | Negative | Missing required field | (no search_term) | { "success": false, "error": "..." } | **Graceful error message** |

**TC-SEC-002 — sec_get_company_info**

Retrieve basic company metadata (name, SIC, state, fiscal year end) for a given CIK.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SEC-002-01 | Happy Path | Known CIK — Apple | cik: "320193" | entityName: "Apple Inc.", sic, stateOfIncorporation present | **All required output fields non-null** |
| TC-SEC-002-02 | Happy Path | CIK with leading zeros | cik: "0000320193" | Same response as short CIK | **CIK normalisation works** |
| TC-SEC-002-03 | Edge Case | Small company CIK | cik: "1090872" | Valid company record returned | **Works for non-mega-caps** |
| TC-SEC-002-04 | Negative | Non-existent CIK | cik: "9999999999" | error or empty result | **No crash; clear error message** |
| TC-SEC-002-05 | Negative | Non-numeric CIK | cik: "INVALID" | { "success": false, "error": "..." } | **Validation error returned** |

**TC-SEC-003 — sec_get_company_filings**

List all SEC filings for a company with form type, date, and accession number.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SEC-003-01 | Happy Path | Get Apple filings | cik: "320193" | filings array with accessionNumber, form, filingDate | **At least 1 filing returned** |
| TC-SEC-003-02 | Happy Path | Filter by form type 10-K | cik: "320193", form_type: "10-K" | All items in filings have form === "10-K" | **Form filter applied correctly** |
| TC-SEC-003-03 | Edge Case | Company with few filings (new issuer) | cik: "1702780" | filings array (may be small) | **Empty array acceptable, no crash** |
| TC-SEC-003-04 | Negative | Invalid form type | cik: "320193", form_type: "XXXX" | empty filings or error | **No crash** |

**TC-SEC-004 — sec_get_company_facts**

Return all XBRL-tagged financial facts for a company (all periods, all concepts).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SEC-004-01 | Happy Path | Apple full XBRL facts | cik: "320193" | facts object with us-gaap taxonomy; entityName present | **facts_count \> 100** |
| TC-SEC-004-02 | Happy Path | Foreign filer (IFRS) | cik: "1067983" (Berkshire) | facts with dei taxonomy present | **taxonomies array non-empty** |
| TC-SEC-004-03 | Edge Case | Company with minimal XBRL history | recent small-cap CIK | Valid response, possibly small facts object | **No crash; facts may be sparse** |
| TC-SEC-004-04 | Negative | Invalid CIK | cik: "0" | error response | **Descriptive error, no exception** |

**TC-SEC-005 — sec_get_financial_data**

Retrieve structured financial statement data (revenue, net income, EPS, etc.) for a given company and concept.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SEC-005-01 | Happy Path | Revenue for Apple | cik: "320193", concept: "Revenues" | time-series values with dates and units | **values array non-empty; unit is USD** |
| TC-SEC-005-02 | Happy Path | EPS concept | cik: "320193", concept: "EarningsPerShareBasic" | numeric values returned | **Values present for multiple periods** |
| TC-SEC-005-03 | Edge Case | Concept not reported by company | cik: "320193", concept: "MineralRights" | empty values or error | **Handled gracefully** |
| TC-SEC-005-04 | Negative | Missing concept param | cik: "320193" | error message | **Schema validation triggered** |

**TC-SEC-006 — sec_get_insider_trading**

Return Form 4 insider buy/sell transactions for a company (via SEC abstracted layer).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SEC-006-01 | Happy Path | Apple insider trades | cik: "320193" | transactions array with filingDate, type, shares | **At least 1 transaction returned** |
| TC-SEC-006-02 | Happy Path | Tesla trades | cik: "1318605" | Multiple Form 4 entries | **transactions_count \> 0** |
| TC-SEC-006-03 | Edge Case | Limit = 1 | cik: "320193", limit: 1 | Exactly 1 transaction | **limit honoured** |
| TC-SEC-006-04 | Negative | Invalid CIK | cik: "abc" | error response | **No crash** |

**TC-SEC-007 — sec_get_mutual_fund_holdings**

Retrieve mutual fund / institutional 13F holdings for a given CIK.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SEC-007-01 | Happy Path | Known fund CIK | cik: "102909" (Vanguard) | holdings array with issuer name and value | **holdings non-empty** |
| TC-SEC-007-02 | Edge Case | Company CIK (not a fund) | cik: "320193" | empty holdings or error | **Handled without crash** |
| TC-SEC-007-03 | Negative | Null CIK | cik: null | error | **Validation error message** |

**2.2 EDGAR Enhanced Layer (20 tools)**

These tools call the EDGAR REST API directly and return raw structured data. Key reference companies: Apple CIK 320193, Microsoft CIK 789019, Tesla CIK 1318605.

**TC-EDGAR-001 — edgar_company_search**

Search EDGAR company database. Has search_type enum: name / ticker / auto.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-001-01 | Happy Path | Ticker search AAPL | query: "AAPL", search_type: "ticker" | companies contains item with cik "0000320193" | **Correct CIK returned** |
| TC-EDGAR-001-02 | Happy Path | Name search Microsoft | query: "Microsoft", search_type: "name", limit: 5 | companies.length \<= 5; title includes "Microsoft" | **Name match; limit honoured** |
| TC-EDGAR-001-03 | Happy Path | Auto mode ambiguous query | query: "TSLA", search_type: "auto" | Tesla in results | **results_count \>= 1** |
| TC-EDGAR-001-04 | Edge Case | Partial name match | query: "Gold" | Multiple companies matching "Gold" | **results_count \> 1** |
| TC-EDGAR-001-05 | Negative | Empty query string | query: "" | error or results_count === 0 | **No crash** |

**TC-EDGAR-002 — edgar_company_submissions**

Return all submission metadata for a company — filing history, forms, dates.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-002-01 | Happy Path | Apple submissions | cik: "320193" | cik, name, sic, filings object present | **filings.recent non-empty** |
| TC-EDGAR-002-02 | Edge Case | Large filer pagination | cik: "320193" | paginated filings handled | **No truncation error** |
| TC-EDGAR-002-03 | Negative | Bad CIK format | cik: "!!!" | error response | **Descriptive error** |

**TC-EDGAR-003 — edgar_company_facts**

Return all XBRL financial facts for a company (enhanced layer).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-003-01 | Happy Path | Apple XBRL facts | cik: "320193" | entityName, facts with us-gaap, facts_count \> 50 | **Taxonomies array non-empty** |
| TC-EDGAR-003-02 | Edge Case | Foreign private issuer | cik: "1800227" (Alibaba) | ifrs-full taxonomy may be present | **No crash; handles IFRS** |
| TC-EDGAR-003-03 | Negative | CIK with no XBRL filings | cik: "0000001" | empty facts or error | **Graceful empty response** |

**TC-EDGAR-004 — edgar_company_concept**

Return time-series data for one specific XBRL concept (e.g. Revenues) for a company.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-004-01 | Happy Path | Apple revenues US-GAAP | cik: "320193", taxonomy: "us-gaap", concept: "Revenues" | units.USD array with val and end dates | **Multiple period values present** |
| TC-EDGAR-004-02 | Happy Path | Quarterly vs annual filter | cik: "320193", taxonomy: "us-gaap", concept: "NetIncomeLoss" | Data for 10-K and 10-Q periods | **Different form types in result** |
| TC-EDGAR-004-03 | Edge Case | Concept not in taxonomy | cik: "320193", taxonomy: "us-gaap", concept: "FakeConceptXYZ" | empty or 404-style error | **No crash** |
| TC-EDGAR-004-04 | Negative | Missing taxonomy param | cik: "320193", concept: "Revenues" | error | **Required param validation** |

**TC-EDGAR-005 — edgar_filing_details**

Retrieve documents list for a specific filing using accession number.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-005-01 | Happy Path | Valid accession number | cik: "320193", accession_number: "0000320193-23-000077" | documents array with filename, type | **Primary document URL accessible** |
| TC-EDGAR-005-02 | Negative | Malformed accession number | accession_number: "NOT-VALID" | error response | **No crash** |

**TC-EDGAR-006 — edgar_filings_by_form**

Return all filings of a specific form type across companies (EDGAR full-text search endpoint).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-006-01 | Happy Path | 10-K filings for Apple | cik: "320193", form_type: "10-K" | filings array with only form === "10-K" | **All items match form_type** |
| TC-EDGAR-006-02 | Happy Path | 8-K current reports | cik: "320193", form_type: "8-K" | Multiple 8-K filings | **filings non-empty** |
| TC-EDGAR-006-03 | Negative | Unknown form type | form_type: "99-X" | empty or error | **No crash** |

**TC-EDGAR-007 — edgar_current_reports**

Get the most recent 8-K and NT filings (current event reports) for a company.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-007-01 | Happy Path | Recent 8-Ks for Microsoft | cik: "789019" | filings array with form 8-K and filing dates | **At least 1 recent 8-K** |
| TC-EDGAR-007-02 | Edge Case | Company with no recent 8-Ks | small-cap CIK | empty array or minimal results | **Empty array OK, no error** |

**TC-EDGAR-008 — edgar_amendments**

Retrieve amended filings (10-K/A, 10-Q/A, 8-K/A) for a company.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-008-01 | Happy Path | Amendments for large filer | cik: "320193" | filings with form ending in /A | **All returned forms are amendment types** |
| TC-EDGAR-008-02 | Edge Case | Company with zero amendments | recently-listed company CIK | empty array | **Returns empty, no crash** |

**TC-EDGAR-009 — edgar_insider_transactions**

Form 4 insider transactions via enhanced EDGAR layer.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-009-01 | Happy Path | Apple insiders | cik: "320193", limit: 20 | transactions array with filingDate, accessionNumber, document_url | **transactions_count matches array length** |
| TC-EDGAR-009-02 | Boundary | Limit = 100 (max) | cik: "320193", limit: 100 | Up to 100 transactions returned | **No overflow error** |
| TC-EDGAR-009-03 | Negative | Limit = 0 | cik: "320193", limit: 0 | Schema validation error (minimum is 1) | **error returned, no crash** |

**TC-EDGAR-010 — edgar_ownership_reports**

Retrieve Forms 3, 4, 5 — initial and annual beneficial ownership statements.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-010-01 | Happy Path | Ownership filings for Tesla | cik: "1318605" | forms 3/4/5 filings with dates | **Non-empty filings array** |
| TC-EDGAR-010-02 | Negative | Invalid CIK | cik: "NONE" | error | **Clean error message** |

**TC-EDGAR-011 — edgar_institutional_holdings**

Return 13F institutional holdings reports for an investment manager CIK.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-011-01 | Happy Path | Vanguard 13F | cik: "102909" | holdings array with issuer, shares, value | **holdings non-empty; values numeric** |
| TC-EDGAR-011-02 | Edge Case | Non-institutional CIK | cik: "320193" (Apple) | empty holdings or error | **Handled gracefully** |

**TC-EDGAR-012 — edgar_mutual_fund_holdings**

Return NPORT-P / N-Q mutual fund portfolio holdings.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-012-01 | Happy Path | Known mutual fund CIK | cik: valid fund CIK | holdings array with CUSIP, issuer, value | **Non-empty holdings** |
| TC-EDGAR-012-02 | Negative | Operating company CIK | cik: "320193" | empty or error | **No crash** |

**TC-EDGAR-013 — edgar_proxy_statements**

Retrieve DEF 14A proxy statements for a company.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-013-01 | Happy Path | Apple proxy | cik: "320193" | filings with form DEF 14A | **At least 1 proxy found** |
| TC-EDGAR-013-02 | Edge Case | Company that uses DEF 14A/A | cik: "789019" | includes amendments if present | **Both DEF 14A and amendments included** |

**TC-EDGAR-014 — edgar_registration_statements**

Retrieve S-1, S-3, S-4 and other registration filings.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-014-01 | Happy Path | Recent IPO company registrations | cik: recent S-1 filer | S-1 filing in results | **form field matches S-1 or S-1/A** |
| TC-EDGAR-014-02 | Edge Case | Established company (no recent S-1) | cik: "320193" | S-3 shelf registrations or empty | **No crash** |

**TC-EDGAR-015 — edgar_foreign_issuers**

Return 20-F and 40-F filings from foreign private issuers.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-015-01 | Happy Path | Foreign issuer 20-F | cik: Alibaba CIK "1800227" | 20-F filing in results | **form === "20-F"** |
| TC-EDGAR-015-02 | Edge Case | US domestic company | cik: "320193" | empty or no 20-F/40-F results | **No crash** |

**TC-EDGAR-016 — edgar_companies_by_sic**

List companies belonging to a given SIC industry code.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-016-01 | Happy Path | SIC 7372 (software) | sic_code: "7372" | companies array with name, cik, ticker | **Multiple companies returned** |
| TC-EDGAR-016-02 | Edge Case | Obscure SIC code | sic_code: "0100" | Possibly small list | **Non-crash; empty array acceptable** |
| TC-EDGAR-016-03 | Negative | Non-numeric SIC | sic_code: "XXXX" | error | **Validation error message** |

**TC-EDGAR-017 — edgar_company_tickers_by_exchange**

Return all listed tickers on a given exchange from EDGAR company_tickers_exchange.json.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-017-01 | Happy Path | NASDAQ tickers | exchange: "Nasdaq" | Large list of tickers and CIKs | **companies.length \> 100** |
| TC-EDGAR-017-02 | Happy Path | NYSE tickers | exchange: "NYSE" | NYSE listed companies | **Non-empty list** |
| TC-EDGAR-017-03 | Negative | Unknown exchange | exchange: "MOON" | empty or error | **No crash** |

**TC-EDGAR-018 — edgar_financial_ratios**

Compute key financial ratios (P/E, debt-to-equity, current ratio) from XBRL data.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-018-01 | Happy Path | Apple financial ratios | cik: "320193" | ratios object with at least 3 named ratios | **All ratio values are numeric** |
| TC-EDGAR-018-02 | Edge Case | Company with negative equity | cik: company with negative book value | Debt-to-equity may be negative or N/A | **No division-by-zero crash** |

**TC-EDGAR-019 — edgar_frame_data**

Cross-sectional data: retrieve a concept for all companies in a given period (EDGAR frames endpoint).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-019-01 | Happy Path | Revenue frame for CY2022 | taxonomy: "us-gaap", concept: "Revenues", unit: "USD", period: "CY2022" | data array with multiple companies | **data.length \> 50** |
| TC-EDGAR-019-02 | Negative | Invalid period format | period: "2022" | error | **Descriptive period format error** |

**TC-EDGAR-020 — edgar_xbrl_frames_multi_concept**

Retrieve multiple XBRL concepts across companies in one call.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-EDGAR-020-01 | Happy Path | Revenue + NetIncome frame | concepts: \["Revenues","NetIncomeLoss"\], period: "CY2022" | Object keyed by concept, each with company data | **Both concepts present in response** |
| TC-EDGAR-020-02 | Edge Case | Single concept array | concepts: \["Revenues"\], period: "CY2022" | Works same as edgar_frame_data | **Non-empty data** |
| TC-EDGAR-020-03 | Negative | Empty concepts array | concepts: \[\] | error | **Validation error** |

**SECTION 3 — Yahoo Finance Tools (Tavily-backed)**

These 3 tools use Tavily to fetch Yahoo Finance pages rather than Yahoo's direct API. Disabled .json.disabled variants must NOT appear in tool listing.

**TC-YF-001 — tavily_yahoo_get_quote**

Fetch real-time quote snapshot (price, change, volume, market cap) for a ticker.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-YF-001-01 | Happy Path | Quote for AAPL | ticker: "AAPL" | price (numeric), change_pct, volume, market_cap | **price \> 0; all fields present** |
| TC-YF-001-02 | Happy Path | Quote for Canadian stock | ticker: "RY.TO" | Valid quote with currency CAD | **No crash; price numeric** |
| TC-YF-001-03 | Edge Case | ETF ticker | ticker: "SPY" | Quote data for ETF | **price present; no error** |
| TC-YF-001-04 | Negative | Invalid ticker | ticker: "ZZZZZ999" | error or empty quote | **Descriptive error; no crash** |
| TC-YF-001-05 | Negative | Empty ticker | ticker: "" | error | **Validation error message** |

**TC-YF-002 — tavily_yahoo_get_history**

Retrieve historical price summary (open, high, low, close, volume) for a ticker.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-YF-002-01 | Happy Path | 1-year history for MSFT | ticker: "MSFT", period: "1y" | history array with date, open, close, volume | **Multiple data points returned** |
| TC-YF-002-02 | Happy Path | 5-day history | ticker: "AAPL", period: "5d" | 5 trading day records | **close price numeric for each record** |
| TC-YF-002-03 | Edge Case | Very long period (10y) | ticker: "AAPL", period: "10y" | Long history returned | **No timeout; data returned** |
| TC-YF-002-04 | Negative | Invalid period string | ticker: "AAPL", period: "FOREVER" | error | **Period validation message** |

**TC-YF-003 — tavily_yahoo_search_symbols**

Search for Yahoo Finance ticker symbols by company name.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-YF-003-01 | Happy Path | Search "Tesla" | query: "Tesla" | symbols array with TSLA | **TSLA in results** |
| TC-YF-003-02 | Happy Path | Search partial name | query: "Royal Bank" | RY or RY.TO present | **At least 1 result** |
| TC-YF-003-03 | Edge Case | Search for ETF | query: "S&P 500 ETF" | SPY or IVV in results | **Non-empty results** |
| TC-YF-003-04 | Negative | Empty query | query: "" | error or empty results | **No crash** |

**SECTION 4 — Tavily Search Tools**

All Tavily tools require TAVILY_API_KEY to be set. A missing API key must return a clear auth error, not a crash.

**TC-TAV-001 — tavily_web_search**

General web search via Tavily. Returns ranked results with title, URL, content snippet, relevance score.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-TAV-001-01 | Happy Path | Simple financial query | query: "Federal Reserve interest rate decision 2025" | results array with title, url, content, score | **results_count \>= 1; scores \> 0** |
| TC-TAV-001-02 | Happy Path | Query with max_results | query: "inflation data", max_results: 10 | Up to 10 results | **results.length \<= 10** |
| TC-TAV-001-03 | Edge Case | Query returning zero results | query: "XQZJKWPQRS99" | results_count === 0 | **Empty results, no crash** |
| TC-TAV-001-04 | Negative | Empty query | query: "" | error | **Tavily returns validation error** |
| TC-TAV-001-05 | Negative | Missing API key (env) | valid query with no API key set | auth error message | **Clear error: "API key missing"** |

**TC-TAV-002 — tavily_domain_search**

Search restricted to specific trusted domains. Requires include_domains OR exclude_domains (oneOf schema).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-TAV-002-01 | Happy Path | Search Bloomberg for rate news | query: "ECB rate hike", include_domains: \["bloomberg.com"\] | results only from bloomberg.com | **All result URLs contain bloomberg.com** |
| TC-TAV-002-02 | Happy Path | Search SEC.gov | query: "10-K Apple 2024", include_domains: \["sec.gov"\] | results from sec.gov | **All URLs from sec.gov** |
| TC-TAV-002-03 | Happy Path | Exclude domains | query: "bank earnings", exclude_domains: \["reddit.com","twitter.com"\] | No results from excluded domains | **No excluded domain in result URLs** |
| TC-TAV-002-04 | Edge Case | Domain with no matching content | query: "quantum computing", include_domains: \["sec.gov"\] | Zero results or very low score results | **Handled gracefully; no crash** |
| TC-TAV-002-05 | Negative | Neither include nor exclude domains supplied | query: "bank news" (no domain params) | Validation error (oneOf violated) | **Schema validation error message** |

**TC-TAV-003 — tavily_news_search**

News-specific search via Tavily with recency weighting.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-TAV-003-01 | Happy Path | Recent earnings news | query: "Apple earnings Q1 2026" | news articles from past 90 days with publish_date | **publish_date present; content non-empty** |
| TC-TAV-003-02 | Edge Case | Old event query | query: "1929 stock market crash" | Historical articles or low relevance | **No crash; results may be empty** |
| TC-TAV-003-03 | Happy Path | include_answer flag | query: "latest Fed meeting outcome", include_answer: true | answer field present in response | **answer is non-empty string** |

**TC-TAV-004 — tavily_research_search**

Deep research search using Tavily advanced mode — longer content extracts, higher depth crawl.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-TAV-004-01 | Happy Path | Deep research query | query: "Basel III capital requirements banks 2025" | results with long content (\>500 chars), sources | **content length \> 200 chars per result** |
| TC-TAV-004-02 | Edge Case | Very broad query | query: "finance" | Multiple diverse results | **results_count \>= 3; no timeout** |
| TC-TAV-004-03 | Negative | Empty query | query: "" | error | **API error message returned** |

**SECTION 5 — Investor Relations Tools**

IR tools scrape company IR pages. Supported tickers are explicitly listed in tool metadata: TSLA, MSFT, C, BMO, RY, JPM, GS. Tests for unsupported tickers must not crash.

**TC-IR-001 — ir_list_supported_companies**

Return the list of companies for which IR scraping is supported.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-IR-001-01 | Happy Path | Get supported company list | (no input required) | Array containing TSLA, MSFT, JPM, GS, RY, BMO, C | **All 7 known tickers present** |

**TC-IR-002 — ir_get_latest_earnings**

Retrieve latest earnings report URL and presentation for a ticker.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-IR-002-01 | Happy Path | Tesla latest earnings | ticker: "TSLA" | quarter, year, report_url, success: true | **report_url is a valid URL; success === true** |
| TC-IR-002-02 | Happy Path | JPMorgan latest earnings | ticker: "JPM" | earnings object with quarter and year | **year \>= 2024** |
| TC-IR-002-03 | Edge Case | Unsupported but valid ticker | ticker: "AAPL" | error or empty result | **success: false with message; no crash** |
| TC-IR-002-04 | Negative | Invalid ticker | ticker: "?????" | error | **Descriptive error message** |

**TC-IR-003 — ir_get_annual_reports**

Return links to annual report documents (10-K, annual review PDF).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-IR-003-01 | Happy Path | Microsoft annual reports | ticker: "MSFT" | documents array with title and url | **At least 1 annual report URL** |
| TC-IR-003-02 | Edge Case | Company with IR page changes | ticker: "RY" | Available annual reports | **No crash even if scrape changes** |

**TC-IR-004 — ir_get_presentations**

Return investor day / earnings presentation decks.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-IR-004-01 | Happy Path | Goldman Sachs presentations | ticker: "GS" | presentations array with url and date | **Non-empty array** |
| TC-IR-004-02 | Edge Case | Company with no recent presentations | ticker: "BMO" | empty array or available decks | **No crash** |

**TC-IR-005 — ir_get_documents**

Return all IR documents (all types) for a company.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-IR-005-01 | Happy Path | All Citi IR documents | ticker: "C" | documents array with type, title, url | **Multiple document types returned** |

**TC-IR-006 — ir_get_all_resources**

Aggregate all available IR resources for a company in one call.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-IR-006-01 | Happy Path | Tesla all resources | ticker: "TSLA" | Nested object with earnings, presentations, annual_reports | **At least 2 resource categories non-empty** |
| TC-IR-006-02 | Negative | Unsupported ticker | ticker: "XOM" | error with supported companies hint | **success: false; helpful message** |

**TC-IR-007 — ir_find_page**

Auto-discover and return the IR homepage URL for a company.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-IR-007-01 | Happy Path | Find TSLA IR page | ticker: "TSLA" | ir_url non-empty string | **URL starts with https://** |
| TC-IR-007-02 | Happy Path | Find JPM IR page | ticker: "JPM" | ir_url present | **URL accessible (2xx status)** |
| TC-IR-007-03 | Negative | Empty ticker | ticker: "" | error | **Validation error** |

**SECTION 6 — Data & Analytics Tools**

DuckDB and SQL tools operate on in-memory CSV data. Available tables: customers (50 rows), orders (80 rows), products (27 rows), sales. Tests must verify SQL safety guards (no DDL/DML).

**6.1 DuckDB Tools**

**TC-DB-001 — duckdb_sql**

Execute arbitrary SQL SELECT on CSV data via DuckDB.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DB-001-01 | Happy Path | Simple SELECT all | sql: "SELECT \* FROM customers LIMIT 10" | rows array with 10 records; columns match schema | **row_count === 10; success: true** |
| TC-DB-001-02 | Happy Path | Aggregate query | sql: "SELECT customer_segment, COUNT(\*) as cnt FROM customers GROUP BY customer_segment" | Grouped rows with cnt values | **success: true; numeric cnt** |
| TC-DB-001-03 | Happy Path | JOIN across tables | sql: "SELECT c.customer_name, SUM(o.quantity \* o.unit_price) as revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_name LIMIT 5" | 5 rows with revenue | **revenue is numeric; no null rows** |
| TC-DB-001-04 | Boundary | Max limit = 1000 | sql: "SELECT \* FROM orders", limit: 1000 | Up to 80 rows (full orders table) | **row_count \<= 1000** |
| TC-DB-001-05 | Negative | DDL injection — DROP TABLE | sql: "DROP TABLE customers" | error: DDL not allowed | **success: false; table unaffected** |
| TC-DB-001-06 | Negative | DML injection — DELETE | sql: "DELETE FROM orders WHERE 1=1" | error: DML not allowed | **success: false; data unaffected** |
| TC-DB-001-07 | Negative | Syntax error | sql: "SELCT \* FORM customers" | SQL syntax error message | **error message includes context** |
| TC-DB-001-08 | Edge Case | Query returning zero rows | sql: "SELECT \* FROM customers WHERE customer_id = -999" | Empty rows array | **success: true; row_count === 0** |

**TC-DB-002 — duckdb_query**

Structured query builder interface for DuckDB (alternative to raw SQL).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DB-002-01 | Happy Path | Table scan with filters | table: "orders", filters: {order_status: "Completed"} | Filtered rows | **All rows have order_status === "Completed"** |
| TC-DB-002-02 | Happy Path | Aggregation via builder | table: "products", agg: "SUM", field: "stock_quantity" | Total stock count | **Single numeric result** |
| TC-DB-002-03 | Negative | Non-existent table | table: "invoices" | error: table not found | **Clear table-not-found message** |

**TC-DB-003 — duckdb_list_tables**

List available tables/views in the DuckDB session.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DB-003-01 | Happy Path | List all tables | (no params) | tables array including customers, orders, products | **All 3+ base tables present** |

**TC-DB-004 — duckdb_list_files**

List CSV/Parquet source files available for querying.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DB-004-01 | Happy Path | List data files | (no params) | files array with filename and size | **At least 3 CSV files listed** |

**TC-DB-005 — duckdb_describe_table**

Return schema (column names and types) for a given table.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DB-005-01 | Happy Path | Describe customers | table: "customers" | columns array with name and type | **customer_id, customer_name in columns** |
| TC-DB-005-02 | Negative | Non-existent table | table: "fakeable" | error | **Table not found message** |

**TC-DB-006 — duckdb_aggregate**

Perform a named aggregation (SUM, AVG, COUNT, MIN, MAX) on a column.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DB-006-01 | Happy Path | SUM unit_price in orders | table: "orders", column: "unit_price", agg: "SUM" | numeric result | **result \> 0** |
| TC-DB-006-02 | Happy Path | COUNT all customers | table: "customers", agg: "COUNT" | count = 50 | **result === 50** |
| TC-DB-006-03 | Negative | Invalid aggregation function | table: "orders", agg: "MEDIAN" | error or fallback | **No crash** |

**TC-DB-007 — duckdb_get_stats**

Return statistical summary (min, max, mean, stddev, null_count) for a column.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DB-007-01 | Happy Path | Stats on unit_price | table: "orders", column: "unit_price" | min, max, mean, stddev, null_count | **All 5 stat fields numeric** |
| TC-DB-007-02 | Edge Case | Stats on string column | table: "customers", column: "customer_name" | null_count and count; numeric stats N/A | **No crash; graceful non-numeric handling** |

**TC-DB-008 — duckdb_refresh_views**

Reload data from CSV files and refresh all views.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DB-008-01 | Happy Path | Trigger refresh | (no params) | success: true; views_refreshed count | **success: true; no error** |

**6.2 OLAP Tools**

**TC-OLAP-001 — olap_pivot_table**

Generate a pivot table from available data.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-OLAP-001-01 | Happy Path | Pivot orders by region and category | rows: "region", columns: "product_category", values: "unit_price", agg: "SUM" | Pivot matrix with row/column headers and values | **All cells numeric; no null crashes** |
| TC-OLAP-001-02 | Edge Case | Single row dimension | rows: "order_status", values: "quantity", agg: "COUNT" | Flat pivot with status rows | **count values are integers** |
| TC-OLAP-001-03 | Negative | Non-existent dimension field | rows: "nonexistent_column" | error | **Column not found message** |

**TC-OLAP-002 — olap_time_series**

Generate a time-series aggregation over a date column.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-OLAP-002-01 | Happy Path | Monthly revenue trend | table: "orders", date_col: "order_date", value_col: "unit_price", freq: "month", agg: "SUM" | series array with period and value | **Periods in ascending order; values numeric** |
| TC-OLAP-002-02 | Happy Path | Daily order count | table: "orders", date_col: "order_date", value_col: "order_id", freq: "day", agg: "COUNT" | Daily count per day | **count \>= 0 for each period** |
| TC-OLAP-002-03 | Negative | Invalid frequency | freq: "biweekly" | error | **Supported frequencies listed in error** |

**TC-OLAP-003 — customer_olap_pivot**

Pre-built OLAP pivot optimised for customer dimension analysis.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-OLAP-003-01 | Happy Path | Customers by segment and region | rows: "customer_segment", columns: "region", values: "customer_id", agg: "COUNT" | Pivot with segment/region breakdown | **All values are integers \>= 0** |

**6.3 SQL Select Tools**

**TC-SQL-001 — sqlselect_execute_query**

Run safe SQL SELECT queries on CSV data sources. Only SELECT is allowed.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SQL-001-01 | Happy Path | Select customers | query: "SELECT \* FROM customers", limit: 50 | 50 rows from customers table | **success: true; columns match schema** |
| TC-SQL-001-02 | Happy Path | Aggregation sales by product | query: "SELECT product_id, SUM(amount) as total FROM sales GROUP BY product_id" | product_id and total per row | **success: true; total is numeric** |
| TC-SQL-001-03 | Negative | INSERT attempt | query: "INSERT INTO customers VALUES (...)" | error: INSERT not allowed | **success: false; safety message** |
| TC-SQL-001-04 | Negative | DROP attempt | query: "DROP TABLE products" | error: DDL not allowed | **Data unaffected** |
| TC-SQL-001-05 | Boundary | Max limit = 10000 | query: "SELECT \* FROM orders", limit: 10000 | All available rows (max 80) | **row_count \<= 10000; no overflow** |

**TC-SQL-002 — sqlselect_list_sources**

Return available data source names and descriptions.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SQL-002-01 | Happy Path | List all sources | (no params) | sources array: customers, orders, products, sales | **All 4 sources present** |

**TC-SQL-003 — sqlselect_get_schema**

Return column schema for a named data source.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SQL-003-01 | Happy Path | Schema of orders | source: "orders" | columns array with name, type | **order_id, customer_id in schema** |
| TC-SQL-003-02 | Negative | Unknown source | source: "ledger" | error | **Source not found message** |

**TC-SQL-004 — sqlselect_describe_source**

Natural language description of a data source — row count, key columns, sample values.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SQL-004-01 | Happy Path | Describe products | source: "products" | description string with row count and column list | **row_count = 27; non-empty description** |

**TC-SQL-005 — sqlselect_sample_data**

Return a random or top-N sample of rows from a data source.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SQL-005-01 | Happy Path | Sample 5 rows from customers | source: "customers", n: 5 | rows array with 5 customer records | **row_count === 5** |
| TC-SQL-005-02 | Boundary | n = 1 | source: "orders", n: 1 | 1 row returned | **row_count === 1** |

**TC-SQL-006 — sqlselect_count_rows**

Return total row count for a data source.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SQL-006-01 | Happy Path | Count customers | source: "customers" | count = 50 | **count === 50; success: true** |
| TC-SQL-006-02 | Happy Path | Count products | source: "products" | count = 27 | **count === 27** |

**SECTION 7 — Risk & Portfolio Tools**

Risk tools read from internal data store (likely in-memory or database). Tests assume sample data is loaded. Numeric fields must be validated as finite, non-NaN values.

**TC-RISK-001 — get_counterparty_exposure**

Return notional, MTM, PFE and net exposure per counterparty.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-RISK-001-01 | Happy Path | All counterparties | (no params — returns all) | Array of exposure objects with notional, mtm, pfe, net_exposure fields | **All numeric fields are finite; array non-empty** |
| TC-RISK-001-02 | Happy Path | Filter by counterparty name | counterparty: "BANK OF AMERICA" | One or more rows for that counterparty | **All rows match filter** |
| TC-RISK-001-03 | Edge Case | Filter no match | counterparty: "NONEXISTENT BANK" | Empty array | **success: true; empty array; no crash** |
| TC-RISK-001-04 | Edge Case | Counterparty with negative MTM | any counterparty | MTM can be negative (out-of-money derivatives) | **Negative numeric value accepted** |

**TC-RISK-002 — get_historical_exposure**

Return time-series of counterparty exposure for trend/stress analysis.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-RISK-002-01 | Happy Path | Historical for all counterparties | (no params) | Array of records with date, counterparty, exposure | **Dates in ISO format; exposure numeric** |
| TC-RISK-002-02 | Happy Path | Filter by counterparty | counterparty: "CITIBANK" | Time-series for Citibank only | **All records match counterparty filter** |
| TC-RISK-002-03 | Edge Case | No history for new counterparty | counterparty: "NEW ENTITY" | Empty array | **No crash** |

**TC-RISK-003 — get_credit_limits**

Return approved credit limits and utilisation per counterparty.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-RISK-003-01 | Happy Path | All credit limits | (no params) | Array with counterparty, limit, utilised, available | **available = limit - utilised for all rows** |
| TC-RISK-003-02 | Edge Case | Counterparty at 100% utilisation | any | available === 0; no negative credit flag | **Handled correctly without error** |
| TC-RISK-003-03 | Edge Case | Counterparty over limit | any | available may be negative (breach) | **Negative available is valid; flagged in response** |

**TC-RISK-004 — get_var_contribution**

Return VaR contribution per counterparty at 95%, 99%, and stress levels.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-RISK-004-01 | Happy Path | All VaR records | (no params) | Array with var_95, var_99, stress_var per counterparty | **All VaR fields are positive numerics** |
| TC-RISK-004-02 | Happy Path | Filter single counterparty | counterparty: "DEUTSCHE BANK" | VaR for Deutsche Bank only | **Single matching record** |
| TC-RISK-004-03 | Edge Case | Verify var_99 \>= var_95 | any counterparty | var_99 \>= var_95 for all records | **Monotonicity preserved (99% VaR \>= 95% VaR)** |

**TC-RISK-005 — get_trade_inventory**

Return current trade inventory / position book.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-RISK-005-01 | Happy Path | Full inventory | (no params) | Trades array with trade_id, counterparty, notional, mtm | **All numeric fields finite; non-empty** |
| TC-RISK-005-02 | Happy Path | Filter by counterparty | counterparty: "JPMORGAN" | JPMorgan trades only | **All rows match counterparty** |
| TC-RISK-005-03 | Edge Case | Counterparty with no trades | counterparty: "NO TRADES FIRM" | Empty array | **No crash; success: true** |

**SECTION 8 — Document Tools (MS Office)**

MS Office tools require python-docx and openpyxl. Tests assume sample files are present in the configured data directory. File paths should use relative names (not absolute paths) per the tool schema.

**TC-DOC-001 — msdoc_read_word**

Extract paragraphs and tables from a .docx file.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-001-01 | Happy Path | Read a known .docx file | filename: "sample_report.docx" | paragraphs array (non-empty), paragraph_count, table_count | **paragraph_count \> 0; success: true** |
| TC-DOC-001-02 | Happy Path | Read file with tables | filename: "table_doc.docx" | tables array with 2D cell data | **table_count \>= 1; tables non-empty** |
| TC-DOC-001-03 | Edge Case | Empty document | filename: "empty.docx" | paragraph_count = 0; tables = \[\] | **No crash; success: true** |
| TC-DOC-001-04 | Negative | File not found | filename: "ghost.docx" | error: file not found | **success: false; clear error** |
| TC-DOC-001-05 | Negative | Non-docx extension | filename: "data.xlsx" | error: unsupported format | **No crash; file format error message** |

**TC-DOC-002 — msdoc_get_word_metadata**

Return document properties (author, created date, modified date, title, word count).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-002-01 | Happy Path | Metadata for sample doc | filename: "sample_report.docx" | author, created, modified, title fields | **created is valid ISO date** |
| TC-DOC-002-02 | Negative | Missing file | filename: "missing.docx" | error | **File not found message** |

**TC-DOC-003 — msdoc_search_word**

Full-text search within a Word document.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-003-01 | Happy Path | Search for keyword | filename: "sample_report.docx", query: "revenue" | matches array with paragraph index and context | **match_count \>= 0; no crash** |
| TC-DOC-003-02 | Edge Case | Search term not in document | filename: "sample_report.docx", query: "ZXQKWPQRS" | matches = \[\]; match_count = 0 | **success: true; empty result** |
| TC-DOC-003-03 | Negative | Empty search query | filename: "sample_report.docx", query: "" | error or all paragraphs | **No crash** |

**TC-DOC-004 — msdoc_extract_text**

Extract full plain text from a Word document (stripped of formatting).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-004-01 | Happy Path | Extract text from report | filename: "sample_report.docx" | text string with all document content | **text.length \> 0; no XML tags in output** |
| TC-DOC-004-02 | Negative | Non-existent file | filename: "nofile.docx" | error | **Descriptive error message** |

**TC-DOC-005 — msdoc_list_files**

List all available Office documents in the configured data directory.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-005-01 | Happy Path | List all docs | (no params) | files array with filename, size, type | **Non-empty list; types include docx/xlsx** |
| TC-DOC-005-02 | Edge Case | Filter by type | file_type: "docx" | Only .docx files listed | **All items are .docx** |

**TC-DOC-006 — msdoc_read_excel**

Read all sheets from an Excel file and return data as arrays.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-006-01 | Happy Path | Read sample Excel | filename: "financial_data.xlsx" | sheets object keyed by sheet name | **At least 1 sheet; rows non-empty** |
| TC-DOC-006-02 | Negative | File not found | filename: "ghost.xlsx" | error | **File not found message** |

**TC-DOC-007 — msdoc_read_excel_sheet**

Read a specific named sheet from an Excel file.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-007-01 | Happy Path | Read Sheet1 | filename: "financial_data.xlsx", sheet: "Sheet1" | rows array for Sheet1 | **rows non-empty; correct sheet data** |
| TC-DOC-007-02 | Negative | Sheet name does not exist | filename: "financial_data.xlsx", sheet: "Phantom" | error: sheet not found | **Descriptive error** |

**TC-DOC-008 — msdoc_get_excel_metadata**

Return Excel file properties (sheet count, named ranges, author, created date).

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-008-01 | Happy Path | Metadata for Excel file | filename: "financial_data.xlsx" | sheet_count, sheets list, author | **sheet_count \>= 1** |

**TC-DOC-009 — msdoc_get_excel_sheets**

Return list of sheet names from an Excel file.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-009-01 | Happy Path | List sheets | filename: "financial_data.xlsx" | sheets array of strings | **Non-empty array; strings are valid names** |

**TC-DOC-010 — msdoc_search_excel**

Search for a value across all cells/sheets in an Excel file.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-DOC-010-01 | Happy Path | Search for keyword in Excel | filename: "financial_data.xlsx", query: "revenue" | matches array with sheet, row, col, value | **match_count \>= 0; no crash** |
| TC-DOC-010-02 | Edge Case | Search not found | query: "ZZZZQQQQQ" | Empty matches; match_count = 0 | **success: true; empty result** |

**SECTION 9 — SharePoint Tools**

SharePoint tools require Azure AD client credentials (tenant_id, client_id, client_secret) and a valid site_url. Missing credentials must produce an auth error, not a crash. Tests require a connected SharePoint environment.

**TC-SP-001 — sharepoint_search**

Enterprise search across SharePoint — documents, people, sites, lists.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SP-001-01 | Happy Path | Search all content for quarterly report | query: "quarterly report", search_type: "all" | results array with title, url, author | **results_count \>= 0; no crash** |
| TC-SP-001-02 | Happy Path | Search documents only | query: "budget", search_type: "documents" | Only document results | **All results are files (not people/sites)** |
| TC-SP-001-03 | Happy Path | Search people | query: "project manager", search_type: "people" | People results with name, email | **email fields present** |
| TC-SP-001-04 | Happy Path | Filter by file type | query: "report", search_type: "documents", file_types: \["xlsx", "pdf"\] | Only xlsx and pdf results | **No docx or other types in results** |
| TC-SP-001-05 | Edge Case | Zero results query | query: "XZQKWPQRS999" | Empty results | **results_count = 0; no crash** |
| TC-SP-001-06 | Boundary | Max results = 500 | query: "report", max_results: 500 | Up to 500 results | **results.length \<= 500** |
| TC-SP-001-07 | Negative | Missing auth credentials | valid query but no Azure credentials configured | auth error message | **success: false; 401/403 message** |

**TC-SP-002 — sharepoint_documents**

Browse and list documents within a SharePoint library or folder.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SP-002-01 | Happy Path | List root document library | library: "Documents" | Array of files with name, url, modified | **Non-empty array for populated library** |
| TC-SP-002-02 | Edge Case | Empty library | library: "EmptyLib" | Empty array | **success: true; no crash** |
| TC-SP-002-03 | Negative | Library does not exist | library: "FakeLibrary999" | error | **Library not found message** |

**TC-SP-003 — sharepoint_lists**

Return SharePoint list items from a named list.

| **Test ID** | **Type** | **Description** | **Input** | **Expected Output** | **Pass Criteria** |
|----|----|----|----|----|----|
| TC-SP-003-01 | Happy Path | Get list items | list_name: "Tasks" | items array with ID, Title, fields | **items non-empty; Title field present** |
| TC-SP-003-02 | Negative | Non-existent list | list_name: "GhostList" | error | **List not found message** |

**10. Acceptance Summary Scorecard**

For each tool, the QA team must record results in the table below before sign-off. A tool is PASS only if all Happy Path tests pass. Edge/Negative failures require a waiver or bug ticket.

|  |  |  |  |  |
|----|----|----|----|----|
| **Tool Category** | **Total Tools** | **Happy Path Pass** | **Issues Found** | **Status** |
| SEC Abstracted | 7 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| EDGAR Enhanced | 20 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| Yahoo Finance (Tavily) | 3 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| Tavily Search | 4 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| Investor Relations | 7 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| DuckDB | 8 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| OLAP | 3 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| SQL Select | 6 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| Risk & Portfolio | 5 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| Document Tools | 10 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| SharePoint | 3 | \_\_\_ | \_\_\_ | \[ \] PASS \[ \] FAIL \[ \] WAIVER |
| **TOTAL** | **76** | \_\_\_ | \_\_\_ |  |

**Sign-off**

QA Lead: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Engineering Lead: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
