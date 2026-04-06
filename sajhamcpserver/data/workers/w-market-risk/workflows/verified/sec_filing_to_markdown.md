# Workflow: SEC Filing Section — Fetch, Save & Read

## Fetches a named section from an SEC 10-K or 10-Q filing via EDGAR, saves it as structured markdown, then reads back a specific sub-heading on demand. Produces a clean, re-readable filing snapshot in my_data.

## Inputs:
- ticker: Stock ticker e.g. GS, JPM, BAC (required)
- company_name: Full company name e.g. Goldman Sachs (required)
- section: Filing section to extract e.g. "Risk Factors", "MD&A", "Management's Discussion", "Financial Statements" (required)
- sub_heading: Sub-section to read back after saving e.g. "Credit Ratings", "Market Risk", "Liquidity" (optional — if omitted, return full saved content)
- filing_type: 10-K or 10-Q (optional — defaults to 10-K)
- year: Four-digit fiscal year e.g. 2024 (optional — defaults to latest available)

## Step 1 — Find Filing

```
tool: edgar_find_filing
params: { "company_name": "{company_name}", "filing_type": "{filing_type}", "year": "{year}" }
```

Note the accession_number from the result. If no 10-K found, fall back to 10-Q. Canadian banks (BMO, RBC, TD, BNS, CM) file 6-K — skip edgar_find_filing and go directly to Step 2 using edgar_extract_section with ticker only.

## Step 2 — Extract Section from EDGAR

```
tool: edgar_extract_section
params: { "section": "{section}", "ticker": "{ticker}" }
```

Take the full text content returned. If the result is truncated or minimal, note it — do not fabricate content.

## Step 3 — Build Markdown and Save

Format the extracted content as clean markdown with the following structure:

```
# {company_name} — {section} ({filing_type}, Filed {filing_date})

## Overview
[1–2 sentence summary of what this section covers]

## Key Points
[Bullet-list the most important facts, figures, or risk statements extracted]

## Full Extract
[Paste the full extracted content verbatim here, preserving any sub-structure]
```

Then save:

```
tool: md_save
params: {
  "content": "{formatted_markdown}",
  "filename": "{ticker}_{filing_type}_{year}_{section_slug}.md",
  "subfolder": "sec_filings"
}
```

Where `{section_slug}` is the section name lowercased with spaces replaced by underscores, e.g. `risk_factors`, `mda`, `financial_statements`.

## Step 4 — Confirm Save and List Headings

```
tool: file_read
params: { "path": "sec_filings/{filename}", "section": "my_data" }
```

Report: filename saved, file size in chars, and list all `##` headings found in the file so the user knows what sub-sections are available for targeted reads.

## Step 5 — Read Sub-Heading (if sub_heading provided)

If `{sub_heading}` was specified:

```
tool: file_read
params: {
  "path": "sec_filings/{filename}",
  "section": "my_data",
  "heading": "{sub_heading}"
}
```

If `matched_heading` is returned, display that section's content. If not found, show `available_headings` returned by the tool so the user can pick the correct one.

## Output Format

Present the result in this order:
1. **Filing found**: company, filing type, period, accession number
2. **Section extracted**: section name, char count, any truncation warning
3. **Saved as**: full relative path in my_data
4. **Available headings**: list all `##` headings for future targeted reads
5. **Sub-section content** (if sub_heading was provided): display the matched section

## Notes for Agent
- Steps 1 and 2 are sequential. Steps 3, 4, 5 are sequential.
- If edgar_extract_section returns very little content (under 200 chars), warn the user — the section may not be present in this filing type.
- Never fabricate financial figures. Only report what EDGAR returns.
- The saved file persists in my_data/sec_filings/ and can be re-read anytime with file_read + heading= without calling EDGAR again.
- If the user later asks to re-read a specific part, use: file_read with path="sec_filings/{filename}" and heading="{sub_heading}" — no need to re-fetch from EDGAR.
