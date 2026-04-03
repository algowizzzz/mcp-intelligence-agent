---
name: Counterparty Intelligence Brief (New Tools)
description: >
  5-step CCR + news intelligence workflow using data-agnostic tools only.
  data_transform on iris_combined.csv handles all exposure, limit and trend
  analytics. generate_chart, fill_template and md_save produce the final brief.
inputs:
  - counterparty_name: Full or partial counterparty name e.g. Royal Bank of Canada (required)
  - news_days: Days back for news search (optional — default 14)
tags: [credit-risk, ccr, counterparty, new-tools, charts, iris]
version: "1.3"
tool_mapping:
  iris_list_dates:             data_transform group by Date → distinct snapshot dates
  iris_search_counterparties:  data_transform filter on Customer Name
  iris_counterparty_dashboard: data_transform group by Product (latest date snapshot)
  iris_limit_breach_check:     data_transform 2b result — LLM flags utilization_pct > 100%
  iris_limit_lookup:           data_transform 2b result — sorted by product_exposure DESC
  iris_exposure_trend:         data_transform group by Date (2a) + generate_chart line
  NEW generate_chart:          embedded product utilisation bar + exposure trend line
  NEW fill_template + md_save: structured saved brief output
iris_csv_path: "./data/domain_data/iris/iris_combined.csv"
---

# Workflow: Counterparty Intelligence Brief (New Tools)

## Step 1 — News Intelligence

Execute all four calls simultaneously in parallel.

```
tool: tavily_news_search
params: { "query": "{counterparty_name} financial news credit risk 2026", "max_results": 5 }
```

```
tool: tavily_news_search
params: { "query": "{counterparty_name} credit rating downgrade outlook S&P Moody's Fitch 2026", "max_results": 4 }
```

```
tool: tavily_news_search
params: { "query": "{counterparty_name} earnings capital guidance outlook 2026", "max_results": 3 }
```

```
tool: tavily_news_search
params: { "query": "{counterparty_name} default restructuring regulatory stress 2026", "max_results": 3 }
```

## Step 2 — IRIS CSV Analytics

Execute both calls simultaneously in parallel. Steps 1 and 2 run in parallel with each other.

### 2a — Exposure Trend by Date
Replaces: `iris_exposure_trend`

```
tool: data_transform
params:
  file_path: "./data/domain_data/iris/iris_combined.csv"
  filters:
    - { "column": "Customer Name", "operator": "contains", "value": "{counterparty_name}" }
  group_by: ["Date"]
  aggregations:
    - { "column": "Product Exposure", "function": "sum", "alias": "total_exposure" }
    - { "column": "Product Limit",    "function": "sum", "alias": "total_limit" }
    - { "column": "Product Avail",    "function": "sum", "alias": "total_avail" }
  sort_by:
    - { "column": "Date", "ascending": true }
```

Store result as `iris_trend`. Set `as_of_date` to the last Date value in the result.
If the result is empty, stop and report: "Counterparty not found in iris_combined.csv — check spelling."

### 2b — Product Utilisation Snapshot
Replaces: `iris_counterparty_dashboard` + `iris_limit_lookup`

```
tool: data_transform
params:
  file_path: "./data/domain_data/iris/iris_combined.csv"
  filters:
    - { "column": "Customer Name", "operator": "contains", "value": "{counterparty_name}" }
  group_by: ["Date", "Product"]
  aggregations:
    - { "column": "Product Exposure", "function": "sum", "alias": "product_exposure" }
    - { "column": "Product Limit",    "function": "sum", "alias": "product_limit" }
    - { "column": "Product Avail",    "function": "sum", "alias": "product_avail" }
  sort_by:
    - { "column": "Date",             "ascending": false }
    - { "column": "product_exposure", "ascending": false }
```

From this result, keep only rows where Date equals `as_of_date`. Store as `iris_products`.
For each row compute `utilization_pct = product_exposure / product_limit * 100`.
Flag any row where utilization_pct > 100 as a breach — replaces `iris_limit_breach_check`.

## Step 3 — Visualisation

Execute both calls simultaneously in parallel after Step 2 completes.

### 3a — Product Utilisation Bar Chart

```
tool: generate_chart
params:
  chart_type: "bar_horizontal"
  data: [use iris_products rows from Step 2b — each row has Product, product_exposure, product_limit, utilization_pct]
  x: "utilization_pct"
  y: "Product"
  title: "{counterparty_name} — Product Limit Utilisation (%) as of {as_of_date}"
  x_label: "Utilisation (%)"
  y_label: "Product"
  theme: "riskgpt"
  width: 700
  height: 320
```

### 3b — Exposure vs Limit Trend Line Chart

```
tool: generate_chart
params:
  chart_type: "line"
  data: [use iris_trend rows from Step 2a — each row has Date, total_exposure, total_limit]
  x: "Date"
  y: ["total_exposure", "total_limit"]
  title: "{counterparty_name} — Exposure vs Limit Trend"
  x_label: "Snapshot Date"
  y_label: "Amount"
  theme: "riskgpt"
  width: 700
  height: 320
```

Store the `html` field from each result as `chart_utilisation_html` and `chart_trend_html`.

## Step 4 — Integrated Risk Analysis

You are a senior counterparty risk analyst. Use all data from Steps 1–3. No tool calls in this step.

### 4a — News Signal Assessment
Classify each article: POSITIVE / NEUTRAL / NEGATIVE / MATERIAL_RISK.
Flag items affecting creditworthiness: rating actions, regulatory findings, earnings misses, liquidity stress.

### 4b — Exposure & Limit Summary
From `iris_products`: list all products with product_exposure, product_limit, product_avail, utilization_pct.
Identify the tightest product (highest utilization_pct). State headroom = product_avail clearly.
From `iris_trend`: state total_exposure and total_limit at `as_of_date`.

### 4c — Breach Flags
Scan `iris_products` for any row where utilization_pct > 100.
For each breach: state Product, product_limit, product_exposure, overage = product_exposure − product_limit, utilization_pct.
Cross-reference with any NEGATIVE or MATERIAL_RISK news signal.

### 4d — Trend Narrative
From `iris_trend`: state total_exposure at earliest and latest Date. Compute delta.
Classify as Increasing / Stable / Decreasing.
Flag if consistently increasing AND latest total_exposure exceeds 75% of total_limit.

### 4e — Assign Overall Risk Signal
- **GREEN**: No breaches, no MATERIAL_RISK news, all products below 75% utilisation, trend flat or decreasing.
- **AMBER**: No breach but ≥1 product >75%, or mixed news signals, or moderate upward trend.
- **RED**: ≥1 breach (utilization_pct > 100), or MATERIAL_RISK news confirmed, or rating downgrade.

## Step 5 — Template Fill & Save

### 5a — Fill the template

```
tool: fill_template
params:
  template_path: "./data/domain_data/templates/cpty_intel_brief.md"
  data:
    counterparty_name:        "{counterparty_name}"
    as_of_date:               "{as_of_date from Step 2}"
    credit_rating:            "{Customer Internal Rating from iris_products rows}"
    overall_signal:           "{GREEN | AMBER | RED from Step 4e}"
    signal_justification:     "{one-sentence justification from Step 4e}"
    total_notional_usd:       "N/A — not in IRIS CSV"
    total_mtm_usd:            "N/A — not in IRIS CSV"
    total_pfe_usd:            "N/A — not in IRIS CSV"
    net_exposure_usd:         "N/A — not in IRIS CSV"
    collateral_posted_usd:    "N/A — not in IRIS CSV"
    headroom_usd:             "{product_avail of tightest product formatted}"
    tightest_limit_type:      "{Product with highest utilization_pct}"
    tightest_utilisation_pct: "{that utilization_pct as a number}"
    active_breaches_summary:  "{breach list from Step 4c, or 'None'}"
    top_asset_class:          "N/A — not in IRIS CSV"
    top_asset_notional_usd:   "N/A — not in IRIS CSV"
    var_99_usd:               "N/A — not in IRIS CSV"
    stress_var_usd:           "N/A — not in IRIS CSV"
    stress_scenario:          "N/A — not in IRIS CSV"
    trend_direction:          "{Increasing | Stable | Decreasing from Step 4d}"
    trend_delta_usd:          "{delta formatted, e.g. +$42M}"
    key_finding_1:            "{finding with source citation [src:...]}"
    key_finding_2:            "{finding with source citation [src:...]}"
    key_finding_3:            "{finding with source citation [src:...]}"
    key_finding_4:            "{finding with source citation [src:...]}"
    key_finding_5:            "{finding with source citation [src:...]}"
    action_priority_1:        "{Immediate action}"
    action_priority_2:        "{This-week action}"
    action_priority_3:        "{Monitor action}"
    chart_utilisation_html:   "{html field from Step 3a result}"
    chart_trend_html:         "{html field from Step 3b result}"
  output_subfolder: "counterparty_briefs"
```

### 5b — Save to my_data

```
tool: md_save
params:
  content:   "{content field from fill_template result}"
  filename:  "cpty_intel_{counterparty_name}_{as_of_date}.md"
  subfolder: "counterparty_briefs"
```

### 5c — Deliver in canvas mode
Wrap the `content` from fill_template in a canvas envelope and deliver to the user.
Both chart HTML blocks are already embedded via the `chart_utilisation_html` and `chart_trend_html` placeholders.

## Notes for Agent

**Parallelisation:**
- Steps 1 and 2 run fully in parallel with each other (all 6 calls simultaneously).
- Step 3: both generate_chart calls run simultaneously after Step 2 completes.
- Step 4: LLM synthesis — no tool calls.
- Step 5: fill_template first, then md_save with the returned content field.

**Tool mapping reference (IRIS → New Tools):**
| Original IRIS Tool            | Replacement in this workflow                                           |
|-------------------------------|------------------------------------------------------------------------|
| iris_list_dates               | data_transform group by Date → distinct snapshot dates                 |
| iris_search_counterparties    | data_transform filter on Customer Name → resolves the match            |
| iris_counterparty_dashboard   | data_transform group by Product (Step 2b, latest date)                 |
| iris_limit_breach_check       | Step 2b result — LLM flags rows where utilization_pct > 100            |
| iris_limit_lookup             | Step 2b result — sorted by product_exposure DESC                       |
| iris_exposure_trend           | data_transform group by Date (Step 2a) + generate_chart line           |
| (no IRIS equivalent)          | generate_chart → embedded visuals in canvas output                     |
| (no IRIS equivalent)          | fill_template + md_save → structured persistent brief                  |

**Data integrity rules:**
- All IRIS CSV figures are in the currency stated in the `Product Limit Currency` column — note this in the brief.
- Never report a breach unless utilization_pct > 100 is computed from the actual data.
- Append `[src:{_source}]` after every specific figure cited from a tool result.
- Fields marked "N/A — not in IRIS CSV" should be omitted from the brief or noted as not available.
