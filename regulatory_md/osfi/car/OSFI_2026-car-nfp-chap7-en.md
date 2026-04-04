<!-- Page 1 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 1
Protected B - External / Protégé B - Externe
Guideline
Subject: Capital Adequacy Requirements (CAR)
Chapter 7 - Settlement and Counterparty Risk
Effective Date:  November 2025 / January  2026
For institutions with a fiscal year ending October 31 or December 31, respectively.
The Capital Adequacy Requirements (CAR) for banks (including federal credit unions), bank
holding companies, federally regulated trust companies, federally regulated loan companies and
cooperative retail associations, collectively referred to as ‘institutions’, are set out in nine
chapters, each of which has been issued as a separate document. This document, Chapter 7 –
Settlement and Counterparty Risk, should be read in conjunction with the other CAR chapters.
The complete list of CAR chapters is as follows:
Chapter 1  Overview
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

---

<!-- Page 2 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 2
Protected B - External / Protégé B - Externe
Table of Contents
7.1. Treatment of counterparty credit risk and cross-product netting  ....................... 2
7.1. Treatment of counterparty credit risk and cross-product netting ........................ 4
7.1.1 Definitions and general terminology ....................................................... 4
7.1.1.1 General terms ............................................................................................ 4
7.1.1.2 Transaction types ....................................................................................... 6
7.1.1.3 Netting sets, hedging sets, and related terms ............................................ 6
7.1.1.4 Distributions .............................................................................................. 7
7.1.1.5 Exposure measures and adjustments ......................................................... 8
7.1.1.6 CCR-related risks ...................................................................................... 9
7.1.2 Scope of application .................................................................................. 9
7.1.3 Methods for Computing CCR Exposure ................................................ 10
7.1.4 Approval to adopt an internal modelling method to estimate EAD ...... 12
7.1.5 Internal Model Method: measuring exposure and minimum
requirements ........................................................................................... 13
7.1.5.1 Exposure amount or EAD under the internal model method .................. 13
7.1.5.2 Own estimates for alpha .......................................................................... 15
7.1.5.3 Maturity ................................................................................................... 15
7.1.5.4 Margin agreements .................................................................................. 16
7.1.5.5 Model validation ...................................................................................... 17
7.1.5.6 Operational requirements for EPE models ............................................. 21
7.1.6 Cross-product netting rules .................................................................... 29
7.1.6.1 Legal Criteria .......................................................................................... 29
7.1.6.2 Operational Criteria ................................................................................ 30
7.1.7 Standardized Approach for Counterparty Credit Risk .......................... 30
7.1.7.1 RC and NICA ........................................................................................... 31
7.1.7.2 PFE Add-ons ........................................................................................... 35
7.1.7.3 Recognition of excess collateral and negative mark-to-market .............. 36
7.1.7.4 Aggregation across asset classes ............................................................ 36
7.1.7.5 Allocation of derivative transactions to one or more asset classes ......... 36
7.1.7.6 General steps for calculating the add-on ................................................ 37
7.1.7.7 Time Period Parameters Mi, Ei, Si, and Ti ............................................. 38

---

<!-- Page 3 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 3
Protected B - External / Protégé B - Externe
7.1.7.8 Trade-level Adjusted Notional (for trade I): di ....................................... 40
7.1.7.9 Supervisory delta adjustments: δi ............................................................ 42
7.1.7.10 Supervisory Factors: SFi ................................................................... 44
7.1.7.11 Hedging Sets ...................................................................................... 44
7.1.7.12 Maturity Factors ................................................................................ 45
7.1.7.13 Supervisory correlation parameters: ρi(a) ....................................... 47
7.1.7.14 Add-on for interest rate derivatives ................................................... 47
7.1.7.15 Add-on for foreign exchange derivatives........................................... 48
7.1.7.16 Add-on for credit derivatives ............................................................. 49
7.1.7.17 Add-on for equity derivatives ............................................................ 51
7.1.7.18 Add-on for commodity derivatives ..................................................... 52
7.1.7.19 Treatment of multiple margin agreements and multiple netting
sets ........................................................................................................... 54
7.1.7.20 Treatment of trades subject to Specific Wrong-Way Risk and
Specific Right-Way Risk........................................................................... 56
7.1.8 Central Counterparties ........................................................................... 57
7.1.8.1 Exposures to Qualifying CCPs ................................................................ 57
7.1.8.2 Exposures to Non-qualifying CCPs ......................................................... 66
7.2. Capital treatment for failed trades and non-DvP transactions ........................... 67
7.2.1 Overarching principles ........................................................................... 67
7.2.2 Capital requirements .............................................................................. 68

---

<!-- Page 4 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 4
Protected B - External / Protégé B - Externe
Chapter 7 –  Settlement and Counterparty Risk
1. This chapter is drawn from the Basel Committee on Banking Supervision (BCBS) Basel
framework, published on the Bank for International Settlements (BIS) website1. For
reference, the Basel paragraph numbers that are associated with the text appearing in this
chapter are indicated in square brackets at the end of each paragraph.
2

7.1. Treatment of counterparty credit risk and cross-product netting

2. This rule identifies permissible methods for estimating the Exposure at Default (EAD)
or the exposure amount for instruments with counterparty credit risk under this guideline.
3
Institutions may seek OSFI approval to make use of an Internal Modelling Method (IMM)
meeting the requirements and specifications identified herein. As an alternative institutions may
also use the Standardized Approach for Counterparty Credit Risk (SA-CCR). [Basel Framework,
CRE 53.1]
7.1.1 Definitions and general terminology
3. This section defines terms that will be used throughout this chapter.

7.1.1.1 General terms

• Counterparty Credit Risk (CCR) is the risk that the counterparty to a transaction could
default before the final settlement of the transaction's cash flows. An economic loss
would occur if the transactions or portfolio of transactions with the counterparty has a
positive economic value at the time of default. Unlike an institution’s exposure to credit
risk through a loan, where the exposure to credit risk is unilateral and only the lending
institution faces the risk of loss, CCR creates a bilateral risk of loss: the market value of
the transaction can be positive or negative to either counterparty to the transaction. The
market value is uncertain and can vary over time with the movement of underlying
market factors.
• A central counterparty (CCP) is a clearing house that interposes itself between
counterparties to contracts traded in one or more financial markets, becoming the buyer
to every seller and the seller to every buyer and thereby ensuring the future performance
of open contracts. A CCP becomes a counterparty to trades with market participants
through novation, an open offer system, or another legally binding arrangement. For the
purposes of the capital framework, a CCP is a financial institution.
• A qualifying central counterparty (QCCP) is an entity that is licensed to operate as a
CCP (including a license granted by way of confirming an exemption), and is permitted
by the appropriate regulator/overseer to operate as such with respect to the products

1    The Basel Framework
2  Following the format: [Basel Framework XXX yy.zz].
3 In this document, the terms “exposure at default” and “exposure amount” are used together in order to identify
measures of exposure under both an internal ratings-based (IRB) and a standardized approach for credit risk.

---

<!-- Page 5 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 5
Protected B - External / Protégé B - Externe
offered. This is subject to the provision that the CCP is based and prudentially supervised
in a jurisdiction where the relevant regulator/overseer has established, and publicly
indicated that it applies to the CCP on an ongoing basis, domestic rules and regulations
that are consistent with the CPSS-IOSCO Principles for Financial Market Infrastructures.
Where the CCP is in a jurisdiction that does not have a CCP regulator applying the
Principles to the CCP, then OSFI may make the determination of whether the CCP meets
this definition.
In addition, for a CCP to be considered as a QCCP, the requirements in paragraph 204
must be met to permit each clearing member institution to calculate its capital
requirement for its default fund contributions.
• A clearing member is a member of, or a direct participant in, a CCP that is entitled to
enter into a transaction with the CCP, regardless of whether it enters into trades with a
CCP for its own hedging, investment or speculative purposes or whether it also enters
into trades as a financial intermediary between the CCP and other market participants.
4
• A client is a party to a transaction with a CCP through either a clearing member acting as
a financial intermediary, or a clearing member guaranteeing the performance of the client
to the CCP.
• Initial margin means a clearing member’s or client’s funded collateral posted to the CCP
to mitigate the potential future exposure of the CCP to the clearing member arising from
the possible future change in the value of their transactions. For the purposes of the
calculation of counterparty credit risk capital requirements, initial margin does not
include contributions to a CCP for mutualized loss sharing arrangements (i.e. in case a
CCP uses initial margin to mutualize losses among the clearing members, it will be
treated as a default fund exposure). Initial margin may include excess collateral, in cases
where the CCP may prevent the clearing member and the clearing member may prevent
the client from withdrawing the excess.
• Variation margin means a clearing member’s or client’s funded collateral posted on a
daily or intraday basis to a CCP based upon price movements of their transactions.
• Trade exposures (in section 7.1.8) include the current
5 and potential future exposure of a
clearing member or a client to a CCP arising from OTC derivatives, exchange traded
derivatives transactions or securities financing transactions (SFTs), as well as initial
margin.
• Default funds, also known as clearing deposits or guaranty fund contributions (or any
other names), are clearing members’ funded or unfunded contributions towards, or
underwriting of, a CCP’s mutualized loss sharing arrangements. The description given by

4  For the purposes of this chapter, where a CCP has a link to a second CCP, that second CCP is to be treated as a
clearing member of the first CCP. Whether the second CCP’s collateral contribution to the first CCP is treated as
initial margin or a default fund contribution will depend upon the legal arrangement between the CCPs. OSFI
should be consulted to determine the treatment of this initial margin and default fund contributions.
5  For the purposes of this definition, the current exposure of a clearing member includes the variation margin due
to the clearing member but not yet received.

---

<!-- Page 6 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 6
Protected B - External / Protégé B - Externe
a CCP to its mutualized loss sharing arrangements is not determinative of its status as a
default fund; rather, the substance of such arrangements will govern its status.
• Offsetting transaction means the transaction leg between the clearing member and the
CCP when the clearing member acts on behalf of a client (e.g. when a clearing member
clears or novates a client’s trade).

• A multi-level client structure is one in which institutions can centrally clear as indirect
clients; that is, when clearing services are provided to the institution by an institution
which is not a direct clearing member, but is itself a client of a clearing member or
another clearing client. For exposures between clients and clients of clients, we use the
term “higher-level client” for the institution providing clearing services; and the term
“lower level client” for the institution clearing through that client.
[Basel Framework, CRE 50.6]

7.1.1.2 Transaction types

• Long Settlement Transactions are transactions where a counterparty undertakes to
deliver a security, a commodity, or a foreign exchange amount against cash, other
financial instruments, or commodities, or vice versa, at a settlement or delivery date that
is contractually specified as more than the lower of the market standard for this particular
instrument and five business days after the date on which the institution enters into the
transaction.
• Securities Financing Transactions (SFTs) are transactions such as repurchase
agreements, reverse repurchase agreements, security lending and borrowing, and margin
lending transactions, where the value of the transactions depends on market valuations
and the transactions are often subject to margin agreements.
• Margin Lending Transactions are transactions in which an institution extends credit in
connection with the purchase, sale, carrying or trading of securities. Margin lending
transactions do not include other loans that happen to be secured by securities collateral.
Generally, in margin lending transactions, the loan amount is collateralized by securities
whose value is greater than the amount of the loan.
[Basel Framework, CRE 50.14]

7.1.1.3 Netting sets, hedging sets, and related terms

• Netting Set is a group of transactions with a single counterparty that are subject to a
legally enforceable bilateral netting arrangement and for which netting is recognized for
regulatory capital purposes under Chapter 4 or the Cross-Product Netting Rules set forth
in this chapter. Each transaction that is not subject to a legally enforceable bilateral
netting arrangement that is recognized for regulatory capital purposes should be
interpreted as its own netting set for the purpose of these rules.
• Hedging Set is a set of transactions within a single netting set within which full or partial
offsetting is recognized for purposes of calculating the potential future exposure (PFE)
add-on of the SA-CCR.

---

<!-- Page 7 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 7
Protected B - External / Protégé B - Externe
• Margin Agreement is a contractual agreement or provisions to an agreement under
which one counterparty must supply collateral to a second counterparty when an
exposure of that second counterparty to the first counterparty exceeds a specified level.
• Margin Threshold is the largest amount of an exposure that remains outstanding until
one party has the right to call for collateral.
• Margin Period of Risk is the time period from the last exchange of collateral covering a
netting set of transactions with a defaulting counterpart until that counterpart is closed out
and the resulting market risk is re-hedged.
• Effective Maturity under the Internal Model Method for a netting set with maturity
greater than one year is the ratio of the sum of expected exposure over the life of the
transactions in a netting set discounted at the risk-free rate of return divided by the sum of
expected exposure over one year in a netting set discounted at the risk-free rate. This
effective maturity may be adjusted to reflect rollover risk by replacing expected exposure
with effective expected exposure for forecasting horizons under one year. The formula is
given in paragraph 35.
• Cross-Product Netting refers to the inclusion of transactions of different product
categories within the same netting set pursuant to the Cross-Product Netting Rules set out
in this chapter.
• Current Market Value (CMV) refers to the net market value of the portfolio of
transactions within the netting set with the counterparty. Both positive and negative
market values are used in computing CMV.
[ Basel Framework, CRE 50.15]

7.1.1.4 Distributions

• Distribution of Market Values is the forecast of the probability distribution of net
market values of transactions within a netting set for some future date (the forecasting
horizon) given the realized market value of those transactions up to the present time.
• Distribution of Exposures is the forecast of the probability distribution of market values
that is generated by setting forecast instances of negative net market values equal to zero
(this takes account of the fact that, when the institution owes the counterparty money, the
institution does not have an exposure to the counterparty).
• Risk-Neutral Distribution is a distribution of market values or exposures at a future
time period where the distribution is calculated using market implied values such as
implied volatilities.
• Actual Distribution is a distribution of market values or exposures at a future time
period where the distribution is calculated using historic or realized values such as
volatilities calculated using past price or rate changes.
[Basel Framework, CRE 50.22 to 50.25]

---

<!-- Page 8 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 8
Protected B - External / Protégé B - Externe
7.1.1.5 Exposure measures and adjustments

• Current Exposure is the larger of zero, or the market value of a transaction or portfolio
of transactions within a netting set with a counterparty that would be lost upon the default
of the counterparty, assuming no recovery on the value of those transactions in
bankruptcy. Current exposure is often also called Replacement Cost.
• Peak Exposure is a high percentile (typically 95% or 99%) of the distribution of
exposures at any particular future date before the maturity date of the longest transaction
in the netting set. A peak exposure value is typically generated for many future dates up
until the longest maturity date of transactions in the netting set.
• Expected Exposure is the mean (average) of the distribution of exposures at any
particular future date before the longest-maturity transaction in the netting set matures.
An expected exposure value is typically generated for many future dates up until the
longest maturity date of transactions in the netting set.
• Effective Expected Exposure at a specific date is the maximum expected exposure that
occurs at that date or any prior date. Alternatively, it may be defined for a specific date as
the greater of the expected exposure at that date, or the effective exposure at the previous
date. In effect, the Effective Expected Exposure is the Expected Exposure that is
constrained to be non-decreasing over time.
• Expected Positive Exposure (EPE) is the weighted average over time of expected
exposures where the weights are the proportion that an individual expected exposure
represents of the entire time interval. When calculating the minimum capital requirement,
the average is taken over the first year or, if all the contracts in the netting set mature
before one year, over the time period of the longest-maturity contract in the netting set.
• Effective Expected Positive Exposure (Effective EPE) is the weighted average over
time of effective expected exposure over the first year, or, if all the contracts in the
netting set mature before one year, over the time period of the longest-maturity contract
in the netting set where the weights are the proportion that an individual expected
exposure represents of the entire time interval.
• Credit Valuation Adjustment is an adjustment to the mid-market valuation of the
portfolio of trades with a counterparty. This adjustment reflects the market value of the
credit risk due to any failure to perform on contractual agreements with a counterparty.
This adjustment may reflect the market value of the credit risk of the counterparty or the
market value of the credit risk of both the institution and the counterparty.
• One-Sided Credit Valuation Adjustment is a credit valuation adjustment that reflects
the market value of the credit risk of the counterparty to the firm, but does not reflect the
market value of the credit risk of the institution to the counterparty.
• Debit Valuation Adjustment is a valuation adjustment that reflects the market value of
the credit risk of the institution to the counterparty (i.e. changes in the reporting
institution’s own credit risk), but does not reflect the market value of the credit risk of the
counterparty to the institution. [Added by OSFI]
[ Basel Framework, CRE 50.26 to 50.33]

---

<!-- Page 9 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 9
Protected B - External / Protégé B - Externe

7.1.1.6 CCR-related risks

• Rollover Risk is the amount by which expected positive exposure is understated when
future transactions with a counterpart are expected to be conducted on an ongoing basis,
but the additional exposure generated by those future transactions is not included in
calculation of expected positive exposure.
• General Wrong-Way Risk arises when the probability of default of counterparties is
positively correlated with general market risk factors.
• Specific Wrong-Way Risk arises when the exposure to a particular counterpart is
positively correlated with the probability of default of the counterparty due to the nature
of the transactions with the counterparty.
[Basel Framework, CRE 50.34 to 50.36]
7.1.2 Scope of application
4. Banks must calculate a counterparty credit risk charge for all exposures that give rise to
counterparty credit risk, with the exception of those transactions listed in paragraphs 10 and 11
below. The categories of transaction that give rise to counterparty credit risk are:
• OTC Derivatives;
• Exchange-traded derivatives (ETDs);
• Long Settlement transactions; and
• Securities Financing Transactions (SFTs).
[Basel Framework, CRE 51.4]

5. Such instruments generally exhibit the following abstract characteristics:
• the transactions generate a current exposure or market value;
• the transactions have an associated random future market value based on market
variables;
• the transactions generate an exchange of future payments or an exchange of a financial
instrument (including commodities) against payment;
• the transactions are undertaken with an identified counterparty against which a unique
probability of default can be determined.
6
[Basel Framework, CRE 51.5]


6  Transactions for which the probability of default is defined on a pooled basis are not included in this treatment of
CCR.

---

<!-- Page 10 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 10
Protected B - External / Protégé B - Externe
6. Other common characteristics of the transactions to be covered may include the
following:
• collateral may be used to mitigate risk exposure and is inherent in the nature of some
transactions;
• short-term financing may be a primary objective in that the transactions mostly consist of
an exchange of one asset for another (cash or securities) for a relatively short period of
time, usually for the business purpose of financing. The two sides of the transactions are
not the result of separate decisions but form an indivisible whole to accomplish a defined
objective;
• netting may be used to mitigate the risk;
• positions are frequently valued (most commonly on a daily basis), according to market
variables.
• remargining may be employed.
[Basel Framework, CRE 51.6]

7.1.3 Methods for Computing CCR Exposure
7. For the transaction types listed in paragraph 4 above, banks must calculate their
counterparty credit risk exposure, or exposure at default (EAD),
7 using one of the methods set
out in paragraphs 8 to 9 below. The methods vary according to the type of the transaction, the
counterparty to the transaction, and whether the bank has received supervisory approval to use
the method (if such approval is required). [Basel Framework, CRE 51.7]
8. For exposures that are not cleared through a central counterparty (CCP) the following
methods must be used to calculate the counterparty credit risk exposure:
(1) The standardized approach for measuring counterparty credit risk exposures (SA-CCR),
which is set out in section 7.1.7. This method is to be used for exposures arising from OTC
derivatives, exchange-traded derivatives and long settlement transactions. This method must be
used if the bank does not have approval to use the internal model method (IMM).
(2) The simple approach or comprehensive approach to the recognition of collateral, which are
both set out in the credit risk mitigation section of the standardized approach to credit risk (see
Chapter 4, section 4.3). These methods are to be used for securities financing transactions (SFTs)
and must be used if the bank does not have approval to use the value-at-risk (VaR) models or the
IMM.

7    The terms “exposure” and “EAD” are used interchangably in the counterparty credit risk chapters of the credit
risk standard. This reflects the fact that the amounts calculated under the counterparty credit risk rules must
typically be used as either the “exposure” within the standardized approach to credit risk, or the EAD within the
internal ratings-based (IRB) approach to credit risk, as described in paragraph 13.

---

<!-- Page 11 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 11
Protected B - External / Protégé B - Externe
(3) The VaR models approach, which is set out in Chapter 4, section 4.3. The VaR models
approach may be used to calculate EAD for SFTs, subject to supervisory approval, as an
alternative to the method set out in (2) above.
(4) The IMM, which is set out in 7.1.5. This method may be used, subject to supervisory
approval, as an alternative to the methods to calculate counterparty credit risk exposures set out
in (1) and (2) above (for all of the exposures referenced in those bullets).
[Basel Framework, CRE 51.8]
9. For exposures that are cleared through a CCP, banks must apply the method set out in
section 7.1.8. This method covers:
(1) the exposures of a bank to a CCP when the bank is a clearing member of the CCP;
(2) the exposures of a bank to its clients, when the bank is a clearing member and acts as an
intermediary between the client and the CCP; and
(3) the exposures of a bank to a clearing member of a CCP, when the bank is a client of the
clearing member and the clearing member is acting as an intermediary between the bank and the
CCP. [Basel Framework, CRE 51.8]
10. Exposures arising from the settlement of cash transactions (equities, fixed income, spot
FX and spot commodities) are not subject to this treatment.
8 The settlement of cash transactions
remains subject to the treatment described in section 7.2. [Basel Framework, CRE 51.10]

11. As an exception to the requirements of paragraph 4 above, banks are not required to
calculate a counterparty credit risk charge for the following types of transactions (i.e. the
exposure amount or EAD for counterparty credit risk for the transaction will be zero):
(1) Credit derivative protection purchased by the bank against a banking book exposure, or
against a counterparty credit risk exposure. In such cases, the bank will determine its capital
requirement for the hedged exposure according to the criteria and general rules for the
recognition of credit derivatives within the standardized approach or IRB approach to credit risk
(i.e. substitution approach).
(2) Sold credit default swaps in the banking book where they are treated in the framework as a
guarantee provided by the bank and subject to a credit risk charge for the full notional amount.
[Basel Framework, CRE 51.16]

12. Under the methods outlined above, the exposure amount or EAD for a given
counterparty is equal to the sum of the exposure amounts or EADs calculated for each netting set

8  For contributions to prepaid default funds covering settlement-risk-only products, the applicable risk weight is
0%.

---

<!-- Page 12 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 12
Protected B - External / Protégé B - Externe
with that counterparty,9 subject to the exception outlined in paragraph 13. [Basel Framework,
CRE 51.11]

13. The exposure or EAD for a given OTC derivative counterparty is defined as the greater
of zero, and the difference between the following: the sum of EADs across all netting sets with
the counterparty, and the credit valuation adjustment (CVA) for that counterparty which has
already been recognized by the bank as an incurred write-down (i.e. a CVA loss). This CVA loss
is calculated without taking into account any offsetting debit valuation adjustments or funding
valuation adjustments deducted from capital under Chapter 2 of this guideline. This reduction of
EAD by incurred CVA losses does not apply to the determination of the CVA risk capital
requirement. [Basel Framework, CRE 51.13]

14. RWAs for a given OTC derivative counterparty may be calculated as the applicable risk
weight under the standardized or IRB approach multiplied by the outstanding EAD of the
counterparty. [Basel Framework, CRE 51.12]
7.1.4 Approval to adopt an internal modelling method to estimate EAD
15. An institution (meaning the individual legal entity or a group) that wishes to adopt an
internal modelling method to measure exposure or EAD for regulatory capital purposes must
seek OSFI approval. IMM is available both for institutions that adopt the internal ratings-based
approach to credit risk and for institutions for which the standardized approach to credit risk
applies to all of their credit risk exposures. Only institutions subject to the market risk rules of
Chapter 9 of this guideline are permitted to apply for the use of the IMM. The institution must
meet all of the requirements given in section 7.1.5. [Basel Framework, CRE 53.1]

16. An institution may also choose to adopt an internal modelling method to measure CCR
for regulatory capital purposes for its exposures or EAD to only OTC derivatives, to only SFTs,
or to both, subject to the appropriate recognition of netting specified below in section 7.1.6. The
institution must apply the method to all relevant exposures within that category, except for those
that are immaterial in size and risk. During the initial implementation of the internal models
method, an institution may use the SACCR for a portion of its business. The institution must
submit a plan to OSFI to bring all material exposures for that category of transactions under the
IMM. [Basel Framework, CRE 53.2]

17. For all OTC derivative transactions and for all long settlement transactions for which an
institution has not received OSFI approval to use the internal models method, the institution must
use the SA-CCR. [Basel Framework, CRE 53.3]

18. Exposures or EAD arising from long settlement transactions can be determined using
either of the methods identified in this guideline regardless of the methods chosen for treating
OTC derivatives and SFTs. In computing capital requirements for long settlement transactions,
institutions that hold permission to use the internal ratings-based approach may opt to apply the

9  Where a single margin agreement applies to multiple netting sets and the SA-CCR is used, refer to paragraphs
166 to 167.

---

<!-- Page 13 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 13
Protected B - External / Protégé B - Externe
risk weights under the standardized approach for credit risk on a permanent basis and
irrespective to the materiality of such positions. [Basel Framework, CRE 53.4]

19. After adoption of the internal model method, the institution must comply with the above
requirements on a permanent basis. Only under exceptional circumstances or for immaterial
exposures can an institution revert to the SA-CCR for all or part of its exposure. In all cases, the
institution must obtain approval from OSFI to do so and demonstrate that reversion to a less
sophisticated method does not lead to an arbitrage of the regulatory capital rules. [Basel
Framework, CRE 53.5]
7.1.5 Internal Model Method: measuring exposure and minimum requirements
7.1.5.1 Exposure amount or EAD under the internal model method
20. CCR exposure or EAD is measured at the level of the netting set as defined in sections
7.1.1 and 7.1.6. A qualifying internal model for measuring counterparty credit exposure must
specify the forecasting distribution for changes in the market value of the netting set attributable
to changes in market variables, such as interest rates, foreign exchange rates, etc. The model then
computes the firm’s CCR exposure for the netting set at each future date given the changes in the
market variables. For margined counterparties, the model may also capture future collateral
movements. Institutions may include eligible financial collateral as defined in section 4.3.3 and
Chapter 9 in their forecasting distributions for changes in the market value of the netting set, if
the quantitative, qualitative and data requirements for internal model method are met for the
collateral. [Basel Framework, CRE 53.6]

21. To determine the default risk capital charge for counterparty credit risk for exposures
subject to the IMM, institutions must use the greater of the portfolio-level capital charge (not
including the CVA charge in Chapter 8) based on Effective EPE using current market data and
the portfolio-level capital charge based on Effective EPE using a stress calibration. The stress
calibration should be a single consistent stress calibration for the whole portfolio of
counterparties. The greater of Effective EPE using current market data and the stress calibration
should be applied on a total portfolio level and not on a counterparty by counterparty basis.
[Basel Framework, CRE 53.7]

22. OSFI expects institutions to have in place a policy for verifying the adequacy of, and
updating, their choice of stress period. This policy would have to be approved in advance by
OSFI as part of the IMM model approval process. Changes to this policy would constitute a
major modification of the IMM model.

23. To the extent that an institution recognizes collateral in exposure amount or EAD via
current exposure, an institution would not be permitted to recognize the benefits in its estimates
of LGD. As a result, the institution would be required to use an LGD of an otherwise similar
uncollateralized facility. In other words, it would be required to use an LGD that does not
include collateral that is already included in EAD. [Basel Framework, CRE 53.8]

24. Under the IMM, the institution need not employ a single model. Although the following
text describes an internal model as a simulation model, no particular form of model is required.

---

<!-- Page 14 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 14
Protected B - External / Protégé B - Externe
Analytical models are acceptable so long as they are subject to OSFI review, meet all of the
requirements set forth in this section and are applied to all material exposures subject to a CCR-
related capital charge as noted above, with the exception of long settlement transactions, which
are treated separately, and with the exception of those exposures that are immaterial in size and
risk. [Basel Framework, CRE 53.9]

25. Expected exposure or peak exposure measures should be calculated based on a
distribution of exposures that accounts for the possible non-normality of the distribution of
exposures, including the existence of leptokurtosis (“fat tails”), where appropriate. [Basel
Framework, CRE 53.10]

26. When using an internal model, exposure amount or EAD is calculated as the product of
alpha times Effective EPE, as specified below (except for counterparties that have been
identified as having explicit specific wrong-way risk or specific right-way risk – see paragraph
65):

EAD = α × Effective EPE  (1)
[Basel Framework, CRE 53.11]
27. Effective EPE (“Expected Positive Exposure”) is computed by estimating expected
exposure (EE
t) as the average exposure at future date t, where the average is taken across
possible future values of relevant market risk factors, such as interest rates, foreign exchange
rates, etc.  The internal model estimates EE as a series of future dates t1, t2, t3… 10. Specifically,
“Effective EE” is computed recursively, where the current date is denoted as t0 and Effective
EEt0 equals current exposure:
Effective EEtk = max(Effective EEtk-1, EEtk)  (2)
where the current date is denoted as t0 and Effective EEt0 equals current exposure.
[Basel Framework, CRE 53.12]
28. In this regard, “Effective EPE” is the average Effective EE during the first year of future
exposure. If all contracts in the netting set mature before one year, EPE is the average of
expected exposure until all contracts in the netting set mature. Effective EPE is computed as a
weighted average of Effective EE:
min(1 , )
1
k
year maturity
tk
k
Effective EPE Effective EE t
=
= ×∆∑  (3)
where the weights Δtk = tk – tk-1 allows for the case when future exposure is calculated at
dates that are not equally spaced over time.

10  In theory, the expectations should be taken with respect to the actual probability distribution of future exposure
and not the risk- neutral one. OSFI recogni zes that practical considerations may make it more feasible to use the
risk-neutral one. As a result, OSFI will not mandate which kind of forecasting distribution to employ.

---

<!-- Page 15 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 15
Protected B - External / Protégé B - Externe
[Basel Framework, CRE 53.13]
29. Alpha (α) is set equal to 1.4. [Basel Framework, CRE 53.14]

30. OSFI retains discretion to require a higher alpha based on a firm’s CCR exposures.
Factors that may require a higher alpha include the low granularity of counterparties; particularly
high exposures to general wrong-way risk; particularly high correlation of market values across
counterparties; and other institution-specific characteristics of CCR exposures. [Basel
Framework, CRE 53.15]
7.1.5.2 Own estimates for alpha
31. Institutions may seek OSFI approval to compute internal estimates of alpha subject to a
floor of 1.2, where alpha equals the ratio of economic capital from a full simulation of
counterparty exposure across counterparties (numerator) and economic capital based on EPE
(denominator), assuming they meet certain operating requirements. Eligible institutions must
meet all the operating requirements for internal estimates of EPE and must demonstrate that their
internal estimates of alpha capture in the numerator the material sources of stochastic
dependency of distributions of market values of transactions or of portfolios of transactions
across counterparties (e.g. the correlation of defaults across counterparties and between market
risk and default). [Basel Framework, CRE 53.16]

32. In the denominator, EPE must be used as if it were a fixed outstanding loan amount.
[Basel Framework, CRE 53.17]

33. To this end, institutions must ensure that the numerator and denominator of alpha are
computed in a consistent fashion with respect to the modelling methodology, parameter
specifications and portfolio composition. The approach used must be based on the firm’s internal
economic capital approach, be well-documented and be subject to independent validation. In
addition, institutions must review their estimates on at least a quarterly basis, and more
frequently when the composition of the portfolio varies over time. Institutions must assess the
model risk given the significant variation in estimates of alpha can arise from the possibility for
mis-specification in the models used for the numerator, especially where convexity is present.
The assessment of model risk must be part of the independent model validation and approval
process and model performance monitoring. [Basel Framework, CRE 53.18]

34. Where appropriate, volatilities and correlations of market risk factors used in the joint
simulation of market and credit risk should be conditioned on the credit risk factor to reflect
potential increases in volatility or correlation in an economic downturn. Internal estimates of
alpha should take account of the granularity of exposures. [Basel Framework, CRE 53.19]
7.1.5.3 Maturity
35. If the original maturity of the longest-dated contract contained in the set is greater than
one year, the formula for effective maturity (M) in Chapter 5 is replaced with the following:

---

<!-- Page 16 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 16
Protected B - External / Protégé B - Externe

where dfk is the risk-free discount factor for future time period tk and the remaining symbols
are defined above. Similar to the treatment under corporate exposures, M has a cap of five
years.11
[Basel Framework, CRE 53.20]

36. For netting sets in which all contracts have an original maturity of less than one year,
the formula for effective maturity (M) in Chapter 5 is unchanged and a floor of one year applies,
with the exception of short-term exposures as described in Chapter 5 - Internal Ratings Based
Approach, section 5.4.1 (iv).  [Basel Framework, CRE 53.21]
37. For derivative contracts subject to paragraph 65 (SWWR) and structured such that on
specified dates any outstanding exposure is settled and the terms are reset so that the fair value of
the contract is zero, the remaining maturity equals the time until the next reset date.
7.1.5.4 Margin agreements
38. If the netting set is subject to a margin agreement and the internal model captures the
effects of margining when estimating EE, the model’s EE measure may be used directly in
equation (2). Such models are noticeably more complicated than models of EPE for unmargined
counterparties. As such, they are subject to a higher degree of supervisory scrutiny before they
are approved, as discussed below.  [Basel Framework, CRE 53.22]

39. An EPE model must also include transaction-specific information in order to capture the
effects of margining. It must take into account both the current amount of margin and margin
that would be passed between counterparties in the future. Such a model must account for the
nature of margin agreements (unilateral or bilateral), the frequency of margin calls, the margin
period of risk, the thresholds of unmargined exposure the institution is willing to accept, and the
minimum transfer amount. Such a model must either model the mark-to-market change in the
value of collateral posted or apply this guideline’s rules for collateral.  [Basel Framework, CRE
53.23]

40. For transactions subject to daily re-margining and mark-to-market valuation, a
supervisory floor of five business days for netting sets consisting only of repo-style transactions,
and 10 business days for all other netting sets is imposed on the margin period of risk used for
the purpose of modelling EAD with margin agreements. In the following cases a higher
supervisory floor is imposed:

11  Conceptually, M equals the effective credit duration of the counterparty exposure. A bank that uses an internal model to
calculate a one-sided credit valuation adjustment (CVA) can use the effective credit duration estimated by such a model in
place of the above formula with prior approval of OSIF.
≤
= >
≤
=
×∆ × + ×∆ ×
=
×∆ ×
∑∑
∑
1
11
1
1
k
k
k
t year maturity
k kk k kk
k t year
t year
k kk
k
Effective EE t df EE t df
M
Effective EE t df

---

<!-- Page 17 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 17
Protected B - External / Protégé B - Externe
• for all netting sets where the number of trades exceeds 5,000 at any point during a
quarter, a supervisory floor of 20 business days is imposed for the margin period of risk
for the following quarter;
• for netting sets containing one or more trades involving either illiquid collateral, or an
OTC derivative that cannot be easily replaced, a supervisory floor of 20 business days
is imposed for the margin period of risk. For these purposes, “Illiquid collateral” and
“OTC derivatives that cannot be easily replaced” must be determined in the context of
stressed market conditions and will be characterized by the absence of continuously
active markets where a counterparty would, within two or fewer days, obtain multiple
price quotations that would not move the market or represent a price reflecting a market
discount (in the case of collateral) or premium (in the case of an OTC derivative).
Examples of situations where trades are deemed illiquid for this purpose include, but
are not limited to, trades that are not marked daily and trades that are subject to specific
accounting treatment for valuation purposes (e.g. OTC derivatives or repo-style
transactions referencing securities whose fair value is determined by models with
inputs that are not observed in the market).
• in addition, an institution must consider whether trades or securities it holds as
collateral are concentrated in a particular counterparty and if that counterparty exited
the market precipitously whether the institution would be able to replace its trades.
[Basel Framework, CRE 53.24]

41. If an institution has experienced more than two margin call disputes on a particular
netting set over the previous two quarters that have lasted longer than the applicable margin
period of risk (before consideration of this provision), then the institution must reflect this
history appropriately by using a margin period of risk that is at least double the supervisory floor
for that netting set for the subsequent two quarters. In the case of derivatives subject to Guideline
E-22, this paragraph only applies to variation margin call disputes.  [Basel Framework, CRE
53.25]

42. For re-margining with a periodicity of N-days, the margin period of risk should be at
least equal to the supervisory floor, F, plus the N days minus one day. That is,

Margin Period of Risk = F + N - 1.

[Basel Framework, CRE 53.26]

43. Institutions using the IMM must not capture the effect of a reduction of EAD due to any
clause in a collateral agreement that requires receipt of collateral when counterparty credit
quality deteriorates. [Basel Framework, CRE 53.27]
7.1.5.5 Model validation
44. In order to assure itself that institutions using models have counterparty credit risk
management systems that are conceptually sound and implemented with integrity, OSFI will
specify a number of qualitative criteria that institutions would have to meet before they are

---

<!-- Page 18 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 18
Protected B - External / Protégé B - Externe
permitted to use a models-based approach. The extent to which institutions meet the qualitative
criteria may influence the level at which OSFI will set the multiplication factor referred to in
paragraph 29 (Alpha). Only those institutions in full compliance with the qualitative criteria will
be eligible for application of the minimum multiplication factor. The qualitative criteria include:
• the institution must conduct a regular programme of backtesting, i.e. an ex-post
comparison of the risk measures
12 generated by the model against realized risk
measures, as well as comparing hypothetical changes based on static positions with
realized measures;
• the institution must carry out an initial validation and an ongoing periodic review of its
IMM model and the risk measures generated by it. The validation and review must be
independent of the model developers;
• senior management should be actively involved in the risk control process and must
regard credit and counterparty credit risk control as an essential aspect of the business
to which significant resources need to be devoted. In this regard, the daily reports
prepared by the independent risk control unit must be reviewed by a level of
management with sufficient seniority and authority to enforce both reductions of
positions taken by individual traders and reductions in the institution’s overall risk
exposure;
• the institution’s internal risk measurement exposure model must be closely integrated
into the day-to-day risk management process of the institution. Its output should
accordingly be an integral part of the process of planning, monitoring and controlling
its counterparty credit risk profile;
• the risk measurement system should be used in conjunction with internal trading and
exposure limits. In this regard, exposure limits should be related to the institution’s risk
measurement model in a manner that is consistent over time and that is well understood
by traders, the credit function and senior management;
• institutions should have a routine in place for ensuring compliance with a documented
set of internal policies, controls and procedures concerning the operation of the risk
measurement system. The institution’s risk measurement system must be well
documented, for example, through a risk management manual that describes the basic
principles of the risk management system and that provides an explanation of the
empirical techniques used to measure counterparty credit risk;
• an independent review of the risk measurement system should be carried out regularly
in the institution’s own internal auditing process. This review should include both the
activities of the business trading units and of the independent risk control unit. A
review of the overall risk management process should take place at regular intervals
(ideally no less than once a year) and should specifically address, at a minimum:
o the adequacy of the documentation of the risk management system and process;

12  “Risk measures” refers not only to Effective EPE, the risk measure used to derive regulatory capital, but also to
the other risk measures used in the calculation of Effective EPE such as the exposure distribution at a series of
future dates, the positive exposure distribution at a series of future dates, the market risk factors used to derive
those exposures and the values of the constituent trades of a portfolio.

---

<!-- Page 19 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 19
Protected B - External / Protégé B - Externe
o the organization of the risk control unit;
o the integration of counterparty credit risk measures into daily risk management;
o the approval process for counterparty credit risk models used in the calculation
of counterparty credit risk used by front office and back office personnel;
o the validation of any significant change in the risk measurement process;
o the scope of counterparty credit risks captured by the risk measurement model;
o the integrity of the management information system;
o the accuracy and completeness of position data;
o the verification of the consistency, timeliness and reliability of data sources
used to run internal models, including the independence of such data sources;
o the accuracy and appropriateness of volatility and correlation assumptions;
o the accuracy of valuation and risk transformation calculations; and
o the verification of the model’s accuracy as described in paragraphs 45 to 48.
• the ongoing validation of counterparty credit risk models, including backtesting, must
be reviewed periodically by a level of management with sufficient authority to decide
the course of action that will be taken to address weaknesses in the models.
[Basel Framework, CRE 53.28]

45. Institutions must document the process for initial and ongoing validation of their IMM
model to a level of detail that would enable a third party to recreate the analysis. Institutions
must also document the calculation of the risk measures generated by the models to a level of
detail that would allow a third party to re-create the risk measures. This documentation must set
out the frequency with which backtesting analysis and any other ongoing validation will be
conducted, how the validation is conducted with respect to data flows and portfolios and the
analyses that are used. [Basel Framework, CRE 53.29]

46. Institutions must define criteria with which to assess their EPE models and the models
that input into the calculation of EPE and have a written policy in place that describes the
process by which unacceptable performance will be determined and remedied. [Basel
Framework, CRE 53.30]

47. Institutions must define how representative counterparty portfolios are constructed for
the purposes of validating an EPE model and its risk measures. [Basel Framework, CRE 53.31]

48. When validating EPE models and its risk measures that produce forecast distributions,
validation must assess more than a single statistic of the model distribution. [Basel Framework,
CRE 53.32]

49. As part of the initial and ongoing validation of an IMM model and its risk measures, the
following requirements must be met:

---

<!-- Page 20 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 20
Protected B - External / Protégé B - Externe
• an institution must carry out backtesting using historical data on movements in market
risk factors prior to OSFI approval. Backtesting must consider a number of distinct
prediction time horizons out to at least one year, over a range of various start
(initialization) dates and covering a wide range of market conditions;
• institutions must backtest the performance of their EPE model and the model’s relevant
risk measures as well as the market risk factor predictions that support EPE. For
collateralized trades, the prediction time horizons considered must include those
reflecting typical margin periods of risk applied in collateralized/margined trading, and
must include long time horizons of at least one year;
• the pricing models used to calculate counterparty credit risk exposure for a given
scenario of future shocks to market risk factors must be tested as part of the initial and
ongoing model validation process. These pricing models may be different from those
used to calculate Market Risk over a short horizon. Pricing models for options must
account for the non-linearity of option value with respect to market risk factors;
• an EPE model must capture transaction specific information in order to aggregate
exposures at the level of the netting set. Institutions must verify that transactions are
assigned to the appropriate netting set within the model;
• static, historical backtesting on representative counterparty portfolios must be a part of
the validation process. At regular intervals, an institution must conduct such
backtesting on a number of representative counterparty portfolios. The representative
portfolios must be chosen based on their sensitivity to the material risk factors and
correlations to which the institution is exposed. In addition, IMM institutions need to
conduct backtesting that is designed to test the key assumptions of the EPE model and
the relevant risk measures, e.g. the modelled relationship between tenors of the same
risk factor, and the modelled relationships between risk factors;
• significant differences between realized exposures and the forecast distribution could
indicate a problem with the model or the underlying data that OSFI would require the
institution to correct. Under such circumstances, OSFI may require additional capital to
be held while the problem is being solved;
• the performance of EPE models and its risk measures must be subject to good
backtesting practice. The backtesting programme must be capable of identifying poor
performance in an EPE model’s risk measures;
• institutions must validate their EPE models and all relevant risk measures out to time
horizons commensurate with the maturity of trades for which exposure is calculated
using an internal modelling method;
• the pricing models used to calculate counterparty exposure must be regularly tested
against appropriate independent benchmarks as part of the ongoing model validation
process;
• the ongoing validation of an institution’s EPE model and the relevant risk measures
include an assessment of recent performance;

---

<!-- Page 21 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 21
Protected B - External / Protégé B - Externe
• the frequency with which the parameters of an EPE model are updated needs to be
assessed as part of the validation process;
• under the IMM, a measure that is more conservative than the metric used to calculate
regulatory EAD for every counterparty, may be used in place of alpha times Effective
EPE with prior approval from OSFI. The degree of relative conservatism will be
assessed upon initial OSFI approval and at the regular supervisory reviews of the EPE
models. The institution must validate the conservatism regularly;
• the ongoing assessment of model performance needs to cover all counterparties for
which the models are used;
• the validation of IMM models must assess whether or not the institution level and
netting set exposure calculations of EPE are appropriate.
[Basel Framework, CRE 53.33]

50. In the case where the pricing model used to calculate counterparty credit risk exposure
is different than the pricing model used to calculate Market Risk over a short horizon, OSFI
expects institutions to provide documented justification for the use of two different pricing
models, including an assessment of the resulting model risk.
7.1.5.6 Operational requirements for EPE models
51. In order to be eligible to adopt an internal model for estimating EPE arising from CCR
for regulatory capital purposes, an institution must meet the following operational requirements.
These include meeting the requirements related to the qualifying standards on CCR
Management, a use test, stress testing, identification of wrong-way risk, and internal controls.
[Basel Framework, CRE 53.34]

Qualifying standards on CCR Management

52. The institution must satisfy its supervisor that, in addition to meeting the operational
requirements identified in paragraphs 53 to 82 below, it adheres to sound practices for CCR
management. [Basel Framework, CRE 53.35]

Use test

53. The distribution of exposures generated by the internal model used to calculate effective
EPE must be closely integrated into the day-to-day CCR management process of the institution.
For example, the institution could use the peak exposure from the distributions for counterparty
credit limits or expected positive exposure for its internal allocation of capital. The internal
model’s output must accordingly play an essential role in the credit approval, counterparty credit
risk management, internal capital allocations, and corporate governance of institutions that seek
approval to apply such models for capital adequacy purposes. Models and estimates designed
and implemented exclusively to qualify for the internal models method are not acceptable. [Basel
Framework, CRE 53.36]

---

<!-- Page 22 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 22
Protected B - External / Protégé B - Externe
54. An institution must have a credible track record in the use of internal models that
generate a distribution of exposures to CCR. Thus, the institution must demonstrate that it has
been using an internal model to calculate the distributions of exposures upon which the EPE
calculation is based that meets broadly the minimum requirements for at least one year prior to
approval. [Basel Framework, CRE 53.37]

55. Institutions employing the internal model method must have an independent control unit
that is responsible for the design and implementation of the firm’s CCR management system,
including the initial and ongoing validation of the internal model. This unit must control input
data integrity and produce and analyze reports on the output of the firm’s risk measurement
model, including an evaluation of the relationship between measures of risk exposure and credit
and trading limits. This unit must be independent from business credit and trading units; it must
be adequately staffed; it must report directly to senior management of the firm. The work of this
unit should be closely integrated into the day-to-day credit risk management process of the firm.
Its output should accordingly be an integral part of the process of planning, monitoring and
controlling the firm’s credit and overall risk profile. [Basel Framework, CRE 53.38]

56. Institutions applying the IMM must have a collateral management unit that is
responsible for calculating and making margin calls, managing margin call disputes and
reporting levels of independent amounts, initial margins and variation margins accurately on a
daily basis. This unit must control the integrity of the data used to make margin calls, and ensure
that it is consistent and reconciled regularly with all relevant sources of data within the
institution. This unit must also track the extent of reuse of collateral (both cash and non-cash)
and the rights that the institution gives away to its respective counterparties for the collateral that
it posts. These internal reports must indicate the categories of collateral assets that are reused,
and the terms of such reuse including instrument, credit quality and maturity. The unit must also
track concentration to individual collateral asset classes accepted by the institutions. Senior
management must allocate sufficient resources to this unit for its systems to have an appropriate
level of operational performance, as measured by the timeliness and accuracy of outgoing calls
and response time to incoming calls. Senior management must ensure that this unit is adequately
staffed to process calls and disputes in a timely manner even under severe market crisis, and to
enable the institution to limit its number of large disputes caused by trade volumes. [Basel
Framework, CRE 53.39]

57. The institution’s collateral management unit must produce and maintain appropriate
collateral management information that is reported on a regular basis to senior management.
Such internal reporting should include information on the type of collateral (both cash and non-
cash) received and posted, as well as the size, aging and cause for margin call disputes. This
internal reporting should also reflect trends in these figures. [Basel Framework, CRE 53.40]

58. An institution employing the IMM must ensure that its cash management policies
account simultaneously for the liquidity risks of potential incoming margin calls in the context of
exchanges of variation margin or other margin types, such as initial or independent margin,
under adverse market shocks, potential incoming calls for the return of excess collateral posted
by counterparties, and calls resulting from a potential downgrade of its own public rating. The

---

<!-- Page 23 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 23
Protected B - External / Protégé B - Externe
institution must ensure that the nature and horizon of collateral reuse is consistent with its
liquidity needs and does not jeopardize its ability to post or return collateral in a timely manner.
[Basel Framework, CRE 53.41]

59. The internal model used to generate the distribution of exposures must be part of a
counterparty risk management framework that includes the identification, measurement,
management, approval and internal reporting of counterparty risk.
13 This framework must
include the measurement of usage of credit lines (aggregating counterparty exposures with other
credit exposures) and economic capital allocation. In addition to EPE (a measure of future
exposure), an institution must measure and manage current exposures. Where appropriate, the
institution must measure current exposure gross and net of collateral held. The use test is
satisfied if an institution uses other counterparty risk measures, such as peak exposure or
potential future exposure (PFE), based on the distribution of exposures generated by the same
model to compute EPE. [Basel Framework, CRE 53.42]

60. An institution is not required to estimate or report EE daily, but to meet the use test it
must have the systems capability to estimate EE daily, if necessary, unless it demonstrates to
OSFI that its exposures to CCR warrant some less frequent calculation. It must choose a time
profile of forecasting horizons that adequately reflects the time structure of future cash flows and
maturity of the contracts. For example, an institution may compute EE on a daily basis for the
first 10 days, once a week out to one month, once a month out to 18 months, once a quarter out
to five years and beyond five years in a manner that is consistent with the materiality and
composition of the exposure. [Basel Framework, CRE 53.43]

61. Exposure must be measured out to the life of all contracts in the netting set (not just to
the one-year horizon), monitored and controlled. The institution must have procedures in place to
identify and control the risks for counterparties where exposure rises beyond the one-year
horizon. Moreover, the forecasted increase in exposure must be an input into the firm’s internal
economic capital model. [Basel Framework, CRE 53.44]

Stress testing

62. An institution must have in place sound stress testing processes for use in the
assessment of capital adequacy. These stress measures must be compared against the measure of
EPE and considered by the institution as part of its internal capital adequacy assessment process.
Stress testing must also involve identifying possible events or future changes in economic
conditions that could have unfavourable effects on a firm’s credit exposures and assessment of
the firm’s ability to withstand such changes. Examples of scenarios that could be used are; (i)
economic or industry downturns, (ii) market-place events, or (iii) decreased liquidity conditions.
[Basel Framework, CRE 53.45]

63. Institutions must have a comprehensive stress testing program for counterparty credit
risk. The stress testing program must include the following elements:

13  This section draws heavily on the Counterparty Risk Management Policy Group’s paper, Improving Counterparty Risk
Management Practices (June 1999)

---

<!-- Page 24 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 24
Protected B - External / Protégé B - Externe
• institutions must ensure complete trade capture and exposure aggregation across all
forms of counterparty credit risk (not just OTC derivatives) at the counterparty-specific
level in a sufficient time frame to conduct regular stress testing;
• for all counterparties, institutions should produce, at least monthly, exposure stress
testing of principal market risk factors (e.g. interest rates, FX, equities, credit spreads,
and commodity prices) in order to proactively identify, and when necessary, reduce
outsized concentrations to specific directional sensitivities;
• institutions should apply multi-factor stress testing scenarios and assess material non-
directional risks (i.e. yield curve exposure, basis risks, etc.) at least quarterly. Multiple-
factor stress tests should, at a minimum, aim to address scenarios in which a) severe
economic or market events have occurred; b) broad market liquidity has decreased
significantly; and c) the market impact of liquidating positions of a large financial
intermediary. These stress tests may be part of institution-wide stress testing;
• stressed market movements have an impact not only on counterparty exposures, but
also on the credit quality of counterparties. At least quarterly, institutions should
conduct stress testing applying stressed conditions to the joint movement of exposures
and counterparty creditworthiness;
• exposure stress testing (including single factor, multifactor and material non-directional
risks) and joint stressing of exposure and creditworthiness should be performed at the
counterparty-specific, counterparty group (e.g. industry and region), and aggregate
institution-wide CCR levels;
• stress tests results should be integrated into regular reporting to senior management.
The analysis should capture the largest counterparty-level impacts across the portfolio,
material concentrations within segments of the portfolio (within the same industry or
region), and relevant portfolio and counterparty specific trends;
• the severity of factor shocks should be consistent with the purpose of the stress test.
When evaluating solvency under stress, factor shocks should be severe enough to
capture historical extreme market environments and/or extreme but plausible stressed
market conditions. The impact of such shocks on capital resources should be evaluated,
as well as the impact on capital requirements and earnings. For the purpose of day-to-
day portfolio monitoring, hedging, and management of concentrations, institutions
should also consider scenarios of lesser severity and higher probability;
• institutions should consider reverse stress tests to identify extreme, but plausible,
scenarios that could result in significant adverse outcomes;
• senior management must take a lead role in the integration of stress testing into the risk
management framework and risk culture of the institution and ensure that the results
are meaningful and proactively used to manage counterparty credit risk. At a minimum,
the results of stress testing for significant exposures should be compared to guidelines
that express the institution’s risk appetite and elevated for discussion and action when
excessive or concentrated risks are present.
[Basel Framework, CRE 53.46]

---

<!-- Page 25 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 25
Protected B - External / Protégé B - Externe
Wrong-way risk

64. Institutions must identify exposures that give rise to a greater degree of general wrong-
way risk. Stress testing and scenario analyses must be designed to identify risk factors that are
positively correlated with counterparty credit worthiness. Such testing needs to address the
possibility of severe shocks occurring when relationships between risk factors have changed.
Institutions should monitor general wrong way risk by product, by region, by industry, or by
other categories that are germane to the business. Reports should be provided to senior
management on a regular basis that communicate wrong way risks and the steps that are being
taken to manage that risk.  [Basel Framework, CRE 53.47]

65. An institution is exposed to “specific wrong-way risk” (SWWR) if future exposure to a
specific counterparty is highly correlated with the counterparty’s probability of default. For
example, a company writing put options on its own stock creates wrong-way exposures for the
buyer that is specific to the counterparty. An institution must have procedures in place to
identify, monitor and control cases of SWWR, beginning at the inception of a trade and
continuing through the life of the trade. To calculate the CCR capital charge, the instruments for
which there exists a legal connection between the counterparty and the underlying issuer, and for
which specific wrong way risk has been identified, are not considered to be in the same netting
set as other transactions with the counterparty. Furthermore, for single-name credit default swaps
where there exists a legal connection between the counterparty and the underlying issuer, and
where SWWR has been identified, EAD in respect of such swap counterparty exposure equals
the full expected loss in the remaining fair value of the underlying instruments assuming the
underlying issuer is in liquidation. The use of the full expected loss in remaining fair value of the
underlying instrument allows the institution to recognize, in respect of such swap, the market
value that has been lost already and any expected recoveries. Accordingly LGD for Advanced or
Foundation IRB institutions must be set to 100% for such swap transactions.
14 For institutions
using the standardized approach for credit risk, the risk weight to use is that of an unsecured
transaction. For equity derivatives, bond options, securities financing transactions etc.
referencing a single company where there exists a legal connection between the counterparty and
the underlying company, and where SWWR has been identified, EAD equals the value of the
transaction under the assumption of a jump-to-default of the underlying security. Inasmuch this
makes re-use of possibly existing (market risk) calculations (for IRC) that already contain an
LGD assumption, the LGD must be set to 100%. LGD for Advanced and Foundation IRB banks
will be that of an unsecured exposure. For institutions using the standardized approach for credit
risk, the risk weight of an unsecured transaction should be used.

The counterparty credit risk arising from trades where SWWR has been identified can be
mitigated through either prepayment or the collection of independent collateral amounts. If a
counterparty prepays the notional amount of the exposure for a trade where SWWR has been

14  Note that the recoveries may also be possible on the underlying instrument beneath such swap. The capital
requirements for such underlying exposure are to be calculated without reduction for the swap which introduces
wrong way risk. Generally this means that such underlying exposure will receive the risk weight and capital
treatment associated with an unsecured transaction (i.e. assuming such underlying exposure is an unsecured
credit exposure).

---

<!-- Page 26 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 26
Protected B - External / Protégé B - Externe
identified, or a portion of it, then the EAD for that trade may be reduced by the amount of the
prepayment.

In situations where independent collateral amounts have been collected, the EAD for those trades
may be reduced by the independent collateral amount (after any applicable haircuts) provided
one of the following situations applies:
• The independent collateral amount is legally pledged to cover risk solely on the trade for
which SWWR has been identified; or
• Both counterparties to the trade where SWWR has been identified agree that the
independent collateral amount is posted to account for the SWWR trade and this
independent amount is managed internally as such.
[Basel Framework, CRE 53.48]

Right-Way Risk

66. An institution is exposed to “specific right-way risk” (SRWR) if the future exposure to a
specific counterparty is highly inversely correlated with the counterparty’s probability of
default. An example of SRWR are warrants, which can be a component of call spread
overlay trades written by the counterparty on the counterparty’s stock.
67. There are transactions where SRWR is present and, given the structure of these,
institutions will have a zero EAD to the counterparty if the counterparty defaults.
68. Where an institution has identified SRWR, only the trade types identified in paragraph
69 below, and subject to due diligence,
15 are permitted to receive a zero EAD. Institutions
wishing to add other trade types should contact OSFI’s Capital Division for prior permission.
69. Permitted trade types include:
• An equity warrant, or option in each case written by the counterparty on the
counterparty’s own stock purchased as part of a call spread overlay transaction, where
a bond hedge has also been purchased. Call spread overlay transactions involve a
counterparty issuing convertible bonds and wishing to synthetically increase the
conversion price.
• Issuer forward as well as issuer range forward sales of equity whereby the institution
has also simultaneously shorted the shares of the counterparty. Issuer and issuer range
forward sales of equity are typically done by a counterparty, with future capital
expenditures or other funding needs, wishing to lock in a favourable current stock
price or range of stock prices without needing to issue shares until the maturity of the
forward or range forward transaction.
• Accelerated share repurchase agreements whereby counterparties provide an
institution with funds to buy back shares in a defined period of time (typically under
six months).

15 Trade types listed in paragraph 69 do not automatically qualify for a zero EAD. Banks must perform their due
diligence to ensure the trade would have a zero EAD if the counterparty were to default.

---

<!-- Page 27 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 27
Protected B - External / Protégé B - Externe

Integrity of Modelling Process

70. Other operational requirements focus on the internal controls needed to ensure the
integrity of model inputs; specifically, the requirements address the transaction data, historical
market data, frequency of calculation, and valuation models used in measuring EPE. [Basel
Framework, CRE 53.49]

71. The internal model must reflect transaction terms and specifications in a timely,
complete, and conservative fashion. Such terms include, but are not limited to, contract notional
amounts, maturity, reference assets, collateral thresholds, margining arrangements, netting
arrangements, etc. The terms and specifications must reside in a secure database that is subject to
formal and periodic audit. The process for recognizing netting arrangements must require signoff
by legal staff to verify the legal enforceability of netting and be input into the database by an
independent unit. The transmission of transaction terms and specifications data to the internal
model must also be subject to internal audit and formal reconciliation processes must be in place
between the internal model and source data systems to verify on an ongoing basis that
transaction terms and specifications are being reflected in EPE correctly or at least
conservatively. [Basel Framework, CRE 53.50]

72. When the Effective EPE model is calibrated using historic market data, the institution
must employ current market data to compute current exposures and at least three years of
historical data must be used to estimate parameters of the model. Alternatively, market implied
data may be used to estimate parameters of the model. In all cases, the data must be updated
quarterly or more frequently if market conditions warrant. To calculate the Effective EPE using a
stress calibration, the institution must also calibrate Effective EPE using three years of data that
include a period of stress to the credit default spreads of an institution’s counterparties or
calibrate Effective EPE using market implied data from a suitable period of stress. The following
process will be used to assess the adequacy of the stress calibration:
• The institution must demonstrate, at least quarterly, that the stress period coincides with a
period of increased CDS or other credit spreads – such as loan or corporate bond spreads
– for a representative selection of the institution’s counterparties with traded credit
spreads. In situations where the institution does not have adequate credit spread data for a
counterparty, the institution should map each counterparty to specific credit spread data
based on region, internal rating and business types.
• The exposure model for all counterparties must use data, either historic or implied, that
includes the data from the stressed credit period, and must use such data in a manner
consistent with the method used for the calibration of the Effective EPE model to current
data.
 [Basel Framework, CRE 53.52]

73. When two different calibration methods are used for different parameters within the
Effective EPE model, OSFI expects institutions’ model development and validation groups to
provide documented justification for the choice of calibration methods that includes an
assessment of the resulting model risk.

---

<!-- Page 28 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 28
Protected B - External / Protégé B - Externe

74. If an institution wished to recognize in its EAD calculations for OTC derivatives the
effect of collateral other than cash of the same currency as the exposure itself, then it must model
collateral jointly with the exposure. If the institution is not able to model collateral jointly with
the exposure then it must use either haircuts that meet the standards of the financial collateral
comprehensive method with own haircut estimates or the standard supervisory haircuts. [Basel
Framework, CRE 53.52]

75. If the internal model includes the effect of collateral on changes in the market value of
the netting set, the institution must model collateral other than cash of the same currency as the
exposure itself jointly with the exposure in its EAD calculations for securities-financing
transactions. [Basel Framework, CRE 53.53]

76. The EPE model (and modifications made to it) must be subject to an internal model
validation process. The process must be clearly articulated in firms’ policies and procedures. The
validation process must specify the kind of testing needed to ensure model integrity and identify
conditions under which assumptions are violated and may result in an understatement of EPE.
The validation process must include a review of the comprehensiveness of the EPE model, for
example such as whether the EPE model covers all products that have a material contribution to
counterparty risk exposures. [Basel Framework, CRE 53.54]

77. The use of an internal model to estimate EPE, and hence the exposure amount or EAD,
of positions subject to a CCR capital charge will be conditional upon the explicit OSFI approval.
[Basel Framework, CRE 53.55]

78. The BCBS has issued guidance regarding the use of internal models to estimate certain
parameters of risk and determine minimum capital charges against those risks. OSFI requires that
institutions seeking to make use of internal models to estimate EPE meet similar requirements
regarding, for example, the integrity of the risk management system, the skills of staff that will
rely on such measures in operational areas and in control functions, the accuracy of models, and
the rigour of internal controls over relevant internal processes. As an example, institutions
seeking to make use of an internal model to estimate EPE must demonstrate that they meet the
Committee’s general criteria for institutions seeking to make use of internal models to assess
market risk exposures, but in the context of assessing counterparty credit risk.
16 [Basel
Framework, CRE 53.56]

79. The Internal Capital Adequacy Assessment Program provides general background and
specific guidance to cover counterparty credit risks that may not be fully covered by the Pillar 1
process.  [Basel Framework, CRE 53.57]

80. No particular form of model is required to qualify to make use of an internal model.
Although this text describes an internal model as a simulation model, other forms of models,
including analytic models, are acceptable subject to OSFI approval and review. Institutions that
seek recognition for the use of an internal model that is not based on simulations must

16  Amendment to the Capital Accord to Incorporate Market Risk, Basel Committee on banking Supervision (1996),
Part B.1., “General Criteria”.

---

<!-- Page 29 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 29
Protected B - External / Protégé B - Externe
demonstrate to OSFI that the model meets all operational requirements.  [Basel Framework, CRE
53.58]

81. For an institution that qualifies to net transactions, the institution must have internal
procedures to verify that, prior to including a transaction in a netting set, the transaction is
covered by a legally enforceable netting contract that meets the applicable requirements of
section 7.1.7.1 and section 4.3.3 of Chapter 4, or the Cross-Product Netting Rules set forth in this
chapter.  [Basel Framework, CRE 53.59]

82. For an institution that makes use of collateral to mitigate its CCR, the institution must
have internal procedures to verify that, prior to recognizing the effect of collateral in its
calculations, the collateral meets the appropriate legal certainty standards as set out in Chapter 4.
[Basel Framework, CRE 53.60]
7.1.6 Cross-product netting rules
17
83. Institutions that receive approval to estimate their exposures to CCR using the internal
model method may include within a netting set SFTs, or both SFTs and OTC derivatives subject
to a legally valid form of bilateral netting that satisfies the legal and operational criteria for a
Cross-Product Netting Arrangement defined below. The institution must also have satisfied any
prior approval or other procedural requirements set out by OSFI for the purposes of recognizing
a Cross-Product Netting Arrangement. [Basel Framework, CRE 53.62]

7.1.6.1 Legal Criteria

84. The institution has executed a written, bilateral netting agreement with the counterparty
that creates a single legal obligation, covering all included bilateral master agreements and
transactions (“Cross-Product Netting Arrangement”), such that the institution would have either
a claim to receive or obligation to pay only the net sum of the positive and negative (i) close-out
values of any included individual master agreements and (ii) mark-to-market values of any
included individual transactions (the “Cross-Product Net Amount”), in the event a counterparty
fails to perform due to any of the following: default, bankruptcy, liquidation or similar
circumstances. [Basel Framework, CRE 53.63]

85. The institution has written and reasoned legal opinions that conclude with a high degree
of certainty that, in the event of a legal challenge, relevant courts or administrative authorities
would find the firm’s exposure under the Cross-Product Netting Arrangement to be the Cross-
Product Net Amount under the laws of all relevant jurisdictions. In reaching this conclusion,
legal opinions must address the validity and enforceability of the entire Cross-Product Netting
Arrangement under its terms and the impact of the Cross-Product Netting Arrangement on the
material provisions of any included bilateral master agreement.

17  These Cross-Product Netting Rules apply specifically to netting across SFTs, or to netting across both SFTs and
OTC derivatives, for purposes of regulatory capital computation under IMM. They do not revise or replace the
rules that apply to recognition of netting within the OTC derivatives, repo -style transaction, and margin lending
transaction product categories under this guideline. The rules in this guideline continue to apply for purposes of
regulatory capital recognition of netting within product categories under IMM or other relevant methodology.

---

<!-- Page 30 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 30
Protected B - External / Protégé B - Externe
• The laws of “all relevant jurisdictions” are: (i) the law of the jurisdiction in which the
counterparty is chartered and, if the foreign branch of a counterparty is involved, then
also under the law of the jurisdiction in which the branch is located, (ii) the law that
governs the individual transactions, and (iii) the law that governs any contract or
agreement necessary to effect the netting.
• A legal opinion must be generally recognized as such by the legal community in the
firm’s home country or a memorandum of law that addresses all relevant issues in a
reasoned manner.
[Basel Framework, CRE 53.64]

86. The institution has internal procedures to verify that, prior to including a transaction in a
netting set, the transaction is covered by legal opinions that meet the above criteria. [Basel
Framework, CRE 53.65]

87. The institution undertakes to update legal opinions as necessary to ensure continuing
enforceability of the Cross-Product Netting Arrangement in light of possible changes in relevant
law. [Basel Framework, CRE 53.66]

88. The Cross-Product Netting Arrangement does not include a walkaway clause. A
walkaway clause is a provision which permits a non-defaulting counterparty to make only
limited payments, or no payment at all, to the estate of the defaulter, even if the defaulter is a net
creditor. [Basel Framework, CRE 53.67]

89. Each included bilateral master agreement and transaction included in the Cross-Product
Netting Arrangement satisfies applicable legal requirements for recognition of credit risk
mitigation techniques in Chapter 4.3.[Basel Framework, CRE 53.68]

90. The institution maintains all required documentation in its files. [Basel Framework,
CRE 53.69]

7.1.6.2 Operational Criteria

91. OSFI is satisfied that the effects of a Cross-Product Netting Arrangement are factored
into the firm’s measurement of a counterparty’s aggregate credit risk exposure and that the
institution manages its counterparty credit risk on such basis. [Basel Framework, CRE 53.70]

92. Credit risk to each counterparty is aggregated to arrive at a single legal exposure across
products covered by the Cross-Product Netting Arrangement. This aggregation must be factored
into credit limit and economic capital processes. [Basel Framework, CRE 53.71]
7.1.7 Standardized Approach for Counterparty Credit Risk
93. Institutions that do not have approval to apply the internal models method must use the
SA-CCR method. SA-CCR can be used for OTC derivatives, exchange-traded derivatives and
long settlement transactions; SFTs are subject to the treatments set out under the Internal Model

---

<!-- Page 31 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 31
Protected B - External / Protégé B - Externe
Method of this chapter or in Chapter 4 of the CAR Guideline. EAD is to be calculated separately
for each netting set. It is determined as follows:

EAD = alpha × (RC + PFE)18, 19
where:
alpha  = 1.4,
RC = the replacement cost calculated according to paragraphs 98 to 114, and
PFE = the amount for potential future exposure calculated according to paragraphs
115 to 168
[Basel Framework, CRE 52.1]

94. The replacement cost (RC) and the PFE components are calculated differently for margined
and unmargined netting sets. Margined netting sets are covered by a margin agreement under
which the bank’s counterparty has to post variation margin; all other netting sets, including
those covered by a one-way margin agreement where only the bank posts variation margin,
are treated as unmargined for the purposes of the SA-CCR. The EAD for a margined netting
set is capped at the EAD of the same netting set calculated on an unmargined basis. [Basel
Framework, CRE 52.2]

95. The EAD for sold options that are outside netting and margin agreements can be set to zero.
[Basel Framework, CRE 52.2, FAQ #1]

96. For credit derivatives where the bank is the protection seller and that are outside netting and
margin agreements, the EAD may be capped at the amount of unpaid premiums. Institutions
have the option to remove such credit derivatives from their legal netting sets and treat them
as individual unmargined transactions in order to apply the cap. [Basel Framework, CRE
52.2, FAQ #2]

97. Non-linear products where no specific treatment exists under the SACCR can be decomposed
in a manner similar to paragraph 131. Linear products may not be decomposed. [Basel
Framework, CRE 52.1, FAQ #3]


7.1.7.1 RC and NICA

98. For unmargined transactions, the RC intends to capture the loss that would occur if a
counterparty were to default and were closed out of its transactions immediately. The PFE add-
on represents a potential conservative increase in exposure over a one-year time horizon from the
present date (i.e. the calculation date). [Basel Framework, CRE 52.3]


18  EAD can be set to zero for sold options that are outside of netting and margin agreements. Options sold outside
of a margin agreement but inside a netting agreement do not qualify for EAD to be set at zero.
19 For crypto-asset exposures, please refer to the Capital and Liquidity Treatment of Crypto-asset
Exposures Guideline for amendments to these calculations.

---

<!-- Page 32 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 32
Protected B - External / Protégé B - Externe
99. For margined trades, the RC intends to capture the loss that would occur if a
counterparty were to default at the present or at a future time, assuming that the closeout and
replacement of transactions occur instantaneously. However, there may be a period (the margin
period of risk) between the last exchange of collateral before default and replacement of the
trades in the market. The PFE add-on represents the potential change in value of the trades
during this time period. [Basel Framework, CRE 52.4]

100. In both cases, the haircut applicable to noncash collateral in the replacement cost
formulation represents the potential change in value of the collateral during the appropriate time
period (one year for unmargined trades and the margin period of risk for margined trades).
[Basel Framework, CRE 52.5]

101. Cash variation margin (VM) is not subject to any additional haircut provided the
variation margin is posted in a currency that is agreed to and listed in the applicable contract.
20
Cash initial margin (IM) that is exchanged in a currency other than the termination currency (that
is, the currency in which the institution will submit its claim upon a counterparty default) is
subject to the additional haircut for foreign currency risk.

102. Replacement cost is calculated at the netting set level, whereas PFE add-ons are
calculated for each asset class within a given netting set and then aggregated (see paragraphs 115
to 168). [Basel Framework, CRE 52.6]

103. For capital adequacy purposes, institutions may net transactions (e.g. when determining
the RC component of a netting set) subject to novation under which any obligation between an
institution and its counterparty to deliver a given currency on a given value date is automatically
amalgamated with all other obligations for the same currency and value date, legally substituting
one single amount for the previous gross obligations. Institutions may also net transactions
subject to any legally valid form of bilateral netting not covered in the preceding sentence,
including other forms of novation.
21 In every such case where netting is applied, an institution
must satisfy its OSFI that it has:
(i) A netting contract with the counterparty or other agreement which creates a single legal
obligation, covering all included transactions, such that the institution would have either
a claim to receive or obligation to pay only the net sum of the positive and negative
mark-to-market values of included individual transactions in the event a counterparty
fails to perform due to any of the following: default, bankruptcy, liquidation or similar
circumstances;
22

20  Currencies listed in the CSA are not subject to additional haircuts.
21  In instances where trades are removed from the netting set in which they naturally belong and are moved to a
separate netting set solely for the purposes of calculating EAD, it is permissible to allocate collateral to these
transactions. An example of such an instance would be Specific Wrong Way Risk (WWR) transactions which are
required to each be moved to their own standalone netting set.
22  The netting contract must not contain any clause which, in the event of default of a counterparty, permits a non-
defaulting counterparty to make limited payments only, or no payments at all, to the estate of the defaulting
party, even if the defaulting party is a net creditor.

---

<!-- Page 33 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 33
Protected B - External / Protégé B - Externe
(ii) Written and reasoned legal reviews that, in the event of a legal challenge, the relevant
courts and administrative authorities would find the institution’s exposure to be such a
net amount under:
• The law of the jurisdiction in which the counterparty is chartered and, if the
foreign branch of a counterparty is involved, then also under the law of the
jurisdiction in which the branch is located;
• The law that governs the individual transactions; and
• The law that governs any contract or agreement necessary to affect the netting.
OSFI, after consultation when necessary with other relevant supervisors, must be
satisfied that the netting is enforceable under the laws of each of the relevant
jurisdictions.
23
(iii) Procedures in place to ensure that the legal characteristics of netting arrangements are
kept under review in light of the possible changes in relevant law.
[Basel Framework, CRE 52.7]

104. There are two formulations of replacement cost depending on whether the trades with a
counterparty are subject to a margin agreement. Where a margin agreement exists, the
formulation could apply both to bilateral transactions and central clearing relationships. The
formulation also addresses the various arrangements that an institution may have to post and/or
receive collateral that may be referred to as initial margin. [Basel Framework, CRE 52.9]

A. Formulation for unmargined transactions

105. For unmargined transactions (that is, where VM is not exchanged, but collateral other
than VM may be present), RC is defined as the greater of: (i) the current market value of the
derivative contracts less net haircut collateral held by the institution (if any), and (ii) zero. This is
consistent with the use of replacement cost as the measure of current exposure, meaning that
when the institution owes the counterparty money it has no exposure to the counterparty if it can
instantly replace its trades and sell collateral at current market prices. Mathematically:

RC = max{V-C,0}
where V is the value of the derivative transactions in the netting set and C is the haircut value of
net collateral held, which is calculated in accordance with the NICA methodology defined in
paragraph 112. For this purpose, the value of non-cash collateral posted by the institution to its
counterparty is increased and the value of the non-cash collateral received by the institution from
its counterparty is decreased using haircuts (which are the same as those that apply to repo-style
transactions) for the time periods described in paragraph 100.
[Basel Framework, CRE 52.10 and 52.11]

106. In the above formulation, it is assumed that the replacement cost representing today’s
exposure to the counterparty cannot go less than zero. However, institutions sometimes hold

23  Thus, if any of these supervisors is dissatisfied about enforceability under its laws, the netting contract or
agreement will not meet this condition and neither counterparty could obtain supervisory benefit.

---

<!-- Page 34 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 34
Protected B - External / Protégé B - Externe
excess collateral (even in the absence of a margin agreement) or have out-of-the-money trades
which can further protect the institution from the increase of the exposure. As discussed in
paragraphs 116 to 118, the SA-CCR would allow such over-collateralization and negative mark-
to market value to reduce PFE, but would not affect replacement cost. [Basel Framework, CRE
52.12]

107. Bilateral transactions with a one-way margining agreement in favour of the institution’s
counterparty (that is, where an institution posts, but does not collect, collateral) must be treated
as unmargined transactions. [Basel Framework, CRE 52.10, FAQ #1]

B. Formulation for margined transactions

108. The RC formula for margined transactions builds on the RC formula for unmargined
transactions. It also employs concepts used in standard margining agreements, as discussed more
fully below. [Basel Framework, CRE 52.13]

109. The RC for margined transactions in the SA-CCR is defined as the greatest exposure
that would not trigger a call for VM, taking into account the mechanics of collateral exchanges in
margining agreements. Such mechanics include, for example, “Threshold”, “Minimum Transfer
Amount” and “Independent Amount” in the standard industry documentation,
24 which are
factored into a call for VM.25 [Basel Framework, CRE 52.14]

C. Incorporating NICA into replacement cost

110. One objective of the SA-CCR is to more fully reflect the effect of margining agreements
and the associated exchange of collateral in the calculation of CCR exposures. The following
paragraphs address how the exchange of collateral is incorporated into the SA-CCR. [Basel
Framework, CRE 52.15]

111. To avoid confusion surrounding the use of terms initial margin and independent amount
which are used in various contexts and sometimes interchangeably, the term independent
collateral amount (ICA) is introduced. ICA represents (i) collateral (other than VM) posted by
the counterparty that the institution may seize upon default of the counterparty, the amount of
which does not change in response to the value of the transactions it secures and/or (ii) the
Independent Amount (IA) parameter as defined in standard industry documentation. ICA can
change in response to factors such as the value of the collateral or a change in the number of
transactions in the netting set. [Basel Framework, CRE 52.16]


24  For example, the 1992 (Multicurrency-Cross Border) Master Agreement and the 2002 Master Agreement
published by the International Swaps & Derivatives Association, Inc. (ISDA Master Agreement). The ISDA
Master Agreement includes the ISDA CSA: the 1994 Credit Support Annex (Security Interest – New York Law),
or, as applicable, the 1995 Credit Support Annex (Transfer – English Law) and the 1995 Credit Support Deed
(Security Interest – English Law).
25  For example, in the ISDA Master Agreement, the term “Credit Support Amount”, or the overall amount of
collateral that must be delivered between the parties, is defined as the greater of the Secured Party’s Exposure
plus the aggregate of all Independent Amounts applicable to the Pledgor minus all Independent Amounts
applicable to the Secured Party, minus the Pledgor’s Threshold and zero.

---

<!-- Page 35 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 35
Protected B - External / Protégé B - Externe
112. Because both an institution and its counterparty may be required to post ICA, it is
necessary to introduce a companion term, net independent collateral amount (NICA), to describe
the amount of collateral that an institution may use to offset its exposure on the default of the
counterparty. NICA does not include collateral that an institution has posted to a segregated,
bankruptcy remote account, which presumably would be returned upon the bankruptcy of the
counterparty. That is, NICA represents any collateral (segregated or unsegregated) posted by the
counterparty less the unsegregated collateral posted by the institution. With respect to IA, NICA
takes into account the differential of IA required for the institution minus IA required for the
counterparty. [Basel Framework, CRE 52.17]

113. For margined trades, the replacement cost is:
RC = max{V – C; TH + MTA – NICA;0}
Where: V and C are defined as in the unmargined formulation, except that C now includes the
net variation margin amount, where the amount received by the institution is accounted with a
positive sign and the amount posted by the institution is accounted with a negative sign, TH is
the positive threshold before the counterparty must send the institution collateral, and MTA is
the minimum transfer amount applicable to the counterparty. [Basel Framework, CRE 52.18]

114. TH + MTA – NICA represents the largest exposure that would not trigger a VM call and
it contains levels of collateral that need always to be maintained. For example, without initial
margin or IA, the greatest exposure that would not trigger a variation margin call is the threshold
plus any minimum transfer amount. In the adapted formulation, NICA is subtracted from TH +
MTA. This makes the calculation more accurate by fully reflecting both the actual level of
exposure that would not trigger a margin call and the effect of collateral held and/or posted by an
institution. The calculation is floored at zero, recognizing that the institution may hold NICA in
excess of TH + MTA, which could otherwise result in a negative replacement cost. [Basel
Framework, CRE 52.19]
7.1.7.2 PFE Add-ons
115. The PFE add-on consists of (i) an aggregate add-on component, which consists of add-
ons calculated for each asset class and (ii) a multiplier that allows for the recognition of excess
collateral or negative mark-to-market value for the transactions. Mathematically:
PFE = multiplier × AddOn
aggregate

Where AddOnaggregate is the aggregate add-on component and multiplier is defined as a
function of three inputs: V, C and AddOnaggregate.

The paragraphs below describe the inputs that enter into the calculation of the add-on formulas in
more detail, and set out the formula for each asset class.
[Basel Framework, CRE 52.20]

---

<!-- Page 36 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 36
Protected B - External / Protégé B - Externe
7.1.7.3 Recognition of excess collateral and negative mark-to-market
116. As a general principle, over-collateralization should reduce capital requirements for
counterparty credit risk. In fact, many institutions hold excess collateral (i.e. collateral greater
than the net market value of the derivatives contracts) precisely to offset potential increases in
exposure represented by the add-on. As discussed in paragraphs 105 and 113, collateral may
reduce the replacement cost component of the exposure under the SA-CCR. The PFE component
also reflects the risk-reducing property of excess collateral. [Basel Framework, CRE 52.21]
117. For prudential reasons and in line with Basel Committee direction, OSFI applied a
multiplier to the PFE component that decreases as excess collateral increases, without reaching
zero (the multiplier is floored at 5% of the PFE add-on). When the collateral held is less than the
net market value of the derivative contracts (“under-collateralization”), the current replacement
cost is positive and the multiplier is equal to one (i.e. the PFE component is equal to the full
value of the aggregate add-on). Where the collateral held is greater than the net market value of
the derivative contracts (“over-collateralization”), the current replacement cost is zero and the
multiplier is less than one (i.e. the PFE component is less than the full value of the aggregate
add-on). [Basel Framework, CRE 52.22]
118. This multiplier will also be activated when the current value of the derivative
transactions is negative. This is because out-of-the-money transactions do not currently represent
an exposure and have less chance to go in-the-money. Mathematically:
𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚𝑚= 𝑚𝑚𝑚𝑚𝑚𝑚�1; 𝐹𝐹𝑚𝑚𝐹𝐹𝐹𝐹𝑚𝑚+ (1 − 𝐹𝐹𝑚𝑚𝐹𝐹𝐹𝐹𝑚𝑚)× 𝑚𝑚
� 𝑉𝑉−𝐶𝐶
2×(1−𝐹𝐹𝐹𝐹𝐹𝐹𝐹𝐹𝐹𝐹)×𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎�
�
where exp(…) equals to the exponential function, Floor is 5%, V is the value of the derivative
transactions in the netting set, and C is the haircut value of net collateral held.
[Basel Framework, CRE 52.23]

7.1.7.4 Aggregation across asset classes

119. Diversification benefits across asset classes are not recognized. Instead, the respective
add-ons for each asset class are simply aggregated. Mathematically:
𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚
𝑎𝑎𝑎𝑎𝑎𝑎𝐹𝐹𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎𝑎= � 𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝑎𝑎
𝑎𝑎

where the sum of each asset class add-on is taken.
[Basel Framework, CRE 52.25]

7.1.7.5 Allocation of derivative transactions to one or more asset classes

120. The designation of a derivative transaction to an asset class is be made on the basis of
its primary risk driver. Most derivative transactions have one primary risk driver, defined by its

---

<!-- Page 37 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 37
Protected B - External / Protégé B - Externe
reference underlying instrument (e.g. an interest rate curve for an interest rate swap, a reference
entity for a credit default swap, a foreign exchange rate for a FX call option, etc). When this
primary risk driver is clearly identifiable, the transaction will fall into one of the asset classes
described above. [Basel Framework, CRE 52.26]
121. For more complex trades that may have more than one risk driver (e.g., multi-asset or
hybrid derivatives), institutions must take sensitivities and volatility of the underlying into
account for determining the primary risk driver.

OSFI may also require more complex trades to be allocated to more than one asset class,
resulting in the same position being included in multiple classes. In this case, for each asset class
to which the position is allocated, institutions must determine appropriately the sign and delta
adjustment of the relevant risk driver.
[Basel Framework, CRE 52.27 and 52.28]

7.1.7.6 General steps for calculating the add-on

122. For each transaction, the primary risk factor or factors need to be determined and
attributed to one or more of the six asset classes: interest rate, foreign exchange, credit, equity,
commodity, or crypto-asset
26. The add-on for each asset class is calculated using asset-class-
specific formulas that represent a stylized Effective EPE calculation under the assumption that
all trades in the asset class have zero current mark-to-market value (i.e. they are at-the-money).
[Basel Framework, CRE 52.29]
123. Although the add-on formulas are asset class-specific, they have a number of features in
common. To determine the add-on, transactions in each asset class are subject to adjustment in
the following general steps:
1) The effective notional (D) must be calculated for each derivative (i.e. each individual
trade) in the netting set. The effective notional is a measure of the sensitivity of the trade
to movements in the underlying risk factors (i.e. interest rates, exchange rates, credit
spreads, equity prices and commodity prices). The effective notional is calculated as the
product of the following parameters (i.e. D = d × MF × δ):
a. The adjustment notional (d). The adjusted notional is a measure of the size of
the trade. For derivatives in the foreign exchange asset class this is simply the
notional value of the foreign currency leg of the derivative contracted, converted
to the domestic currency. For derivatives in the equity and commodity asset
classes, it is simply the current price of the relevant share or unit of commodity
multiplied by the number of shares/units that the derivative references. For
derivatives in the interest rate and credit asset classes, the notional amount is
adjusted by a measure of the duration of the instrument to account for the fact that
the value of the instruments with longer durations are more sensitive to
movements in underlying risk factors (i.e. interest rates and credit spreads).

26 For the calculation of the add-on for the “crypto-asset” asset class introduced in paragraph 122, please refer to the
Capital and Liquidity Treatment of Crypto-asset Exposures Guideline.

---

<!-- Page 38 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 38
Protected B - External / Protégé B - Externe
b. The maturity factor (MF). The maturity factor is a parameter that takes account
of the time period over which the potential future exposure is calculated. The
calculation of the maturity factor varies depending on whether the netting set is
margined or unmargined.
c. The supervisory delta (δ). The supervisory delta ensures the effective notional
takes into account the direction of the trade, i.e. whether the trade is long or short,
by having a positive or negative sign. It is also takes into account whether the
trade has a non-linear relationship with the underlying risk factor (which is the
case for options and collateralized debt obligation tranches).
2) A supervisory factor (SF) is identified for each individual trade in the netting set. The
supervisory factor is the supervisory specified change in value of the underlying risk
factor on which the potential future exposure calculation is based, which has been
calibrated to take into account the volatility of underlying risk factors.
3) The trades within each asset class are separated into supervisory specified hedging sets.
The purpose of the hedging sets is to group together trades within the netting set where
long and short positions should be permitted to offset each other in the calculation of the
potential future exposure.
4) Aggregation formulas are applied to aggregate the effective notionals and supervisory
factors across all trades within each hedging set and finally at the asset-class level to give
the asset class level add-on. The method of aggregation varies between assets classes and
for credit, equity and commodity derivatives. It also involves the application of
supervisory correlation parameters to capture diversification of the trades and basis risk.
 [Basel Framework, CRE 52.30]
7.1.7.7 Time Period Parameters Mi, Ei, Si, and Ti
124. Four time period parameters are used in the SA-CCR (all expressed in years):
• For all asset classes, the maturity Mi of a contract is the time period (starting today) until
the latest day when the contract may still be active. This time period appears in the
maturity factor defined in paragraphs 139 to 144 that scales down adjusted notional for
unmargined trades for all asset classes. If a derivative contract has another derivative
contract as its underlying (for example, a swaption) and may be physically exercised into
the underlying contract (i.e. an institution would assume a position in the underlying
contract in the event of exercise), then maturity of the contract is the time period until the
final settlement date of the underlying derivative contract.
• For interest rate and credit derivatives, S
i is the period of time (starting today) until the
start of the time period referenced by an interest rate or credit contract. If the derivative
references the value of another interest rate or credit instrument (e.g. swaption or bond
option), the time period must be determined on the basis of the underlying instrument. S
i
appears in the definition of supervisory duration defined in paragraph 126.
• For interest rate and credit derivatives, Ei is the period of time (starting today) until the
end of the time period referenced by an interest rate or credit contract. If the derivative
references the value of another interest rate or credit instrument (e.g. swaption or bond

---

<!-- Page 39 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 39
Protected B - External / Protégé B - Externe
option), the time period must be determined on the basis of the underlying instrument. Ei
appears in the definition of supervisory duration defined in paragraph 126. In addition, Ei
is used for allocating derivatives in the interest rate asset class to maturity buckets, which
are used in the calculation of the add-on (see paragraph 146).For options in all asset
classes, Ti is the time period (starting today) until the latest contractual exercise date as
referenced by the contract. This period shall be used for the determination of the option
delta in paragraph 132.
• Unless otherwise specified, time periods between dates should be measured in years.
[Basel Framework, CRE 52.31]
125. Table 1 includes example transactions and provides each transaction’s related maturity
M
i, start date Si and end date Ei. In addition, the option delta in paragraph 132 depends on the
latest contractual exercise date Ti (not separately shown in the table).
Table 1

Instrument  Mi Si Ei
Interest rate or credit default swap maturing in 10 years  10 years 0 10 years
10-year interest rate swap, forward starting in 5 years  15 years 5 years 15 years
Forward rate agreement for time period starting in 6 months
and ending in 12 months
1 year 0.5 year 1 year
Cash-settled European swaption referencing 5-year interest
rate swap with exercise date in 6 months
0.5 year 0.5 year 5.5 years
Physically-settled European swaption referencing 5-year
interest rate swap with exercise date in 6 months
5.5 years 0.5 year 5.5 years
10-year Bermudan swaption with annual exercise dates  10 years 1 year 10 years
Interest rate cap or floor specified for semi-annual interest
rate with maturity 5 years
5 years 0 5 years
Option on a bond maturing in 5 years with the latest
exercise date in 1 year
1 year 1 year 5 years
3-month Eurodollar futures that matures in 1 year27  1 year 1 year 1.25 years
Futures on 20-year treasury bond that matures in 2 years  2 years 2 years 22 years
6-month option on 2-year futures on 20-year treasury bond  2 years 2 years 22 years
[Basel Framework, CRE 52.32]


27  Eurodollar example does not include the effect of margining or settlement and would apply only in the case
where a futures contract were neither margined nor settled. Concerning the end date (E i), the value of 1.25 years
applies. Note that per paragraph 146, the parameter Ei defines the maturity bucket for the purpose of netting. This
means that the trade of this example will be attributed to the intermediate maturity bucket "between one and five
years" and not to the short maturity bucket "less than one year" irrespective of  daily settlement

---

<!-- Page 40 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 40
Protected B - External / Protégé B - Externe
7.1.7.8 Trade-level Adjusted Notional (for trade I): di(a)

126. The adjusted notionals are defined at the trade level and take into account both the size
of a position and its maturity dependency, if any. [Basel Framework, CRE 52.33]
127. For interest rate and credit derivatives, the trade-level adjusted notional is the product of
the trade notional amount, converted to the domestic currency, and the supervisory duration SDi
(i.e. di = notional x SDi) which is given by the formula below. The calculated value of SDi is
floored at 10 business days.28 If the start date has occurred (e.g. an ongoing interest rate swap), Si
must be set to zero.
𝑆𝑆𝑆𝑆𝑖𝑖=  𝑚𝑚(−0.05 ×𝑆𝑆𝑖𝑖) − e(−0.05×𝐸𝐸𝑖𝑖)
0.05
[Basel Framework, CRE 52.34]
128. For foreign exchange derivatives, the adjusted notional is defined as the notional of the
foreign currency leg of the contract, converted to the domestic currency. If both legs of a foreign
exchange derivative are denominated in currencies other than the domestic currency, the notional
amount of each leg is converted to the domestic currency and the leg with the larger domestic
currency value is the adjusted notional amount. [Basel Framework, CRE 52.35]
129. For equity and commodity derivatives, the adjusted notional is defined as the product of
the current price of one unit of the stock or commodity (e.g. a share of equity or barrel of oil) and
the number of units referenced by the trade. For equity and commodity volatility transactions, the
underlying volatility or variance referenced by the transactions should replace the unit price and
the contractual notional should replace the number of units.
[Basel Framework, CRE52.36]

130. In many cases the trade notional amount is stated clearly and fixed until maturity. When
this is not the case, institutions must use the following rules to determine the trade notional
amount.
• Where the notional is a formula of market values, the institution must enter the current
market values to determine the trade notional amount.
• For all interest rate and credit derivatives with variable notional amounts specified in the
contract (such as amortizing and accreting swaps), institutions must use the average
notional over the remaining life of the swap as the trade notional amount. The average
should be calculated as “time weighted”. The averaging described in this paragraph does
not cover transactions where the notional varies due to price changes (typically FX,
equity and commodity derivatives).

28  There is a distinction between the time period of the underlying transaction and the remaining maturity of the
derivative contract. For example, a European interest rate swaption with expiry of one  year and the term of the
underlying swap of five years has Si = one year and Ei = six years.

---

<!-- Page 41 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 41
Protected B - External / Protégé B - Externe
• Leveraged swaps must be converted to the notional of the equivalent unleveraged swap,
that is, where all rates in a swap are multiplied by a factor, the stated notional must be
multiplied by the factor on the interest rates to determine the trade notional amount.
• For a derivative contract with multiple exchanges of principal, the notional is multiplied
by the number of exchanges of principal in the derivative contract to determine the trade
notional amount.
• For a derivative contract that is structured such that on specified dates any outstanding
exposure is settled and the terms are reset so that the fair value of the contract is zero, the
remaining maturity equals the time until the next reset date.
• Consistent with the above point, trades with daily settlement should be treated as
unmargined transactions with a maturity factor given by the first formula in paragraph
139 with the parameter M
i set to its floor value of 10 business days. For trades subject to
daily margining, the maturity factor is given by the second formula of paragraph 143
depending on the margin period of risk (MPOR), which can be as low as five business
days. Note that, the parameter E
i defines the maturity bucket for the purpose of netting.
 [ Basel Framework, CRE 52.32, FAQ #1]

Calculation of effective notional for options

131. For the purposes of effective notional calculations (i.e. D = d × MF × δ), single-
payment options must be treated as follows:

• For European, Asian, American and Bermudan put and call options, the supervisory delta
must be calculated using the simplified Black-Scholes formula in paragraph 133. In the
case of Asian options, the underlying price must be set equal to the current value of the
average used in the payoff. In the case of American and Bermudan options, the latest
allowed exercise date must be used as the exercise date
iT  in the formula.
For Bermudan swaptions, the start date iS  must be equal to the earliest allowed exercise
date, while the end date iE  must be equal to the end date of the underlying swap.
• For digital options (also known as binary options), the payoff of each digital option
(bought or sold) with strike
iK  must be approximated via the “collar” combination of
bought and sold European options of the same type (call or put) with the strikes set equal
to
0.95 iK⋅  and 1.05 iK⋅ . The size of the position in the collar components must be such
that the digital payoff is reproduced exactly outside of the region between the two strikes.
The effective notional is then computed for the bought and sold European components of
the collar separately, using the option formulas for the supervisory delta in paragraph 132
(the exercise date
iT  and the current value of the underlying iP  of the digital option must
be used). The absolute value of the digital option effective notional must be capped by the
ratio of the digital payoff to the relevant supervisory factor.

---

<!-- Page 42 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 42
Protected B - External / Protégé B - Externe
• If a trade’s payoff can be represented as a combination of European option payoffs (e.g.
collar, butterfly/calendar spread, straddle, strangle, etc.), each European option
component must be treated as a separate trade.
[Basel Framework, CRE 52.42]

•
For the purposes of effective notional calculations, multi-payment options must be represented
as a combination of single-payment options. In particular, interest rate caps/floors may be
represented as a combination of single-payment options. In particular, interest rate
caps/floors may be represented as the portfolio of individual caplets/floorlets, each of
which is a European option on the floating interest rate over a specific coupon period. For
each caplet/floorlet,
iS  and iT  are the time periods starting from the current date to the
start of the coupon period, while iE  is the time period starting from the current date to
the end of the coupon period.
[Basel Framework, CRE 52.43]

7.1.7.9 Supervisory delta adjustments: δi
132. The supervisory delta adjustment parameters are also defined at the trade level and are
applied to the adjusted notional amounts to reflect the direction of the transaction and its non-
linearity. [Basel Framework, CRE 52.38]
133. The delta adjustments for all derivatives are defined as follows:
Delta for Instruments that are not Options of CDO Tranches
δi Long in the primary risk factor29 Short in the primary risk factor30
Instruments that are not
options or CDO tranches  +1 -1

Delta for Options
δi Bought Sold
Call Options31
+Φ �
ln �𝑃𝑃𝑖𝑖
𝐾𝐾𝑖𝑖
�+ 0.5 × 𝜎𝜎2 × 𝑇𝑇𝑖𝑖
𝜎𝜎𝑖𝑖× �𝑇𝑇𝑖𝑖
� −Φ �
ln �𝑃𝑃𝑖𝑖
𝐾𝐾𝑖𝑖
�+ 0.5 × 𝜎𝜎2 × 𝑇𝑇𝑖𝑖
𝜎𝜎𝑖𝑖× �𝑇𝑇𝑖𝑖
�
Put Options
−Φ �−
ln �𝑃𝑃𝑖𝑖
𝐾𝐾𝑖𝑖
�+ 0.5 × 𝜎𝜎2 × 𝑇𝑇𝑖𝑖
𝜎𝜎𝑖𝑖× �𝑇𝑇𝑖𝑖
� +Φ �−
ln �𝑃𝑃𝑖𝑖
𝐾𝐾𝑖𝑖
�+ 0.5 × 𝜎𝜎2 × 𝑇𝑇𝑖𝑖
𝜎𝜎𝑖𝑖× �𝑇𝑇𝑖𝑖
�
With the following parameters that institutions must determine appropriately:

29  “Long in the primary risk factor” means that the market value of the instrument increases when the value of the
primary risk factor increases.
30  “Short in the primary risk factor” means that the market value of the instrument decreases when the value of the
primary risk factor increases.
31  The symbol Φ in these equations represents the standard normal cumulative distribution function.

---

<!-- Page 43 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 43
Protected B - External / Protégé B - Externe
Pi : Underlying price (spot, forward, average, etc.)
Ki : Strike price
Ti : Latest contractual exercise date of the option
The supervisory volatility of an option is specified on the basis of supervisory factor applicable to the
trade (see Table 2 in paragraph 162).

Delta for CDO Tranches
δi Purchased (long protection) Sold (short protection)
CDO tranche32 + 15
(1 + 14 × 𝐴𝐴𝑖𝑖) × (1 + 14 × 𝑆𝑆𝑖𝑖) − 15
(1 + 14 × 𝐴𝐴𝑖𝑖) × (1 + 14 × 𝑆𝑆𝑖𝑖)
With the following parameters that institutions must determine appropriately:
Ai : Attachment point of the CDO tranche
Di : Detachment point of the CDO tranche


Whenever appropriate, the forward (rather than spot) value of the underlying in the supervisory
delta adjustments formula should be used in order to account for the risk-free rate as well as for
possible cash flows prior to the option expiry (such as dividends).
[Basel Framework, CRE 52.39 to 52.41]

134. For cases where the term P/K is either zero or negatives such that the term In(P/K)
cannot be computed, the following adjustments should be made:
• institutions must incorporate a shift in the price value and strike value by adding λ, where
λ represents the presumed lowest possible extent to which interest rates in the respective
currency can become negative.
33
• For commodity derivatives, institutions must incorporate a shift in the price value and
strike value by adding λ, where λ represents the presumed lowest possible extent to which
prices in that particular commodity can become negative.
34
Therefore, the Delta δi for a transaction i in such cases is calculated as:

Delta for options if Term P/K is Zero or Negative
Delta(𝛅𝛅) Bought Sold

32  First-to-default, second-to-default and subsequent-to-default credit derivative transactions should be treated as
CDO tranches under the SACCR. For an nth-to-default transaction on a pool of m reference names, banks must
use an attachment point of A=(n–1)/m and a detachment point of D=n/m in order to calculate the supervisory
delta formula set out paragraph 133.
33  This assumes for the strike price that 𝐾𝐾𝑚𝑚+ 𝜆𝜆𝑗𝑗 is also greater than zero, otherwise a greater value needs to be
chosen for 𝜆𝜆𝑗𝑗.  λ  adjustment values which are unique to each currency.
34  This assumes for the strike price that 𝐾𝐾𝑚𝑚+ 𝜆𝜆𝑗𝑗 is also greater than zero, otherwise a greater value needs to be
chosen for 𝜆𝜆𝑗𝑗.  λ adjustment values which are unique to each commodity type.

---

<!-- Page 44 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 44
Protected B - External / Protégé B - Externe
Call Options
+Φ �
 ln�(𝑃𝑃𝑖𝑖+𝜆𝜆𝑗𝑗)
(𝐾𝐾𝑖𝑖+𝜆𝜆𝑗𝑗)� �+0 .5×𝜎𝜎𝑖𝑖2×𝑇𝑇𝑖𝑖
𝜎𝜎𝑖𝑖×�𝑇𝑇𝑖𝑖
�  −Φ �
 ln�(𝑃𝑃𝑖𝑖+𝜆𝜆𝑗𝑗)
(𝐾𝐾𝑖𝑖+𝜆𝜆𝑗𝑗)� �+0 .5×𝜎𝜎𝑖𝑖2×𝑇𝑇𝑖𝑖
𝜎𝜎𝑖𝑖×�𝑇𝑇𝑖𝑖
�
Put Options
−Φ �
− ln��𝑃𝑃𝑖𝑖+𝜆𝜆𝑗𝑗�
�𝐾𝐾𝑖𝑖+𝜆𝜆𝑗𝑗�� �−0.5×𝜎𝜎𝑖𝑖 2×𝑇𝑇𝑖𝑖
𝜎𝜎𝑖𝑖×�𝑇𝑇𝑖𝑖
�  +Φ �
− ln��𝑃𝑃𝑖𝑖+𝜆𝜆𝑗𝑗�
�𝐾𝐾𝑖𝑖+𝜆𝜆𝑗𝑗�� �−0.5×𝜎𝜎𝑖𝑖2×𝑇𝑇𝑖𝑖
𝜎𝜎𝑖𝑖×�𝑇𝑇𝑖𝑖
�

The same parameter must be used consistently for all interest rate options in the same currency
and all commodity options on the same commodity type. Institutions should select a value of λ
j,
which is low but still gives a positive Ki+λj value.
[Basel Framework, CRE 52.40, FAQ #2]
7.1.7.10  Supervisory Factors: SFi
135. Supervisory factors (SFi) are used, together with aggregation formulas, to convert the
effective notional amounts into the add-on for each hedging set. Each factor has been calibrated
to reflect the Effective EPE of a single at-the-money linear trade of unit notional and one-year
maturity. This includes the estimate of realized volatilities assumed by supervisors for each
underlying asset class. The supervisory factors are listed in Table 2 in paragraph 162.[Basel
Framework, CRE 52.44]
7.1.7.11  Hedging Sets
136. The hedging sets in the different asset classes are defined as follows, except for those
described in paragraphs 137 and 138.
• Interest rate derivatives consist of a separate hedging set for each currency;
• FX derivatives consist of a separate hedging set for each currency pair;
• Credit derivatives consist of a single hedging set;
• Equity derivatives consist of a single hedging set;
• Commodity derivatives consist of four hedging sets defined for broad categories of
commodity derivatives: energy, metals, agricultural and other commodities.
[Basel Framework, CRE 52.45]

137. Derivatives that reference the basis between two risk factors and are denominated in a
single currency
35 (basis transactions) must be treated within separate hedging sets within the
corresponding asset class. There is a separate hedging set36 for each pair of risk factors (i.e. for
each specific basis). Examples of specific bases include three-month Libor versus six-month

35  Derivatives with two floating legs that are denominated in different currencies (such as cross -currency swaps)
are not subject to this treatment; rather, they should be treated as non-basis foreign exchange contracts.
36  Within this hedging set, long and short positions are determined with respect to the basis.

---

<!-- Page 45 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 45
Protected B - External / Protégé B - Externe
Libor, three-month Libor versus three-month T-Bill, one-month Libor versus OIS rate, Brent
Crude oil versus Henry Hub gas. For hedging sets consisting of basis transactions, the
supervisory factor applicable to a given asset class must be multiplied by one-half. Basket equity
derivatives comprised of 10 or less effective constituents37 may be decomposed into their
underlying constituents. Baskets comprised of more than 10 effective constituents should be
treated as indices.  [Basel Framework, CRE 52.46]
138. Derivatives that reference the volatility of a risk factor (volatility transactions) must be
treated within separate hedging sets within the corresponding asset class. Volatility hedging sets
must follow the same hedging set construction outlined in paragraph 136 (for example, all equity
volatility transactions form a single hedging set). Examples of volatility transactions include
variance and volatility swaps, options on realized or implied volatility. For hedging sets
consisting of volatility transactions, the supervisory factor applicable to a given asset class must
be multiplied by a factor of five.
 [Basel Framework, CRE 52.36]

7.1.7.12  Maturity Factors

139. The minimum time risk horizons for an unmargined transaction is the lesser of one year
and remaining maturity of the derivative contract, floored at 10 business days. Therefore, the
calculation of the effective notional for an unmargined transaction includes the following
maturity factor, where Mi is the remaining maturity floored by 10 business days:
𝑀𝑀𝐹𝐹𝑖𝑖
(𝑢𝑢𝑢𝑢𝑎𝑎𝐹𝐹𝑎𝑎𝑖𝑖𝐴𝐴𝑎𝑎𝐴𝐴) = �𝑚𝑚𝑚𝑚𝑚𝑚{𝑀𝑀𝑖𝑖; 1 𝑦𝑦𝑚𝑚𝑦𝑦𝑚𝑚}
1 𝑦𝑦𝑚𝑚𝑦𝑦𝑚𝑚
[Basel Framework, CRE 52.48]
140. The maturity parameter (Mi) is expressed in years but is subject to a floor of 10 business
days. Banks should use standard market convention to convert business days into years, and vice
versa. For example, 250 business days in a year, which results in a floor of 10/250 years for Mi.
[Basel Framework, CRE 52.49]
141. For margined transactions, the maturity factor is calculated using the minimum margin
period of risk (MPOR), subject to specified floors. That is, institutions must first estimate the
margin period of risk (as defined in section 7.1.1.3) for each of their netting sets. They must then
use the higher of their estimated margin period of risk and the relevant floor in the calculation of
the maturity factor (defined in paragraph 143). The floors for the margin period of risk are as
follows:

o Ten business days for non-centrally cleared derivative transactions subject to
daily margin agreements.

37  Number of effective constituents = �
(∑ 𝑠𝑠ℎ𝑎𝑎𝐹𝐹𝑎𝑎 𝑝𝑝𝐹𝐹𝑖𝑖𝑝𝑝𝑎𝑎𝑖𝑖 ×𝐴𝐴𝑢𝑢𝑢𝑢𝑛𝑛𝑎𝑎𝐹𝐹 𝐹𝐹𝑜𝑜 𝑠𝑠ℎ𝑎𝑎𝐹𝐹𝑎𝑎𝑠𝑠𝑖𝑖𝑖𝑖 )2
∑ (𝑠𝑠ℎ𝑎𝑎𝐹𝐹𝑎𝑎 𝑝𝑝𝐹𝐹𝑖𝑖𝑝𝑝𝑎𝑎𝑖𝑖 ×𝐴𝐴𝑢𝑢𝑢𝑢𝑛𝑛𝑎𝑎𝐹𝐹 𝐹𝐹𝑜𝑜 𝑠𝑠ℎ𝑎𝑎𝐹𝐹𝑎𝑎𝑠𝑠𝑖𝑖)2𝑖𝑖
�

---

<!-- Page 46 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 46
Protected B - External / Protégé B - Externe
o The sum of nine business days plus the re-margining period for non-centrally
cleared transactions that are not subject to daily margin agreements.
o The relevant floors for centrally cleared transactions are prescribed in section
7.1.8.
[Basel Framework, CRE 52.50]
142. The following are exceptions to the floors on the minimum margin period of risk set out
in paragraph 141 above:
o For netting sets consisting of 5,000 transactions that are not with a central
counterparty or client cleared trades, the floor on the margin period of risk is 20
business days.
o For netting sets containing one or more trades involving either illiquid inbound
variation margin, or an OTC derivative that cannot be easily replaced, the floor on
the margin period of risk is 20 business days. For these purposes, "Illiquid
inbound variation margin" and "OTC derivatives that cannot be easily replaced"
must be determined in the context of stressed market conditions and will be
characterized by the absence of continuously active markets where a counterparty
would, within two or fewer days, obtain multiple price quotations that would not
move the market or represent a price reflecting a market discount (in the case of
collateral) or premium (in the case of an OTC derivative). Examples of situations
where trades are deemed illiquid for this purpose include, but are not limited to,
trades that are not marked daily and trades that are subject to specific accounting
treatment for valuation purposes (e.g. OTC derivatives transactions referencing
securities whose fair value is determined by models with inputs that are not
observed in the market).
o If an institution has experienced more than two margin call disputes on a
particular netting set over the previous two quarters that have lasted longer than
the applicable margin period of risk (before considering this provision), then the
institution must reflect this history appropriately by doubling the applicable
supervisory floor on the margin period of risk for that netting set for the
subsequent two quarters.
o In the case of non-centrally cleared derivatives subject to Guideline E-22 (Margin
Requirements for non-centrally Cleared Derivatives), the previous bullet point
only applies to variation margin call disputes.
[Basel Framework, CRE 52.51]

143. The calculation of the effective notional for a margined transaction includes the
following maturity factor, where MPOR
i is the margin period of risk appropriate for the margin
agreement containing the transaction i (subject to floors set out in paragraphs 141 and 142
above):
𝑀𝑀𝐹𝐹𝑖𝑖
(𝑢𝑢𝑎𝑎𝐹𝐹𝑎𝑎𝑖𝑖𝐴𝐴𝑎𝑎𝐴𝐴) = 3
2 × �𝑀𝑀𝑃𝑃𝐴𝐴𝑀𝑀𝑖𝑖
1 𝑦𝑦𝑚𝑚𝑦𝑦𝑚𝑚

---

<!-- Page 47 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 47
Protected B - External / Protégé B - Externe
[Basel Framework, CRE 52.52]
144. The margin period of risk (MPORi) is often expressed in days, but the calculation of the
maturity factor for margined netting sets references one year in the denominator. Banks should
use standard market convention to convert business days into years, and vice-versa. For example,
one year can be converted into 250 business days in the denominator of the MF formula if
MPOR is expressed in business days. Alternatively, the MPOR expressed in business days can
be converted into years by dividing it by 250.
[Basel Framework, CRE 52.53]
7.1.7.13  Supervisory correlation parameters: 𝜌𝜌
𝑖𝑖
(𝑎𝑎)
145. These parameters only apply to the PFE add-on calculation for equity, credit and
commodity derivatives, and are set out in Table 2 in paragraph 162. For these asset classes, the
supervisory correlation parameters are derived from a single-factor model and specify the weight
between systematic and idiosyncratic components. This weight determines the degree of offset
between individual trades, recognizing that imperfect hedges provide some, but not perfect,
offset. Supervisory correlation parameters do not apply to interest rate and foreign exchange
derivatives. [Basel Framework, CRE 52.54]
Asset Class Level Add-ons
7.1.7.14  Add-on for interest rate derivatives38
146. The add-on for interest rate derivatives captures the risk of interest rate derivatives of
different maturities being imperfectly correlated. It does this by allocating trades to maturity
buckets, in which full offsetting of long and short positions is permitted, and by using an
aggregation formula that only permits limited offsetting between transactions in different
maturity buckets. This allocation of derivatives to maturity buckets and the process of
aggregation are only used in the interest rate derivative asset class.[Basel Framework, CRE
52.56]
147. The add-on for interest rate derivatives within a netting set is calculated using the
following steps.
(1) Step 1: Calculate the effective notional for each trade in the netting set that is in the rate
derivative asset class. The is calculated as the product of the following three terms (i) the
adjusted notional of the trade (d); (ii) the supervisory delta adjustment of the trade (δ); and (iii)
the maturity factor (MF). That is, for each trade i, D
i = di x δi x MFi.
(2) Step 2: Allocate the trades in the interest rate derivative asset class to hedging sets. In the
interest rate derivative asset class the hedging sets consist of all the derivatives that reference the
same currency.

38  Inflation derivatives may be treated in the same manner as interest rate derivatives. Derivatives referencing
inflation rates for the same currency should form a separate hedging set and should be subjected to the same
0.5% supervisory factor. AddOn amounts from inflation derivatives must be added to Addon IR mentioned in
step 7 of the paragraph 147.

---

<!-- Page 48 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 48
Protected B - External / Protégé B - Externe
(3) Step 3: Within each hedging set, allocate each of the trades to the following three maturity
buckets: less than one year (bucket 1), between one and five years (bucket 2) and more than five
years (bucket 3).
(4) Step 4: Calculate the effective notional of each maturity bucket by adding together all the
trade-level effective notionals calculated in step 1 of the trades within the maturity bucket. Let
D
B1, DB2 and DB3 be the effective notionals of the buckets 1,2 and 3 respectively.
(5) Step 5: Calculate the effective notional of the hedging set (ENHS) by using either of the two
following aggregation formulas (the latter to be used if the banks chooses not to recognize
offsets between long and short positions across maturity buckets):

Offset formula:
𝐸𝐸𝐸𝐸𝐻𝐻𝑆𝑆= [(𝑆𝑆𝐵𝐵1)2 + (𝑆𝑆𝐵𝐵2)2 + (𝑆𝑆𝐵𝐵3)2 + 1.4 × 𝑆𝑆𝐵𝐵1 × 𝑆𝑆𝐵𝐵2 + 1.4 × 𝑆𝑆𝐵𝐵2 × 𝑆𝑆𝐵𝐵3 + 0.6 × 𝑆𝑆𝐵𝐵1 × 𝑆𝑆𝐵𝐵3]
1
2

No offset formula:
𝐸𝐸𝐸𝐸𝐻𝐻𝑆𝑆= |𝑆𝑆𝐵𝐵1| + |𝑆𝑆𝐵𝐵2| + |𝑆𝑆𝐵𝐵3|
(6) Step 6: Calculate the hedging set level add-on (AddOnHS) by multiplying the effective notional of the
hedging set (ENHS) by the prescribed supervisory factor (SFHS). The prescribed supervisory factor in the
interest rate asset class is set to 0.5%, which means AddOnHS = ENHS x 0.005.
(7) Step 7: Calculate the asset class level add-on (AddOnIR) by adding together all of the hedging set level
add-ons calculated in step 6.

𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐼𝐼𝐼𝐼= � 𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐻𝐻𝑆𝑆
𝐻𝐻𝑆𝑆

[Basel Framework, CRE 52.57]
7.1.7.15  Add-on for foreign exchange derivatives
148. The steps to calculate the add-on for foreign exchange derivatives are similar to the
steps for the interest rate derivative asset class, except that there is no allocation of trades to
maturity buckets (which means that there is full offsetting of long and short positions within the
hedging set of the foreign exchange derivative asset class).
[Basel Framework, CRE 52.58]
149. The add-on for foreign exchange derivative asset class (AddOnFX) within a netting set is
calculated using the following steps:
(1) Step 1: Calculate the effective notional for each trade in the netting set that is in the
foreign exchange derivative asset class. This is calculated as the product of the following
three terms: (i) the adjusted notional of the trade (d); (ii) the supervisory delta adjustment

---

<!-- Page 49 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 49
Protected B - External / Protégé B - Externe
of the trade39 (δ); and (iii) the maturity factor (MF). That is, for each trade i, Di = di x δi x
MFi.
(2) Step 2: Allocate the trade in the foreign exchange derivative asset class to hedging sets.
In the foreign exchange derivative asset class the hedging sets consist of all the
derivatives that reference the same currency pair.
(3) Step 3: Calculate the effective notional of each hedging set (EN
HS) by adding together the
trade level effective notionals calculated in step 1.
(4) Step 4: Calculate the hedging set level add-on (AddOnHS) by multiplying the absolute
value of the effective notional of the hedging set (ENHS) by the prescribed supervisory
factor (SFHS). The prescribed supervisory factor in the foreign exchange derivative asset
class is set at 4%, which means that AddOnHS = |ENHS| x 0.04.
(5) Step 5: Calculate the asset class level add-on (AddOnFX) by adding together all of the
hedging set level add-ons calculated in step 4.
𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐹𝐹𝐹𝐹= � 𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐻𝐻𝑆𝑆
𝐻𝐻𝑆𝑆

[Basel Framework, CRE 52.59]
7.1.7.16 Add-on for credit derivatives
150. The calculation of the add-on for the credit derivative asset class only gives full
recognition of the offsetting of long and short positions for derivatives that reference the same
entity (e.g. the same corporate issuer of bonds). Partial offsetting is recognized between
derivatives that reference different entities in step 4 below. [Basel Framework, CRE 52.60]
151. The add-on for the credit derivative asset class (AddOnCredit) within a netting set is
calculated using the following steps:
(1) Step 1: Calculate the effective notional for each trade in the netting set that is in the credit
derivative asset class. This is calculated as the product of the following three terms: (i)
the adjusted notional of the trade (d); (ii) the supervisory delta adjustment of the trade (δ);
and (iii) the maturity factor (MF). That is, for each trade i, D
i = di × δi × MFi.
(2) Step 2: Calculate the combined effective notional for all derivatives that reference the
same entity. Each separate credit index that is referenced by derivatives in the credit
derivative asset class should be treated as a separate entity. The combined effective

39 For foreign exchange options, the ordering of the respective currency pair will impact the calculation of the
supervisory delta adjustment. As such, for each currency pair, the same ordering convention must be used
consistently across an institution and over time. The convention is to be chosen in such a way that it corresponds
best to the market practice for how derivatives in the respective currency pair are usually quoted and traded.

---

<!-- Page 50 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 50
Protected B - External / Protégé B - Externe
notional of the entity (ENentity) is calculated by adding together the trade level effective
notionals calculated in step 1 that reference that entity.
(3) Step 3: Calculate the add-on for each entity (AddOnentity) by multiplying the combined
effective notional for that entity calculated in step 2 by the supervisory factor that is
specified for that entity (SFentity). The supervisory factors vary according to the credit
rating of the entity in the case of single name derivatives, and whether the index is
considered investment grade or non-investment grade in the case of derivatives that
reference an index. The supervisory factors are set out in Table 2 in paragraph 162.
(4) Step 4: Calculate the asset class level add-on (AddOnCredit) by using the formula that
follows. In the formula the summations are across all entities referenced by the
derivatives, AddOnentity is the add-on amount calculated in step 3 for each entity
referenced by the derivatives and ρentity is the supervisory prescribed correlation factor
corresponding to the entity. As set out in Table 2 in paragraph 162, the correlation factor
is 50% for single entities and 80% for indices.
𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐶𝐶𝐹𝐹𝑎𝑎𝐴𝐴𝑖𝑖𝑎𝑎= �� � ρ𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒× 𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒
𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒
�
2
+ � �1 − �ρ𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒�
2
�× �𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒�
2
𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒
�
1
2

[Basel Framework, CRE 52.61]
152. The formula to recognized partial offsetting in step 4 above, is a single-factor model,
which divides the risk of the credit derivative asset class into a systemic component and an
idiosyncratic component. The entity level add-ons are allowed to offset each other fully in the
systemic component, whereas, there is no offsetting benefit in the idiosyncratic component.
These two components are weighted by a correlation factor which determines the degree of
offsetting/hedging benefit within the credit derivative asset class. The higher the correlation
factor, the higher the importance of the systemic component, hence the higher the degree of
offsetting benefits. [Basel Framework, CRE 52.62]

153. It should be noted that a higher or lower correlation does not necessarily mean a higher
or lower capital charge. For portfolios consisting of long and short credit positions, a high
correlation factor would reduce the charge. For portfolios consisting exclusively of long
positions (or short positions), a higher correlation factor would increase the charge. If most of the
risk consists of systematic risk, then individual reference entities would be highly correlated and
long and short positions should offset each other. If, however, most of the risk is idiosyncratic to
a reference entity, then individual long and short positions would not be effective hedges for
each other. [Basel Framework, CRE 52.63]
154. The use of a single hedging set for credit derivatives implies that credit derivatives from
different industries and regions are equally able to offset the systematic component of an
exposure, although they would not be able to offset the idiosyncratic portion. This approach
recognizes that meaningful distinctions between industries and/or regions are complex and
difficult to analyze for global conglomerates. [Basel Framework, CRE 52.64]

---

<!-- Page 51 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 51
Protected B - External / Protégé B - Externe
7.1.7.17  Add-on for equity derivatives
155. The calculation of the add-on for the equity derivative asset class is very similar to the
calculation of the add-on for the credit derivative asset class. It only gives full recognition of the
offsetting of long and short positions for derivatives that reference the same entity (e.g. the same
corporate issuer of shares). Partial offsetting is recognized between derivatives that reference
different entities in step 4 below. [Basel Framework CRE 52.65]
156. The add-on for the equity derivative asset class (AddOnEquity) within a netting set is
calculated using the following steps:
(1) Step 1: Calculate the effective notional for each trade in the netting set that is in the
equity derivative asset class. This is calculated as the product of the following three
terms: (i) the adjusted notional of the trade (d); (ii) the supervisory delta adjustment of
the trade (δ); and (iii) the maturity factor (MF). That is, for each trade i, D
i = di × δi ×
MFi.
(2) Step 2: Calculate the combined effective notional for all derivatives that reference the
same entity. Each separate equity index that is referenced by derivatives in the equity
derivative asset class should be treated as a separate entity. The combined effective
notional of the entity (EN
entity) is calculated by adding together the trade level effective
notionals calculated in step 1 that reference that entity.
(3) Step 3: Calculate the add-on for each entity (AddOnentity) by multiplying the combined
effective notional for that entity calculated in step 2 by the supervisory factor that is
specified for that entity (SFentity). The supervisory factors are set out in Table 2 of
paragraph 162 and vary according to whether the entity is a single name (SFentity = 32%)
or an index (SFentity = 20%).
(4) Step 4: Calculate the asset class level add-on (AddOnEquity) by using the formula that
follows. In the formula the summations are across all entities referenced by the
derivatives, AddOnentity is the add-on amount calculated in step 3 for each entity
referenced by the derivatives and ρentity is the supervisory prescribed correlation factor
corresponding to the entity. As set out in Table 2 in paragraph 162, the correlation factor
is 50% for single entities and 80% for indices.
𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐸𝐸𝐸𝐸𝑢𝑢𝑖𝑖𝑎𝑎𝑒𝑒= �� � ρ𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒× 𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒
𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒
�
2
+ � �1 − �ρ𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒�
2
�× �𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒�
2
𝑎𝑎𝐴𝐴𝑎𝑎𝑖𝑖𝑎𝑎𝑒𝑒
�
1
2

[Basel Framework, CRE 52.66]

---

<!-- Page 52 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 52
Protected B - External / Protégé B - Externe
157. The calibration of the supervisory factors for equity derivatives rely on estimates of the
market volatility of equity indices, with the application of a conservative beta factor40 to translate
this estimate into an estimate of individual volatilities.[Basel Framework, CRE 52.67]
158.  Institutions are not permitted to make any modelling assumptions in the calculation of
the PFE add-ons, including estimating individual volatilities or taking publicly available
estimates of beta. This is a pragmatic approach to ensure a consistent implementation across
jurisdictions but also to keep the add-on calculation relatively simple and prudent. Therefore,
only two values of supervisory factors have been defined for equity derivatives, one for single
entities and one for indices.
 [Basel Framework, CRE52.68]
7.1.7.18  Add-on for commodity derivatives
159. The calculation of the add-on for the commodity derivative asset class is similar to the
calculation of the add-on for the credit and equity derivative asset classes. It recognizes the full
offsetting of long and short positions for derivatives that reference the same type of underlying
commodity. It also allows partial offsetting between derivatives that reference different types of
commodity, however, this partial offsetting is only permitted within each of the four hedging sets
of the commodity derivative asset class, where the different commodity types are more likely to
demonstrate some stable, meaningful joint dynamics. Offsetting between hedging sets is not
recognized (e.g. a forward contract on crude oil cannot hedge a forward contract on corn). [Basel
framework, CRE 52.69]
160. The add-on for the commodity derivative asset class (AddOn
Commodity) within a netting
set is calculated using the following steps:
(1) Step 1: Calculate the effective notional for each trade in the netting set that is in the
commodity derivative asset class. This is calculated as the product of the following three
terms: (i) the adjusted notional of the trade (d); (ii) the supervisory delta adjustment of
the trade (δ); and (iii) the maturity factor (MF). That is, for each trade i, D
i = di × δi ×
MFi.
(2) Step 2: Allocate the trades in the commodity derivative asset class to hedging sets. In the
commodity derivative asset class there are four hedging sets consisting of derivatives that
reference: energy, metals, agriculture and other commodities.
(3) Step 3: Calculate the combined effective notional for all derivatives within each hedging
set that reference the same commodity type (e.g. all derivatives that reference copper
within the metals hedging set). The combined effective notional of the commodity type
(EN
ComType) is calculated by adding together the trade level effective notionals calculated
in step 1 that reference the commodity type.

40 The beta of an individual equity measures the volatility of the stock relative to a broad market index. A value of
beta greater than one means the individual equity is more volatile than the index. The greater the beta is, the
more volatile the stock. The beta is calculated by running a linear regression of the stock on the broad index.

---

<!-- Page 53 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 53
Protected B - External / Protégé B - Externe
(4) Step 4: Calculate the add-on for each commodity type (AddOnComType) within each
hedging set by multiplying the combined effective notional for that commodity calculated
in step 3 by the supervisory factor that is specified for that commodity type (SFComType).
The supervisory factors are set out in Table 2 in paragraph 162 and are set to 40% for
electricity derivatives and 18% for derivatives that reference all other types of
commodities.
(5) Step 5: Calculate the add-on for each of the four commodity hedging sets (AddOnHS) by
using the formula that follows. In the formula the summations are across all commodity
types within the hedging set, AddOnComType is the add-on amount calculated in step 4 for
each commodity type and ρComType is the supervisory prescribed correlation factor
corresponding to the commodity type. As set out in Table 2 of paragraph 162, the
correlation factor is set to 40% for all commodity types.
𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐻𝐻𝑆𝑆= �� � ρ𝐶𝐶𝐹𝐹𝑢𝑢𝑇𝑇𝑒𝑒𝑝𝑝𝑎𝑎× 𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐶𝐶𝐹𝐹𝑢𝑢𝑇𝑇𝑒𝑒𝑝𝑝𝑎𝑎
𝐶𝐶𝐹𝐹𝑢𝑢𝑇𝑇𝑒𝑒𝑝𝑝𝑎𝑎
�
2
+ � �1 − �ρ𝐶𝐶𝐹𝐹𝑢𝑢𝑇𝑇𝑒𝑒𝑝𝑝𝑎𝑎�
2
�× �𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐶𝐶𝐹𝐹𝑢𝑢𝑇𝑇𝑒𝑒𝑝𝑝𝑎𝑎�
2
𝐶𝐶𝐹𝐹𝑢𝑢𝑇𝑇𝑒𝑒𝑝𝑝𝑎𝑎
�
1
2

(6) Step 6: Calculate the asset class level add-on (AddOnCommodity) by adding together all of
the hedging set level add-ons calculated in step 5:
𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐶𝐶𝐹𝐹𝑢𝑢𝑢𝑢𝐹𝐹𝐴𝐴𝑖𝑖𝑎𝑎𝑒𝑒= � 𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝐴𝑚𝑚𝐻𝐻𝑆𝑆
𝐻𝐻𝑆𝑆

[Basel Framework, CRE 52.70]
161. Regarding the calculation steps above, defining individual commodity types is
operationally difficult. In fact, it is impossible to fully specify all relevant distinctions between
commodity types so that all basis risk is captured. For example crude oil could be a commodity
type within the energy hedging set, but in certain cases this definition could omit a substantial
basis risk between different types of crude oil (West Texas Intermediate, Brent, Saudi Light, etc).
Also, the four commodity type hedging sets have been defined without regard to characteristics
such as location and quality. For example, the energy hedging set contains commodity types such
as crude oil, electricity, natural gas and coal. OSFI may require banks to use more refined
definitions of commodities when they are significantly exposed to the basis risk of different
products within those commodity types. [Basel Framework, CRE 52.71]
Supervisory Specific Parameters
162. Table 2 includes the supervisory factors, correlations and supervisory option volatility
add-ons for each asset class and subclass.
Table 2 – Summary Table of Supervisory Parameters

---

<!-- Page 54 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 54
Protected B - External / Protégé B - Externe
Asset Class Subclass Supervisory
factor
Correlation Supervisory
option
volatility41
Interest Rate N/A 0.50% N/A 50%
Foreign Exchange N/A 4.0% N/A 15%
Credit, Single Name AAA 0.38% 50% 100%
Credit, Single Name AA 0.38% 50% 100%
Credit, Single Name A 0.42% 50% 100%
Credit, Single Name BBB 0.54% 50% 100%
Credit, Single Name BB 1.06% 50% 100%
Credit, Single Name B 1.6% 50% 100%
Credit, Single Name CCC 6.0% 50% 100%
Credit, Index IG 0.38% 80% 80%
Credit, Index SG 1.06% 80% 80%
Equity, Single Name N/A 32% 50% 120%
Equity, Index N/A 20% 80% 75%
Commodity Electricity 40% 40% 150%
Commodity Oil/Gas 18% 40% 70%
Commodity Metals 18% 40% 70%
Commodity Agricultural 18% 40% 70%
Commodity Other 18% 40% 70%

[Basel Framework, CRE 52.72]

163. For credit derivatives where the institution is the protection seller and that are outside
netting and margin agreements, the EAD may be capped to the amount of unpaid premiums.
Institutions have the option to remove such credit derivatives from their legal netting sets and
treat them as individual un-margined transactions in order to apply the cap. For add-on factors,
refer to Table 2 of paragraph 162.

164. For a basis transaction hedging set, the supervisory factor applicable to its relevant asset
class must be multiplied by one-half. For a volatility transaction hedging set, the supervisory
factor applicable to its relevant asset class must be multiplied by a factor of five. [Basel
Framework 52.73]
7.1.7.19  Treatment of multiple margin agreements and multiple netting sets
165. If multiple margin agreements apply to a single netting set, (for example: one Credit
Support Annex [CSA] for VM and one for Initial Margin [IM]), all collateral collected against
the netting set in question can be used to offset exposures as if it were collected in a single
netting set, provided the institution has performed sufficient legal review to ensure the
requirements of paragraph 103 are satisfied.

41  For swaptions for all currencies, a 50% supervisory option volatility should be used.

---

<!-- Page 55 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 55
Protected B - External / Protégé B - Externe
When multiple CSAs apply to an individual netting set, the RC and PFE are calculated as
follows:

RC
• The V and C terms should consider all transactions within a netting set, across all CSAs;
and
• The TH + MTA - NICA is the sum of the thresholds and MTAs across all CSA
agreement.

PFE
• In the multiplier term, similarly to RC, the V and C terms should consider all transactions
in the netting set across all CSA agreements; and
• The margin period of risk applied to calculate effective notionals is specific to the
individual CSA to which a trade belongs.
[Basel Framework, CRE 52.74]

166. If a single margin agreement applies to several netting sets, special treatment is
necessary because it is problematic to allocate the common collateral to individual netting sets.
The replacement cost at any given time is determined by the sum of two terms. The first term is
equal to the unmargined current exposure of the institution to the counterparty aggregated across
all netting sets within the margin agreement reduced by the positive current net collateral (i.e.
collateral is subtracted only when the institution is a net holder of collateral). The second term is
non-zero only when the institution is a net poster of collateral: it is equal to the current net posted
collateral (if there is any) reduced by the unmargined current exposure of the counterparty to the
institution aggregated across all netting sets within the margin agreement. Net collateral
available to the institution should include both VM and NICA. Mathematically, RC for the entire
margin agreement is:
𝑀𝑀𝑅𝑅𝑀𝑀𝐴𝐴= 𝑚𝑚𝑦𝑦 𝑚𝑚� � 𝑚𝑚𝑦𝑦 𝑚𝑚{𝑉𝑉𝑁𝑁𝑆𝑆; 0} − 𝑚𝑚𝑦𝑦 𝑚𝑚{𝑅𝑅𝑀𝑀𝐴𝐴; 0}; 0
𝑁𝑁𝑆𝑆∈𝑀𝑀 𝐴𝐴
�+ 𝑚𝑚𝑦𝑦 𝑚𝑚� � 𝑚𝑚𝑚𝑚𝑚𝑚{𝑉𝑉𝑁𝑁𝑆𝑆; 0} − 𝑚𝑚𝑚𝑚𝑚𝑚{𝑅𝑅𝑀𝑀𝐴𝐴; 0}; 0
𝑁𝑁𝑆𝑆∈𝑀𝑀 𝐴𝐴
�
w
here the summation 𝐸𝐸𝑆𝑆∈ 𝑀𝑀
𝐴𝐴i
s across the netting sets covered by the margin agreement
(hence the notation), VNS is the current mark-to-market value of the netting set NS and CMA is the
cash equivalent value of all currently available collateral under the margin agreement.
[
Basel Framework 52.75]

167. Where a single margin agreement applies to several netting sets as described in
paragraph 166, collateral will be exchanged based on mark-to-market values that are netted
across all transactions covered under the margin agreement, irrespective of netting sets. That is,
collateral exchanged on a net basis may not be sufficient to cover PFE.
In this situation, therefore, the PFE add-on must be calculated according to the unmargined
methodology. Netting set-level PFEs are then aggregated. Mathematically:

---

<!-- Page 56 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 56
Protected B - External / Protégé B - Externe
𝑃𝑃𝐹𝐹𝐸𝐸𝑀𝑀𝐴𝐴= � 𝑃𝑃𝐹𝐹𝐸𝐸𝑁𝑁𝑆𝑆
(𝑢𝑢𝐴𝐴𝑢𝑢𝑎𝑎𝐹𝐹𝑎𝑎𝑖𝑖𝐴𝐴𝑎𝑎𝐴𝐴)
𝑁𝑁𝑆𝑆∈𝑀𝑀𝐴𝐴

where 𝑃𝑃𝐹𝐹𝐸𝐸𝑁𝑁𝑆𝑆
(𝑢𝑢𝐴𝐴𝑢𝑢𝑎𝑎𝐹𝐹𝑎𝑎𝑖𝑖𝐴𝐴𝑎𝑎𝐴𝐴)is the PFE add-on for the netting set NS calculated according to the
unmargined requirements.

For the calculation of the multiplier of the PFE of each individual netting set covered by a single
margin agreement or collateral amount, the available collateral C (which, in the case of a
variation margin agreement, includes variation margin posted or received) should be allocated to
the netting sets as follows:

• If the institution is a net receiver of collateral (C>0), all of the individual amounts
allocated to the individual netting sets must also be positive or zero. Netting sets with
positive market values must first be allocated collateral up to the amount of those market
values. Only after all positive market values have been compensated may surplus
collateral be attributed freely among all netting sets.
• If the institution is a net provider of collateral (C<0), all of the individual amounts
allocated to the individual netting sets must also be negative or zero. Netting sets with
negative market values must first be allocated collateral up to the amount of their market
values. If the collateral provided is larger than the sum of the negative market values,
then all multipliers must be set equal to 1 and no allocation is necessary.
• The allocated parts must add up to the total collateral available for the margin agreement.

Apart from these limitations, institutions may allocate available collateral at their discretion. The
multiplier is then calculated per netting set according to paragraph 118 taking the allocated
amount of collateral into account.
[Basel Framework 52.76]
168. Eligible collateral which is taken outside a netting set, but is available to a bank to offset
losses due to counterparty default on one netting set only, should be treated as an independent
collateral amount associated with the netting set and used within the calculation of replacement
cost in paragraph 105 when the netting set is unmargined and in paragraph 113 when the netting
set is margined. Eligible collateral which is taken outside a netting set, and is available to a bank
to offset losses due to counterparty default on more than one netting set, should be treated as
collateral taken under a margin agreement applicable to multiple netting sets, in which case the
treatment in paragraphs 166 and 167 applies. If eligible collateral is available to offset losses on
non-derivatives exposures as well as exposures determined using the SA-CCR, only that portion
of the collateral assigned to the derivatives may be used to reduce the derivatives exposure.
7.1.7.20  Treatment of trades subject to Specific Wrong-Way Risk and Specific
Right-Way Risk
169. The requirements for trades where SWWR or SRWR has been identified outlined in
paragraphs
65 and 66, respectively, also apply to trades where the exposure is measured using the
SACCR.

---

<!-- Page 57 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 57
Protected B - External / Protégé B - Externe
7.1.8 Central Counterparties
170. When the clearing member-to-client leg of an exchange-traded derivative transaction is
conducted under a bilateral agreement, both the client and the clearing member are to capitalize
that transaction as an OTC derivative.42 This treatment also applies to transactions between
lower-level clients and higher-level clients in a multi-level client structure. [Basel Framework,
CRE 54.2]
171. Regardless of whether a CCP is classified as a QCCP, an institution retains the
responsibility to ensure that it maintains adequate capital for its exposures. Under the ICAAP, an
institution should consider whether it might need to hold capital in excess of the minimum
capital requirements if, for example, (i) its dealings with a CCP give rise to more risky exposures
or (ii) where, given the context of that institution’s dealings, it is unclear that the CCP meets the
definition of a QCCP or (iii) an external assessment such as an International Monetary Fund
Financial Sector Assessment Program has found material shortcomings in the CCP or regulation
of CCPs, and the CCP and/or CCP regulator have not since publicly addressed the identified
issues. [Basel Framework, CRE 54.3]
172. Where the institution is acting as a clearing member, the institution should assess
through appropriate scenario analysis and stress testing whether the level of capital held against
exposures to a CCP adequately addresses the inherent risks of those transactions. This
assessment will include potential future or contingent exposures resulting from future drawings
on default fund commitments, and/or from secondary commitments to take over or replace
offsetting transactions from clients of another clearing member in case of this clearing member
defaulting or becoming insolvent. [Basel Framework, CRE 54.4]
173. An institution must monitor and report to senior management on a regular basis all of its
exposures to CCPs, including exposures arising from trading through a CCP and exposures
arising from CCP membership obligations such as default fund contributions. [Basel Framework,
CRE 54.5]
174. Where an institution is clearing derivative, SFT and/or long settlement transactions
through a Qualifying CCP (QCCP) as defined in paragraph 3, then paragraphs 175 to 207 will
apply. In the case of non-qualifying CCPs, paragraphs 208 and 209 will apply. Within three
months of a central counterparty ceasing to qualify as a QCCP, unless OSFI requires otherwise,
the trades with a former QCCP may continue to be capitalized as though they are with a QCCP.
After that time, the bank’s exposures with such a central counterparty must be capitalized
according to paragraphs 208 and 209. [Basel Framework, CRE 54.6]

7.1.8.1 Exposures to Qualifying CCPs

A. Trade exposures

(i)  Clearing member exposures to CCPs

42  For this purpose, the treatment in paragraph 179 would also apply.

---

<!-- Page 58 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 58
Protected B - External / Protégé B - Externe

175. Where an institution acts as a clearing member of a CCP for its own purposes, a risk
weight of 2% must be applied to the institution’s trade exposure to the CCP in respect of OTC
derivatives, exchange-traded derivative transactions, SFTs and long-settlement transactions.
Where the clearing member offers clearing services to clients, the 2% risk weight also applies to
the clearing member’s trade exposure to the CCP that arises when the clearing member is
obligated to reimburse the client for any losses suffered due to changes in the value of its
transactions in the event that the CCP defaults. The risk weight applied to collateral posted to the
CCP by the institution must be determined in accordance with paragraphs 185 to 188. [Basel
Framework, CRE 54.7]
176. The exposure amount for such trade exposure is to be calculated in accordance with this
chapter using the IMM or the SACCR, as consistently applied by such an institution to such an
exposure in the ordinary course of its business, or Chapter 4 for collateralized transactions. In
applying these methods:

(1)The 20-day floor for the margin period of risk (MPOR) as established in the first bullet point
of paragraph 40 (IMM) and 142 (SACCR) dealing with the number of transactions will not
apply, provided that the netting set does not contain illiquid collateral or exotic trades and
provided there are no disputed trades. This refers to exposure calculations under the IMM and
the SACCR as well as for the holding periods entering the exposure calculation of repo-style
transactions in Chapter 4.
(2) In all cases, a minimum MPOR of 10 days must be used for the calculation of trade
exposures to CCPs for OTC derivatives.
(3) Where CCPs retain variation margin against certain trades (e.g. where CCPs collect and hold
variation margin against positions in exchange-traded or OTC forwards), and the member
collateral is not protected against the insolvency of the CCP, the minimum time risk horizon
applied to institutions’ trade exposures on those trades must be the lesser of one year and the
remaining maturity of the transaction, with a floor of 10 business days.
[Basel Framework, CRE 54.8]

177. The methods for calculating counterparty credit risk exposures , when applied to
bilateral trading exposures (i.e. non-CCP counterparties), require banks to calculate exposures
for each individual netting set. However, netting arrangements for CCPs are not as standardized
as those for OTC netting agreements in the context of bilateral trading. As a consequence,
paragraph 178 below makes certain adjustments to the methods for calculating counterparty
credit risk exposure to permit netting under certain conditions for exposures to CCPs. [Basel
Framework, CRE 54.9]

178. Where settlement is legally enforceable on a net basis in an event of default and
regardless of whether the counterparty is insolvent or bankrupt, the total replacement cost of all
contracts relevant to the trade exposure determination can be calculated as a net replacement cost
if the applicable close-out netting sets meet the requirements set out in:

---

<!-- Page 59 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 59
Protected B - External / Protégé B - Externe
• Paragraphs 253 and, where applicable, also 254 of Chapter 4 in the case of repo-style
transactions,
• Paragraph 103 of this Chapter in the case of derivative transactions, and
• Paragraphs 83 to 92 of this Chapter in the case of cross-product netting.
To the extent that the rules referenced above include the term “master agreement” or the phrase
“a netting contract with a counterparty or other agreement”, this terminology must be read as
including any enforceable arrangement that provides legally enforceable rights of set-off.
43 If the
institution cannot demonstrate that netting agreements meet these requirements, each single
transaction will be regarded as a netting set of its own for the calculation of trade exposure.
[Basel Framework, CRE 54.10 and 54.11]

(ii)  Clearing member exposures to clients

179. The clearing member will always capitalize its exposure  to clients as bilateral trades,
irrespective of whether the clearing member guarantees the trade or acts as an intermediary
between the client and the CCP. However, to recognize the shorter close-out period for cleared
client transactions, clearing members can capitalize the exposure to their clients applying a
margin period of risk of at least five days in IMM or SA-CCR.
44 In addition, the clearing
member does not need to hold capital for CVA risk for its exposures to a client when the trade is
cleared through a QCCP. [Basel Framework, CRE 54.12]
180. If a clearing member collects collateral from a client for client cleared trades and this
collateral is passed on to the CCP, the clearing member may recognize this collateral for both the
CCP-clearing member leg and the clearing member-client leg of the client cleared trade.
Therefore, initial margin posted by clients to their clearing member mitigates the exposure the
clearing member has against these clients. The same treatment applies, in an analogous fashion,
to multi-level client structures (between a higher level client and a lower level client). [Basel
Framework, CRE 54.13]

(iii) Client exposures

181. Subject to the two conditions set out in paragraph 182 below being met, the treatment
set out in paragraphs 175 to 178 above (i.e. the treatment of clearing member exposures to CCPs)
also applies to the following:
(1) An institution’s exposure to a clearing member where:
a. The institution is a client of the clearing member; and

43  This is to take account of the fact that netting arrangements for CCPs are not as standardized as those for OTC
netting agreements in the context of bilateral trading; however, netting is generally provided for in CCP rules.
44  The reduced EAD should also be used for the calculation of both the Advanced and Standardized CVA capital
charge.

---

<!-- Page 60 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 60
Protected B - External / Protégé B - Externe
b. The transactions arise as a result of the clearing member active as a financial
intermediary (i.e. the clearing member completes an offsetting transaction with a
CCP).
(2) An institution’s exposure to a CCP resulting from a transactions with the CCP where:
a. The institution is a client of a clearing member; and
b. The clearing member guarantees the performance of the institution’s exposure to
the CCP.
(3) Exposures of lower-level clients to higher-level clients in a multi-level client structure,
provided that for all clients levels in-between the two conditions in paragraph 182 below
are met.
[Basel Framework, CRE 54.14]
182. The two conditions referenced in paragraph 181 above are:
(1) The offsetting transactions are identified by the CCP as client transactions and collateral
to support them is held by the CCP and/or the clearing member, as applicable, under
arrangements that prevent any losses to the client due to: (a) the default or insolvency of
the clearing member; (b) the default or insolvency of the clearing member’s other clients;
and (c) the joint default or insolvency of the clearing member and any of its other clients.
Regarding the condition set out in this paragraph:
a. Upon the insolvency of the clearing member, there must be no legal impediment
(other than the need to obtain a court order to which the client is entitled) to the
transfer of the collateral belonging to clients of a defaulting clearing member to
the CCP, to one or more other surviving clearing members or to the client or the
client’s nominee.
b. The client must have conducted a sufficient legal review (and undertake such
further review as necessary to ensure continuing enforceability) and have a well
founded basis to conclude that, in the event of legal challenge, the relevant courts
and administrative authorities would find that such arrangements mentioned
above would be legal, valid, binding and enforceable under the relevant laws of
the relevant jurisdiction(s).
(2) Relevant laws, regulation, rules, contractual, or administrative arrangements provide that
the offsetting transactions with the defaulted or insolvent clearing member are highly
likely to continue to be indirectly transacted through the CCP, or by the CCP, if the
clearing member defaults or becomes insolvent. In such circumstances, the client
positions and collateral with the CCP will be transferred at market value unless the client
requests to close out the position at market value. Regarding the condition set out in this
paragraph, if there is a clear precedent for transactions being ported at a CCP and
industry intent for this practice to continue, then these factors must be considered when
assessing if trades are highly likely to be ported. The fact that CCP documentation does

---

<!-- Page 61 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 61
Protected B - External / Protégé B - Externe
not prohibit client trades from being ported is not sufficient to say they are highly likely
to be ported.
[Basel Framework, CRE 54.15]

183. Where a client is not protected from losses in the case that the clearing member and
another client of the clearing member jointly default or become jointly insolvent, but all other
conditions in the preceding paragraph are met, a risk weight of 4% will apply to the client’s
exposure to the clearing member, or to the higher level client, respectively. [Basel Framework,
CRE 53.16]
184. Where the institution is a client of the clearing member and the requirements in
paragraphs 181 to 183 are not met, the institution will capitalize its exposure (including potential
CVA risk exposure) to the clearing member as a bilateral trade. [Basel Framework, CRE 54.17]
(iv) Treatment of posted collateral

185. In all cases, any assets or collateral posted must, from the perspective of the institution
posting such collateral, receive the risk weights that otherwise applies to such assets or collateral
under the capital adequacy framework, regardless of the fact that such assets have been posted as
collateral.
45 That is, collateral posted must receive the banking book or trading book treatment it
would receive if it had not been posted to the CCP. [Basel Framework, CRE 54.18]
186. In addition to the requirements in paragraph 185 above, the posted assets or collateral
are subject to counterparty credit risk requirements, regardless of whether they are in the banking
or trading book. This includes the increase in the counterparty credit risk exposure due to the
application of haircuts. The counterparty credit risk requirements arise where assets or collateral
of a clearing member or client are posted with a CCP or a clearing member and are not held in a
bankruptcy remote manner. In such cases, the institution posting such assets or collateral must
also recognize the credit risk based upon the assets or collateral being exposed to risk of loss
based on the creditworthiness of the entity holding such assets or collateral, as described further
below. [Basel Framework, CRE 54.19]
187. Where such collateral is included in the definition of trade exposures and the entity
holding the collateral is the CCP, the following risk weights apply where the assets or collateral
is not held on a bankruptcy-remote basis:
(1) For institutions that are clearing members a risk-weight of 2% applies.
(2) For institutions that are clients of clearing members:

45  Collateral posted must receive the banking book or trading book treatment it would receive if it had not been
posted to the CCP. In addition, this collateral is subject to the CCR framework of the Basel rules, regardless of
whether it is in the banking or trading book. This includes the increase due to haircuts under either the
standardized supervisory haircuts or the own estimates.

---

<!-- Page 62 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 62
Protected B - External / Protégé B - Externe
a) A 2% risk weight applies if the conditions in paragraph 181 and 182 are met; or
b) A 4% risk weight applied if the conditions in paragraph 183 are met
[Basel Framework, CRE 54.20]
188. Where such collateral is included in the definition of trades exposures, there is no
capital requirement for counterparty credit risk exposures if the collateral is: (a) held by a
custodian;46 and (b) bankruptcy remote from the CCP. Regarding this paragraph, all forms of
collateral are included, such as: cash, securities, other pledged assets, and excess initial or
variation margin, also called overcollateralization, that is held by a custodian, and is bankruptcy
remote from the CCP, is not subject to a capital requirement for counterparty credit risk exposure
to such bankruptcy remote custodian (i.e. the related risk weight or EAD is equal to zero). [Basel
Framework, CRE 54.21]
189. The relevant risk weight of the CCP will apply to assets or collateral posted by a bank
that do not meet the definition of trade exposures (for example, treating the exposure as a
financial institution under the standardized approach or internal ratings-based approach to credit
risk). [Basel Framework, CRE 54.22]
190. Regarding the calculation of the exposure, or EAD, where banks use the SA-CCR to
calculate exposures, collateral posted which is not held in a bankruptcy remote manner must be
accounted for in the net independent collateral amount term in accordance with paragraph 110 to
114. For banks using IMM models, the alpha multiplier must be applied to the exposure on
posted collateral. [Basel Framework, CRE 54.23]

B. Default fund exposures

191. Where a default fund is shared between products or types of business with settlement
risk only (e.g. equities and bonds) and products or types of business which give rise to
counterparty credit risk (i.e. OTC derivatives, exchange-traded derivatives, SFTs or long
settlement transactions), all of the default fund contributions will receive the risk weight
determined according to the formulae and methodology set forth below, without apportioning to
different classes or types of business or products. However, where the default fund contributions
from clearing members are segregated by product types and only accessible for specific product
types, the capital requirements for those default fund exposures determined according to the
formulae and methodology set forth below must be calculated for each specific product giving
rise to counterparty credit risk. In case the CCP’s prefunded own resources are shared among
product types, the CCP will have to allocate those funds to each of the calculations, in proportion
to the respective product specific EAD. [Basel Framework, CRE 54.24]

46  In this paragraph, the word “custodian” may include a trustee, agent, pledgee, secured creditor or any other
person that holds property in a way that does not give such person a beneficial interest in such property and will
not result in such property being subject to legally-enforceable claims by such persons creditors, or to a court-
ordered stay of the return of such property, if such person becomes insolvent or bankrupt.

---

<!-- Page 63 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 63
Protected B - External / Protégé B - Externe
192. Whenever an institution is required to capitalize for exposures arising from default fund
contributions to a QCCP, clearing member institutions will apply the following approach. [Basel
Framework, CRE 54.25]
193. Clearing member institutions will apply a risk weight to their default fund contributions
determined according to a risk sensitive formula that considers (i) the size and quality of a
qualifying CCP’s financial resources, (ii) the counterparty credit risk exposures of such CCP,
and (iii) the application of such financial resources via the CCP’s loss bearing waterfall, in the
case of one or more clearing member defaults. The clearing member institution’s risk sensitive
capital requirement for its default fund contribution (𝐾𝐾𝐶𝐶𝑀𝑀𝑖𝑖) must be calculated using the
formulae and methodology set forth below. This calculation may be performed by a CCP,
institution, supervisor or other body with access to the required data, as long as the conditions in
paragraphs 204 to 206 are met. [Basel Framework, CRE 54.26]
194. The clearing member bank’s risk-sensitive capital requirement for its default fund
contribution (K
CMi) is calculated in two steps:
1) Calculate the hypothetical capital requirement of the CCP due to its counterparty credit
risk exposures to all of its clearing members and their clients.
2) Calculate the capital requirement for the clearing member institution.
[Basel Framework, CRE 54.27]
Hypothetical Capital Requirement of the CCP
195. The first step in calculating the clearing member institution’s capital requirement for its
default fund contribution is to calculate the hypothetical capital requirement of the CCP
(K
CCP) due to its counterparty credit risk exposures to all of its clearing members and their
clients. KCCP is a hypothetical capital requirement for a CCP, calculated on a consistent basis
for the sole purpose of determining the capitalization of clearing member default fund
contributions; it does not represent the actual capital requirements for a CCP which may be
determine by a CCP and its supervisor. [Basel Framework, CRE 54.28]
196. K
CCP is calculated using the following formula
𝐾𝐾𝐶𝐶𝐶𝐶𝑃𝑃= � 𝐸𝐸𝐴𝐴𝑆𝑆𝑖𝑖× 𝑀𝑀𝑅𝑅× 𝑐𝑐𝑦𝑦𝑚𝑚𝑚𝑚𝑚𝑚𝑦𝑦𝑚𝑚 𝑚𝑚𝑦𝑦𝑚𝑚𝑚𝑚𝐹𝐹
𝐶𝐶𝑀𝑀𝑖𝑖

where
(1) RW is a risk weight of 20%47

47  The 20% risk weight is a minimum requirement. As with other parts of the capital adequacy framework, OSFI
may increase the risk weight. An increase in such risk weight would be appropriate if, for example, the clearing
members in a CCP are not highly rated. Any such increase in risk weight is to be communicated by the affected
institutions to the person completing this calculation.

---

<!-- Page 64 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 64
Protected B - External / Protégé B - Externe
(2) Capital ratio means 8%
(3) CM is the clearing member
(4) EADi is the exposure amount of the CCP to CM ‘i’, including both the CM’s own
transactions and client transactions guaranteed by the CM, and all values of
collateral held by the CCP (including the CM’s prefunded default fund
contribution) against these transactions, relating to the valuation at the end of the
regulatory reporting date before the margin called on the final margin call of that
day is exchanged.
(5) The sum is over all clearing member accounts.
[Basel Framework, CRE 54.29]
197. Where clearing members provide client clearing services, and client transactions and
collateral are held in separate (individual or omnibus) sub-accounts to the clearing member’s
proprietary business, each such client sub-account should enter the sum in paragraph 196
separately, i.e. the member EAD in the formula above is then the sum of the client sub-
account EADs and any house sub-account EAD. This will ensure that client collateral cannot
be used to offset the CCP’s exposures to clearing members’ proprietary activity in the
calculation of K
CCP. If any of these sub-accounts contains both derivatives and SFTs, the
EAD of that sub-account is the sum of the derivative EAD and the SFT EAD. [Basel
Framework, CRE 54.30]
198. In the case that collateral is held against an account containing both SFTs and
derivatives, the prefunded initial margin provided by the member or client must be allocated
to the SFT and derivatives exposures in proportion to the respective product specific EADs,
calculated according to Chapter 4 for SFTs and the SACCR in this chapter (without including
the effects of collateral) for derivatives. [Basel Framework, CRE 54.31]

199. If the default fund contributions of the member (DFi) are not split with regard to client
and house sub-accounts, they must be allocated per sub-account according to the respective
fraction the initial margin of that sub-account has in relation to the total initial margin posted
by or for the account of the clearing member. [Basel Framework, CRE 54.32]
200. For derivatives, EAD
i is calculated as the bilateral trade exposure the CCP has against
the clearing member using the SACCR.48 49 In applying the SACCR:
1) A MPOR of 10 days must be used to calculate the CCP’s potential future exposure to its
clearing members on derivatives transactions (the 20 day floor on the MPOR for netting
sets with more than 5,000 trades does not apply).

48  A MPOR of 10 days must be used to calculate the CCP’s potential future exposure to its clearing members on
derivatives transactions
49  For exposures to QCCPs located in jurisdictions where the SA-CCR has not been implemented the EAD may be
computed using the current exposure method as described Capital requirements for bank exposures to central
counterparties.

---

<!-- Page 65 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 65
Protected B - External / Protégé B - Externe
2) All collateral held by a CCP to which that CCP has a legal claim in the event of the
default of the member or client, including default fund contributions of that member
(DF
i), is used to offset the CCP’s exposure to that member or client, through inclusion in
the PFE multiplier in accordance with paragraphs 117 to 118.
[Basel Framework, CRE 54.33]
201. For SFTs, EAD is equal to max(EBRMi – IMi – DFi; 0), where
1) EBRMi denotes the exposure value to clearing member ‘i’ before risk mitigation under
Chapter 4; where, for the purposes of this calculation, variation margin that has been
exchanged (before the margin called on the final margin call of that day) enters into the
mark-to-market value of the transactions;
2) IM
i is the initial margin collateral posted by the clearing member with the CCP;
3) DFi is the prefunded default fund contribution by the clearing member that will be
applied upon such clearing member’s default, either along with or immediately following
such member’s initial margin, to reduce the CCP loss.
[Basel Framework, CRE 54.34]
202. As regards the calculation in this first step (i.e. paragraphs 195 to 201):
(1) Any haircuts to be applied for SFTs must be the standard supervisory haircuts in Chapter
4.
(2) The holding periods for SFT calculations in Chapter 4 and those.
(3) The netting sets that are applicable to regulated clearing members are the same as those
referred to in paragraph 177. For all other clearing members, they need to follow the
netting rules as laid out by the CCP based upon notification of each of its clearing
members. OSFI can demand more granular netting sets than laid out by the CCP.
[Basel Framework, CRE 54.35]
Capital Requirement for Each Clearing Member
203. The second step in calculatingthe clearing member institution’s capital requirement for
its default fund contributions (K
CMi) is to apply the following formula:
𝐾𝐾𝐶𝐶𝑀𝑀𝑖𝑖= 𝑚𝑚𝑦𝑦𝑚𝑚�𝐾𝐾𝐶𝐶𝐶𝐶𝑃𝑃× � 𝑆𝑆𝐹𝐹𝑖𝑖
𝑝𝑝𝐹𝐹𝑎𝑎𝑜𝑜
𝑆𝑆𝐹𝐹𝐶𝐶𝐶𝐶𝑃𝑃+ 𝑆𝑆𝐹𝐹𝐶𝐶𝑀𝑀
𝑝𝑝𝐹𝐹𝑎𝑎𝑜𝑜�; 8% × 2% × 𝑆𝑆𝐹𝐹𝑖𝑖
𝑝𝑝𝐹𝐹𝑎𝑎𝑜𝑜�
where
• 𝐾𝐾𝐶𝐶𝑀𝑀𝑖𝑖is the capital requirements on the default contribution of member i;

---

<!-- Page 66 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 66
Protected B - External / Protégé B - Externe
• 𝑆𝑆𝐹𝐹𝐶𝐶𝑀𝑀
𝑝𝑝𝐹𝐹𝑎𝑎𝑜𝑜is the total prefunded default fund contributions from clearing members;
• 𝑆𝑆𝐹𝐹𝐶𝐶𝐶𝐶𝑃𝑃 is the CCP’s prefunded own resources (e.g. contributed capital, retained
earnings, etc), which are contributed to the default waterfall, where these are
junior or pari passu to prefunded member contributions; and
• 𝑆𝑆𝐹𝐹𝑖𝑖
𝑝𝑝𝐹𝐹𝑎𝑎𝑜𝑜is the prefunded default fund contributions provided by clearing member i.
[Basel Framework, CRE 54.36]
204. The CCP, institution, OSFI or other body with access to the required data, must make a
calculation of KCCP, 𝑆𝑆𝐹𝐹𝐶𝐶𝑀𝑀
𝑝𝑝𝐹𝐹𝑎𝑎𝑜𝑜, and DFCCP in such a way to permit the supervisor of the CCP to
oversee those calculations, and it must share sufficient information of the calculation results to
permit each clearing member to calculate their capital requirement for the default fund and for
the supervisor of such clearing member to review and confirm such calculations. [Basel
Framework, CRE 54.37]
205. KCCP must be calculated on a quarterly basis at a minimum; although national
supervisors may require more frequent calculations in case of material changes (such as the CCP
clearing a new product). The CCP, institution, supervisor or other body that did the calculations
must make available to the home supervisor of any clearing member sufficient aggregate
information about the composition of the CCP’s exposures to clearing members and information
provided to the clearing member for the purposes of the calculation of K
CCP, 𝑆𝑆𝐹𝐹𝐶𝐶𝑀𝑀
𝑝𝑝𝐹𝐹𝑎𝑎𝑜𝑜, and DFCCP.
Such information must be provided no less frequently than OSFI would require for monitoring
the risk of the clearing member that it supervises. [Basel Framework, CRE 54.38]
206. KCCP and 𝐾𝐾𝐶𝐶𝑀𝑀𝑖𝑖 must be recalculated at least quarterly, and should also be recalculated
when there are material changes to the number or exposure of cleared transactions or material
changes to the financial resources of the CCP.
[Basel Framework, CRE 54.39]
C. Cap with regard to QCCPs
207. Where the sum of an institution’s capital charges for exposures to a qualifying CCP due
to its trade exposure and default fund contribution is higher than the total capital charge that
would be applied to those same exposures if the CCP were for a non-qualifying CCP, as outlined
in paragraphs 208 and 209, the latter total capital charge shall be applied. [Basel Framework,
CRE 54.40]


7.1.8.2 Exposures to Non-qualifying CCPs

208. Institutions must apply the standardized approach for credit risk in Chapter 4, according
to the category of the counterparty, to their trade exposure to a non-qualifying CCP.
[Basel Framework, CRE 54.41]

---

<!-- Page 67 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 67
Protected B - External / Protégé B - Externe
209. Institutions must deduct from CET1 capital their amount of default fund contributions to
a non-qualifying CCP. For the purposes of this paragraph, the default fund contributions of such
institutions will include both the funded and the unfunded contributions which are liable to be
paid should the CCP so require. Where there is a liability for unfunded contributions (i.e.
unlimited binding commitments) OSFI will determine in its Pillar 2 assessments the amount of
unfunded commitments which must be deducted from CET1 capital amounts. [Basel Framework,
CRE 54.42]
7.2. Capital treatment for failed trades and non-DvP transactions
[previously Annex 3]

210. The capital requirement for failed trades and non-DvP transactions outlined in this
Chapter applies in addition to (i.e. it does not replace) the requirements for the transactions
themselves under this framework.
7.2.1 Overarching principles
211. Institutions should continue to develop, implement and improve systems for tracking
and monitoring the credit risk exposures arising from unsettled and failed transactions as
appropriate for producing management information that facilitates action on a timely basis.
[Basel Framework, CRE 70.2]

212. Transactions settled through a delivery-versus-payment system (DvP),
50 providing
simultaneous exchanges of securities for cash, expose firms to a risk of loss on the difference
between the transaction valued at the agreed settlement price and the transaction valued at
current market price (i.e. positive current exposure). Transactions where cash is paid without
receipt of the corresponding receivable (securities, foreign currencies, gold, or commodities) or,
conversely, deliverables were delivered without receipt of the corresponding cash payment (non-
DvP, or free-delivery) expose firms to a risk of loss on the full amount of cash paid or
deliverables delivered. The current rules set out specific capital charges that address these two
kinds of exposures.  [Basel Framework, CRE 70.3 and 70.4]

213. The following capital treatment is applicable to all transactions on securities, foreign
exchange instruments, and commodities that give rise to a risk of delayed settlement or delivery.
This includes transactions through recognized clearing houses and central counterparties that are
subject to daily mark-to-market and payment of daily variation margins and that involve a
mismatched trade.
51 The treatment does not apply to the instruments that are subject to the
counterparty credit risk requirements set out in section 7.1 or the credit risk mitigation section of
chapter 4 of this guideline (i.e. over-the-counter derivatives, exchange-traded derivatives, long
settlement transactions, securities financing transactions).[Basel Framework, CRE 70.5]

50  For the purpose of this guideline, DvP transactions include payment-versus-payment (PvP) transactions.
51  An exposure value of zero for counterparty credit risk can be attributed to payment transactions (e.g. funds
transfer transactions) and other spot transactions that are outstanding with a central counterparty (e.g. a clearing
house), when the central counterparty CCR exposures with all participants in its arrangements are fully
collateralized on a daily basis.

---

<!-- Page 68 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 68
Protected B - External / Protégé B - Externe

214. In cases of a system wide failure of a settlement, clearing system or central
counterparty, a national supervisor may use its discretion to waive capital charges until the
situation is rectified. [BCBS June 2006 Annex 3 par 4] and [Basel Framework, CRE 70.7]

215. Failure of a counterparty to settle a trade in itself will not be deemed a default for
purposes of credit risk under this guideline.  [Basel Framework, CRE 70.8]

216. In applying a risk weight to failed free-delivery exposures, institutions using the IRB
approach for credit risk may assign PDs to counterparties for which they have no other banking
book exposure on the basis of the counterparty’s external rating. Institutions using the Advanced
IRB approach may use a 45% LGD in lieu of estimating LGDs so long as they apply it to all
failed trade exposures. Alternatively, institutions using the IRB approach may opt to apply the
standardized approach risk weights or a 100% risk weight.  [Basel Framework, CRE 70.10]
7.2.2 Capital requirements
217. For DvP transactions, if the payments have not yet taken place five business days after
the settlement date, firms must calculate a capital charge by multiplying the positive current
exposure of the transaction by the appropriate factor, according to the Table 3.


Table 3
Number of working days after the
agreed settlement date
Corresponding risk multiplier
From 5 to 15 8%
From 16 to 30 50%
From 31 to 45 75%
46 or more 100%
[Basel Framework, CRE 70.9]

218. For non-DvP transactions (i.e. free deliveries), after the first contractual
payment/delivery leg, the institution that has made the payment will treat its exposure as a loan if
the second leg has not been received by the end of the business day.
52 This means that an
institution under the IRB approach will apply the appropriate IRB formula set out in this
guideline, for the exposure to the counterparty, in the same way as it does for all other banking
book exposures. Similarly, institutions under the standardized approach will use the standardized
risk weights set forth in this guideline. However, when exposures are not material, institutions
may choose to apply a uniform 100% risk-weight to these exposures, in order to avoid the
burden of a full credit assessment. If five business days after the second contractual

52  If the dates when two payment legs are made are the same according to the time zones where each payment is
made, it is deemed that they are settled on the same day. For example, if a bank in Tokyo transfers Yen on day X
(Japan Standard Time) and receives corresponding US Dollar via CHIPS on day X (US Eastern Standard Time),
the settlement is deemed to take place on the same value date.

---

<!-- Page 69 -->

Banks/BHC/T&L  Settlement and Counterparty Risk
 September 2025 Chapter 7 - Page 69
Protected B - External / Protégé B - Externe
payment/delivery date the second leg has not yet effectively taken place, the institution that has
made the first payment leg will deduct from capital the full amount of the value transferred plus
replacement cost, if any. This treatment will apply until the second payment/delivery leg is
effectively made.  [Basel Framework, CRE 70.4]
