# Workflow: Data Quality & Governance Report

## Profiles a parquet or CSV data file for completeness, integrity, and distribution issues. Produces a 1-2 page data governance brief suitable for an Op Risk or Data Steward review.

## Inputs:
- filename: File name in uploads folder e.g. "trades_q1.parquet" (required)
- subfolder: Subfolder within uploads e.g. "iris" (optional)
- key_columns: Comma-separated columns to prioritise for null/outlier checks e.g. "exposure,counterparty_code,date" (optional — profiles all if omitted)

## Step 1 — Schema & Sample (parallel)

```
tool: parquet_read
params: { "filename": "{filename}", "subfolder": "{subfolder}", "limit": 5 }
```

```
tool: list_uploaded_files
params: { "subfolder": "{subfolder}" }
```

## Step 2 — Profile (parallel, using columns confirmed from Step 1 schema)

```
tool: data_transform
params: {
  "filename": "{filename}",
  "subfolder": "{subfolder}",
  "operation": "null_check",
  "columns": "{key_columns_or_all}"
}
```

```
tool: data_transform
params: {
  "filename": "{filename}",
  "subfolder": "{subfolder}",
  "operation": "describe",
  "columns": "{numeric_columns}"
}
```

```
tool: data_transform
params: {
  "filename": "{filename}",
  "subfolder": "{subfolder}",
  "operation": "value_counts",
  "columns": "{categorical_columns}"
}
```

## Step 3 — Chart (after Step 2, only if null_check returns at least one column with nulls > 0)

```
tool: generate_chart
params: {
  "data": "{null_check_result}",
  "chart_type": "bar_horizontal",
  "x": "column",
  "y": "null_count",
  "title": "Null Count by Column — {filename}",
  "theme": "riskgpt",
  "save_png": true
}
```

## Step 4 — Brief

Classify overall data quality:
- PASS: null rate < 1% on all key columns, no duplicate keys detected
- WARN: null rate 1–5% on any key column OR duplicate keys found
- FAIL: null rate > 5% on any key column OR primary key is fully null

Write in exactly this format. Under 350 words.

---
**DATA QUALITY BRIEF** | {filename} | {today} | Op Risk / Data Governance

**SIGNAL:** PASS / WARN / FAIL — [4 words max justification]

**FILE SUMMARY**
| Attribute | Value |
|-----------|-------|
| Row Count | |
| Column Count | |
| File Size | |
| Data Period (if date col present) | |

**NULL & COMPLETENESS**
| Column | Null Count | Null % | Assessment |
|--------|-----------|--------|------------|
[one row per key column; flag any > 1% as WARN, > 5% as FAIL]

**DISTRIBUTION SUMMARY** (numeric columns only)
| Column | Min | Max | Mean | Std Dev | Outlier Flag |
|--------|-----|-----|------|---------|--------------|
[one row per numeric column; flag as outlier if max > mean + 3×std]

**TOP CATEGORICAL VALUES** (first categorical column only, top 5 values)
| Value | Count | % of Total |
|-------|-------|------------|

**DATA QUALITY FINDINGS**
- [Finding 1 — specific column/metric — severity]
- [Finding 2 — specific column/metric — severity]
- [If PASS: "No material data quality issues detected."]

**RECOMMENDED ACTIONS**
1. [Specific remediation — data owner — deadline]
2. [Monitoring cadence recommendation]
3. [If PASS: "Proceed to downstream use. Schedule next quality review in 30 days."]

**LINEAGE NOTE**
Source: {filename} | Location: uploads/{subfolder} | Profiled: {today}

---

Save with:
```
tool: md_save
params: { "content": "{brief}", "filename": "dq_report_{filename}_{today}.md", "subfolder": "reports" }
```

## Notes for Agent
- Step 1 and Step 2 are sequential (need schema from Step 1 to select columns for Step 2). Within each step, all calls parallel.
- If file not found in Step 1, stop and report: "File not found — check filename and subfolder."
- Do not impute or fix data — report only what is observed.
- Outlier flag = True if max > mean + 3×std dev; surface these as findings.
- Wrap final output in canvas mode.
