# Workflow: CCR Portfolio Concentration Brief

## Portfolio-wide breach scan, rating distribution, and top concentration names. Produces a 1-2 page executive brief.

## Inputs:
- date: Snapshot date YYYY-MM-DD (optional — defaults to latest IRIS date)

## Step 1 — Data Pull (parallel after date resolved)

Call iris_list_dates first if date not provided. Then run in parallel:

```
tool: iris_portfolio_breach_scan
params: { "date": "{date}" }
```

```
tool: iris_rating_screen
params: { "date": "{date}", "min_utilisation": 0 }
```

## Step 2 — Chart (after Step 1)

Only if breach data is non-empty:

```
tool: generate_chart
params: {
  "data": "{breach_scan_result.breaches}",
  "chart_type": "bar_horizontal",
  "x": "counterparty_name",
  "y": "overage_amount",
  "title": "Active Limit Breaches — Overage (USD)",
  "theme": "riskgpt",
  "save_png": true
}
```

## Step 3 — Brief

Write the brief in exactly this structure. No prose beyond what is specified. Every number must come from tool results.

---
**CCR PORTFOLIO BRIEF** | {date} | Risk Intelligence Agent

**SITUATION**
[1 sentence: total exposure, total limit, utilisation %, breach count]

**SIGNAL:** GREEN / AMBER / RED — [4 words max justification]

| Metric | Value |
|--------|-------|
| Total Exposure | |
| Total Limit | |
| Utilisation | |
| Active Counterparties | |
| Limit Breaches | |

**TOP CONCENTRATIONS**
- Rating: [top 2 rating buckets, exposure, % of portfolio]
- Names: [top 3 counterparties by exposure — name, amount, utilisation%]

**ACTIVE BREACHES** [None / bullet per breach: counterparty — overage — severity]

**ACTIONS**
1. [Immediate — if RED signal or breach]
2. [This week]

---

Save with:
```
tool: md_save
params: { "content": "{report}", "filename": "ccr_portfolio_{date}.md", "subfolder": "reports" }
```

## Notes for Agent
- Step 1 parallel. Step 2 only if breaches > 0. Step 3 is LLM-only except md_save.
- Keep total written content under 300 words. Every line is data, not explanation.
- Wrap final output in canvas mode.
