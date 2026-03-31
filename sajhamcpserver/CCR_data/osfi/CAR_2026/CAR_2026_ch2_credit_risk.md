# Chapter 2: Credit Risk

**Part of:** Capital Adequacy Requirements (CAR) Guideline — 2026
**Issuing Authority:** Office of the Superintendent of Financial Institutions Canada (OSFI)
**Effective Date:** November 1, 2025 (fiscal year 2026)
**BCBS Reference:** Basel III: Finalising Post-Crisis Reforms — Credit Risk Standardized Approach and IRB Approach (BCBS, December 2017)

---

## 2.1 Overview of Credit Risk Framework

Credit risk is the risk of financial loss arising from a borrower, issuer, or counterparty failing to meet its contractual obligations. For most Canadian deposit-taking institutions, credit risk capital requirements represent the single largest component of risk-weighted assets (RWA) and therefore the largest driver of regulatory capital needs.

The CAR Guideline provides two primary frameworks for quantifying credit risk capital:

1. **Standardized Approach (SA):** Assigns fixed regulatory risk weights to exposures based on the exposure class (e.g., sovereign, bank, corporate, retail, residential mortgage) and, where applicable, the external credit rating of the counterparty assigned by an OSFI-recognized External Credit Assessment Institution (ECAI). The SA is the mandatory approach for institutions that have not received OSFI approval to use internal models, and it also serves as the benchmark for calculating the output floor for IRB institutions.

2. **Internal Ratings-Based (IRB) Approach:** Permits institutions with OSFI approval to use their own estimates of key risk parameters — probability of default (PD), loss given default (LGD), exposure at default (EAD), and effective maturity (M) — within regulatory capital formulae to produce risk weights that are more sensitive to individual counterparty and transaction characteristics. The Foundation IRB (F-IRB) approach uses bank-estimated PD with regulatory LGD and EAD; the Advanced IRB (A-IRB) approach allows bank-estimated PD, LGD, and EAD.

Regardless of the approach used, institutions are subject to the **output floor**: IRB-derived RWA cannot fall below 72.5% of the RWA calculated under the Standardized Approach. The output floor is fully phased in at 72.5% as of January 1, 2026.

---

## 2.2 Standardized Approach — Risk Weights by Exposure Class

Under the Standardized Approach, each on-balance-sheet exposure is assigned a **risk weight** that reflects the credit quality of the counterparty and the nature of the exposure. The exposure amount multiplied by its risk weight produces the credit risk-weighted asset (credit RWA) for that exposure. Off-balance-sheet items are first converted to a credit equivalent using Credit Conversion Factors (CCF) before the applicable risk weight is applied.

The risk weight framework is organized by exposure class as follows.

### 2.2.1 Sovereign Exposures

Exposures to central governments, central banks, and entities explicitly guaranteed by a sovereign receive risk weights based on the sovereign's external credit rating or OECD Country Risk Classification (CRC):

| External Rating | Risk Weight |
|---|---|
| AAA to AA- | 0% |
| A+ to A- | 20% |
| BBB+ to BBB- | 50% |
| BB+ to B- | 100% |
| Below B- | 150% |
| Unrated | 100% |

Canada, rated AAA by all major rating agencies, receives a 0% risk weight. OSFI has approved domestic currency exposures to the Government of Canada and the Bank of Canada to receive a 0% risk weight regardless of rating. Exposures to Canadian provincial and territorial governments are treated as sovereign exposures for purposes of this risk weight table, consistent with OSFI's longstanding domestic policy.

Exposures to the Bank for International Settlements (BIS), the International Monetary Fund (IMF), the European Central Bank, and the European Commission receive a 0% risk weight.

### 2.2.2 Public Sector Entity (PSE) Exposures

Exposures to domestic public sector entities (including municipalities and Crown corporations) are risk-weighted as follows: where the PSE has explicit sovereign-level guarantee, it receives the sovereign risk weight; otherwise, the corporate risk weight table applies based on external rating.

### 2.2.3 Bank and Multilateral Development Bank Exposures

Exposures to regulated financial institutions (banks and credit unions) receive risk weights based on the counterparty institution's external credit rating:

| External Rating | Risk Weight |
|---|---|
| AAA to AA- | 20% |
| A+ to A- | 30% |
| BBB+ to BBB- | 50% |
| BB+ to B- | 100% |
| Below B- | 150% |
| Unrated — short-term (≤ 3 months) | 20% |
| Unrated — long-term | 50% |

Eligible multilateral development banks (MDBs) recognized by OSFI — including the World Bank Group, Asian Development Bank, African Development Bank, and similar institutions — receive a preferential 0% risk weight, provided they meet the criteria established in the Basel framework.

For exposures with an original maturity of three months or less arising in the ordinary course of cross-border trade transactions, a 20% risk weight applies regardless of the counterparty's external rating (the "short-term preferential treatment").

### 2.2.4 Corporate Exposures

Exposures to incorporated entities, partnerships, and sole proprietorships classified as corporate counterparties receive risk weights based on external credit rating:

| External Rating | Risk Weight |
|---|---|
| AAA to AA- | 20% |
| A+ to A- | 50% |
| BBB+ to BBB- | 75% |
| BB+ to BB- | 100% |
| Below BB- | 150% |
| Unrated | 100% |

**Investment-grade corporates:** Where an institution assesses a corporate counterparty as investment grade (based on the institution's own credit assessment process, meeting OSFI's standards for such assessments), and the counterparty is unrated, a 65% risk weight applies.

**SME Corporates:** Exposures to small and medium-sized enterprises (annual consolidated revenues below CAD 75 million) classified under the corporate exposure class receive an 85% risk weight when unrated.

**Specialized Lending:** Exposures to project finance, object finance, commodities finance, and income-producing real estate (IPRE) that cannot be separated from the cash flows of the underlying project or asset are classified as specialized lending. Risk weights for slotting categories (Strong, Good, Satisfactory, Weak, Default) range from 70% to 625% (under A-IRB) or supervisory slotting risk weights under F-IRB.

### 2.2.5 Residential Mortgage Exposures

Exposures secured by first-lien residential real estate receive risk weights differentiated by the Loan-to-Value (LTV) ratio at origination:

| LTV at Origination | Risk Weight (Standard) |
|---|---|
| ≤ 50% | 20% |
| 50% – 60% | 25% |
| 60% – 70% | 30% |
| 70% – 80% | 40% |
| 80% – 90% | 50% |
| 90% – 100% | 70% |
| > 100% | 100% |

The standard 35% risk weight referenced in Basel III for residential mortgages applies as a simplified flat weight where LTV-differentiated data is unavailable at origination. OSFI encourages all institutions to use the LTV-tiered risk weight table above as the primary approach.

Mortgage exposures insured under the National Housing Act (CMHC, Sagen, or Canada Guaranty) receive a 20% risk weight under the SA, reflecting the credit quality of the insurer as a federal government-backed entity.

**Qualifying Revolving Retail Exposures (QRRE):** Revolving credit facilities (including credit cards) with repayment flexibility receive a 75% risk weight.

### 2.2.6 Regulatory Retail Exposures

Exposures meeting all of the following criteria qualify for the regulatory retail risk weight of **75%**:
- The counterparty is an individual person, group of persons, or a small business
- The aggregate on-balance-sheet and off-balance-sheet exposure to any single counterparty does not exceed CAD 1.5 million (consolidated)
- The exposure is a revolving credit, personal term loan, auto lease, student loan, or small business facility
- The portfolio is sufficiently granular (no single exposure exceeds 0.2% of the aggregate retail portfolio)

Exposures not meeting all four criteria are classified as corporate or other applicable exposure classes.

### 2.2.7 Commercial Real Estate (CRE)

Income-producing commercial real estate exposures receive risk weights based on LTV:

| LTV at Origination | Risk Weight |
|---|---|
| ≤ 60% | 60% |
| 60% – 80% | 75% |
| > 80% | 100% |

Land acquisition, development, and construction (ADC) lending receives a **150% risk weight**, reflecting the elevated risk of these exposures during the development phase. Exceptions may apply where the project meets prescribed pre-sale or pre-lease thresholds.

### 2.2.8 Equity Exposures

Equity exposures held in the banking book that are not deducted from regulatory capital receive the following risk weights:
- Listed equities: **250%**
- Unlisted equities (held in a sufficiently diversified portfolio): **250%**
- Speculative unlisted equity investments: **400%**

Equity investments in funds that cannot be looked through receive a 1250% risk weight or are deducted from capital.

### 2.2.9 Past Due and Defaulted Exposures

An exposure is classified as in default when it is past due more than **90 days** or when the institution judges the obligor unlikely to pay its obligations in full (regardless of days past due). Past due exposures receive:
- **150% risk weight** for the net unsecured portion (after accounting for specific allowances)
- **100% risk weight** for the secured portion (where collateral is of recognized eligible type)

If specific allowances already held against the exposure exceed 20% of the gross outstanding, the risk weight on the net unsecured exposure reduces to **100%**.

---

## 2.3 Credit Risk Mitigation

Credit risk mitigation (CRM) techniques allow institutions to reduce the effective risk weight of an exposure where eligible collateral, guarantees, or netting arrangements are in place and meet prescribed legal and operational standards.

### 2.3.1 General Requirements for CRM Recognition

For any CRM technique to be recognized, the institution must demonstrate:
- **Legal certainty:** The CRM arrangement must be legally enforceable in all relevant jurisdictions and binding on all parties.
- **Operational robustness:** The institution must have processes to maintain the CRM arrangement, monitor its value, and take timely action upon counterparty default.
- **No material wrong-way risk:** The value of the CRM instrument must not be materially correlated with the credit quality of the counterparty.

### 2.3.2 Eligible Financial Collateral

The following collateral types are recognized under the SA simple approach and comprehensive approach:
- Cash on deposit with the lending institution
- Gold (bullion)
- Debt securities rated BBB- or higher issued by sovereigns, PSEs, banks, or corporates
- Debt securities unrated but issued by a bank and listed on a recognized exchange
- Equity securities included in a main index (e.g., S&P/TSX Composite, S&P 500)
- OSFI-recognized mutual funds and ETFs that invest exclusively in the above

**Haircuts:** Standard supervisory haircuts are applied to adjust the recognized value of collateral for market price volatility:

| Collateral Type | Residual Maturity | Standard Supervisory Haircut |
|---|---|---|
| Sovereign bonds (AAA to AA-) | ≤ 1 year | 0.5% |
| Sovereign bonds (AAA to AA-) | 1 to 5 years | 2.0% |
| Sovereign bonds (AAA to AA-) | > 5 years | 4.0% |
| Sovereign bonds (A+ to BBB-) | ≤ 1 year | 1.0% |
| Sovereign bonds (A+ to BBB-) | > 5 years | 8.0% |
| Corporate bonds (A+ to BBB-) | ≤ 1 year | 1.0% |
| Corporate bonds (A+ to BBB-) | > 5 years | 8.0% |
| Main index equities | N/A | 15% |
| Cash (same currency) | N/A | 0% |
| Gold | N/A | 15% |
| FX currency mismatch add-on | N/A | 8% |

### 2.3.3 Guarantees and Credit Derivatives

Guarantees and credit default swaps (CDS) from eligible protection providers are recognized under the substitution approach — the risk weight of the exposure is replaced with the risk weight applicable to the guarantor or protection seller.

Eligible protection providers include:
- Sovereigns, central banks, and BIS/IMF
- Public sector entities that receive sovereign risk weight treatment
- Banks and other financial institutions rated A- or better
- Other entities (including parent companies) rated A- or better

Partial guarantees are applied to the covered portion only. For maturity mismatches (where the protection has a shorter remaining maturity than the exposure), a proportional adjustment to the recognized protection amount is required.

### 2.3.4 On-Balance Sheet Netting

On-balance sheet netting of loans and deposits with the same counterparty is recognized where:
- A legally enforceable master netting agreement is in place
- The institution can at any time determine the net position
- The net position is monitored and managed on a net basis

For repo-style transactions, bilateral netting under a qualifying master netting agreement (ISDA Master Agreement or equivalent) reduces the net exposure subject to the haircut framework described above.

---

## 2.4 Counterparty Credit Risk — SA-CCR Methodology

Counterparty credit risk (CCR) arises from OTC derivatives, exchange-traded derivatives, and securities financing transactions (SFTs) where a counterparty may default prior to the final settlement of cash flows. Effective January 1, 2026, the Standardized Approach for Counterparty Credit Risk (SA-CCR) is the mandatory framework for all institutions not approved to use the Internal Model Method (IMM).

### 2.4.1 SA-CCR — EAD Calculation

The Exposure at Default (EAD) for a qualifying netting set under SA-CCR is:

```
EAD = alpha × (RC + PFE)
```

Where:
- **alpha = 1.4** (regulatory scaling factor, set by the BCBS)
- **RC = Replacement Cost** — the current mark-to-market value of the netting set, net of eligible variation margin received, subject to a floor of zero. For unmargined transactions, RC equals the positive mark-to-market value. For margined transactions, RC = max(V - C, TH + MTA - NICA, 0), where V is current portfolio value, C is collateral held, TH is the counterparty's threshold, MTA is minimum transfer amount, and NICA is the net independent collateral amount.
- **PFE = Potential Future Exposure** — reflects potential adverse moves in portfolio value over the margin period of risk. PFE = multiplier × Aggregated Add-On.

The **multiplier** recognizes over-collateralization and is calculated as:

```
multiplier = min{1; Floor + (1 - Floor) × exp(V - C) / (2 × (1 - Floor) × Aggregated Add-On)}
```

Where Floor = 5%.

The **Aggregated Add-On** is calculated at the netting-set level as the sum of add-ons across five asset classes: interest rate, foreign exchange, credit, equity, and commodities.

### 2.4.2 Credit Valuation Adjustment (CVA)

In addition to the counterparty default risk capital requirement, institutions must hold capital against **CVA risk** — the risk of losses arising from changes in the credit spread of the counterparty, which affect the mark-to-market value of derivative assets. CVA capital requirements are calculated under the CVA Standardized Approach (SA-CVA) or, where OSFI approval is obtained, the Basic CVA (BA-CVA) approach. CVA risk requirements are set out in Chapter 5 of this guideline.

### 2.4.3 Central Counterparty (CCP) Exposures

Exposures to qualifying central counterparties (QCCPs) recognized by OSFI receive preferential capital treatment:
- **Trade exposures to QCCPs:** 2% risk weight
- **Default fund contributions:** Calculated using the KCCP method, which derives the hypothetical capital requirement for the CCP's default fund

Exposures to non-qualifying CCPs are treated as exposures to a corporate counterparty with a 100% risk weight (or as rated if the CCP has an external credit rating).

---

## 2.5 Off-Balance Sheet Exposures — Credit Conversion Factors

Off-balance-sheet items (commitments, guarantees, trade finance, note issuance facilities, and similar instruments) are converted to an on-balance sheet credit equivalent amount using Credit Conversion Factors (CCF), before being risk-weighted at the applicable risk weight for the counterparty class:

| Off-Balance Sheet Instrument | CCF |
|---|---|
| Unconditionally cancellable commitments (at institution's discretion) | 10% |
| Short-term self-liquidating trade letters of credit (import/export) | 20% |
| Performance-related contingencies | 50% |
| Transaction-related contingencies | 50% |
| Note issuance facilities (NIFs) and revolving underwriting facilities (RUFs) | 50% |
| Commitments with original maturity ≤ 1 year | 20% |
| Commitments with original maturity > 1 year | 40% |
| Direct credit substitutes (financial guarantees, standby letters of credit) | 100% |
| Forward asset purchases, forward deposits, partly-paid shares | 100% |
| Securities lending and borrowing exposures | 100% |

For commitments that are unconditionally cancellable at any time without prior notice at the sole discretion of the institution, the 10% CCF reflects the residual risk that the institution may not exercise its cancellation rights promptly.

---

## 2.6 Securitization Framework

Exposures arising from traditional and synthetic securitization transactions — including asset-backed securities (ABS), residential mortgage-backed securities (RMBS), commercial mortgage-backed securities (CMBS), collateralized loan obligations (CLOs), and other structured credit products — are subject to the Securitization Framework set out in Chapter 5 of this guideline.

### 2.6.1 Hierarchy of Approaches

Institutions apply the following hierarchy of approaches to securitization exposures:
1. **SEC-IRBA** (Securitization IRB Approach): Available only to institutions with OSFI-approved IRB models for the underlying asset pool.
2. **SEC-ERBA** (Securitization External Ratings-Based Approach): Available for rated securitization tranches.
3. **SEC-SA** (Securitization Standardized Approach): Applied when neither SEC-IRBA nor SEC-ERBA is available.

### 2.6.2 Representative Risk Weights

Senior tranches of high-quality RMBS (with underlying assets meeting BCBS STC criteria) receive risk weights as low as 15% under SEC-ERBA for AAA-rated positions. Mezzanine tranches receive higher risk weights commensurate with credit subordination. First-loss or equity tranches typically receive 1250% risk weight or are deducted from CET1 capital.

### 2.6.3 Simple, Transparent, and Comparable (STC) Criteria

Securitizations meeting BCBS STC criteria are eligible for the differentiated (lower) risk weight tables under SEC-ERBA. Institutions acting as originators, sponsors, or investors in STC-compliant securitizations must ensure compliance with all STC criteria, including asset quality, structural simplicity, and transparency standards.

---

## 2.7 Internal Ratings-Based (IRB) Approach — Overview

### 2.7.1 IRB Risk Components

| Parameter | Definition |
|---|---|
| PD (Probability of Default) | One-year probability that the borrower or counterparty will default |
| LGD (Loss Given Default) | Proportion of EAD expected to be lost upon default, net of recoveries |
| EAD (Exposure at Default) | Expected outstanding amount at the time of default |
| M (Effective Maturity) | Weighted average remaining contractual maturity of the facility |

Under F-IRB, only PD is bank-estimated for corporate, bank, and sovereign exposures; LGD and EAD are regulatory prescribed. Under A-IRB, all four parameters are bank-estimated.

### 2.7.2 IRB Minimum Requirements

Approval to use IRB requires demonstrated compliance with extensive minimum requirements, including:
- Meaningful differentiation of credit risk with at least seven rating grades for non-default exposures
- Separate quantification of PD, LGD, EAD with rigorous statistical validation
- Minimum data history: five years for PD, seven years for LGD and EAD
- Independent model validation function
- Board and senior management oversight of the rating system
- Annual review and back-testing of rating model performance

---

*This document is part of OSFI's Capital Adequacy Requirements (CAR) Guideline — 2026. For binding requirements, refer to the official OSFI CAR Guideline published at osfi-bsif.gc.ca.*
