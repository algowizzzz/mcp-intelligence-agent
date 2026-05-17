# UAT Results — phase2

**Run ID:** `phase2_2026-04-03_16-15-01`  
**Generated:** 2026-04-03 21:21:52 UTC  

## Summary

| Status | Count |
|--------|-------|
| ✓ PASS  | 73  |
| ✗ FAIL  | 0  |
| ○ SKIP  | 3  |
| ! ERROR | 0 |
| **Total** | **76** |

**Pass rate: 96% (73/76)**

## Module 5 — Chat & Agent

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| C-01 | simple query returns non-empty text | ✓ PASS |  | 1365 |
| C-02 | agent run returns a thread_id | ✓ PASS |  |  |
| C-03 | tool-calling query invokes at least one tool | ✓ PASS |  |  |
| C-04 | resume thread: agent returns text | ✓ PASS |  |  |
| C-05 | thread appears in /api/agent/threads | ✓ PASS |  |  |
| C-06 | agent accepts CCR worker query | ✓ PASS |  |  |
| C-07 | tool allowlist: EDGAR tools not called when restricted | ✓ PASS |  |  |
| C-08 | invalid worker_id: agent returns error or empty gracefu | ✓ PASS |  |  |
| C-09 | agent can list uploaded files after upload | ✓ PASS |  |  |

*9/9 passed*

## Module 6A — IRIS CCR Tools

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| T-01 | iris_search_counterparties — find by name | ✓ PASS |  | 3791 |
| T-02 | iris_counterparty_dashboard — full dashboard | ✓ PASS |  | 5491 |
| T-03 | iris_exposure_trend — time series | ✓ PASS |  | 6511 |
| T-04 | iris_limit_lookup — find limits | ✓ PASS |  | 6302 |
| T-05 | iris_limit_breach_check — scan for breaches | ✓ PASS |  | 6909 |
| T-06 | iris_portfolio_breach_scan — portfolio-wide | ✓ PASS |  | 6000 |
| T-07 | iris_multi_counterparty_comparison — side by side | ✓ PASS |  | 6951 |
| T-08 | iris_rating_screen — filter by rating | ✓ PASS |  | 5003 |
| T-09 | iris_list_dates — available snapshots | ✓ PASS |  | 3235 |

*9/9 passed*

## Module 6B — OSFI Regulatory Tools

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| T-10 | osfi_list_docs — list available documents | ✓ PASS |  | 4200 |
| T-11 | osfi_search_guidance — keyword search | ✓ PASS |  | 5731 |
| T-12 | osfi_read_document — read CAR guideline | ✓ PASS |  | 6081 |
| T-13 | osfi_fetch_announcements — live fetch | ✓ PASS |  | 6227 |
| T-14 | osfi_read_document — multi-chunk navigation | ✓ PASS |  | 6591 |

*5/5 passed*

## Module 6C — EDGAR / SEC Tools

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| T-15 | edgar_find_filing — JPMorgan 10-K | ✓ PASS |  | 5442 |
| T-16 | edgar_extract_section — MD&A | ✓ PASS |  | 7094 |
| T-17 | edgar_get_metric — revenue XBRL | ✓ PASS |  | 5275 |
| T-18 | edgar_get_statements — balance sheet | ✓ PASS |  | 6103 |
| T-19 | edgar_earnings_brief — recent quarter | ✓ PASS |  | 7361 |
| T-20 | edgar_peer_comparison — 3 banks | ✓ PASS |  | 10591 |
| T-21 | edgar_risk_summary — risk factors | ✓ PASS |  | 8956 |
| T-22 | edgar_segment_analysis — business segments | ✓ PASS |  | 8757 |
| T-23 | edgar_company_brief — one-pager | ✓ PASS |  | 9024 |
| T-24 | edgar_calculate_ratios — ROE / ROA / CET1 | ✓ PASS |  | 4764 |
| T-25 | Canadian bank (BMO) — 6-K guidance | ✓ PASS |  | 5692 |

*11/11 passed*

## Module 6D — Tavily / IR / News Tools

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| T-26 | tavily_news_search — bank stress tests | ✓ PASS |  | 5188 |
| T-27 | tavily_web_search — general query | ✓ PASS |  | 9978 |
| T-28 | tavily_research_search — deep research | ✓ PASS |  | 16089 |
| T-29 | tavily_yahoo_get_quote — JPM stock | ✓ PASS |  | 4396 |
| T-30 | tavily_yahoo_get_history — GS 30-day price | ✓ PASS |  | 4953 |
| T-31 | tavily_yahoo_search_symbols — symbol search | ✓ PASS |  | 3415 |
| T-32 | ir_list_supported_companies | ✓ PASS |  | 5047 |
| T-33 | ir_get_latest_earnings — RBC | ✓ PASS |  | 6629 |

*8/8 passed*

## Module 6E — DuckDB / SQL Tools

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| T-34 | duckdb_list_files — list databases | ✓ PASS |  | 5369 |
| T-35 | duckdb_list_tables — list tables | ✓ PASS |  | 3460 |
| T-36 | duckdb_query — SELECT query | ✓ PASS |  | 6527 |
| T-37 | duckdb_sql — aggregation | ✓ PASS |  | 10675 |
| T-38 | sqlselect_list_sources — list CSV/Parquet | ✓ PASS |  | 3523 |
| T-39 | sqlselect_execute_query — query iris CSV | ✓ PASS |  | 5209 |
| T-40 | sqlselect_sample_data — sample iris | ✓ PASS |  | 6394 |
| T-41 | sqlselect_get_schema — iris schema | ✓ PASS |  | 10578 |

*8/8 passed*

## Module 6F — MS Document Tools

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| T-42 | msdoc_list_files — list Word/Excel files | ✓ PASS |  | 4294 |
| T-43 | msdoc_read_word — read uploaded .docx | ✓ PASS |  | 6355 |
| T-45 | msdoc_search_word — keyword in Word doc | ✓ PASS |  | 3835 |
| T-44 | msdoc_read_excel (skipped: requires real .xlsx upload — | ○ SKIP |  |  |
| T-46 | msdoc_search_excel (skipped: requires real .xlsx upload | ○ SKIP |  |  |

*3/5 passed*

## Module 6G — Utility Tools

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| T-47 | list_uploaded_files — list uploads | ✓ PASS |  | 6070 |
| T-48 | pdf_read — extract text from PDF | ✓ PASS |  | 4680 |
| T-49 | parquet_read (skipped: requires pre-uploaded .parquet — | ○ SKIP |  |  |
| T-50 | md_save — save analysis to markdown | ✓ PASS |  | 4372 |
| T-51 | md_to_docx — convert markdown to Word | ✓ PASS |  | 4444 |
| T-52 | generate_chart — create a chart | ✓ PASS |  | 7327 |
| T-53 | fill_template — fill a workflow template | ✓ PASS |  | 6614 |
| T-54 | search_files — keyword search in uploads | ✓ PASS |  | 3916 |

*7/8 passed*

## Module 6H — CCR Exposure Tools

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| T-55 | get_counterparty_exposure — by counterparty | ✓ PASS |  | 5747 |
| T-56 | get_credit_limits — limits table | ✓ PASS |  | 5977 |
| T-57 | get_trade_inventory — trade-level details | ✓ PASS |  | 5520 |
| T-58 | get_var_contribution — VaR attribution | ✓ PASS |  | 4303 |
| T-59 | get_historical_exposure — time series | ✓ PASS |  | 4419 |
| T-60 | CCR tool on worker with no iris data: graceful response | ✓ PASS |  |  |

*6/6 passed*

## Module 7 — Workflows

| ID | Scenario | Status | Detail | ms |
|----|----------|--------|--------|----|
| WF-01 | workflow_list — list all available workflows | ✓ PASS |  | 3468 |
| WF-02 | workflow_get — fetch counterparty_intelligence steps | ✓ PASS |  | 7821 |
| WF-03 | counterparty_intelligence workflow — Deutsche Bank | ✓ PASS |  | 6675 |
| WF-04 | osfi_regulatory_watch workflow | ✓ PASS |  | 8624 |
| WF-05 | custom workflow upload → on disk in worker workflows fo | ✓ PASS |  |  |
| WF-06 | workflow with missing inputs: agent asks for parameters | ✓ PASS |  |  |
| WF-07 | CCR workflow not visible from MR worker | ✓ PASS |  |  |

*7/7 passed*
