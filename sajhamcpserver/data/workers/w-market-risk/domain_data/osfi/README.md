# OSFI Regulatory Documents — Index

This directory contains synthetic reference summaries of key OSFI guidelines for use by the SAJHA MCP agent. Each document reflects realistic regulatory language based on publicly available OSFI guidance. For binding requirements, always consult official OSFI publications at [osfi-bsif.gc.ca](https://www.osfi-bsif.gc.ca).

---

## Document Index

| File Path | Guideline Code | Year | Description |
|---|---|---|---|
| `CAR_2026/CAR_2026_overview.md` | CAR | 2026 | Capital Adequacy Requirements — Overview: purpose, scope, key definitions (CET1, AT1, T2, RWA, leverage ratio, TLAC, output floor), Pillar 1 minimum ratios (CET1 ≥ 4.5%, T1 ≥ 6%, Total ≥ 8%, LR ≥ 3%), Capital Conservation Buffer, D-SIB surcharge, Domestic Stability Buffer (0–4%), guideline structure, and applicability. |
| `CAR_2026/CAR_2026_ch2_credit_risk.md` | CAR Ch. 2 | 2026 | Capital Adequacy Requirements — Chapter 2: Credit Risk. Covers the Standardized Approach risk weight tables by exposure class (sovereigns, banks, corporates, retail, residential mortgages, CRE, equity, past due), credit risk mitigation (eligible collateral, haircuts, guarantees, netting), counterparty credit risk (SA-CCR, EAD = alpha × (RC + PFE), CVA), credit conversion factors for off-balance-sheet items, securitization framework (SEC-IRBA, SEC-ERBA, SEC-SA), and IRB approach overview. |
| `LAR_2026/LAR_2026_overview.md` | LAR | 2026 | Liquidity Adequacy Requirements — Overview: purpose, LCR (minimum 100%; HQLA Level 1: cash, central bank reserves, 0% RW sovereign bonds; Level 2A: 15% haircut; Level 2B: 25–50% haircut; stressed outflow rates), NSFR (minimum 100%; ASF factors by funding type; RSF factors by asset type), intraday liquidity management, monitoring tools (contractual maturity ladder, funding concentration, available unencumbered assets, LCR by currency), and regulatory reporting requirements. |
| `B13_tech_cyber.md` | B-13 | 2024 | OSFI Guideline B-13: Technology and Cyber Risk Management. Covers governance (Board and Senior Management responsibilities, three lines of defence), technology risk management (risk appetite, IT asset management, change management), cyber risk management (risk identification, access controls, patch management program — emergency patches within 72 hours, critical patches within 30 days), vulnerability management, penetration testing, incident response (OSFI notification within 72 hours), third-party technology risk, and business continuity and disaster recovery. |

---

## Key Regulatory Metrics Quick Reference

| Metric | Requirement | Source |
|---|---|---|
| CET1 Minimum Ratio | ≥ 4.5% of RWA | CAR 2026 |
| Tier 1 Minimum Ratio | ≥ 6.0% of RWA | CAR 2026 |
| Total Capital Minimum Ratio | ≥ 8.0% of RWA | CAR 2026 |
| Leverage Ratio (general) | ≥ 3.0% | CAR 2026 |
| Leverage Ratio (D-SIBs) | ≥ 3.5% | CAR 2026 |
| Capital Conservation Buffer | 2.5% CET1 | CAR 2026 |
| D-SIB Surcharge | 1.0% CET1 | CAR 2026 |
| Domestic Stability Buffer (current) | 3.5% CET1 (D-SIBs only) | CAR 2026 |
| All-in CET1 for D-SIBs | 11.5% (4.5 + 2.5 + 1.0 + 3.5) | CAR 2026 |
| Output Floor | 72.5% of SA RWA | CAR 2026 |
| LCR Minimum | ≥ 100% at all times | LAR 2026 |
| NSFR Minimum | ≥ 100% at all times | LAR 2026 |
| Emergency Patch Deployment | Within 72 hours | B-13 |
| Critical Patch Deployment | Within 30 days | B-13 |
| Cyber Incident OSFI Reporting | Within 72 hours | B-13 |

---

## Directory Structure

```
CCR_data/osfi/
├── README.md                              ← This file (index)
├── CAR_2026/
│   ├── CAR_2026_overview.md               ← CAR 2026 Overview
│   └── CAR_2026_ch2_credit_risk.md        ← CAR 2026 Chapter 2: Credit Risk
├── LAR_2026/
│   └── LAR_2026_overview.md               ← LAR 2026 Overview
└── B13_tech_cyber.md                      ← Guideline B-13: Technology & Cyber Risk
```

---

## Usage Notes for SAJHA MCP Agent

- Use `osfi_search_guidance` to locate relevant sections before using `osfi_read_document` to retrieve full document content.
- When answering questions about capital ratios, reference `CAR_2026_overview.md` for minimum ratios and buffers, and `CAR_2026_ch2_credit_risk.md` for specific risk weights by asset class.
- When answering questions about liquidity requirements (LCR, NSFR, HQLA), reference `LAR_2026_overview.md`.
- When answering questions about cybersecurity, patch management, incident response, or technology governance, reference `B13_tech_cyber.md`.
- These documents are synthetic reference summaries for agent use. Always qualify answers with the note that binding requirements should be confirmed against official OSFI publications.
