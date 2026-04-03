
# Counterparty Intelligence Brief

**Counterparty:** Deutsche Bank
**As of Date:** 2025-12-31
**Credit Rating:** BBB+
**Prepared by:** RiskGPT CCR Intelligence Agent

---

## Overall Risk Signal: RED

> Active Settlement limit breach at 99% utilisation ($198M of $200M) combined with elevated PFE warning (83.8%) and material geopolitical risk exposure.

---

## Key Findings

1. Settlement limit breach at 99% utilisation ($198M MTM of $200M limit) represents critical exposure concentration. [src:data/domain_data/counterparties/credit_limits.json]
2. PFE limit at 83.8% utilisation ($134M of $160M) signals elevated pre-settlement risk in derivative portfolio. [src:data/domain_data/counterparties/credit_limits.json]
3. Geopolitical stress from Iran conflict creating market uncertainty and elevated correlation breakdowns affecting energy, credit, and tech valuations. [src:https://api.tavily.com/search]
4. Stress VaR under 2011 EU Debt Crisis scenario ($35.7M) represents 21.4% of net exposure, indicating elevated tail risk. [src:data/domain_data/counterparties/var.json]
5. Interest Rate derivatives dominate trade book ($380M notional, $26M MTM), with stable IRIS exposure at $60M across Derivative Products and FX Forward limits. [src:data/domain_data/counterparties/trades.json]

---

## Exposure Snapshot

| Metric | Amount (USD) |
|--------|-------------|
| Total Notional | $2.8B |
| Mark-to-Market (MTM) | $198M |
| Potential Future Exposure (PFE) | $134M |
| Net Exposure | $167M |
| Collateral Posted | $31M |

**Tightest Limit:** Settlement at **99.0% utilisation** — headroom $2M USD

---

## Limit Utilisation

[Chart: Product Limit Utilisation — Derivative Products 70%, FX Forward 62.5%]

**Active Breaches:** Settlement limit: $198M used of $200M limit (99.0% utilisation, $2M overage)

---

## Net Exposure Trend

[Chart: Exposure vs Limit Trend — Stable at $60M exposure vs $90M limit Jan-Mar 2026]

**Trend Direction:** Stable | **Period Delta:** $0M USD

---

## Trade Book Composition

**Largest Asset Class:** Interest Rate — Total Notional $380M USD

---

## VaR & Stress Context

| Measure | Amount (USD) | Scenario |
|---------|-------------|----------|
| VaR 99% (1-day) | $17.7M | — |
| Stress VaR | $35.7M | 2011 EU Debt Crisis |

---

## Recommended Actions

**Priority 1 — Immediate:** IMMEDIATE: Escalate Settlement limit breach to Credit Committee. Reduce MTM exposure by $2M minimum to restore headroom or request limit increase with Board approval.

**Priority 2 — This Week:** THIS WEEK: Stress test portfolio under 2011 EU Debt Crisis scenario. Validate collateral adequacy ($31M posted) against $35.7M stress VaR.

**Priority 3 — Monitor:** MONITOR: Track geopolitical developments (Iran conflict, energy markets). Review correlation assumptions in VaR model given breakdown signals from Deutsche Bank research.

---

*RiskGPT MCP Server | CCR Intelligence | 2025-12-31*
