# Workflow: Counterparty Exposure Trend Brief

## Tracks a single counterparty's exposure trajectory over time, compares to limit, and identifies trend inflection points. Produces a 1-page risk brief for a CCR analyst or relationship manager review.

## Inputs:
- counterparty_name: Name or partial name e.g. "Deutsche Bank" (required)
- date: Snapshot date YYYY-MM-DD (optional — defaults to latest IRIS date)
- lookback_months: How many months of trend to show (optional — default 6)

## Step 1 — Resolve Counterparty + Date (parallel)

```
tool: iris_search_counterparties
params: { "name": "{counterparty_name}" }
```

```
tool: iris_list_dates
params: {}
```

## Step 2 — Exposure Data (parallel, using counterparty_code from Step 1)

```
tool: iris_counterparty_dashboard
params: { "counterparty_code": "{counterparty_code}", "date": "{date}" }
```

```
tool: iris_limit_breach_check
params: { "counterparty_code": "{counterparty_code}", "date": "{date}" }
```

```
tool: iris_exposure_trend
params: { "counterparty_code": "{counterparty_code}", "lookback_months": "{lookback_months}" }
```

```
tool: tavily_news_search
params: { "query": "{counterparty_name} credit risk financial health 2026", "max_results": 3 }
```

## Step 3 — Trend Chart (after Step 2)

```
tool: generate_chart
params: {
  "data": "{exposure_trend_rows}",
  "chart_type": "line",
  "x": "date",
  "y": ["exposure", "limit"],
  "title": "{counterparty_name} — Exposure vs Limit Trend",
  "theme": "riskgpt",
  "save_png": true
}
```

## Step 4 — Brief

Classify exposure trajectory:
- INCREASING: Exposure grew > 10% over lookback period
- STABLE: Exposure within ±10% over lookback period
- DECREASING: Exposure fell > 10% over lookback period

Classify limit utilisation:
- HIGH: utilisation > 80%
- MODERATE: utilisation 50–80%
- LOW: utilisation < 50%

Write in exactly this format. Under 300 words.

---
**COUNTERPARTY EXPOSURE TREND BRIEF**
**{counterparty_name}** | As of {date} | CCR Intelligence Agent

**SIGNAL:** GREEN / AMBER / RED — [4 words max]

**CURRENT POSITION**
| Metric | Value |
|--------|-------|
| Current Exposure | |
| Limit | |
| Utilisation % | |
| Limit Breach | Yes / No |
| Breach Amount (if any) | |

**EXPOSURE TREND** ({lookback_months}-month lookback)
| Date | Exposure | Limit | Utilisation % |
|------|----------|-------|---------------|
[one row per period from trend data — latest 6 rows max]

**TRAJECTORY:** INCREASING / STABLE / DECREASING — [1 sentence: rate of change and direction]

**LIMIT UTILISATION:** HIGH / MODERATE / LOW — [1 sentence on headroom]

**NEWS SIGNAL** (last 30 days)
- [Top relevant news item — source — implication for credit exposure]
- [If no news: "No material news identified in period."]

**CREDIT ASSESSMENT**
[1 sentence: overall read on counterparty exposure health combining utilisation, trend, and news]

**ACTIONS**
1. [If RED or INCREASING + HIGH utilisation: specific action — owner — deadline]
2. [If AMBER: monitoring recommendation]
3. [If GREEN: "No action required. Next review: {date + 30 days}."]

---

Save with:
```
tool: md_save
params: { "content": "{brief}", "filename": "exposure_trend_{counterparty_code}_{date}.md", "subfolder": "reports" }
```

## Notes for Agent
- Step 1 parallel. Step 2 parallel (depends on counterparty_code from Step 1). Step 3 and Step 4 depend on Step 2.
- If multiple counterparties match the name search, pick the closest match by name similarity and note the full name used.
- AMBER signal if: utilisation > 80% OR trajectory INCREASING, no breach. RED signal if: active breach OR utilisation > 100%.
- Wrap final output in canvas mode.
