# Workflow: OSFI Regulatory Watch Brief

## Scans OSFI announcements and guidance documents for recent updates, assesses applicability to CCR/Op Risk functions, and produces a 1-page regulatory watch memo.

## Inputs:
- topic: Regulatory area of focus e.g. "counterparty credit risk" or "operational resilience" (optional — scans all if omitted)
- days_back: How many days of announcements to scan (optional — default 30)

## Step 1 — OSFI Intelligence (parallel)

```
tool: osfi_fetch_announcements
params: { "days_back": "{days_back}" }
```

```
tool: osfi_list_docs
params: {}
```

```
tool: osfi_search_guidance
params: { "query": "{topic}", "max_results": 5 }
```

## Step 2 — Deep Read (parallel, for top 2 most relevant documents from Step 1)

```
tool: osfi_read_document
params: { "filename": "{most_relevant_doc_1}" }
```

```
tool: osfi_read_document
params: { "filename": "{most_relevant_doc_2}" }
```

## Step 3 — Regulatory Memo

For each announcement or document change, classify:
- EFFECTIVE NOW: already in force
- UPCOMING: proposed or consultation period
- MONITOR: draft / early stage

Write in exactly this format. Under 300 words.

---
**OSFI REGULATORY WATCH**
**Period:** Last {days_back} days | **Focus:** {topic} | **Date:** {today}

**NEW / UPDATED GUIDANCE**
| Document | Type | Status | Effective Date | Key Change |
|---|---|---|---|---|
[one row per relevant item]

**APPLICABILITY ASSESSMENT**
- CCR Impact: [HIGH / MEDIUM / LOW] — [1 sentence on what specifically changes]
- Op Risk Impact: [HIGH / MEDIUM / LOW] — [1 sentence]
- Capital Impact: [HIGH / MEDIUM / LOW] — [1 sentence]

**ACTION ITEMS**
1. [Specific action — owner — deadline]
2. [Specific action — owner — deadline]
3. [If nothing new: "No material regulatory changes in period. Next watch: {date + 30 days}"]

**REFERENCE DOCUMENTS**
[List doc names used with their OSFI category]

---

Save with:
```
tool: md_save
params: { "content": "{memo}", "filename": "osfi_watch_{today}.md", "subfolder": "regulatory" }
```

## Notes for Agent
- Step 1 parallel. Step 2 parallel (only for documents actually returned in Step 1).
- If no announcements in the period, state this explicitly — do not fabricate updates.
- Keep applicability assessment grounded in document content only.
- Wrap final output in canvas mode.
