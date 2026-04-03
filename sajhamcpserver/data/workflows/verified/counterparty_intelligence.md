# Workflow: Counterparty Intelligence Brief

## 4-step CCR + news intelligence combining IRIS internal data with Tavily market news.

## Inputs:
- counterparty_name: Full or partial counterparty name e.g. Royal Bank of Canada (required)
- date: Snapshot date YYYY-MM-DD (optional — defaults to latest IRIS date)
- news_days: Days back for news search (optional — default 7)
- trend_from: Start date for exposure trend YYYY-MM-DD (optional)

## Step 1 — News Intelligence

Execute ALL four of the following tool calls in parallel:

```
tool: tavily_news_search
params: { "query": "{counterparty_name} financial news", "max_results": 5 }
```

```
tool: tavily_news_search
params: { "query": "{counterparty_name} credit risk regulatory 2026", "max_results": 5 }
```

```
tool: tavily_news_search
params: { "query": "{counterparty_name} earnings results outlook", "max_results": 3 }
```

```
tool: tavily_news_search
params: { "query": "{counterparty_name} default bankruptcy restructuring distress", "max_results": 3 }
```

## Step 2 — IRIS Data Pull

First call iris_list_dates to get the latest available date.
Then call iris_search_counterparties to resolve the counterparty code.
Then execute the following three tool calls in parallel using the resolved code:

```
tool: iris_counterparty_dashboard
params: { "counterparty_code": "{resolved_code}", "date": "{date}" }
```

```
tool: iris_limit_breach_check
params: { "counterparty_code": "{resolved_code}", "date": "{date}" }
```

```
tool: iris_exposure_trend
params: { "counterparty_code": "{resolved_code}", "date_from": "{trend_from}", "date_to": "{date}" }
```

## Step 3 — Integrated Risk Analysis

You are a senior counterparty risk analyst at a financial institution. Using the news from Step 1 and the IRIS data from Step 2, perform an integrated analysis:

1. NEWS SIGNAL ASSESSMENT
Classify each news item: POSITIVE / NEUTRAL / NEGATIVE / MATERIAL_RISK.
Identify any news that directly affects creditworthiness.
Flag any regulatory, legal, or financial stress signals.

2. INTERNAL EXPOSURE SUMMARY
Summarise current total exposure across all products and legal entities.
Identify the largest product exposure and highest utilisation rates.
State current headroom clearly.

3. BREACH AND STRESS FLAGS
List any active limit breaches with limit_key, overage amount, and severity.
Correlate breaches with any negative news signals.

4. TREND ANALYSIS
Is exposure increasing, decreasing, or stable? Quantify the delta and flag if the trend is concerning.

5. CORRELATION: NEWS vs INTERNAL DATA
Does internal CCR data corroborate or contradict news signals?
Flag divergences that warrant escalation.

## Step 4 — Executive Brief

Write a concise executive intelligence brief for a senior risk manager. Use exactly this structure:

COUNTERPARTY: [Name, Code, Internal Rating, Country]
OVERALL RISK SIGNAL: [GREEN / AMBER / RED]
[One sentence justification for the signal]

KEY FINDINGS (max 5 bullet points):
Each finding must reference either a news source or an IRIS limit_key.

EXPOSURE SNAPSHOT:
Top 3 exposures by product — limit, exposure, headroom, currency.

ACTIVE BREACHES: [None / list with limit_key and overage]

RECOMMENDED ACTIONS:
Priority 1 (Immediate): ...
Priority 2 (This week): ...
Priority 3 (Monitor): ...

PREPARED BY: IRIS CCR Intelligence Agent | {date}

## Notes for Agent
- Execute Steps 1 and 2 before Step 3. Steps 1 and 2 can run in parallel with each other.
- Within Step 1, all 4 tavily calls run in parallel.
- Within Step 2, the 3 IRIS calls (dashboard, breach, trend) run in parallel after counterparty is resolved.
- Step 3 and Step 4 are LLM synthesis — no tool calls.
- Wrap final output in canvas mode.
