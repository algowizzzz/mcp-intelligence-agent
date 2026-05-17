# Test Questions — New Tools

## IRIS CCR Tools

### iris_list_dates
- What snapshot dates are available in IRIS?

### iris_search_counterparties
- Search for Goldman Sachs in IRIS
- Find all Canadian counterparties in IRIS
- Look up counterparty code RBC

### iris_limit_lookup
- What are the current limits and exposures for GS as of 2026-03-27?
- Show me all limit records for Deutsche Bank on the latest date

### iris_counterparty_dashboard
- Give me a full dashboard view for RBC on 2026-03-27
- Show me everything we have on RISK_CP on the latest date

### iris_limit_breach_check
- Is Goldman Sachs in breach of any limits on 2026-03-27?
- Run a limit breach check for RISK_CP on the latest date — check all levels
- Check if Deutsche Bank has any customer-level breaches on 2026-03-27

### iris_exposure_trend
- Show me the FX Forward exposure trend for TD from 2026-01-27 to 2026-03-27 — is it increasing or decreasing?
- What is the trend in JPM Derivative Products exposure over all available dates?

### iris_multi_counterparty_comparison
- Compare RBC and TD side by side on 2026-03-27
- Compare GS, DB, and CS exposures on the latest date

### iris_portfolio_breach_scan
- Run a full portfolio breach scan for 2026-03-27 with a $1M minimum overage — who is in breach?
- Scan the portfolio on 2026-03-27 for any breaches over $5M overage
- Which counterparties are breaching customer-level limits as of 2026-03-27?

### iris_rating_screen
- Show me all counterparties with an internal rating of 4 or below on 2026-03-27
- Which counterparties have a rating of 3 on the latest date?
- Screen the portfolio for low-rated counterparties (rating ≤ 5) with exposure above $50M

---

## OSFI Tool Suite

### osfi_list_docs
- What OSFI documents are available?
- List all regulatory guidelines loaded in the system

### osfi_search_guidance
- What does OSFI say about patch management?
- Search OSFI guidance for credit risk weight requirements
- Find OSFI guidance on LCR and HQLA
- What are OSFI's requirements for cyber incident reporting?

### osfi_read_document
- Read the B-13 guideline section on patch management timelines
- What are the minimum CET1 capital requirements in CAR 2026?
- What does OSFI's CAR 2026 say about risk weights for residential mortgages?
- What are the NSFR requirements in the LAR 2026 guideline?

---

## File Upload

### Upload + Read
- Upload one of the requirements documents using the upload button, then ask: what tools were required in this document?
- List all uploaded files
- I uploaded a document — what does it say about workflow steps?

---

## Workflow Tools

### op_risk_controls_workflow
- Run the op risk controls workflow for this control: "A compliance officer manually reviews a sample of 10 trade confirmations each week against ISDA agreements and flags discrepancies to the front office within 2 business days"
- Analyse this control using the op risk controls workflow: "The system automatically blocks any trade that would cause a counterparty's exposure to exceed its approved credit limit"
- Evaluate this control: "Risk managers produce a monthly report of all limit utilisation above 80% and distribute it to senior management"

### counterparty_intelligence_workflow
- Run the counterparty intelligence workflow for RBC
- Run a full counterparty intelligence briefing for RISK_CP
- Perform counterparty intelligence analysis for Goldman Sachs (GS)
