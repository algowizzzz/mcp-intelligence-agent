# Workflow: Data File Analysis & Transform Brief

## 4-step analysis of any CSV or Parquet file — inspect, filter, aggregate, and export a structured brief using data-agnostic tools.

## Inputs:
- file_path: Path to a CSV or Parquet file e.g. ./data/uploads/exposure.csv (required — call list_uploaded_files first if unsure)
- filter_column: Column to filter rows on (optional — agent infers from schema if not provided)
- filter_value: Value to filter on (optional — e.g. Royal Bank of Canada)
- group_column: Column to group-by for aggregation (optional — agent infers from schema)
- metric_column: Numeric column to aggregate (optional — agent infers from schema)
- output_filename: Name for the exported result (optional — defaults to analysis_result.csv)

## Step 1 — Schema Confirmation

Call parquet_read to confirm the actual column names before building any transform calls.
If the user provided filter_column, group_column, and metric_column, you already have candidate names — but still call parquet_read to validate they exist and get data types, null counts, and value ranges.

```
tool: parquet_read
params: {
  "file_path": "{file_path}",
  "sample_rows": 10,
  "include_stats": true
}
```

After parquet_read returns, lock in the confirmed column names:
- If user-supplied column names appear in the schema → use them exactly as returned
- If not supplied → infer: filter_column = first object/string column, group_column = second categorical column, metric_column = first numeric column
- Note null rates and value ranges from stats — reference these in Step 3

## Step 2 — Parallel Transforms

Execute all three transforms simultaneously using the confirmed column names from Step 1:

```
tool: data_transform
params: {
  "file_path": "{file_path}",
  "filters": [{ "column": "{filter_column}", "operator": "==", "value": "{filter_value}" }],
  "sort_by": [{ "column": "{metric_column}", "ascending": false }],
  "limit": 100
}
```

```
tool: data_transform
params: {
  "file_path": "{file_path}",
  "filters": [{ "column": "{filter_column}", "operator": "==", "value": "{filter_value}" }],
  "group_by": ["{group_column}"],
  "aggregations": { "{metric_column}": "sum" },
  "sort_by": [{ "column": "{metric_column}_sum", "ascending": false }]
}
```

```
tool: data_transform
params: {
  "file_path": "{file_path}",
  "filters": [{ "column": "{filter_column}", "operator": "==", "value": "{filter_value}" }],
  "group_by": ["{filter_column}"],
  "aggregations": { "{metric_column}": "sum" }
}
```

Note: If filter_value was not provided, omit filters and run transforms on the full dataset. If group_column is absent, skip the group_by transform and replace with a top-N sort instead.

## Step 3 — Integrated Analysis

You are a senior data analyst. Using the schema from Step 1 and the transform results from Step 2, produce a structured analysis:

1. DATA PROFILE
Summarise: row count, column count, key identifiers, and numeric ranges from stats.
Flag any columns with null rate >20% or where max > 5x mean (skewed).

2. ENTITY SUMMARY (if filter applied)
How many rows match the filter? What is the total and average of the metric column?
Is the entity over- or under-represented relative to the dataset average?

3. BREAKDOWN BY GROUP
From the group_by result: which group has the highest total? Quantify top 3 with share of total (%).

4. OUTLIERS & ANOMALIES
Using min/max/mean from stats: flag rows or groups more than 2x the mean.

5. DATA QUALITY FLAGS
List columns with nulls, unexpected dtypes, or zero/negative values in a numeric column.

## Step 4 — Export & Brief

First, export the group_by summary to my_data:

```
tool: data_export
params: {
  "data": "{group_by_transform_result.data}",
  "filename": "{output_filename}",
  "format": "csv",
  "subfolder": "exports",
  "versioning": true
}
```

Then write the brief in exactly this structure:

FILE: [filename, format, row count, column count]
ANALYSIS SCOPE: [filter applied / full dataset]
OVERALL SIGNAL: [CLEAN / WARN / FLAG]
[One sentence justification]

KEY FINDINGS (max 5 bullet points):
Each finding must reference a column name and a numeric value from the transform results.

METRIC SUMMARY:
Top 3 groups by {metric_column} — group, sum, share of total (%).

DATA QUALITY:
[PASS / list of flagged columns with issue type]

EXPORT: [filename, rows written, path]

PREPARED BY: Data Analysis Agent | {today's date}

## Notes for Agent
- Step 1 must complete before Step 2 — column names from parquet_read lock in the exact field names. Do not guess column names from user input alone; always validate against the schema first.
- Within Step 2, all transform calls run in parallel.
- If filter_value returns zero rows, report this and re-run without filters.
- data_export receives the .data array from the group_by transform result directly.
- Steps 3 and 4 synthesis are LLM-only — no additional tool calls except data_export at the start of Step 4.
- Wrap final output in canvas mode.
