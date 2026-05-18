# SAJHA MCP Server — Holistic Tool Test Plan
**Version:** 1.0 | **Date:** 2026-04-03 | **Total Tools:** 85

## How to Use This Plan
- Run each test in the chat UI or directly via the MCP client.
- **PASS criteria** are explicit — do not accept partial output as passing.
- Tools marked **[API KEY REQUIRED]** will silently fail or return errors if keys are missing.
- Run categories in dependency order: Infrastructure → IRIS → Data → EDGAR/IR → OSFI → Market → Visualisation → Workflow.

---

## 1. Infrastructure & System Tools

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 1 | `workflow_list` | `{}` | Returns list of workflow filenames; at least 6 entries |
| 2 | `workflow_get` | `{"name": "portfolio_concentration_report"}` | Returns full markdown content of workflow file |
| 3 | `list_uploaded_files` | `{}` | Returns files across all upload subfolders with `relative_path`, `size`, `subfolder` fields |
| 4 | `list_uploaded_files` | `{"subfolder": "iris"}` | Returns only files under uploads/iris |
| 5 | `search_files` | `{"query": "iris"}` | Returns matching filenames |
| 6 | `list_versions` | `{"filename": "iris_combined.csv"}` | Returns version list or "no versions" message |
| 7 | `md_save` | `{"content": "# Test\nHello", "filename": "test_md_save.md", "subfolder": "reports"}` | File created; returns saved path |
| 8 | `fill_template` | `{"template": "Hello {name}!", "variables": {"name": "SAJHA"}}` | Returns "Hello SAJHA!" |

---

## 2. IRIS CCR Tools

**Prerequisite:** `iris_combined.csv` exists at `data/iris/iris_combined.csv`.

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 9 | `iris_list_dates` | `{}` | Returns array of date strings in YYYY-MM-DD format; at least 1 entry |
| 10 | `iris_search_counterparties` | `{"name": "Deutsche"}` | Returns array with `counterparty_code`, `counterparty_name`; at least 1 row |
| 11 | `iris_counterparty_dashboard` | `{"counterparty_code": "<code from #10>", "date": "<date from #9>"}` | Returns exposure, limit, utilisation, rating fields |
| 12 | `iris_limit_lookup` | `{"counterparty_code": "<code from #10>"}` | Returns limit key, amount, currency |
| 13 | `iris_limit_breach_check` | `{"counterparty_code": "<code from #10>", "date": "<date from #9>"}` | Returns `breach: true/false` and overage amount |
| 14 | `iris_exposure_trend` | `{"counterparty_code": "<code from #10>", "lookback_months": 3}` | Returns array of `{date, exposure, limit}` rows |
| 15 | `iris_multi_counterparty_comparison` | `{"counterparty_codes": ["<code1>", "<code2>"], "date": "<date>"}` | Returns side-by-side comparison rows |
| 16 | `iris_portfolio_breach_scan` | `{"date": "<date from #9>"}` | Returns `breaches` array (may be empty); includes total_exposure, total_limit |
| 17 | `iris_rating_screen` | `{"date": "<date from #9>", "min_utilisation": 0}` | Returns rows grouped by rating bucket with exposure totals |

---

## 3. Data File Tools (Parquet / CSV / Transform)

**Prerequisite:** At least one `.parquet` or `.csv` file in uploads folder.

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 18 | `parquet_read` | `{"filename": "iris_combined.csv", "subfolder": "iris", "limit": 5}` | Returns `schema` (column list) and `rows` (5 dicts) |
| 19 | `parquet_read` | `{"filename": "<any .parquet>", "limit": 5}` | Same as above for parquet format |
| 20 | `data_transform` | `{"filename": "iris_combined.csv", "subfolder": "iris", "operation": "describe", "columns": ["exposure"]}` | Returns min, max, mean, std, count |
| 21 | `data_transform` | `{"filename": "iris_combined.csv", "subfolder": "iris", "operation": "null_check"}` | Returns null_count and null_pct per column |
| 22 | `data_transform` | `{"filename": "iris_combined.csv", "subfolder": "iris", "operation": "value_counts", "columns": ["rating"]}` | Returns top values with counts |
| 23 | `data_transform` | `{"filename": "iris_combined.csv", "subfolder": "iris", "operation": "filter", "column": "utilisation_pct", "operator": "gt", "value": 80}` | Returns only rows where utilisation_pct > 80 |
| 24 | `data_export` | `{"data": [{"a":1,"b":2},{"a":3,"b":4}], "filename": "test_export.csv", "format": "csv"}` | File saved; returns file path |
| 25 | `data_export` | `{"data": [{"a":1,"b":2}], "filename": "test_export.parquet", "format": "parquet"}` | Parquet saved; returns file path |

---

## 4. DuckDB Tools

**Prerequisite:** `.duckdb` file exists in `data/duckdb/` OR parquet files are present for view creation.

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 26 | `duckdb_list_files` | `{}` | Returns list of `.duckdb` files |
| 27 | `duckdb_list_tables` | `{"db_name": "<db from #26>"}` | Returns table/view names |
| 28 | `duckdb_describe_table` | `{"db_name": "<db>", "table_name": "<table from #27>"}` | Returns column names and types |
| 29 | `duckdb_get_stats` | `{"db_name": "<db>", "table_name": "<table>"}` | Returns row count and column-level stats |
| 30 | `duckdb_query` | `{"db_name": "<db>", "sql": "SELECT COUNT(*) AS n FROM <table>"}` | Returns `{n: <integer>}` |
| 31 | `duckdb_sql` | `{"sql": "SELECT 1+1 AS result"}` | Returns `{result: 2}` |
| 32 | `duckdb_aggregate` | `{"db_name": "<db>", "table_name": "<table>", "group_by": "<col>", "agg_col": "<num_col>", "agg_func": "sum"}` | Returns grouped aggregation rows |
| 33 | `duckdb_refresh_views` | `{}` | Returns "views refreshed" or list of views created |

---

## 5. SQL Select Tools

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 34 | `sqlselect_list_sources` | `{}` | Returns list of registered data sources |
| 35 | `sqlselect_describe_source` | `{"source": "<source from #34>"}` | Returns schema for that source |
| 36 | `sqlselect_get_schema` | `{"source": "<source>"}` | Returns column names and types |
| 37 | `sqlselect_sample_data` | `{"source": "<source>", "limit": 5}` | Returns 5 sample rows |
| 38 | `sqlselect_count_rows` | `{"source": "<source>"}` | Returns integer row count |
| 39 | `sqlselect_execute_query` | `{"query": "SELECT * FROM <source> LIMIT 3"}` | Returns 3 rows |

---

## 6. OLAP / Pivot Tools

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 40 | `olap_pivot_table` | `{"filename": "iris_combined.csv", "subfolder": "iris", "rows": "rating", "values": "exposure", "agg": "sum"}` | Returns pivot table with rating buckets and summed exposure |
| 41 | `olap_time_series` | `{"filename": "iris_combined.csv", "subfolder": "iris", "date_col": "date", "value_col": "exposure", "freq": "M"}` | Returns monthly aggregated series |
| 42 | `customer_olap_pivot` | `{"filename": "iris_combined.csv", "subfolder": "iris", "rows": "rating", "values": "exposure"}` | Returns pivot result; no error |

---

## 7. CCR Simulation Tools (Static Data)

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 43 | `get_counterparty_exposure` | `{"counterparty_id": "CP001"}` | Returns exposure amount or "not found" |
| 44 | `get_trade_inventory` | `{"counterparty_id": "CP001"}` | Returns list of trades or empty array |
| 45 | `get_credit_limits` | `{"counterparty_id": "CP001"}` | Returns limit keys and amounts |
| 46 | `get_var_contribution` | `{"counterparty_id": "CP001"}` | Returns VaR contribution value |
| 47 | `get_historical_exposure` | `{"counterparty_id": "CP001", "lookback_days": 30}` | Returns array of `{date, exposure}` |

---

## 8. OSFI Regulatory Tools

**Prerequisite:** OSFI documents exist at `data/osfi/`.

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 48 | `osfi_list_docs` | `{}` | Returns list of OSFI document filenames |
| 49 | `osfi_search_guidance` | `{"query": "counterparty credit risk", "max_results": 3}` | Returns up to 3 matching documents with relevance |
| 50 | `osfi_read_document` | `{"filename": "<doc from #48>"}` | Returns document text content; non-empty |
| 51 | `osfi_fetch_announcements` | `{"days_back": 30}` | Returns announcements array (may be empty); includes date range |

---

## 9. SEC EDGAR Tools [API KEY REQUIRED: EDGAR public, no key; Tavily key for some]

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 52 | `edgar_find_filing` | `{"company_name": "JPMorgan Chase", "filing_type": "10-K", "year": "2023"}` | Returns `accession_number`, `cik`, `filing_date` |
| 53 | `edgar_get_statements` | `{"accession_number": "<accession from #52>", "statement_type": "income"}` | Returns income statement rows with revenue, net_income |
| 54 | `edgar_calculate_ratios` | `{"accession_number": "<accession from #52>"}` | Returns CET1, ROE, NIM, NPL or available ratios |
| 55 | `edgar_risk_summary` | `{"accession_number": "<accession from #52>"}` | Returns top 3–5 risk factors as text |
| 56 | `edgar_extract_section` | `{"accession_number": "<accession>", "section": "MD&A"}` | Returns MD&A text; non-empty |
| 57 | `edgar_get_metric` | `{"accession_number": "<accession>", "metric": "NetIncomeLoss"}` | Returns metric value and period |
| 58 | `edgar_earnings_brief` | `{"accession_number": "<accession>"}` | Returns 1-paragraph earnings summary |
| 59 | `edgar_segment_analysis` | `{"accession_number": "<accession>"}` | Returns segment revenue breakdown |
| 60 | `edgar_peer_comparison` | `{"ticker": "JPM", "peers": "BAC,C", "year": "2023"}` | Returns comparison table; at least 1 ratio column |
| 61 | `edgar_company_brief` | `{"company_name": "JPMorgan Chase"}` | Returns 1-page company overview |

---

## 10. IR (Investor Relations) Tools [API KEY REQUIRED: Tavily]

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 62 | `ir_list_supported_companies` | `{}` | Returns list of companies with IR support |
| 63 | `ir_find_documents` | `{"company_name": "JPMorgan Chase"}` | Returns list of IR document types available |
| 64 | `ir_get_latest_earnings` | `{"company_name": "JPMorgan Chase"}` | Returns earnings summary with management commentary |
| 65 | `ir_get_annual_reports` | `{"company_name": "JPMorgan Chase"}` | Returns annual report URLs or summaries |
| 66 | `ir_get_presentations` | `{"company_name": "JPMorgan Chase"}` | Returns investor presentation links/summaries |
| 67 | `ir_get_all_resources` | `{"company_name": "JPMorgan Chase"}` | Returns all IR resource types |
| 68 | `ir_find_page` | `{"company_name": "JPMorgan Chase", "page_type": "earnings"}` | Returns IR page URL |
| 69 | `ir_get_documents` | `{"company_name": "JPMorgan Chase", "doc_type": "press_release"}` | Returns press release list |
| 70 | `ir_extract_content` | `{"url": "<URL from #68>"}` | Returns extracted text from IR page |

---

## 11. Market Data Tools [API KEY REQUIRED: Tavily]

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 71 | `tavily_yahoo_get_quote` | `{"ticker": "JPM"}` | Returns price, market_cap, 52w_high, 52w_low, pe_ratio |
| 72 | `tavily_yahoo_get_history` | `{"ticker": "JPM", "period": "3mo", "interval": "1mo"}` | Returns array of `{date, open, close, volume}` |
| 73 | `tavily_yahoo_search_symbols` | `{"query": "Canadian banks"}` | Returns matching ticker list |
| 74 | `tavily_news_search` | `{"query": "JPMorgan earnings 2026", "max_results": 3}` | Returns 3 news items with title, date, url, summary |
| 75 | `tavily_web_search` | `{"query": "Basel IV capital requirements 2025"}` | Returns web results with snippets |
| 76 | `tavily_domain_search` | `{"query": "capital requirements", "domain": "osfi-bsif.gc.ca"}` | Returns results from that domain |
| 77 | `tavily_research_search` | `{"query": "counterparty credit risk trends 2026", "max_results": 3}` | Returns research-quality results |

---

## 12. Document Tools (MS Office / PDF)

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 78 | `msdoc_list_files` | `{}` | Returns list of Word/Excel files in uploads |
| 79 | `msdoc_get_word_metadata` | `{"filename": "<any .docx>"}` | Returns title, author, created date |
| 80 | `msdoc_read_word` | `{"filename": "<any .docx>"}` | Returns document text; non-empty |
| 81 | `msdoc_search_word` | `{"filename": "<any .docx>", "query": "risk"}` | Returns matching paragraph excerpts |
| 82 | `msdoc_extract_text` | `{"filename": "<any .docx or .pdf>"}` | Returns extracted text |
| 83 | `msdoc_get_excel_metadata` | `{"filename": "<any .xlsx>"}` | Returns sheet names, row/column counts |
| 84 | `msdoc_get_excel_sheets` | `{"filename": "<any .xlsx>"}` | Returns list of sheet names |
| 85 | `msdoc_read_excel` | `{"filename": "<any .xlsx>"}` | Returns first sheet rows |
| 86 | `msdoc_read_excel_sheet` | `{"filename": "<any .xlsx>", "sheet": "<sheet from #84>"}` | Returns rows for specific sheet |
| 87 | `msdoc_search_excel` | `{"filename": "<any .xlsx>", "query": "exposure"}` | Returns matching cells/rows |
| 88 | `pdf_read` | `{"filename": "<any .pdf>"}` | Returns extracted text; non-empty |

---

## 13. Visualisation Tools

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 89 | `generate_chart` (bar) | `{"data": [{"cat":"A","val":10},{"cat":"B","val":20}], "chart_type": "bar", "x": "cat", "y": "val", "title": "Test"}` | Returns `html` string containing `<div`; `data_rows_plotted: 2` |
| 90 | `generate_chart` (line) | `{"data": [{"m":"Jan","v":5},{"m":"Feb","v":8}], "chart_type": "line", "x": "m", "y": "v", "title": "Trend"}` | Returns valid HTML with embedded Plotly |
| 91 | `generate_chart` (pie) | `{"data": [{"cat":"X","val":40},{"cat":"Y","val":60}], "chart_type": "pie", "x": "cat", "y": "val", "title": "Mix"}` | Returns HTML; `data_rows_plotted: 2` |
| 92 | `generate_chart` (save_png) | `{"data": [{"a":1,"b":2}], "chart_type": "bar", "x": "a", "y": "b", "title": "PNG Test", "save_png": true}` | Returns `png_path` ending in `.png`; file exists on disk |
| 93 | `generate_chart` (save_html) | `{"data": [{"a":1,"b":2}], "chart_type": "bar", "x": "a", "y": "b", "title": "HTML Test", "save_html": true}` | Returns `html_file` path; standalone `.html` file exists |
| 94 | `generate_chart` (dark theme) | `{"data": [{"a":1,"b":2}], "chart_type": "bar", "x": "a", "y": "b", "title": "Dark", "theme": "dark"}` | Returns HTML containing dark background styling |

---

## 14. SharePoint Tools [API KEY / CONFIG REQUIRED]

| # | Tool | Test Input | PASS Criteria |
|---|------|-----------|---------------|
| 95 | `sharepoint_search` | `{"query": "credit risk"}` | Returns results or "not configured" message — no crash |
| 96 | `sharepoint_documents` | `{"folder": "/Shared Documents"}` | Returns document list or auth error (no unhandled exception) |
| 97 | `sharepoint_lists` | `{}` | Returns SharePoint list names or auth error |

---

## 15. Workflow Tools (End-to-End)

Run these as chat prompts to verify full workflow execution:

| # | Workflow | Prompt | PASS Criteria |
|---|---------|--------|---------------|
| 98 | `portfolio_concentration_report` | "Run a CCR portfolio concentration report" | Produces formatted brief with signal, metrics table, breach list, md_save confirmation |
| 99 | `limit_breach_escalation` | "Show me all limit breaches as of today" | Produces escalation memo or "No breaches" message |
| 100 | `financial_institution_credit_profile` | "Pull a credit profile for JPMorgan Chase (JPM) for 2023" | Produces credit note with EDGAR metrics, SIGNAL classification, recommendation |
| 101 | `osfi_regulatory_watch` | "Run an OSFI regulatory watch brief for counterparty credit risk" | Produces regulatory memo with NEW/UPDATED table, applicability assessment, action items |
| 102 | `data_file_analysis` | "Analyse the file iris_combined.csv in the iris folder" | Produces data brief with schema, null checks, describe stats |
| 103 | `data_quality_report` | "Run a data quality report on iris_combined.csv in the iris subfolder" | Produces DQ brief with PASS/WARN/FAIL signal, null table, distribution summary |
| 104 | `op_risk_kri_monitoring` | "Analyse my KRI file kri_monthly.parquet" | Produces KRI brief with dashboard table, trend chart, RED/AMBER/GREEN status |
| 105 | `market_credit_intelligence` | "Give me a market and credit intelligence brief on TD Bank (ticker TD)" | Produces MCI brief with market snapshot, fundamentals, news, recommendation |
| 106 | `counterparty_exposure_trend` | "Show me the exposure trend for Deutsche Bank over the last 6 months" | Produces trend brief with utilisation, trajectory, chart |

---

## Dependency Map

```
Tavily API key  → tools 71-77, 62-70 (IR), osfi_fetch (if web), edgar qualitative
EDGAR (public)  → tools 52-61 (no key, rate-limited at 10 req/10s)
IRIS CSV file   → tools 9-17
Parquet/CSV     → tools 18-25, 40-42
DuckDB file     → tools 26-33
OSFI docs dir   → tools 48-51
Uploads dir     → tools 3-5, 78-88
```

## Quick Smoke Test (5 minutes)

Run these 5 in sequence to verify the core stack is alive:

1. `iris_list_dates {}` → should return dates
2. `iris_portfolio_breach_scan {"date": "<latest date>"}` → should return scan result
3. `parquet_read {"filename": "iris_combined.csv", "subfolder": "iris", "limit": 3}` → should return rows
4. `generate_chart {"data": [{"x":1,"y":2}], "chart_type": "bar", "x": "x", "y": "y", "title": "Smoke"}` → should return HTML
5. `workflow_list {}` → should return workflow names

If all 5 pass: core stack is healthy. Proceed with full test plan.
