<!-- Page 1 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 1

Protected B - External / Protégé B - Externe
Guideline

Subject: Capital Adequacy Requirements (CAR)

Chapter 8 – Credit Valuation Adjustment (CVA) Risk

Effective Date:  November 2025 / January 2026

The Capital Adequacy Requirements (CAR) for banks, banks holding companies, and trust and
loan companies, collectively referred to as ‘institutions’, are set out in nine chapters, each of
which has been issued as a separate document. This document, Chapter 8 – Credit Valuation
Adjustment (CVA) Risk, should be read in conjunction with the other CAR chapters. The
complete list of CAR chapters is as follows:

Chapter 1  Overview of Risk-based Capital Requirements
Chapter 2  Definition of Capital
Chapter 3  Operational Risk
Chapter 4  Credit Risk – Standardized Approach
Chapter 5  Credit Risk – Internal Ratings Based Approach
Chapter 6  Securitization
Chapter 7  Settlement and Counterparty Risk
Chapter 8  Credit Valuation Adjustment (CVA) Risk
Chapter 9  Market Risk


Please refer to OSFI’s Corporate Governance Guideline for OSFI’s expectations of institution
Boards of Directors in regard to the management of capital and liquidity.






For institutions with a fiscal year ending October 31 or December 31, respectively.

---

<!-- Page 2 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 2
Protected B - External / Protégé B - Externe

Table of Contents

8.1. Definitions and application .......................................................................................... 3
8.2. Basic approach for credit valuation adjustment risk ................................................ 6
8.2.1 Reduced version of the BA-CVA (hedges are not recognized) .......................... 6
8.2.2 Full version of the BA-CVA (hedges are recognized)........................................ 8
8.3. Standardized approach for credit valuation adjustment risk ................................ 11
8.3.1 Regulatory CVA calculations ........................................................................... 12
8.3.2 Eligible hedges .................................................................................................. 16
8.3.3 Multiplier .......................................................................................................... 16
8.3.4 Calculations....................................................................................................... 16
8.3.5 Interest rate buckets, risk factors, sensitivities, risk weights and
correlations ........................................................................................................ 20

8.3.6 Foreign exchange buckets, risk factors, sensitivities, risk weights and
correlations ........................................................................................................ 22

8.3.7 Counterparty credit spread buckets, risk factors, sensitivities, risk weights
and correlations ................................................................................................. 23

8.3.8 Reference credit spread buckets, risk factors, sensitivities, risk weights and
correlations ........................................................................................................ 25

8.3.9 Equity buckets, risk factors, sensitivities, risk weights and correlations .......... 29
8.3.10 Commodity buckets, risk factors, sensitivities, risk weights and
correlations ........................................................................................................ 31

---

<!-- Page 3 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 3
Protected B - External / Protégé B - Externe
Chapter 8 – Credit Valuation Adjustment (CVA) Risk

1. This chapter is drawn from the Basel Committee on Banking Supervision (BCBS) Basel
Framework published on the Bank for International Settlements (BIS) website1. For
reference, the Basel paragraph numbers that are associated with the text appearing in this
chapter are indicated in square brackets at the end of each paragraph
2.
8.1. Definitions and application
2. Institutions that are required to determine market risk capital requirements for trading
book positions (as per paragraphs 2 and 3 of Chapter 9) must meet the requirements of
this chapter. In addition, all institutions that enter into transactions specified in paragraph
6 are also subject to the requirements of this chapter. The risk-weighted assets for credit
value adjustment risk are determined by multiplying the capital requirements calculated
as set out in this chapter by 12.5. [Basel Framework, MAR 50.1]
3. In the context of this document, CVA stands for credit valuation adjustment specified at
a counterparty level. CVA reflects the adjustment of default risk-free prices of
derivatives and securities financing transactions (SFTs) due to a potential default of the
counterparty. [Basel Framework, MAR 50.2]
4. Unless explicitly specified otherwise, the term CVA in this document means regulatory
CVA. Regulatory CVA may differ from CVA used for accounting purposes as follows:
(1) regulatory CVA excludes the effect of the institution’s own default; and
(2) several constraints reflecting best practice in accounting CVA are imposed on
calculations of regulatory CVA. [Basel Framework, MAR 50.3]
5. CVA risk is defined as the risk of losses arising from changing CVA values in response
to changes in counterparty credit spreads and market risk factors that drive prices of
derivative transactions and SFTs. [Basel Framework, MAR 50.4]
6. The capital requirements for CVA risk must be calculated by all institutions involved in
covered transactions in both banking book and trading book. Covered transactions
include:
(1) all derivatives except those transacted directly with  a qualified central
counterparty and those exempted in section 7.1.8.1 A (ii) of Chapter 7; and
(2) SFTs that are fair -valued by an institution  for accounting purposes , if OSFI
determines that the institution 's CVA loss exposures arising from SFT
transactions are material. In case the institution deems the exposures immaterial,
the institution must justify its assessment to OSFI  by providing relevant
supporting documentation.

1 The Basel Framework
2 Following the format: [Basel Framework, XXX yy.zz]

---

<!-- Page 4 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 4
Protected B - External / Protégé B - Externe
For the purpose of CVA capital requirement, SFTs that are fair -valued for
accounting purposes and for which an institution records zero for CVA reserves
for accounting purposes are included in the scope of covered transactions if the
CVA risk of those SFTs is deemed material as described in the above sub -
paragraph (2).
[Basel Framework, MAR 50.5]
7. The CVA risk capital requirements are calculated for an institution’s “CVA portfolio”
on a standalone basis. The CVA portfolio includes CVA for an institution’s entire
portfolio of covered transactions and eligible CVA hedges. [Basel Framework, MAR
50.6]
8. Two approaches are available for calculating CVA capital requirements: the
standardized approach (SA-CVA) and the basic approach (BA-CVA). Institutions must
use the BA-CVA unless they receive approval from OSFI to use the SA-CVA.3 [Basel
Framework, MAR 50.7]
9. Institutions that have received approval of OSFI to use the SA-CVA may carve out from
the SA-CVA calculations any number of netting sets. CVA capital requirements for all
carved-out netting sets must be calculated using the BA-CVA. When applying the carve-
out, a legal netting set may also be split into two synthetic netting sets, one containing
the carved-out transactions subject to the BA-CVA and the other subject to the SA-
CVA, subject to one or both of the following conditions:
(1) the split is consistent with the treatment of the legal netting set used by the
institution for calculating accounting CVA (e.g. where certain transactions are not
processed by the front office/accounting exposure model); or
(2) OSFI approval to use the SA-CVA is limited and does not cover all transactions
within a legal netting set.
[Basel Framework, MAR 50.8]
10. Institutions that are below the materiality threshold specified in subsection (1) may opt
not to calculate its CVA capital requirements using the SA-CVA or BA-CVA and
instead choose an alternative treatment.
(1) Any institution whose aggregate notional amount of non- centrally cleared
derivatives is less than or equal to $150 billion
4 is deemed as being below the
materiality threshold.
(2) Any institution below the materiality threshold may choose to set its CVA capital
requirement equal to 100% of the institution ’s capital requirement for
counterparty credit risk (CCR).
(3) CVA hedges are not recognized under this treatment.

3  Note that this is in contrast to the application of the market risk approaches set out in section 9.1.2 of Chapter 9,
where institutions do not need OSFI’s approval to use the standardized approach.
4  All dollar values in this guideline are in Canadian dollars, unless otherwise noted.

---

<!-- Page 5 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 5
Protected B - External / Protégé B - Externe
(4) If chosen, this treatment must be applied to the institution’s entire portfolio instead
of the BA-CVA or the SA-CVA.
(5) OSFI, however, can remove this option if it determines that CVA risk resulting
from the institution ’s derivative positions materially contributes to the
institution’s overall risk.
[Basel Framework, MAR 50.9]
11. Eligibility criteria for CVA hedges are specified in paragraph 18 to paragraph 20 for the
BA-CVA and in paragraph 38 to paragraph 40 for the SA-CVA. [Basel Framework,
MAR 50.10]
12. CVA hedging instruments can be external (i.e. with an external counterparty) or internal
(i.e. with one of the institution’s trading desks).
(1) All external CVA hedges (including both eligible and ineligible external CVA
hedges) that are covered transactions must be included in the CVA calculation of
the counterparty providing to the hedge.
(2) All eligible external CVA hedges must be excluded from an institution ’s market
risk capital requirement calculations under Chapter 9.
(3) Ineligible external CVA hedges are treated as trading book instruments and are
capitalized under Chapter 9.
(4) An internal CVA hedge involves two perfectly offsetting positions: one of the
CVA desk and the opposite position of the trading desk:
(5) If an internal CVA hedge is ineligible, both positions belong to the trading book
where they cancel each other, so there is no impact on either the CVA portfolio
or the trading book.
(6) If an internal CVA hedge is eligible, the CVA desk’s position is part of the CVA
portfolio where it is capitalized as set out in this chapter, while the trading desk’s
position is part of the trading book where it is capitalized as set out in Chapter 9.
(7) If an internal CVA hedge involves an instrument that is subject to curvature risk,
default risk charge or the residual risk add-on under the standardized approach as
set out in Chapter 9 , it can be eligible only if the trading desk that is the CVA
desk’s internal counterparty executes a transaction with an external counterparty
that exactly offsets the trading desk’s position with the CVA desk.
[Basel Framework, MAR 50.11]
13. Institutions that use the BA-CVA or the SA-CVA for calculating CVA capital
requirements may cap the maturity adjustment factor at 1 for all netting sets contributing
to CVA capital requirements when they calculate CCR capital requirements under the
Internal Ratings Based (IRB) approach. [Basel Framework, MAR 50.12]

---

<!-- Page 6 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 6
Protected B - External / Protégé B - Externe
8.2. Basic approach for credit valuation adjustment risk
14. The BA-CVA calculations may be performed either via the reduced version or the full
version. An institution under the BA-CVA approach can choose whether to implement
the full version or the reduced version at its discretion. However, all institutions using
the BA-CVA must calculate the reduced version of BA-CVA capital requirements as the
reduced BA-CVA is also part of the full BA-CVA capital calculations as a conservative
means to limit hedging recognition. Institutions under the BA-CVA approach must
capitalize any market risk hedges of accounting CVA according to Chapter 9, Market
Risk.
(1) The full version recognizes counterparty credit spread hedges and is intended for
institutions that hedge CVA risk.
(2) The reduced version eliminates the element of hedging recognition from the full
version. The reduced version is designed to simplify BA -CVA implementation
for less sophisticated institutions that do not hedge CVA.
[Basel Framework, MAR 50.13]
8.2.1 REDUCED VERSION OF THE BA-CVA (HEDGES ARE NOT RECOGNIZED)
15. The capital requirements for CVA risk under the reduced version of the BA-CVA
(DSBA−CVA ×Kreduced, where the discount scalar DSBA−CVA = 0.65) are calculated as
follows (where the summations are taken over all counterparties that are within scope of
the CVA charge), where:
(1) SCVA
c is the CVA capital requirement that counterparty c would receive if
considered on a stand-alone basis (referred to as “stand-alone CVA capital” – see
the paragraph below for its calculation);
(2) The supervisory correlation parameter is ρ = 50%. Its square, ρ2=25%, represents
the correlation between credit spreads of any two counterparties .5 In the formula
below, the effect of ρ is to recognize  the fact that the CVA risk to which an
institution is exposed is less than the sum of the CVA risk for each counterparty,
given that the credit spreads of counterparties are typically not perfectly
correlated; and
(3) The first term under the square root in the formula below aggregates the
systematic components of CVA risk, and the second term under the square root
aggregates the idiosyncratic components of CVA risk.
Kreduced = � � ρ ∙ � SCVAC
C
�
2
+ (1 − ρ2) ∙ � SCVAC
2
C


5  One of the basic assumptions underlying the BA-CVA is that systematic credit spread risk is driven by a single
factor. Under this assumption, ρ can be interpreted as the correlation between the credit spread of a counterparty
and the single credit spread systematic factor.

---

<!-- Page 7 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 7
Protected B - External / Protégé B - Externe
[Basel Framework, MAR 50.14]
16. The stand-alone CVA capital requirements for counterparty c that are used in the
formula in the paragraph above (SCVAc) are calculated as follows (where the
summation is across all netting sets with the counterparty), where:
(1) RWc is the risk weight for counterparty c that reflects the volatility of its credit
spread. These risk weights are based on a combination of sector and credit quality
of the counterparty as prescribed in the paragraph below.
(2) MNS is the effective maturity for the netting set NS. For institution s that have
OSFI’s approval to use the IMM, M NS is calculated as per paragraphs 35 and 36
of Chapter 7, with the exception that the five -year cap in paragraph 35 is not
applied. For institutions that do not have OSFI  approval to use the IMM, M NS is
calculated according to paragraph 133 to paragraph 141 of Chapter 5, with the
exception that the five-year cap in paragraph 132 of Chapter 5 is not applied.
(3) EADNS is the exposure at default (EAD) of the netting set NS, calculated in the
same way as the institution  calculates it for minimum capital requirements for
CCR.
(4) DFNS is a supervisory discount factor. It is 1 for institutions using the IMM to
calculate EAD, and is
1−𝑒𝑒−0.05∙𝑀𝑀𝑁𝑁𝑁𝑁
0.05∙𝑀𝑀𝑁𝑁𝑁𝑁
 for institutions not using the IMM.6
(5) 𝛼𝛼 =  1.4 .7
𝑆𝑆𝑆𝑆𝑆𝑆𝑆𝑆𝐶𝐶= 1
𝛼𝛼∙ 𝑅𝑅𝑅𝑅𝐶𝐶∙ � 𝑀𝑀𝑁𝑁𝑁𝑁
𝑁𝑁𝑁𝑁
∙ 𝐸𝐸𝑆𝑆𝐸𝐸𝑁𝑁𝑁𝑁∙ 𝐸𝐸 𝐷𝐷𝑁𝑁𝑁𝑁
[Basel Framework, MAR 50.15]
17. The supervisory risk weights (𝑅𝑅𝑅𝑅𝑐𝑐) are given in Table 1. Credit quality is specified as
either investment grade (IG), high yield (HY), or not rated (NR). Where there are no
external ratings or where external ratings are not recognized within a jurisdiction,
institutions may, subject to OSFI’s approval, map the internal rating to an external rating
and assign a risk weight corresponding to either IG or HY.
8 Otherwise, the risk weights
corresponding to NR is to be applied.

6  DF is the supervisory discount factor averaged over time between today and the netting set's effective maturity
date. The interest rate used for discounting is set at 5%, hence 0.05 in the formula. The product of EAD and
effective maturity in the BA-CVA formula is a proxy for the area under the discounted expected exposure
profile of the netting set. The IMM definition of effective maturity already includes this discount factor, hence
DF is set to 1 for IMM institutions. Outside IMM, the netting set’s effective maturity is defined as an average of
actual trade maturities. This definition lacks discounting, so the supervisory discount factor is added to
compensate for this.
7  α is the multiplier used to convert effective expected positive exposure (EEPE) to EAD in both SA-CCR and
IMM. Its role in the calculation, therefore, is to convert the EAD of the netting set (EADNS) back to EEPE.
8  If an institution has prior approval from OSFI to use the Advanced Internal Ratings -Based approach (AIRB) or
Foundation Internal Ratings Based approach (FIRB) for credit risk and to use its internal ratings mappings for a
particular reference, it does not need to seek OSFI approval in the context of BA -CVA.

---

<!-- Page 8 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 8
Protected B - External / Protégé B - Externe
Table 1  Supervisory risk weights, RWC

Sector of counterparty Credit quality of counterparty
IG HY and NR
Sovereigns including central banks and multilateral development
banks
0.5% 2.0%
Local government, government-backed non-financials, education
and public administration
1.0% 4.0%
Financials including government-backed financials 5.0% 12.0%
Basic materials, energy, industrials, agriculture, manufacturing,
mining and quarrying
3.0% 7.0%
Consumer goods and services, transportation and storage,
administrative and support service activities
3.0% 8.5%
Technology, telecommunications 2.0% 5.5%
Health care, utilities, professional and technical activities 1.5% 5.0%
Other sector 5.0% 12.0%

[Basel Framework, MAR 50.16]
8.2.2 FULL VERSION OF THE BA-CVA (HEDGES ARE RECOGNIZED)
18. As set out in paragraph 14 the full version of the BA-CVA recognizes the effect of
counterparty credit spread hedges. Only transactions used for the purpose of mitigating
the counterparty credit spread component of CVA risk, and managed as such, can be
eligible hedges. [Basel Framework, MAR 50.17]
19. Only single-name credit default swaps (CDS), single-name contingent CDS, risk
participation agreements and index CDS can be eligible CVA hedges. [Basel
Framework, MAR 50.18]
20. Eligible single-name credit instruments must:
(1) reference the counterparty directly; or
(2) reference an entity legally related to the counterparty, where legally related refers
to cases where the reference name and the counterparty are either a parent and its
subsidiary or two subsidiaries of a common parent; or
(3) reference an entity that belongs to the same sector and region as the counterparty.
[Basel Framework, MAR 50.19]
21. Institutions that intend to use the full version of BA-CVA must calculate the reduced
version (K
reduced) as well. Under the full version, capital requirements for CVA risk
DSBA−CVA ×Kfull is calculated as follows, where DSBA−CVA = 0.65, and β=0.25 is the
supervisory parameter that is used to provide a floor that limits the extent to which
hedging can reduce the capital requirements for CVA risk:

---

<!-- Page 9 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 9
Protected B - External / Protégé B - Externe
 Kfull = β ∙ Kreduced + (1 − β) ∙ Khedged
 [Basel Framework, MAR 50.20]

22. The part of capital requirements that recognizes eligible hedges (Khedged) is calculated
as follows (where the summations are taken over all counterparties c that are within
scope of the CVA charge), where:
(1) Both the stand-alone CVA capital (SCVAC) and the correlation parameter (ρ) are
defined in exactly the same way as for the reduced version calculation of the BA-
CVA.
(2) SNHC is a quantity that gives recognition to the reduction in CVA risk of the
counterparty c arising from the institution ’s use of single-name hedges of credit
spread risk. See paragraph 24 for its calculation.
(3) IH is a quantity that gives recognition to the reduction in CVA risk across all
counterparties arising from the institution ’s use of index hedges. See paragraph
25 for its calculation.
(4) HMA
C is a quantity characteri zing hedging misalignment, which is designed to
limit the extent to which indirect hedges can reduce capital requirements given
that they will not fully offset movements in a counterparty’s credit spread. That
is, with indirect hedges present, K
hedged cannot reach zero. See paragraph 26 for
its calculation.
Khedged =
� (ρ ∙ ∑ (SCVAC − SNHC)C − IH)2 + (1 − ρ2) ∙ ∑ (SCVAC − SNHC)C
2 + ∑ HMAC C

  [Basel Framework, MAR 50.21]

23. The formula for K
hedged in the paragraph above comprises three main terms as below:
(1) The first term (ρ ∙ ∑ (SCVAC − SNHC)C − IH)2  aggregates the systematic
components of CVA risk arising from the institution’s counterparties, the single-
name hedges and the index hedges.
(2) The second term  (1 − ρ2) ∙ ∑ (SCVAC − SNHC)C
2
 aggregates the idiosyncratic
components of CVA risk arising from the institution ’s counterparties and the
single-name hedges.
(3) The third term  ∑ HMAC C aggregates the components of indirect hedges that are
not aligned with counterparties’ credit spreads.
[Basel Framework, MAR 50.22]
24. The quantity SNHc is calculated as follows (where the summation is across all single
name hedges h that the institution has taken out to hedge the CVA risk of counterparty
c), where:

---

<!-- Page 10 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 10
Protected B - External / Protégé B - Externe
(1) rhc  is the supervisory prescribed correlation between the credit spread of
counterparty c and the credit spread of a single -name hedge h of counterparty c.
The value of  rhcis set out in the Table 2 of paragraph 27. It is set at 100% if the
hedge directly references the counterparty c, and set at lower values if it does not.
(2) Mh
SN is the remaining maturity of single-name hedge h.
(3) Bh
SN is the notional of single-name hedge h. For single-name contingent CDS, the
notional is determined by the current market value of the reference portfolio or
instrument.
(4) DFh
SN is the supervisory discount factor calculated as
1−e−0.05∙Mh
SN
0.05∙Mh
SN .
(5) RWh  is the supervisory risk weight of single -name hedge h that reflects the
volatility of the credit spread of the reference name of the hedging instrument.
These risk weights are based on a combination of the sector and the credit quality
of the reference name of the hedging instrument as prescribed in Table 1 of
paragraph 17.
 SNH
c = ∑ rhch∈c ∙ RWh ∙ Mh
SN ∙ Bh
SN ∙ DFh
SN

[Basel Framework, MAR 50.23]

25. The quantity IH is calculated as follows (where the summation is across all index hedges
i that the institution has taken out to hedge CVA risk), where:
(1) M
i
ind  is the remaining maturity of index hedge i.
(2) Bi
ind is the notional of the index hedge i.
(3) DFi
ind  is the supervisory discount factor calculated as
1−e−0.05∙Mi
ind
0.05∙Mi
ind
(4) RWi is the supervisory risk weight of the index hedge i. RW i is taken from the
Table 1 of paragraph 17 based on the sector and the credit quality of the index
constituents and adjusted as follows:
a. For an index where all index constituents belong to the same sector and are of the
same credit quality, the relevant value in the Table 1 of paragraph 17 is multiplied
by 0.7 to account for diversification of idiosyncratic risk within the index.
b. For an index spanning multiple sectors or with a mixture of investment grade
constituents and other grade constituents, the name -weighted average of the risk
weights from the Table 1 of paragraph 17 should be calculated and then multiplied
by 0.7.
a. IH = ∑ RW
i ∙ Mi
ind ∙ Bi
ind ∙ DFi
ind
i
     [Basel Framework, MAR 50.24]

---

<!-- Page 11 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 11
Protected B - External / Protégé B - Externe
26. The quantity HMAC is calculated as follows (where the summation is across all single
name hedges h that have been taken out to hedge the CVA risk of counterparty c), where
rhc, Mh
SN, Bh
SN, DFh
SN  and RWh have the same definitions as set out in [MAR50.23].
 HMAc = ∑ �1 − rhc
2 �h∈c ∙ �RWh ∙ Mh
SN ∙ Bh
SN ∙ DFh
SN�
2

 [Basel Framework, MAR 50.25]

27. The supervisory prescribed correlations rhc between the credit spread of counterparty c
and the credit spread of its single-name hedge h are set in Table 2 as follows:
Table 2 Correlations between credit spread of a counterparty and its single-
name hedge
Single-name hedge h of counterparty c Value of rhc
References counterparty c directly 100%
Has legal relation with counterparty c 80%
Shares sector and region with counterparty c 50%
  [Basel Framework, MAR 50.26]

8.3. Standardized approach for credit valuation adjustment risk
28. The SA-CVA is an adaptation of the standardized approach for market risk set out in
Chapter 9. The primary differences of the SA-CVA from the standardized approach for
market risk are:
(1) the SA-CVA features a reduced granularity of market risk factors; and
(2) the SA-CVA does not include default risk and curvature risk.
[Basel Framework, MAR 50.27]
29. Under the SA-CVA, capital requirements must be calculated and reported to OSFI at a
monthly frequency. In addition, institutions using the SA-CVA must have the ability to
produce SA-CVA capital requirement calculations at the request of OSFI and must
accordingly provide the calculations. [Basel Framework, MAR 50.28]
30. The SA-CVA uses as inputs the sensitivities of regulatory CVA to counterparty credit
spreads and market risk factors driving the values of covered transactions. Sensitivities
must be computed by institutions in accordance with the prudent valuation standards set
out in Chapter 9. [Basel Framework, MAR 50.29]
31. For an institution to be considered eligible for the use of SA-CVA by OSFI as set out in
paragraph 8, the institution must meet the following criteria at the minimum.
(1) An institution must be able to model exposure and calculate, on at least a monthly
basis, CVA and CVA sensitivities to the market risk factors specified in paragraph
55 to paragraph 78.

---

<!-- Page 12 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 12
Protected B - External / Protégé B - Externe
(2) An institution must have a CVA desk (or a similar dedicated function) responsible
for risk management and hedging of CVA.
[Basel Framework, MAR 50.30]
8.3.1 REGULATORY CVA CALCULATIONS
32. An institution must calculate regulatory CVA for each counterparty with which it has at
least one covered position for the purpose of the CVA risk capital requirements. [Basel
Framework, MAR 50.31]
33. Regulatory CVA at a counterparty level must be calculated according to the following
principles. An institution must demonstrate its compliance to the principles to OSFI.
(1) Regulatory CVA must be calculated as the expectation of future losses resulting
from default of the counterparty under the assumption that the institution itself is
free from the default risk. In expressing the regulatory CVA, non-zero losses must
have a positive sign .  This is reflected in paragraph 53 where WS
k
hdgmust be
subtracted from WSk
CVA.
(2) The calculation must be based on at least the following three sets of inputs:
(a) term structure of market-implied probability of default (PD);
(b) market-consensus expected loss-given-default (ELGD);
(c) simulated paths of discounted future exposure.
(3) The term structure of market -implied PD must be estimated from credit spreads
observed in the markets. For counterparties whose credit is not actively traded (ie
illiquid counterparties), the market -implied PD must be estimated from proxy
credit spreads es timated for these counterparties according to the following
requirements:
(a) An institution  must estimate the credit spread curves of illiquid
counterparties from credit spreads observed in the markets of the
counterparty’s liquid peers via an algorithm that discriminates on at least
the following three variables: a measure of credit quality (e .g. rating),
industry, and region.
(b) In certain cases, mapping an illiquid counterparty to a single liquid
reference name can be allowed. A typical example would be mapping a
municipality to its home country (i .e. setting the municipality credit
spread equal to the sovereign credit spread plus a premium). An
institution must justify to OSFI  each case of mapping an illiquid
counterparty to a single liquid reference name.
(c) When no credit spreads of any of the counterparty’s peers is available due
to the counterparty’s specific type (e.g. project finance, funds), an
institution is allowed to use a more fundamental analysis of credit risk to
proxy the spread of an illiquid counterparty. However, where historical

---

<!-- Page 13 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 13
Protected B - External / Protégé B - Externe
PDs are used as part of this assessment, the resulting spread cannot be
based on historical PD only – it must relate to credit markets.
(4) The market-consensus ELGD value must be the same as the one used to calculate
the risk-neutral PD from credit spreads unless the institution can demonstrate that
the seniority of the exposure resulting from covered positions differs from the
seniority of senior unsecured bonds. 9 Collateral provided by the counterparty
does not change the seniority of the exposure.
(5) The simulated paths of discounted future exposure are produced by pricing all
derivative transactions with the counterparty along simulated paths of relevant
market risk factors and discounting the prices to today using risk-free interest rates
along the path.
(6) All market risk factors material for the transactions with a counterparty must be
simulated as stochastic processes for an appropriate number of paths defined on
an appropriate set of future time points extending to the maturity of the longest
transaction.
(7) For transactions with a significant level of dependence between exposure and the
counterparty’s credit quality, this dependence should be taken into account.
(8) For margined counterparties, collateral is permitted to be recognize d as a risk
mitigant under the following conditions:
(a) Collateral management requirements outlined in paragraph 56 and 57 of
Chapter 7 are satisfied.
(b) All documentation used in collateralized transactions must be binding on
all parties and legally enforceable in all relevant jurisdictions. Institutions
must have conducted sufficient legal review to verify this and have a well
founded legal basis to reach this conclusion, and undertake such further
review as necessary to ensure continuing enforceability.
(9) For margined counterparties, the simulated paths of discounted future exposure
must capture the effects of margining collateral that is recogn ized as a risk
mitigant along each exposure path. All the relevant contractual features such as
the nature of the margin agreement (unilateral vs bilateral), the frequency of
margin calls, the type of collateral, thresholds, independent amounts, initial
margins and minimum transfer amounts must be appropriately captured by the
exposure model. To determine collateral a vailable to an institution  at a given
exposure measurement time point, the exposure model must assume that the
counterparty will not post or return any collateral within a certain time period
immediately prior to that time point. The assumed value of this time period,
known as the margin period of risk (MPoR), cannot be less than a supervisory
floor. For SFTs and client cleared transactions as specified in paragraph 179 of
Chapter 7  the supervisory floor for the MPoR is equal to 4+N business days,

9  This would include non-CSA securities or other physical collateral which impacts the seniority in the recovery
process including real estate, oil reserves or other inventories.

---

<!-- Page 14 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 14
Protected B - External / Protégé B - Externe
where N is the re -margining period specified in the margin agreement (in
particular, for margin agreements with daily or intra -daily exchange of margin,
the minimum MPoR is 5 business days). For all other transactions, the supervisory
floor for the MPoR is equal to 9+N business days.
[Basel Framework, MAR 50.32]
34. The simulated paths of discounted future exposure are obtained via the exposure models
used by an institution for calculating front office/accounting CVA, adjusted (if needed)
to meet the requirements imposed for regulatory CVA calculation. Model calibration
process (with the exception of the MPoR), market and transaction data used for
regulatory CVA calculation must be the same as the ones used for accounting CVA
calculation. [Basel Framework, MAR 50.33]
35. The generation of market risk factor paths underlying the exposure models must satisfy
and an institution must demonstrate to OSFI its compliance to the following
requirements:
(1) Drifts of risk factors must be consistent with a risk -neutral probability measure.
Historical calibration of drifts is not allowed.
(2) The volatilities and correlations of market risk factors must be calibrated to
market data whenever sufficient data exist in a given market. Otherwise, historical
calibration is permissible.
(3) The distribution of modelled risk factors must account for the possible non-
normality of the distribution of exposures, including the existence of leptokurtosis
(“fat tails”), where appropriate.
[Basel Framework, MAR 50.34]
36. Netting recognition is the same as in the accounting CVA calculations used by the
institution. In particular, netting uncertainty can be modelled. [Basel Framework, MAR
50.35]
37. An institution must satisfy and demonstrate to OSFI its compliance to the following
requirements:
(1) Exposure models used for calculating regulatory CVA must be part of a CVA risk
management framework that includes the identification, measurement,
management, approval and internal reporting of CVA risk. An institution  must
have a credible track record in using these exposure models for calculating CVA
and CVA sensitivities to market risk factors.
(2) Senior management should be actively involved in the risk control process and
must regard CVA risk control as an essential aspect of the business to which
significant resources need to be devoted.
(3) An institution  must have a process in place for ensuring compliance with a
documented set of internal policies, controls and procedures concerning the
operation of the exposure system used for accounting CVA calculations.

---

<!-- Page 15 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 15
Protected B - External / Protégé B - Externe
(4) An institution must have an independent control unit that is responsible for the
effective initial and ongoing validation of the exposure models. This unit must be
independent from business credit and trading units (including the CVA desk),
must be adequately staffed and must report directly to senior management of the
institution.
(5) An institution must document the process for initial and ongoing validation of its
exposure models to a level of detail that would enable a third party to understand
how the models operate, their limitations, and their key assumptions; and recreate
the analysis. This documentation must set out the minimum frequency with which
ongoing validation will be conducted as well as other circumstances (such as a
sudden change in market behaviour) under which additional validation should be
conducted. In addition, the documentation must describe how the validation is
conducted with respect to data flows and portfolios, what analyses are used and
how representative counterparty portfolios are constructed.
(6) The pricing models used to calculate exposure for a given path of market risk
factors must be tested against appropriate independent benchmarks for a wide
range of market states as part of the initial and ongoing model validation process.
Pricing models for options must account for the non-linearity of option value with
respect to market risk factors.
(7) An independent review of the overall CVA risk management process should be
carried out regularly in the institution’s own internal auditing process. This review
should include both the activities of the CVA desk and of the independent risk
control unit.
(8) An institution must define criteria on which to assess the exposure models and
their inputs and have a written policy in place to describe the process to assess the
performance of exposure models and remedy unacceptable performance.
(9) Exposure models must capture transaction- specific information in order to
aggregate exposures at the level of the netting set. An institution must verify that
transactions are assigned to the appropriate netting set within the model.
(10) Exposure models must reflect transaction terms and specifications in a timely,
complete, and conservative fashion. The terms and specifications must reside in a
secure database that is subject to formal and periodic audit. The transmission of
transaction t erms and specifications data to the exposure model must also be
subject to internal audit, and formal reconciliation processes must be in place
between the internal model and source data systems to verify on an ongoing basis
that transaction terms and spec ifications are being reflected in the exposure
system correctly or at least conservatively.
(11) The current and historical market data must be acquired independently of the lines
of business and be compliant with accounting. They must be fed into the exposure
models in a timely and complete fashion, and maintained in a secure database
subject to form al and periodic audit. An institution  must also have a well -
developed data integrity process to handle the data of erroneous and/or anomalous
observations. In the case where an exposure model relies on proxy market data,

---

<!-- Page 16 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 16
Protected B - External / Protégé B - Externe
an institution  must set internal policies to identify suitable proxies and the
institution must demonstrate empirically on an ongoing basis that the proxy
provides a conservative representation of the underlying risk under adverse
market conditions.
[Basel Framework, MAR 50.36]
8.3.2 ELIGIBLE HEDGES
38. Only whole transactions that are used for the purpose of mitigating CVA risk, and
managed as such, can be eligible hedges. Transactions cannot be split into several
effective transactions. [Basel Framework, MAR 50.37]
39. Eligible hedges can include:
(1) instruments that hedge variability of the counterparty credit spread; and
(2) instruments that hedge variability of the exposure component of CVA risk.
[Basel Framework, MAR 50.38]
40. Instruments that are not eligible for the internal models approach for market risk under
Chapter 9 (e.g. tranched credit derivatives) cannot be eligible CVA hedges. [Basel
Framework, MAR 50.39]
8.3.3 MULTIPLIER
41. Aggregated capital requirements can be scaled up by the multiplier 𝑚𝑚
𝑐𝑐𝑐𝑐𝑐𝑐 [Basel
Framework, MAR 50.40]
42. The multiplier 𝑚𝑚𝑐𝑐𝑐𝑐𝑐𝑐 is set at 1. OSFI may require an institution to use a higher value of
𝑚𝑚𝑐𝑐𝑐𝑐𝑐𝑐  if the supervisor determines that the institution’s CVA model risk warrants it (e.g.
if the level of model risk for the calculation of CVA sensitivities is too high or the
dependence between the institution’s exposure to a counterparty and the counterparty’s
credit quality is not appropriately taken into account in its CVA calculations). [Basel
Framework, MAR 50.41]
8.3.4 CALCULATIONS
43. The SA-CVA capital requirements are calculated as the sum of the capital requirements
for delta and vega risks calculated for the entire CVA portfolio (including eligible
hedges). [Basel Framework, MAR 50.42]
44. The capital requirements for delta risk are calculated as the simple sum of delta capital
requirements calculated independently for the following six risk classes:
(1) interest rate risk;
(2) foreign exchange (FX) risk;
(3) counterparty credit spread risk;

---

<!-- Page 17 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 17
Protected B - External / Protégé B - Externe
(4) reference credit spread risk (i .e. credit spreads that drive the CVA exposure
component);
(5) equity risk; and
(6) commodity risk.
[Basel Framework, MAR 50.43]
45. If an instrument is deemed as an eligible hedge for credit spread delta risk, it must be
assigned in its entirety (see paragraph 38) either to the counterparty credit spread or to
the reference credit spread risk class. Instruments must not be split between the two risk
classes. [Basel Framework, MAR 50.44]
46. The capital requirements for vega risk are calculated as the simple sum of vega capital
requirements calculated independently for the following five risk classes. Note there
here are no vega capital requirements for counterparty credit spread risk.
(1) interest rate risk;
(2) FX risk;
(3) reference credit spread risk;
(4) equity risk; and
(5) commodity risk.
[Basel Framework, MAR 50.45]
47. Delta and vega capital requirements are calculated in the same manner using the same
procedures set out in paragraph 48 to paragraph 54. [Basel Framework, MAR 50.46]
48. For each risk class, (i) the sensitivity of the aggregate CVA, s
k
CVA, and (ii) the sensitivity
of the market value of all eligible hedging instruments in the CVA portfolio, sk
Hdg, to
each risk factor k in the risk class are calculated. The sensitivities are defined as the ratio
of the change of the value in question (i.e. (i) aggregate CVA or (ii) market value of all
CVA hedges) caused by a small change of the risk factor’s current value to the size of
the change. Specific definitions for each risk class are set out in paragraph 55 to
paragraph 78. These definitions include specific values of changes or shifts in risk
factors. However, an institution may use smaller or larger values of risk factor shifts if
doing so is consistent with internal risk management calculations.
An institution may use algorithmic techniques, such as adjoint algorithmic differentiation
to calculate CVA sensitivities under the SA -CVA if doing so is consistent with the
institution’s internal risk management calculations and the relevant validation standards
described in the SA-CVA framework. [Basel Framework, MAR 50.47]
49. CVA sensitivities for vega risk are always material and must be calculated regardless of
whether or not the portfolio includes options. When CVA sensitivities for vega risk are
calculated, the volatility shift must apply to both types of volatilities that appear in
exposure models:

---

<!-- Page 18 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 18
Protected B - External / Protégé B - Externe
(1) volatilities used for generating risk factor paths; and
(2) volatilities used for pricing options.
[Basel Framework, MAR 50.48]
50. If a hedging instrument is an index, its sensitivities to all risk factors upon which the
value of the index depends must be calculated. The index sensitivity to risk factor k must
be calculated by applying the shift of risk factor k to all index constituents that depend
on this risk factor and recalculating the changed value of the index. For example, to
calculate delta sensitivity of S&P500 to large financial companies, an institution must
apply the relevant shift to equity prices of all large financial companies that are
constituents of S&P500 and re-compute the index. [Basel Framework, MAR 50.49]
51. For the following risk classes, an institution may choose to introduce a set of additional
risk factors that directly correspond to qualified credit and equity indices. For delta risks,
a credit or equity index is qualified if it satisfies liquidity and diversification conditions
specified in paragraph 143 of Chapter 9; for vega risks, any credit or equity index is
qualified. Under this option, an institution must calculate sensitivities of CVA and the
eligible CVA hedges to the qualified index risk factors in addition to sensitivities to the
non-index risk factors. Under this option, for a covered transaction or an eligible hedging
instrument whose underlying is a qualified index, its contribution to sensitivities to the
index constituents is replaced with its contribution to a single sensitivity to the
underlying index. For example, for a portfolio consisting only of equity derivatives
referencing only qualified equity indices, no calculation of CVA sensitivities to non-
index equity risk factors is necessary. If more than 75% of constituents of a qualified
index (taking into account the weightings of the constituents) are mapped to the same
sector, the entire index must be mapped to that sector and treated as a single-name
sensitivity in that bucket. In all other cases, the sensitivity must be mapped to the
applicable index bucket.
(1) counterparty credit spread risk;
(2) reference credit spread risk; and
(3) equity risk.
[Basel Framework, MAR 50.50]
52. The weighted sensitivities WS
k
CVA and WSk
Hdgfor each risk factor k are calculated by
multiplying the net sensitivities sk
CVA and sk
Hdg, respectively, by the corresponding risk
weight RWk (the risk weights applicable to each risk class are specified in paragraph 55
to paragraph 78). [Basel Framework, MAR 50.51]
WSk
CVA = RWksk
CVA
WSk
Hdg = RWksk
Hdg
53. The net weighted sensitivity of the CVA portfolio sk to risk factor k is obtained by:

---

<!-- Page 19 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 19
Protected B - External / Protégé B - Externe
 WSk = WSK
CVA − WSk
Hdg

Note that the formula in paragraph 53 is set out under the convention that the CVA is
positive as specified in paragraph 33. It intends to recognize the risk reducing effect of
hedging. For example, when hedging the counterparty credit spread component of CVA
risk for a specific counterparty by buying credit protection on the counterparty: if the
counterparty’s credit spread widens, the CVA (expressed as a positive value) increases
resulting in the positive CVA sensitivity to the counterparty credit spread. At the same
time, as the value of the hedge from the institution ’s perspective increases as well (as
credit protection becomes more valuable), the sensitivity of the hedge is also positive. The
positive weighted sensitivities of the CVA and its hedge offset each other using the
formula with the minus sign. If CVA loss had been expressed as a negative value, the
minus sign in paragraph 53 would have been replaced by a plus sign. [Basel Framework,
MAR 50.52]
54. For each risk class, the net sensitivities are aggregated as follows:
(1) The weighted sensitivities must be aggregated into a capital requirement K
b
within each bucket b (the buckets and correlation parameters ρkl applicable to each
risk class are specified in paragraph 55 to paragraph 78), where R is the hedging
disallowance parameter, set at 0.01, that prev ents the possibility of recogniz ing
perfect hedging of CVA risk.
Kb = � � � WSk
2
k∈b
+ � � ρ klWSkWSl
l∈b,l≠kk∈b
� + R ∙ � ��WSk
Hdg�
2
�
k∈b

(2) Bucket-level capital requirements must then be aggregated across buckets within
each risk class (the correlation parameters  γbc applicable to each risk class are
specified in paragraph 55 to paragraph 78). Note that this equation differs from
the corresponding aggregation equation for market risk capital requirements in
paragraph 116 of Chapter 9, including the multiplier mCVA.
K = m CVA� � Kb
2 + � � γ bc
b≠c
SbSc
bb

(3) In calculating K in above (2), Sb is defined as the sum of the weighted sensitivities
WSk for all risk factors k within bucket b, floored by -K b and capped by Kb, and
the Sc is defined in the same way for all risk factors k in bucket c:
Sb = max �−Kb; min � � WSk; Kb
kϵb
� �

---

<!-- Page 20 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 20
Protected B - External / Protégé B - Externe
Sc = max �−Kc; min � � WSk; Kc
kϵc
� �
[Basel Framework, MAR 50.53]
8.3.5 INTEREST RATE BUCKETS, RISK FACTORS, SENSITIVITIES, RISK
WEIGHTS AND CORRELATIONS
55. For interest rate delta and vega risks, buckets must be set per individual currencies.
[Basel Framework, MAR 50.54]
56. For interest rate delta and vega risks, cross-bucket correlation γbc is set at 0.5 for all
currency pairs. [Basel Framework, MAR 50.55]
57. The interest rate delta risk factors for an institution’s reporting currency and for the
following currencies USD, EUR, GBP, AUD, CAD, SEK or JPY:
(1) The interest rate delta risk factors are the absolute changes of the inflation rate
and of the risk-free yields for the following five tenors: 1 year, 2 years, 5 years,
10 years and 30 years.
(2) The sensitivities to the abovementioned risk-free yields are measured by changing
the risk-free yield for a given tenor for all curves in a given currency by 1 basis
point (0.0001 in absolute terms) and dividing the resulting change in the aggregate
CVA (or the value of CVA hedges) by 0.0001. The sensitivity to the inflation rate
is obtained by changing the inflation rate by 1 basis point (0.0001 in absolute
terms) and dividing the resulting change in the aggregate CVA (or the value of
CVA hedges) by 0.0001.
(3) The risk weights RW
k are set as follows:
Table 3 Risk weight for interest rate risk factors (specified currencies)
1 year 2 years 5 years 10 years 30 years Inflation
Risk weight 1.11% 0.93% 0.74% 0.74% 0.74% 1.11%

(4) The correlations between pairs of risk factors ρkl are set as follows:

---

<!-- Page 21 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 21
Protected B - External / Protégé B - Externe
Table 4 Correlations for interest rate risk factors (specified currencies)
Tenor
Tenor 1 year 2 years 5 years 10 years 30 years Inflation
1 year 100%  91%  72%  55%  31%  40%
2 years   100%  87%  72%  45%  40%
5 years      100%  91%  68%  40%
10 years        100%  83%  40%
30 years          100%  40%
Inflation            100%
[Basel Framework, MAR 50.56]
58. The interest rate delta risk factors for other currencies not specified in paragraph above:
(1) The interest rate risk factors are the absolute change of the inflation rate and the
parallel shift of the entire risk-free yield curve for a given currency.
(2) The sensitivity to the yield curve is measured by applying a parallel shift to all
risk-free yield curves in a given currency by 1 basis point (0.0001 in absolute
terms) and dividing the resulting change in the aggregate CVA (or the value of
CVA hedges) by 0.0001. The sensitivity to the inflation rate is obtained by
changing the inflation rate by 1 basis point (0.0001 in absolute terms) and dividing
the resulting change in the aggregate CVA (or the value of CVA hedges) by
0.0001.
(3) The risk weights for both the risk-free yield curve and the inflation rate RW
k are
set at 1.58%.
(4) The correlations between the risk-free yield curve and the inflation rate ρkl are set
at 40%.
[Basel Framework, MAR 50.57]
59. The interest rate vega risk factors for all currencies:
(1) The interest rate vega risk factors are a simultaneous relative change of all
volatilities for the inflation rate and a simultaneous relative change of all interest
rate volatilities for a given currency.
(2) The sensitivity to (i) the interest rate volatilities or (ii) inflation rate volatilities is
measured by respectively applying a simultaneous shift to (i) all interest rate
volatilities or (ii) inflation rate volatilities by 1% relative to their current va lues
and dividing the resulting change in the aggregate CVA (or the value of CVA
hedges) by 0.01.
(3) The risk weights for both the interest rate volatilities and the inflation rate
volatilities RW
k are set to 100%.

---

<!-- Page 22 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 22
Protected B - External / Protégé B - Externe
(4) Correlations between the interest rate volatilities and the inflation rate volatilities
ρkl are set at 40%.
[Basel Framework, MAR 50.58]
8.3.6 FOREIGN EXCHANGE BUCKETS, RISK FACTORS, SENSITIVITIES, RISK
WEIGHTS AND CORRELATIONS
60. For FX delta and vega risks, buckets must be set per individual currencies except for an
institution’s own reporting currency. [Basel Framework, MAR 50.59]
61. For FX delta and vega risks, the cross-bucket correlation γbc is set at 0.6 for all currency
pairs. [Basel Framework, MAR 50.60]
62. The FX delta risk factors for all currencies:
(1) The single FX delta risk factor is defined as the relative change of the FX spot
rate between a given currency and an institution ’s reporting currency, where the
FX spot rate is the current market price of one unit of another currency expressed
in the units of the institution’s reporting currency.
(2) Sensitivities to FX spot rates are measured by shifting the exchange rate between
the institution’s reporting currency and another currency (i.e. the value of one unit
of another currency expressed in units of the reporting currency) by 1% relative
to its current value and dividing the resulting change in the aggregate CVA (or
the value of CVA hedges) by 0.01. For transactions that reference an exc hange
rate between a pair of non -reporting currencies, the sensitivities to the FX spot
rates between the institution’s reporting currency and each of the referenced non-
reporting currencies must be measured.
10
(3) The risk weights for all exchange rates between the institution ’s reporting
currency and another currency are set at 11%.
[Basel Framework, MAR 50.61]
63. The FX vega risk factors for all currencies:
(1) The single FX vega risk factor is a simultaneous relative change of all volatilities
for an exchange rate between an institution’s reporting currency and another given
currency.
(2) The sensitivities to the FX volatilities are measured by simultaneously shifting all
volatilities for a given foreign -domestic exchange rate between the institution ’s
reporting or base currency and another currency by 1% relative to their current
values and dividing the resulting change in the aggregate CVA (or the value of
CVA hedges) by 0.01. For transactions that reference an exchange rate between a
pair of non- reporting foreign-foreign currencies, the volatilities of the FX spot
rates are shifted according to the representation of the foreign- foreign exchange

10  For example, if a EUR-reporting bank holds an instrument that references the USD-GBP exchange rate, the
bank must measure CVA sensitivity both to the EUR-GBP exchange rate and to the EUR-USD exchange rate.

---

<!-- Page 23 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 23
Protected B - External / Protégé B - Externe
rate volatility via two foreign-domestic (or base) exchange rate volatilities and the
relevant implied correlation (the latter is assumed to be fixed).
(3) The risk weights for FX volatilities RWk are set to 100%.
[Basel Framework, MAR 50.62]
8.3.7 COUNTERPARTY CREDIT SPREAD BUCKETS, RISK FACTORS,
SENSITIVITIES, RISK WEIGHTS AND CORRELATIONS
64. Counterparty credit spread risk is not subject to vega risk capital requirements. Buckets
for delta risk are set as follows:
a) Buckets 1 to 7 are defined for factors that are not qualified indices as set out in
paragraph 51;
b) Bucket 8 is set for the optional treatment of qualified indices. Under the optional
treatment, only instruments that reference qualified indices can be assigned to bucket
8, while all single -name and all non- qualified index hedges must be assigned to
buckets 1 to 7 for calculations of CVA sensitivities and sensitivities. For any
instrument referencing an index assigned to buckets 1 to 7, the look-through approach
must be used (i .e. sensitivity of the hedge to each index constituent must be
calculated).
Table 5 Buckets for counterparty credit spread delta risk
Bucket number Sector
1

a) Sovereigns including central banks, multilateral development banks
 b) Local government, government -backed non -financials, education and
public administration
2  Financials including government-backed financials
3  Basic materials, energy, industrials, agriculture, manufacturing, mining and
quarrying
4  Consumer goods and services, transportation and storage, administrative and
support service activities
5  Technology, telecommunications
6  Health care, utilities, professional and technical activities
7  Other sector
8  Qualified Indices
[Basel Framework, MAR 50.63]
65. For counterparty credit spread delta risk, the cross-bucket correlations γbc are set as
follows:

---

<!-- Page 24 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 24
Protected B - External / Protégé B - Externe
Table 6 Cross-bucket correlations for counterparty credit spread
delta risk

 Bucket
Bucket 1 2 3 4 5 6 7 8
1 100% 10% 20% 25% 20% 15% 0% 45%
2  100% 5% 15% 20% 5% 0% 45%
3   100% 20% 25% 5% 0% 45%
4    100% 25% 5% 0% 45%
5     100% 5% 0% 45%
6      100% 0% 45%
7       100% 0%
8        100%
[Basel Framework, MAR 50.64]
66. The counterparty credit spread delta risk factors for a given bucket:
(1) The counterparty credit spread delta risk factors are absolute shifts of credit
spreads of individual entities (counterparties and reference names for
counterparty credit spread hedges) and qualified indices (if the optional treatment
is chosen) for the following tenors: 0.5 years, 1 year, 3 years, 5 years and 10 years.
(2) For each entity and each tenor point, the sensitivities are measured by shifting the
relevant credit spread by 1 basis point (0.0001 in absolute terms) and dividing the
resulting change in the aggregate CVA (or the value of CVA hedges) by 0.0001.
(3) The risk weights RW
k are set as follows depending on the entity’s bucket, where
IG, HY and NR represent “investment grade”, “high yield” and “not rated” as
specified for the BA -CVA in paragraph 17. The same risk weight for a given
bucket and given credit quality applies to all tenors.
Table 7 Risk weights for counterparty credit spread delta risk
 Bucket
 1 a) 1 b) 2 3 4 5 6 7 8
IG names 0.5% 1.0% 5.0% 3.0% 3.0% 2.0% 1.5% 5.0% 1.5%
HY and NR names 2.0% 4.0% 12.0% 7.0% 8.5% 5.5% 5.0% 12.0% 5.0%
(4) For buckets 1 to 7, the correlation parameter ρ kl between two weighted
sensitivities 𝑅𝑅𝑆𝑆𝑘𝑘 and 𝑅𝑅𝑆𝑆𝑙𝑙 is calculated as follows, where:
(
a) 𝜌𝜌𝑡𝑡𝑒𝑒𝑡𝑡 𝑡𝑡𝑡𝑡 is equal to 100% if the two tenors are the same and 90% otherwise;

---

<!-- Page 25 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 25
Protected B - External / Protégé B - Externe
(b) 𝜌𝜌𝑡𝑡𝑐𝑐𝑛𝑛𝑒𝑒 is equal to 100% if the two names are the same, 90% if the two
names are distinct, but legally related and 50% otherwise;
(c) 𝜌𝜌𝑞𝑞𝑞𝑞𝑐𝑐𝑙𝑙𝑞𝑞𝑡𝑡𝑞𝑞 is equal to 100% if the credit quality of the two names is the same
(ie IG and IG or HY/NR and HY/NR) and 80% otherwise.
𝜌𝜌𝑘𝑘𝑙𝑙= 𝜌𝜌𝑡𝑡𝑒𝑒𝑡𝑡𝑡𝑡𝑡𝑡∙ 𝜌𝜌𝑡𝑡𝑐𝑐𝑛𝑛𝑒𝑒∙ 𝜌𝜌𝑞𝑞𝑞𝑞𝑐𝑐𝑙𝑙𝑞𝑞𝑡𝑡𝑞𝑞
(5) For bucket 8, the correlation parameter ρ kl between two weighted sensitivities
𝑅𝑅𝑆𝑆𝑘𝑘 and 𝑅𝑅𝑆𝑆𝑙𝑙 is calculated as follows, where
(a) 𝜌𝜌𝑡𝑡𝑒𝑒𝑡𝑡𝑡𝑡𝑡𝑡 is equal to 100% if the two tenors are the same and 90% otherwise;
(b) 𝜌𝜌𝑡𝑡𝑐𝑐𝑛𝑛𝑒𝑒 is equal to 100% if the two indices are the same and of the same
series, 90% if the two indices are the same, but of distinct series, and 80%
otherwise;
(c) 𝜌𝜌𝑞𝑞𝑞𝑞𝑐𝑐𝑙𝑙𝑞𝑞𝑡𝑡𝑞𝑞 is equal to 100% if the credit quality of the two indices is the
same (ie IG and IG or HY and HY) and 80% otherwise.
𝜌𝜌𝑘𝑘𝑙𝑙= 𝜌𝜌𝑡𝑡𝑒𝑒𝑡𝑡𝑡𝑡𝑡𝑡∙ 𝜌𝜌𝑡𝑡𝑐𝑐𝑛𝑛𝑒𝑒∙ 𝜌𝜌𝑞𝑞𝑞𝑞𝑐𝑐𝑙𝑙𝑞𝑞𝑡𝑡𝑞𝑞
 [Basel Framework, MAR 50.65]
8.3.8 REFERENCE CREDIT SPREAD BUCKETS, RISK FACTORS, SENSITIVITIES,
RISK WEIGHTS AND CORRELATIONS
67. Reference credit spread risk is subject to both delta and vega risk capital requirements.
Buckets for delta and vega risks are set as follows, where IG, HY and NR represent
“investment grade”, “high yield” and “not rated” as specified for the BA-CVA in
paragraph 17:

---

<!-- Page 26 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 26
Protected B - External / Protégé B - Externe
Table 8 Buckets for reference credit spread risk
Bucket
number
Credit quality Sector
1 IG Sovereigns including central banks, multilateral development banks
2 IG Local government, government-backed non-financials, education and
public administration
3 IG Financials including government-backed financials
4 IG Basic materials, energy, industrials, agriculture, manufacturing, mining
and quarrying
5 IG Consumer goods and services, transportation and storage, administrative
and support service activities
6 IG Technology, telecommunications
7 IG Health care, utilities, professional and technical activities
8 HY and NR Sovereigns including central banks, multilateral development banks
9 HY and NR Local government, government-backed non-financials, education and
public administration
10 HY and NR Financials including government-backed financials
11 HY and NR Basic materials, energy, industrials, agriculture, manufacturing, mining
and quarrying
12 HY and NR Consumer goods and services, transportation and storage, administrative
and support service activities
13 HY and NR Technology, telecommunications
14 HY and NR Health care, utilities, professional and technical activities
15 (Not applicable) Other sector
16 IG Qualified Indices
17 HY Qualified Indices
[Basel Framework, MAR 50.66]
68. For reference credit spread delta and vega risks, the cross-bucket correlations γbc are set
as follows:
(1) The cross-bucket correlations γbc between buckets of the same credit quality (i.e.
either IG or HY/NR) are set as follows:

---

<!-- Page 27 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 27
Protected B - External / Protégé B - Externe
Table 9 Cross-bucket correlations for reference credit spread
risk


 Bucket
Bucket 1/8 2/9 3/10 4/11 5/12 6/13 7/14 15 16 17
1/8 100% 75% 10% 20% 25% 20% 15% 0% 45% 45%
2/9  100% 5% 15% 20% 15% 10% 0% 45% 45%
3/10   100% 5% 15% 20% 5% 0% 45% 45%
4/11    100% 20% 25% 5% 0% 45% 45%
5/12     100% 25% 5% 0% 45% 45%
6/13      100% 5% 0% 45% 45%
7/14       100% 0% 45% 45%
15        100% 0% 0%
16         100% 75%
17          100%

(2) For cross -bucket correlations γ bc between buckets 1 to 14 of different credit
quality (ie IG and HY/NR), the correlations γ bc specified in subsection (1) are
divided by 2.
[Basel Framework, MAR 50.67]
69. Reference credit spread delta risk factors for a given bucket:
(1) The single reference credit spread delta risk factor is a simultaneous absolute shift
of the credit spreads of all tenors for all reference names in the bucket.
(2) The sensitivity to reference credit spread delta risk is measured by simultaneously
shifting the credit spreads of all tenors for all reference names in the bucket by 1
basis point (0.0001 in absolute terms) and dividing the resulting change in the
aggregate CVA (or the value of CVA hedges) by 0.0001.
(3) The risk weights RW
k are set as follows depending on the reference name’s
bucket:

---

<!-- Page 28 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 28
Protected B - External / Protégé B - Externe
Table 10 Risk weights for reference credit spread delta
risk
Bucket
number
Bucket Risk weight
1 IG 0.5%
2 IG 1.0%
3 IG 5.0%
4 IG 3.0%
5 IG 3.0%
6 IG 2.0%
7 IG 1.5%
8 IG 2.0%
9 IG 4.0%
10 HY/NR 12.0%
11 HY/NR 7.0%
12 HY/NR 8.5%
13 HY/NR 5.5%
14 HY/NR 5.0%
15 HY/NR 12.0%
16 HY/NR 1.5%
17 HY/NR 5.0%

[Basel Framework, MAR 50.68]
70. Reference credit spread vega risk factors for a given bucket:
(1) The single reference credit spread vega risk factor is a simultaneous relative shift
of the volatilities of credit spreads of all tenors for all reference names in the
bucket.
(2) The sensitivity to the reference credit spread vega risk factor is measured by
simultaneously shifting the volatilities of credit spreads of all tenors for all
reference names in the bucket by 1% relative to their current values and dividing
the resulting change in the aggregate CVA (or the value of CVA hedges) by 0.01.
(3) Risk weights for reference credit spread volatilities RW
k are set to 100%.
[Basel Framework, MAR 50.69]

---

<!-- Page 29 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 29
Protected B - External / Protégé B - Externe
8.3.9 EQUITY BUCKETS, RISK FACTORS, SENSITIVITIES, RISK WEIGHTS AND
CORRELATIONS
71. For equity delta and vega risks, buckets are set as follows, where:
(1) Market capitali zation (“market cap”) is defined as the sum of the market
capitalizations of the same legal entity or group of legal entities across all stock
markets globally.  The reference to “group of legal entities” covers cases where
the listed entity is a parent company of a group of legal entities. Under no
circumstances should t he sum of the market capitali zations of multiple related
listed entities be used to determine whether a listed entity is “large market cap”
or “small market cap”.
(2) “Large market cap” is defined as a market capitalization equal to or greater than
$2.5 billion and “small market cap” is defined as a market capitaliz ation of less
than $2.5 billion.
(3) The advanced economies are Canada, the United States, Mexico, the euro area,
the non- euro area western European countries (the United Kingdom, Norway,
Sweden, Denmark and Switzerland), Japan, Oceania (Australia and New
Zealand), Singapore and Hong Kong SAR.
(4) To assign a risk exposure to a sector, institutions must rely on a classification that
is commonly used in the market for grouping issuers by industry sector. The
institution must assign each issuer to one of the sector buckets in the table above
and it must assign all issuers from the same industry to the same sector. Risk
positions from any issuer that an institution  cannot assign to a sector in this
fashion must be assigned to the “other sector” (i.e. bucket 11). For multinational
multi-sector equity iss uers, the allocation to a particular bucket must be done
according to the most material region and sector in which the issuer operates.

---

<!-- Page 30 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 30
Protected B - External / Protégé B - Externe

Table 11 Buckets for equity risk
Bucket number Size Region Sector
1
Large
Emerging
market
economies
Consumer goods and services, transportation and
storage, administrative and support service activities,
healthcare, utilities
2 Large Telecommunications, industrials
3
Large
Basic materials, energy, agriculture, manufacturing,
mining and quarrying
4
Large
Financials including government -backed financials,
real estate activities, technology
5
Large
Advanced
economies
Consumer goods and services, transportation and
storage, administrative and support service activities,
healthcare, utilities
6 Large Telecommunications, industrials
7
Large
Basic materials, energy, agriculture, manufacturing,
mining and quarrying
8
Large
Financials including government -backed financials,
real estate activities, technology
9
Small
Emerging
market
economies
All sectors described under bucket numbers 1, 2, 3,
and 4
10
Small
Advanced
economies
All sectors described under bucket numbers 5, 6, 7,
and 8
11 (Not
applicable)
(Not
applicable)
Other sector
12 Large cap Advanced
economies
Qualified Indices
13 Other Other Qualified Indices
 [Basel Framework, MAR 50.70]
72. For equity delta and vega risks, cross-bucket correlation γbc is set at 15% for all cross-
bucket pairs that fall within bucket numbers 1 to 10. The cross-bucket correlation
between buckets 12 and 13 is set at 75% and the cross-bucket correlation between
buckets 12 or 13 and any of the buckets 1-10 is 45%. γbc is set at 0% for all cross-bucket
pairs that include bucket 11. [Basel Framework, 50.71]
73. Equity delta risk factors for a given bucket:
(1) The single equity delta risk factor is a simultaneous relative shift of equity spot
prices for all reference names in the bucket.

---

<!-- Page 31 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 31
Protected B - External / Protégé B - Externe
(2) The sensitivity to the equity delta risk factor is measured by simultaneously
shifting the equity spot prices for all reference names in the bucket by 1% relative
to their current values and dividing the resulting change in the aggregate CVA (or
the value of CVA hedges) by 0.01.
(3) Risk weights RW
k are set as follows depending on the reference name’s bucket:
Table 12 Risk weights for equity delta risk
Bucket number Risk weight
1 55%
2 60%
3 45%
4 55%
5 30%
6 35%
7 40%
8 50%
9 70%
10 50%
11 70%
12 15%
13 25%
[Basel Framework, MAR 50.72]
74. Equity vega risk factors for a given bucket:
(1) The single equity vega risk factor is a simultaneous relative shift of the volatilities
for all reference names in the bucket.
(2) The sensitivity to the equity vega risk factor is measured by simultaneously
shifting the volatilities for all reference names in the bucket by 1% relative to their
current values and dividing the resulting change in the aggregate CVA (or the
value of CVA hedges) by 0.01.
(3) The risk weights for equity volatilities RW
k are set to 78% for large market
capitalization buckets and to 100% for the other buckets.
[Basel Framework, MAR 50.73]
8.3.10 COMMODITY BUCKETS, RISK FACTORS, SENSITIVITIES, RISK WEIGHTS
AND CORRELATIONS
75. For commodity delta and vega risks, buckets are set as follows:
Table 13 Buckets for commodity risk

---

<!-- Page 32 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 32
Protected B - External / Protégé B - Externe
Bucket
number
Commodity group Examples
1 Energy – Solid
combustibles
coal, charcoal, wood pellets, nuclear fuel (such as
uranium)
2 Energy – Liquid
combustibles
crude oil (such as Light -sweet, heavy, West Texas
Intermediate and Brent); biofuels (such as bioethanol and
biodiesel); petrochemicals (such as propane, ethane,
gasoline, methanol and butane); refined fuels (such as jet
fuel, kerosene, gasoil, fuel oil, naphtha, heating oil and
diesel)
3 Energy – Electricity and
carbon trading
electricity (such as spot, day-ahead, peak and off -peak);
carbon emissions trading (such as certified emissions
reductions, in- delivery month EU allowance, Regional
Greenhouse Gas Initiative CO2 allowance and renewable
energy certificates)
4 Freight dry-bulk route (such as Capesize, Panamax, Handysize
and Supramax); liquid- bulk/gas shipping route (such as
Suezmax, Aframax and very large crude carriers)
5 Metals – non-precious base metal (such as aluminium, copper, lead, nickel, tin
and zinc); steel raw materials (such as steel billet, steel
wire, steel coil, steel scrap and steel rebar, iron ore,
tungsten, vanadium, titanium and tantalum); minor metals
(such as cobalt, manganese, molybdenum)
6 Gaseous combustibles natural gas; liquefied natural gas
7 Precious metals
(including gold)
gold; silver; platinum; palladium
8 Grains & oilseed corn; wheat; soybean (such as soybean seed, soybean oil
and soybean meal); oats; palm oil; canola; barley;
rapeseed (such as rapeseed seed, rapeseed oil, and
rapeseed meal); red bean, sorghum; coconut oil; olive oil;
peanut oil; sunflower oil; rice
9 Livestock & dairy cattle (such live and feeder); hog; poultry; lamb; fish;
shrimp; dairy (such as milk, whey, eggs, butter and
cheese)
10 Softs and other
agricultural
cocoa; coffee (such as arabica and robusta); tea; citrus and
orange juice; potatoes; sugar; cotton; wool; lumber and
pulp; rubber
11 Other commodity industrial minerals (such as potash, fertilizer and
phosphate rocks), rare earths; terephthalic acid; flat glass
 [Basel Framework, MAR 50.74]
76. For commodity delta and vega risks, cross-bucket correlation γbc is set at 20% for all
cross-bucket pairs that fall within bucket numbers 1 to 10. γbc is set at 0% for all cross-
bucket pairs that include bucket 11. [Basel Framework, MAR 50.75]

---

<!-- Page 33 -->

Banks/BHC/T&L  Credit Valuation Adjustment (CVA) Risk
 September 2025 Chapter 8 - Page 33
Protected B - External / Protégé B - Externe
77. Commodity delta risk factors for a given bucket:
(1) The single commodity delta risk factor is a simultaneous relative shift of the
commodity spot prices for all commodities in the bucket.
(2) The sensitivities to commodity delta risk factors are measured by simultaneously
shifting the spot prices of all commodities in the bucket by 1% relative to their
current values and dividing the resulting change in the aggregate CVA (or the
value of CVA hedges) by 0.01.
(3) The risk weights RW
k are set as follows depending on the reference name’s
bucket:
Table 14 Risk weights for commodity delta risk
 Bucket number
 1 2 3 4 5 6 7 8 9 10 11
RW 30% 35% 60% 80% 40% 45% 20% 35% 25% 35% 50%
[Basel Framework, MAR 50.76]
78. Commodity vega risk factors for a given bucket:
(1) The single commodity vega risk factor is a simultaneous relative shift of the
volatilities for all commodities in the bucket.
(2) The sensitivity to the commodity vega risk factor is measured by simultaneously
shifting the volatilities for all commodities in the bucket by 1% relative to their
current values and dividing the resulting change in the aggregate CVA (or the
value of CVA hedges) by 0.01.
(3) The risk weights for commodity volatilities RW
k are set to 100%.
[Basel Framework, MAR 50.77]
