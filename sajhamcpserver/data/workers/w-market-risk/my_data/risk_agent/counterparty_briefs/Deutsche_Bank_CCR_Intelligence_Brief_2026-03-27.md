# Deutsche Bank — Counterparty Intelligence Brief

**Snapshot Date**: 2026-03-27  
**Credit Rating**: BBB+ [src:data/domain_data/counterparties/exposure.json]  
**Internal Rating**: 5 (Mid-Tier) [src:iris_search_counterparties]  
**Country**: Germany (Rating: A) [src:iris_search_counterparties]  
**Legal Entity**: BCMC  
**Customer Code**: DB  
**Connection Code**: DBGRP

---

## Executive Summary

**Overall Risk Signal: 🔴 RED**

Deutsche Bank is currently in **breach of two product-level credit limits** (Derivative Products and FX Forward) with a combined overage of **$20M (12.5% above limits)**. The Settlement limit is at 99% utilization with only $2M headroom. While recent news sentiment is neutral and the bank's credit rating remains stable at BBB+, the combination of active breaches, elevated stress VaR (21.4% of net exposure), and tight limit headroom requires immediate remedial action.

---

## Current Exposure Snapshot

**As of 2025-12-31** [src:data/domain_data/counterparties/exposure.json]

| Metric | Value | Currency |
|---|---|---|
| **Total Notional** | $2,800,000,000 | USD |
| **Mark-to-Market (MTM)** | $198,000,000 | USD |
| **Potential Future Exposure (PFE)** | $134,000,000 | USD |
| **Net Exposure** | $167,000,000 | USD |
| **Collateral Posted** | $31,000,000 | USD |

---

## Credit Limit Status & Breaches

**As of 2026-03-27** [src:data/domain_data/counterparties/credit_limits.json]

### Limit Utilization Summary

| Limit Type | Limit (USD) | Used (USD) | Utilization | Status | Headroom (USD) |
|---|---|---|---|---|---|
| **Settlement** | $200M | $198M | **99.0%** | 🔴 BREACH | $2M |
| **Pre-Settlement (PFE)** | $180M | $134M | 74.4% | 🟡 WARNING | $46M |
| **PFE** | $160M | $134M | 83.8% | 🟡 WARNING | $26M |
| **Wrong-Way-Risk** | $70M | $31M | 44.3% | 🟢 NORMAL | $39M |

### Active Limit Breaches

**Breach 1: Derivative Products (Facility 81000)** [src:iris_limit_breach_check]
- **Limit**: $80M (Customer Level)
- **Exposure**: $90M
- **Overage**: $10M (12.5%)
- **Limit Key**: DB / 81000 / BCMC / Derivative Products

**Breach 2: FX Forward (Facility 81001)** [src:iris_limit_breach_check]
- **Limit**: $80M (Customer Level)
- **Exposure**: $90M
- **Overage**: $10M (12.5%)
- **Limit Key**: DB / 81001 / BCMC / FX Forward

**Total Overage**: $20M across two facilities

---

## Trade Book Composition

**As of 2025-12-31** [src:data/domain_data/counterparties/trades.json]

| Asset Class | Notional (USD) | MTM (USD) | Instrument Type | Maturity | Direction |
|---|---|---|---|---|---|
| **Interest Rate** | $380M | $26M | IRS | 2029-04-15 | Buy |
| **FX** | $210M | $4M | FX Forward | 2025-09-20 | Sell |
| **Credit** | $150M | $9M | CDS | 2028-01-08 | Buy |
| **TOTAL** | **$740M** | **$39M** | — | — | — |

**Key Observations**:
- All three asset classes show **positive MTM**, indicating no distressed positions
- Interest Rate derivatives dominate notional exposure ($380M, 51% of book)
- FX Forward position is near maturity (2025-09-20), suggesting potential roll-off
- Credit exposure via CDS is modest ($150M) with positive carry ($9M MTM)

---

## Risk Metrics & Stress Analysis

**As of 2025-12-31** [src:data/domain_data/counterparties/var.json]

| Metric | Value (USD) | Notes |
|---|---|---|
| **VaR 95%** | $12.2M | 1-day horizon, 95% confidence |
| **VaR 99%** | $17.7M | 1-day horizon, 99% confidence |
| **Stress VaR** | $35.7M | 2011 EU Debt Crisis scenario |
| **Stress Ratio** | 21.4% | Stress VaR / Net Exposure (exceeds 20% threshold) |

**Stress Scenario**: 2011 EU Debt Crisis  
**Interpretation**: Under a repeat of the 2011 European sovereign debt crisis, Deutsche Bank's exposure could deteriorate by $35.7M, representing 21.4% of current net exposure. This elevated ratio reflects the bank's structural exposure to European credit and interest rate markets.

---

## Recent News & Market Intelligence

**Search Period**: Last 7 days (as of 2026-03-30)  
**Sentiment**: NEUTRAL [src:https://api.tavily.com/search]

### Key News Items

1. **Market Commentary** (2026-03-30)  
   Deutsche Bank analyst Sameer Goel discusses breakdown in correlations due to Iran war, highlighting risks to Asian economies from elevated oil prices. [src:https://www.cnbc.com/video/2026/03/30/breakdown-in-correlations-signal-market-uncertainty-over-the-iran-war.html]  
   **Signal**: NEUTRAL — Macro commentary, no credit impact

2. **Equity Research** (2026-04-01)  
   Deutsche Bank added Applied Materials and Broadcom to top tech picks for 2026, citing chip sector strength and AI-chip revenue growth. [src:https://www.marketwatch.com/story/these-2-chip-stocks-were-added-to-deutsche-banks-list-of-top-tech-picks-6a243333]  
   **Signal**: NEUTRAL — Positive equity research activity

3. **Personnel Move** (2026-03-31)  
   Ole Matthiessen, former Deutsche Bank executive (18 years), appointed as global head of transaction services at Standard Chartered. [src:https://www.fintechfutures.com/job-cuts-new-hires/ole-matthiessen-joins-standard-chartered]  
   **Signal**: NEUTRAL — Routine executive mobility

4. **Sector Coverage** (2026-03-29)  
   Deutsche Bank initiated buy coverage on AtaiBeckley (psychedelic drug developer) with $12 price target. [src:https://www.cnbc.com/2026/03/29/deutsche-bank-says-psychedelic-therapy-boom-will-benefit-this-stock.html]  
   **Signal**: NEUTRAL — Equity research activity

### Credit Rating Actions

**No rating downgrades, upgrades, or outlook changes detected** for Deutsche Bank in the past 7 days.

---

## Key Findings

### 1. **Critical: Settlement Limit at Breach Threshold**
The Settlement limit is at 99% utilization ($198M of $200M) with only $2M headroom. This is effectively a breach and leaves no room for additional MTM deterioration. [src:data/domain_data/counterparties/credit_limits.json]

### 2. **Active Breaches on Two Product Facilities**
Derivative Products and FX Forward facilities are each $10M over their $80M customer-level limits (12.5% overage). These breaches are at the customer level and require immediate remediation. [src:iris_limit_breach_check]

### 3. **Elevated Stress VaR Ratio**
Stress VaR of $35.7M represents 21.4% of net exposure under the 2011 EU Debt Crisis scenario, exceeding the 20% threshold. This reflects structural exposure to European credit and rate markets. [src:data/domain_data/counterparties/var.json]

### 4. **Positive Trade Book MTM**
All three asset classes (Interest Rate, FX, Credit) show positive MTM totaling $39M. No distressed positions or negative carry detected. [src:data/domain_data/counterparties/trades.json]

### 5. **Stable Credit Profile**
BBB+ rating, internal rating 5, and country rating A (Germany) remain stable. No recent negative news signals or rating actions. [src:data/domain_data/counterparties/exposure.json, iris_search_counterparties]

---

## Risk Assessment Summary

| Risk Category | Assessment | Severity |
|---|---|---|
| **Limit Breach Risk** | Two active breaches; Settlement limit at 99% | 🔴 CRITICAL |
| **Credit Risk** | BBB+ rating stable; no negative news | 🟢 LOW |
| **Market Risk** | Positive MTM across all asset classes | 🟢 LOW |
| **Stress Risk** | Stress VaR at 21.4% of exposure | 🟡 ELEVATED |
| **Collateral Risk** | $31M posted; 18.6% of net exposure | 🟡 MODERATE |

---

## Recommended Actions

### **Immediate (This Week)**
1. **Limit Breach Remediation**: Contact Deutsche Bank to discuss position reduction or limit increase request for Derivative Products and FX Forward facilities. Target: Bring exposures to ≤80% of limits within 5 business days.
2. **Settlement Limit Monitoring**: Establish daily monitoring of Settlement limit utilization. Alert threshold: >95%.
3. **Collateral Review**: Confirm adequacy of $31M collateral posted under CSA agreement (DB_AGR_001). Consider requesting additional collateral if MTM deteriorates.

### **This Week**
4. **Stress Scenario Analysis**: Run updated stress test under 2011 EU Debt Crisis scenario with current positions. Quantify impact on net exposure and limit headroom.
5. **Netting Agreement Verification**: Confirm that netting agreement (DB_AGR_001) is current and enforceable. Verify CSA terms and collateral triggers.

### **Ongoing Monitoring**
6. **Weekly Exposure Tracking**: Monitor notional, MTM, and PFE daily. Flag any increase >5% week-over-week.
7. **News Monitoring**: Continue weekly news scan for Deutsche Bank credit events, rating actions, or regulatory stress.
8. **Limit Utilization Dashboard**: Maintain real-time dashboard of all four limit types. Alert on any utilization >80%.

---

## Appendix: Counterparty Profile

**Customer Code**: DB  
**Customer Name**: Deutsche Bank  
**Connection Code**: DBGRP  
**Legal Entity**: BCMC  
**Country**: Germany  
**Country Rating**: A (S&P)  
**Internal Rating**: 5 (Mid-Tier)  
**Credit Rating**: BBB+  

**Facilities**:
- **Facility 81000**: Derivative Products | Limit: $50M | Exposure: $35M | Headroom: $15M
- **Facility 81001**: FX Forward | Limit: $40M | Exposure: $25M | Headroom: $15M

**Agreements**:
- **DB_AGR_001**: CSA Agreement (Y) | Netting Agreement (Y) | Term: 36 months (ends 2027-12-31)

**Measure**: Notional (USD)

---

## Document Metadata

- **Report Date**: 2026-03-27
- **Data Sources**: IRIS CCR System, Tavily News API, Internal Exposure Database
- **Prepared By**: Counterparty Intelligence Workflow (New Tools)
- **Classification**: Internal Use Only
- **Next Review**: 2026-04-03 (weekly)

---

**END OF BRIEF**
