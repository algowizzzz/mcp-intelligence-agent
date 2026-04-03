# Workflow: Op Risk KRI Monitoring Brief

## Analyses a Key Risk Indicator data file (time-series KRI data), computes trend and threshold breaches, and produces a 1-2 page Op Risk monitoring brief for senior risk review.

## Inputs:
- filename: KRI data file name e.g. "kri_2026_q1.parquet" or "kri_monthly.csv" (required)
- subfolder: Subfolder within uploads e.g. "op_risk" (optional)
- kri_column: Column name holding KRI values e.g. "kri_value" (optional — inferred from schema if omitted)
- date_column: Column holding date/period e.g. "period" (optional — inferred if omitted)
- name_column: Column holding KRI name/category e.g. "kri_name" (optional — inferred if omitted)
- threshold_column: Column holding breach threshold e.g. "amber_threshold" (optional)

## Step 1 — Schema & Sample (parallel)

```
tool: parquet_read
params: { "filename": "{filename}", "subfolder": "{subfolder}", "limit": 10 }
```

## Step 2 — KRI Analysis (parallel, using columns confirmed from Step 1)

```
tool: data_transform
params: {
  "filename": "{filename}",
  "subfolder": "{subfolder}",
  "operation": "describe",
  "columns": "{kri_column}"
}
```

```
tool: data_transform
params: {
  "filename": "{filename}",
  "subfolder": "{subfolder}",
  "operation": "value_counts",
  "columns": "{name_column}"
}
```

```
tool: data_transform
params: {
  "filename": "{filename}",
  "subfolder": "{subfolder}",
  "operation": "filter",
  "column": "{kri_column}",
  "operator": "gt",
  "value": "{amber_threshold_or_p75}"
}
```

## Step 3 — Trend Chart (parallel, after Step 2)

```
tool: generate_chart
params: {
  "data": "{kri_time_series_rows}",
  "chart_type": "line",
  "x": "{date_column}",
  "y": "{kri_column}",
  "color": "{name_column}",
  "title": "KRI Trend — {filename}",
  "theme": "riskgpt",
  "save_png": true
}
```

## Step 4 — Brief

For each KRI, classify status:
- RED: current value exceeds red threshold OR is in top 5% of all historical values
- AMBER: current value exceeds amber threshold OR increased > 20% month-over-month
- GREEN: within thresholds and stable or declining

Write in exactly this format. Under 350 words.

---
**OP RISK KRI MONITORING BRIEF**
**Period:** {latest_period_in_data} | **Source:** {filename} | **Date:** {today}

**PORTFOLIO SIGNAL:** GREEN / AMBER / RED — [one reason]

**KRI STATUS DASHBOARD**
| KRI Name | Current Value | Prior Period | MoM Change | Threshold | Status |
|----------|--------------|--------------|------------|-----------|--------|
[one row per KRI; colour-code status: RED / AMBER / GREEN]

**BREACHES & ESCALATIONS**
[If any RED/AMBER items:]
- **{KRI Name}** — {current value} vs threshold {threshold} — [1 sentence on what this signals operationally]
[If no breaches:]
- No KRI threshold breaches in current period.

**TREND OBSERVATIONS**
- [Observation 1 from time-series — which KRI, direction, duration]
- [Observation 2 — if applicable]

**ROOT CAUSE INDICATORS** [where data supports inference — max 2 bullets]
- [KRI with steepest upward trend] — possible driver based on KRI category
- [Stable or improving KRI] — positive signal

**REQUIRED ACTIONS**
1. [RED items — escalate to — by when]
2. [AMBER items — owner — monitoring frequency]
3. [If all GREEN: "All KRIs within tolerance. Next scheduled review: {date + 30 days}."]

**DATA NOTE**
Periods in file: {min_date} to {max_date} | KRI count: {N} | Breach rate: {N breaches / N total readings}%

---

Save with:
```
tool: md_save
params: { "content": "{brief}", "filename": "kri_brief_{today}.md", "subfolder": "reports" }
```

## Notes for Agent
- Step 1 must complete before Step 2 (need schema). Step 2 and Step 3 run in parallel after Step 1.
- If threshold_column not present in file, use statistical proxies: AMBER = value > 75th percentile of historical distribution; RED = value > 90th percentile.
- MoM change = (current − prior) / prior × 100. If only one period exists, omit MoM column.
- Do not invent KRI categories — use name_column values verbatim.
- Wrap final output in canvas mode.
