# Workflow: Limit Breach Escalation Memo

## Scans for all active limit breaches and produces a 1-page escalation memo with severity classification and immediate action owners.

## Inputs:
- date: Snapshot date YYYY-MM-DD (optional — defaults to latest IRIS date)
- counterparty_code: Scope to a single counterparty (optional — default scans full portfolio)

## Step 1 — Breach Detection (parallel)

```
tool: iris_portfolio_breach_scan
params: { "date": "{date}" }
```

```
tool: iris_list_dates
params: {}
```

For each breached counterparty returned (max 5, by overage amount descending), run in parallel:

```
tool: iris_limit_breach_check
params: { "counterparty_code": "{code}", "date": "{date}" }
```

```
tool: tavily_news_search
params: { "query": "{counterparty_name} credit risk default 2026", "max_results": 3 }
```

## Step 2 — Memo

Classify each breach:
- CRITICAL: overage > 15% of limit OR accompanied by negative news
- WATCH: overage 5–15%
- MONITOR: overage < 5%, no news signal

Write in exactly this format:

---
**LIMIT BREACH ESCALATION MEMO**
**TO:** Credit Risk Committee **FROM:** CCR Intelligence Agent **DATE:** {date}

**SUBJECT:** {N} Active Limit Breach(es) — Action Required

**SUMMARY**
[1 sentence: number of breaches, total overage, highest severity level]

| Counterparty | Limit Key | Exposure | Limit | Overage | Severity | News Signal |
|---|---|---|---|---|---|---|
[one row per breach]

**CRITICAL ITEMS** [list only CRITICAL severity items with 1-line context from news]

**REQUIRED ACTIONS**
[one bullet per CRITICAL/WATCH breach — specific action, owner (Risk Manager / Relationship Manager / Credit Committee), deadline]

**EXPIRES:** This memo is valid for 24 hours. Re-run workflow for updated data.

---

Save with:
```
tool: md_save
params: { "content": "{memo}", "filename": "breach_escalation_{date}.md", "subfolder": "escalations" }
```

## Notes for Agent
- If zero breaches: output "No active limit breaches as of {date}" — do not generate memo.
- News lookup runs only for CRITICAL/WATCH items to save latency.
- Total written output: under 200 words. Table rows excluded from word count.
- Wrap final output in canvas mode.
