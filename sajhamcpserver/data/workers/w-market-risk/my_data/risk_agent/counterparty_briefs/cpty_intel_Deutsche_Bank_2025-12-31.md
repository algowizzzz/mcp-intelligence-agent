# Deutsche Bank — Counterparty Intelligence Brief

**As of:** 2025-12-31  
**Credit Rating:** BBB+  
**Overall Risk Signal:** 🔴 **RED**

---

## Executive Summary

Deutsche Bank presents **elevated counterparty credit risk** driven by an **active Settlement limit breach** at 99% utilisation ($198M of $200M limit), combined with elevated pre-settlement exposure and material geopolitical headwinds. The bank's stress VaR under a 2011 EU Debt Crisis scenario ($35.7M) represents 21.4% of net exposure, indicating significant tail risk. Immediate escalation and exposure reduction are required.

---

## Risk Signal Justification

**RED** — Active Settlement limit breach at 99% utilisation ($198M of $200M) combined with elevated PFE warning (83.8%) and material geopolitical risk exposure.

---

## Current Exposure Snapshot

| Metric | Value | Source |
|--------|-------|--------|
| **Total Notional** | $2.8B | [src:data/domain_data/counterparties/exposure.json] |
| **Mark-to-Market (MTM)** | $198M | [src:data/domain_data/counterparties/exposure.json] |
| **Potential Future Exposure (PFE)** | $134M | [src:data/domain_data/counterparties/exposure.json] |
| **Net Exposure** | $167M | [src:data/domain_data/counterparties/exposure.json] |
| **Collateral Posted** | $31M | [src:data/domain_data/counterparties/exposure.json] |

---

## Limit Utilisation & Breach Status

### Active Breach

| Limit Type | Limit | Used | Utilisation | Status | Headroom |
|------------|-------|------|-------------|--------|----------|
| **Settlement** | $200M | $198M | **99.0%** | 🔴 **BREACH** | **$2M** |

### Warning Status (>75%)

| Limit Type | Limit | Used | Utilisation | Status |
|------------|-------|------|-------------|--------|
| **PFE** | $160M | $134M | 83.8% | ⚠️ Warning |
| **Pre-Settlement** | $180M | $134M | 74.4% | ⚠️ Warning |

### Normal Status

| Limit Type | Limit | Used | Utilisation | Status |
|------------|-------|------|-------------|--------|
| **Wrong-Way-Risk** | $70M | $31M | 44.3% | ✅ Normal |

---

## Product Limit Utilisation (as of 2026-03-27)

**IRIS CSV Data:**
- **Derivative Products:** $35M exposure / $50M limit = **70.0%** utilisation
- **FX Forward:** $25M exposure / $40M limit = **62.5%** utilisation

**Trend:** Stable exposure at $60M total across both products (Jan–Mar 2026).

---

## Trade Book Composition

### Top Asset Classes

| Asset Class | Notional | MTM | Instrument | Maturity |
|-------------|----------|-----|------------|----------|
| **Interest Rate** | $380M | $26M | IRS (Buy) | 2029-04-15 |
| **FX** | $210M | $4M | FX Forward (Sell) | 2025-09-20 |
| **Credit** | $150M | $9M | CDS (Buy) | 2028-01-08 |

**Key Observation:** Interest Rate derivatives dominate the portfolio at $380M notional. All trades are in EUR, creating FX basis risk. [src:data/domain_data/counterparties/trades.json]

---

## Value-at-Risk (VaR) & Stress Analysis

| Metric | Value | Scenario |
|--------|-------|----------|
| **VaR 95%** | $12.2M | 2011 EU Debt Crisis |
| **VaR 99%** | $17.7M | 2011 EU Debt Crisis |
| **Stress VaR** | $35.7M | 2011 EU Debt Crisis |

**Stress Ratio:** $35.7M / $167M net exposure = **21.4%** — **ELEVATED**  
*Threshold: >20% indicates elevated tail risk.*

[src:data/domain_data/counterparties/var.json]

---

## Key Findings & Risk Drivers

### 1. Settlement Limit Breach — Critical
Settlement limit breach at 99% utilisation ($198M MTM of $200M limit) represents critical exposure concentration. Only $2M headroom remains. This is the tightest constraint on the counterparty relationship. [src:data/domain_data/counterparties/credit_limits.json]

### 2. Pre-Settlement Risk — Elevated
PFE limit at 83.8% utilisation ($134M of $160M) signals elevated pre-settlement risk in the derivative portfolio. Combined with the Settlement breach, this indicates the counterparty is approaching maximum derivative capacity. [src:data/domain_data/counterparties/credit_limits.json]

### 3. Geopolitical Stress — Material
Geopolitical stress from Iran conflict creating market uncertainty and elevated correlation breakdowns affecting energy, credit, and tech valuations. Deutsche Bank's own research highlights simultaneous risks in government debt, private credit, and tech valuations. [src:https://api.tavily.com/search]

### 4. Tail Risk — Significant
Stress VaR under 2011 EU Debt Crisis scenario ($35.7M) represents 21.4% of net exposure, indicating elevated tail risk. This scenario is relevant given current geopolitical tensions and credit market fragility. [src:data/domain_data/counterparties/var.json]

### 5. Trade Book Concentration — Interest Rate Heavy
Interest Rate derivatives dominate trade book ($380M notional, $26M MTM), with stable IRIS exposure at $60M across Derivative Products and FX Forward limits. EUR currency concentration creates additional FX basis risk. [src:data/domain_data/counterparties/trades.json]

---

## Recommended Actions

### 🔴 IMMEDIATE (Next 24 hours)
1. **Escalate Settlement limit breach to Credit Committee.** Reduce MTM exposure by minimum $2M to restore headroom, or request limit increase with Board approval.
2. **Notify Treasury and Risk Management.** Confirm collateral adequacy and review any pending trades that would increase Settlement exposure.

### 🟡 THIS WEEK
1. **Stress test portfolio** under 2011 EU Debt Crisis scenario. Validate collateral adequacy ($31M posted) against $35.7M stress VaR.
2. **Review correlation assumptions** in VaR model given breakdown signals from Deutsche Bank research on geopolitical impacts.
3. **Assess FX basis risk** in EUR-denominated trade book ($740M notional across all trades).

### 🟢 MONITOR (Ongoing)
1. **Track geopolitical developments** (Iran conflict, energy markets, credit spreads).
2. **Monitor Settlement MTM daily.** Set alert threshold at $195M (97.5% utilisation).
3. **Review quarterly earnings** and capital adequacy ratios for any deterioration in credit profile.

---

## Credit Profile Context

**Rating:** BBB+ (Investment Grade, lower end)  
**No recent rating downgrade signals** in market data as of March 2026.  
**Positive signals:** Deutsche Bank research team remains active in equity markets (tech picks, psychedelic therapies), suggesting operational confidence.

---

## Conclusion

Deutsche Bank requires **immediate attention** due to the active Settlement limit breach. While the IRIS CSV data shows stable product-level exposure ($60M), the JSON exposure data reveals critical MTM concentration ($198M) that has consumed 99% of the Settlement limit. The combination of tail risk (21.4% stress VaR ratio), geopolitical uncertainty, and minimal headroom ($2M) warrants escalation and proactive exposure reduction.

**Next Review:** Daily MTM monitoring until breach is resolved. Formal reassessment in 5 business days.

---

*Brief generated: 2026-04-03*  
*Data sources: IRIS CCR, Counterparty Exposure JSON, Trade Inventory, VaR Analysis, Tavily News*