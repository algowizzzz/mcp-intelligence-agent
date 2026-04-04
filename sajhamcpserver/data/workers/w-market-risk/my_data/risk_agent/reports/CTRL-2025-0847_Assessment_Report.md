# Operational Risk Control Assessment: CTRL-2025-0847
## Daily Derivatives Exposure Reconciliation

---

## Executive Summary

**Control ID:** CTRL-2025-0847 | **Type:** Detective | **Owner:** Credit Risk Operations  
**Overall Rating:** EFFECTIVE with MEDIUM-priority remediation

This control performs daily automated reconciliation of derivatives exposure between Bloomberg EMSX (front-office) and IRIS CCR (back-office). Variances exceeding USD 100K or 2% of notional trigger alerts; Credit Risk Manager investigates within 4 hours. The control is well-designed with clear ownership and strong evidence trails, but requires remediation on exception handling, backup coverage, and SLA feasibility.

---

## 5Ws Decomposition

| Dimension | Finding | Status |
|-----------|---------|--------|
| **WHO** | Credit Risk Manager (investigation), Head of CRO (weekly review), CCO (monthly), CRO (escalation) | ✅ Clear |
| **WHAT** | Daily automated reconciliation (notional, MTM, collateral); alerts for variances > USD 100K or 2% | ✅ Clear |
| **WHERE** | Bloomberg EMSX ↔ IRIS CCR; all active derivatives counterparties | ✅ Clear |
| **WHEN** | Daily (automated); 4-hour investigation SLA; weekly/monthly reviews; 1-day escalation for > USD 500K | ✅ Clear |
| **WHY** | Mitigate data integrity failures, exposure misstatement, regulatory reporting errors | ✅ Clear |

**Description Quality:** COMPLETE — All dimensions fully specified; audit-ready.

---

## Design Effectiveness: EFFECTIVE

### Strengths
- ✅ **Risk Alignment:** Directly addresses data integrity and exposure accuracy
- ✅ **Coverage:** Daily frequency appropriate for derivatives; USD 100K/2% threshold balances sensitivity and feasibility
- ✅ **Evidence:** Multiple layers (automated alerts, control log, management sign-offs, escalation records)
- ✅ **Escalation:** Clear two-tier path (4-hour investigation → 1-day CRO escalation for > USD 500K)
- ✅ **Control Type:** Detective classification is appropriate

### Design Gaps (5 findings)

| # | Gap | Severity | Remediation |
|---|-----|----------|-------------|
| 1 | Asset class scope limited to derivatives | MEDIUM | Extend to FX forwards, loans, bonds OR document exclusion |
| 2 | No system downtime contingency | MEDIUM | Define fallback (manual reconciliation, extended SLA) |
| 3 | Unresolved variance escalation unclear | MEDIUM | Clarify auto-escalation if unresolved after 4 hours |
| 4 | Collateral scope undefined | LOW | Clarify: amount, haircut, pledge status |
| 5 | Root cause taxonomy not formalized | LOW | Establish code list (TIMING, DATA_ENTRY, SYSTEM_LAG) |

---

## Operational Effectiveness: PARTIALLY EFFECTIVE

### Strengths
- ✅ **Executability:** Automated reconciliation is technically feasible; 4-hour SLA is realistic
- ✅ **Ownership Clarity:** All roles explicitly named (no vague references)
- ✅ **Frequency Feasibility:** Daily cadence catches errors before settlement
- ✅ **Auditability:** Control log, alerts, and sign-offs are fully testable

### Operational Gaps (3 findings)

| # | Gap | Impact | Remediation |
|---|-----|--------|-------------|
| 1 | No backup coverage for Credit Risk Manager | HIGH | Define backup manager and escalation procedure |
| 2 | 4-hour SLA feasibility unconfirmed | HIGH | Conduct staffing analysis for peak trading periods |
| 3 | Exception handling incomplete | HIGH | Add procedures for unresolved variances, repeat offenders, regulatory errors |

---

## Remediation Plan (8 Actions)

| Priority | Action | Owner | Timeline |
|----------|--------|-------|----------|
| **HIGH** | Define exception handling for unresolved variances (auto-escalation to Head of CRO) | Chief Credit Officer | 2 weeks |
| **HIGH** | Establish backup coverage for Credit Risk Manager on duty | Head of Credit Risk Operations | 2 weeks |
| **HIGH** | Confirm 4-hour SLA feasibility via staffing analysis | Head of Credit Risk Operations | 2 weeks |
| **MEDIUM** | Extend scope to non-derivatives OR document exclusion | Head of Credit Risk Operations | 4 weeks |
| **MEDIUM** | Define system downtime fallback procedure | Head of CRO + IT | 4 weeks |
| **MEDIUM** | Clarify auto-escalation for unresolved variances | Chief Credit Officer | 2 weeks |
| **LOW** | Clarify collateral reconciliation scope | Head of Credit Risk Operations | 3 weeks |
| **LOW** | Establish root cause taxonomy | Credit Risk Operations team | 3 weeks |

---

## Conclusion

CTRL-2025-0847 is a **well-designed detective control** with sound risk alignment, clear ownership, and strong audit trails. It is **operationally feasible** but requires **3 HIGH-priority remediation actions** (exception handling, backup coverage, SLA confirmation) and **5 supporting actions** to achieve full operational effectiveness. Once remediated, this control will provide robust protection against counterparty exposure data integrity failures.

**Recommendation:** Approve control with mandatory completion of HIGH-priority remediation within 2 weeks.
