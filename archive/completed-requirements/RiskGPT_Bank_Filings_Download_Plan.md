# Bank Filings Data Download Plan
## 10-K / 10-Q (US) and 40-F / 6-K / Annual Reports (Canada)
**Scope:** Past 5 years (FY2020–FY2025) | **Date:** 2026-04-03

---

## 1. Target Companies

### US Banks — SEC EDGAR (10-K annual, 10-Q quarterly)

| # | Bank | Ticker | CIK | Notes |
|---|------|--------|-----|-------|
| 1 | JPMorgan Chase | JPM | 0000019617 | Largest US bank by assets |
| 2 | Bank of America | BAC | 0000070858 | |
| 3 | Wells Fargo | WFC | 0000072971 | |
| 4 | Citigroup | C | 0000831001 | |
| 5 | Goldman Sachs | GS | 0000886982 | |
| 6 | Morgan Stanley | MS | 0000895421 | |
| 7 | US Bancorp | USB | 0000036104 | |
| 8 | Truist Financial | TFC | 0000092230 | |
| 9 | PNC Financial | PNC | 0000713676 | |
| 10 | Capital One | COF | 0000927628 | |

**Filing types:** `10-K` (1/year) + `10-Q` (3/year) = **4 filings/bank/year**
**5-year volume:** 10 banks × 4 × 5 = **~200 US filings**

---

### Canadian Banks — SEC EDGAR (40-F annual, 6-K quarterly)

| # | Bank | Ticker | CIK | Notes |
|---|------|--------|-----|-------|
| 1 | Royal Bank of Canada | RY | 0001000275 | Largest CA bank |
| 2 | Toronto-Dominion Bank | TD | 0000947263 | |
| 3 | Bank of Nova Scotia | BNS | 0000009631 | |
| 4 | Bank of Montreal | BMO | 0000927971 | |
| 5 | CIBC | CM | 0001045520 | |
| 6 | National Bank of Canada | NA | N/A — SEDAR+ only | Not SEC-registered |

**Filing types:** `40-F` (1/year) + `6-K` (quarterly supplements) = ~4–6/bank/year
**5-year volume:** 5 SEC-filing CA banks × ~5 × 5 = **~125 Canadian SEC filings**
**National Bank:** Manual download from SEDAR+ or investor relations site

**Note:** Canadian banks file annual reports on their fiscal year (Oct 31 year-end for RY, TD, BNS, BMO, CIBC; Oct 31 for NA). 6-K filings contain quarterly reports and supplementary packages.

---

## 2. Filing Volume Estimate

| Source | Banks | Filing Types | Years | Est. Filings |
|--------|-------|--------------|-------|-------------|
| SEC EDGAR US | 10 | 10-K, 10-Q | 5 | ~200 |
| SEC EDGAR CA | 5 | 40-F, 6-K | 5 | ~125 |
| SEDAR+ / IR site | 1 (National Bank) | Annual, Quarterly | 5 | ~20 |
| **Total** | **16** | | | **~345** |

Average filing size: 5–25 MB (HTML), 500 KB–3 MB (converted MD)
Estimated total storage: ~3–8 GB raw HTML, ~500 MB–1 GB as Markdown

---

## 3. Data Sources & APIs

### 3.1 SEC EDGAR (US + Canadian banks)
- **Submissions endpoint:** `https://data.sec.gov/submissions/CIK{cik_padded}.json`
  Returns full filing history with accession numbers, dates, and document names
- **Document URL pattern:**
  `https://www.sec.gov/Archives/edgar/data/{cik}/{accessionNoDashes}/{primaryDoc}`
- **Rate limit:** Max 10 req/sec; `User-Agent` header required
- **No API key needed**

### 3.2 SEDAR+ (National Bank of Canada)
- Web portal: `https://www.sedarplus.ca/`
- No official programmatic API; documents must be downloaded via browser automation (Playwright)
- Search by issuer: "National Bank of Canada", filter by Annual Report / Quarterly Report

### 3.3 National Bank IR Fallback
- Investor Relations: `https://www.nbc.ca/en/about-us/investors.html`
- Annual reports and quarterly supplements available as PDFs

---

## 4. Folder Structure

```
bank_filings/
├── us/
│   ├── jpm/
│   │   ├── 10k/
│   │   │   ├── JPM_10K_2020.htm
│   │   │   ├── JPM_10K_2020.md
│   │   │   └── ...
│   │   └── 10q/
│   │       ├── JPM_10Q_2020Q1.htm
│   │       ├── JPM_10Q_2020Q1.md
│   │       └── ...
│   ├── bac/
│   ├── wfc/
│   ├── c/
│   ├── gs/
│   ├── ms/
│   ├── usb/
│   ├── tfc/
│   ├── pnc/
│   └── cof/
└── canada/
    ├── ry/
    │   ├── 40f/
    │   └── 6k/
    ├── td/
    ├── bns/
    ├── bmo/
    ├── cm/
    └── na/          ← SEDAR+ / IR manual
        ├── annual/
        └── quarterly/
```

Alongside each filing: a `.json` sidecar with metadata (CIK, form type, period, accession number, date filed, source URL).

---

## 5. Download Strategy

### Phase 1 — Index & Inventory (no downloads yet)
1. Hit EDGAR submissions API for all 15 SEC-registered banks
2. Filter filings: form type in `{10-K, 10-Q, 40-F, 6-K}`, date >= 2020-01-01
3. Build a master CSV/JSON inventory of every filing: bank, form, period, accession, doc URL
4. Flag any gaps (missing quarters, years)
5. Output: `bank_filings/filing_inventory.json`

### Phase 2 — US Banks (10-K + 10-Q)
- Download primary HTML document for each filing
- Prefer `.htm` over `.txt` for readability
- For 10-K filings: also attempt to grab exhibits (EX-13 if separate annual report)
- Rate-limit: 1 req/sec with exponential backoff on 429/503
- Save raw HTML + convert to Markdown immediately
- Write to manifest after each file

### Phase 3 — Canadian Banks on EDGAR (40-F + 6-K)
- Same approach as Phase 2
- 40-F filings often reference the Canadian Annual Report as an exhibit
- 6-K filings: only grab quarterly earnings supplements (not every 6-K; filter by subject)

### Phase 4 — National Bank (SEDAR+)
- Use Playwright to navigate SEDAR+ search
- Filter: Issuer = "National Bank of Canada", Doc type = Annual Report / Quarterly Report
- Download PDFs, convert to Markdown

### Phase 5 — Conversion & Cleanup
- All HTML → Markdown via html2text
- All PDF → Markdown via pypdf
- Strip navigation boilerplate, headers/footers
- Validate each MD has substantive content (>10 KB)

---

## 6. Manifest & Tracking

All progress tracked in `bank_filings/manifest.json`:

```json
{
  "generated": "2026-04-03",
  "summary": {
    "total_planned": 345,
    "downloaded": 0,
    "converted": 0,
    "failed": 0,
    "missing": 0
  },
  "filings": [
    {
      "bank": "JPM",
      "form": "10-K",
      "period": "2024-12-31",
      "fiscal_year": 2024,
      "accession": "0000019617-25-000021",
      "source_url": "https://...",
      "raw_file": "bank_filings/us/jpm/10k/JPM_10K_2024.htm",
      "md_file": "bank_filings/us/jpm/10k/JPM_10K_2024.md",
      "status": "ok | failed | missing | skipped",
      "size_kb": 12400,
      "downloaded_at": "2026-04-03T14:00:00Z"
    }
  ]
}
```

A separate `bank_filings/GAPS.md` will list every missing or failed filing with the reason.

---

## 7. Known Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| EDGAR rate limit (10 req/sec) | Sleep 0.15s between requests; backoff on 429 |
| Large file sizes (10-K = 10–50 MB HTML) | Stream download; skip if >100 MB |
| 6-K filings are numerous and varied | Filter by 6-K description keyword: "quarterly", "results", "interim" |
| SEDAR+ no API | Playwright browser automation; fall back to IR site PDFs |
| Canadian bank fiscal year is Oct 31 | Filter by period-of-report, not calendar year |
| Filing amended (10-K/A, 10-Q/A) | Download both original and amendment; note in manifest |
| Some older filings are `.txt` SGML | Parse and strip SGML tags before MD conversion |

---

## 8. Implementation Files (to be created)

| File | Purpose |
|------|---------|
| `download_bank_filings.py` | Main orchestrator — Phase 1–3 |
| `download_national_bank.py` | Phase 4 — SEDAR+ via Playwright |
| `convert_filings_to_md.py` | Phase 5 — bulk HTML/PDF → MD |
| `bank_filings/manifest.json` | Live download manifest |
| `bank_filings/GAPS.md` | Summary of what was missed and why |

---

## 9. Execution Order

```bash
# Step 1 — Build inventory (fast, ~2 min)
venv/bin/python download_bank_filings.py --phase inventory

# Step 2 — Download US banks
venv/bin/python download_bank_filings.py --phase us

# Step 3 — Download Canadian banks (EDGAR)
venv/bin/python download_bank_filings.py --phase canada

# Step 4 — National Bank (SEDAR+)
venv/bin/python download_national_bank.py

# Step 5 — Convert all to Markdown
venv/bin/python convert_filings_to_md.py

# Review gaps
cat bank_filings/GAPS.md
```

---

## 10. Review Checkpoint

Before moving files into worker domain folders, you will review:
- `bank_filings/manifest.json` — full download log
- `bank_filings/GAPS.md` — everything missed and why
- Sample spot-checks of converted Markdown quality
- Decision on which workers each filing feeds

---

*Plan status: PENDING APPROVAL — no downloads started*
