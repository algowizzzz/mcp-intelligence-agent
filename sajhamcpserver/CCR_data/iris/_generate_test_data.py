"""
Script to generate IRIS CCR test data CSVs.
Run once to populate test data.
"""
import os
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))

DATES = ['2026-01-27', '2026-02-27', '2026-03-25', '2026-03-26', '2026-03-27']

# ---------------------------------------------------------------------------
# Master data definition
# Each entry: (date, product, cust_code, cust_name, rating, le, facility_id,
#              agreement, term, term_end, max_avail,
#              prod_limit, prod_exp,
#              cust_limit, cust_exp,
#              conn_limit, conn_exp,
#              fac_limit_cust, fac_exp_cust,
#              fac_limit_conn, fac_exp_conn,
#              agr_limit_cust, agr_exp_cust,
#              country, country_rating, csa, netting,
#              currency, conn_code)
# ---------------------------------------------------------------------------

def make_row(date, product, cust_code, cust_name, rating, le, facility_id,
             agreement, csa, netting,
             prod_limit, prod_exp,
             cust_limit, cust_exp,
             conn_limit, conn_exp,
             country, country_rating, currency, conn_code):
    prod_avail = prod_limit - prod_exp
    cust_avail = cust_limit - cust_exp
    conn_avail = conn_limit - conn_exp
    fac_lim_cust = prod_limit
    fac_exp_cust = prod_exp
    fac_avail_cust = fac_lim_cust - fac_exp_cust
    fac_lim_conn = prod_limit
    fac_exp_conn = prod_exp
    fac_avail_conn = fac_lim_conn - fac_exp_conn
    agr_lim_cust = cust_limit
    agr_exp_cust = cust_exp
    agr_avail_cust = agr_lim_cust - agr_exp_cust
    return {
        'Date': date,
        'Product': product,
        'Customer Code': cust_code,
        'Customer Name': cust_name,
        'Customer Internal Rating': rating,
        'Legal Entity': le,
        'Facility ID': facility_id,
        'Agreement': agreement,
        'Term': 36,
        'Term End Date': '2027-12-31',
        'Max Avail': prod_limit,
        'Product Limit': prod_limit,
        'Product Exposure': prod_exp,
        'Product Avail': prod_avail,
        'Cust Limit': cust_limit,
        'Cust Exposure': cust_exp,
        'Cust Avail': cust_avail,
        'Conn Limit': conn_limit,
        'Conn Exposure': conn_exp,
        'Conn Avail': conn_avail,
        'Facility Limit (Cust Level)': fac_lim_cust,
        'Facility Exposure (Cust Level)': fac_exp_cust,
        'Facility Avail (Cust Level)': fac_avail_cust,
        'Agreement Limit (Cust Level)': agr_lim_cust,
        'Agreement Exposure (Cust Level)': agr_exp_cust,
        'Agreement Avail (Cust Level)': agr_avail_cust,
        'Facility Limit (Conn Level)': fac_lim_conn,
        'Facility Exposure (Conn Level)': fac_exp_conn,
        'Facility Avail (Conn Level)': fac_avail_conn,
        'Country': country,
        'Country Rating': country_rating,
        'CSA Agreement': csa,
        'Netting Agreement': netting,
        'Measure': 'Notional',
        'Product Limit Currency': currency,
        'Agreement Limit Currency': currency,
        'Customer Limit Currency': currency,
        'Connection Limit Currency': currency,
        'Facility Cust Currency': currency,
        'Facility Conn Currency': currency,
        'Connection Code': conn_code,
    }


rows = []

# ============================================================
# RBC — clean, no breaches. BCMC (3 products) + BMO (1 product)
#        FX Forward facility_id=76830 under BCMC
#        CSA=Y, Netting=Y on FX Forward records
# ============================================================
for date in DATES:
    # BCMC — Derivative Products
    rows.append(make_row(date, 'Derivative Products', 'RBC', 'Royal Bank of Canada', 10,
                         'BCMC', 76831, 'RBC_AGR_001', 'N', 'N',
                         200_000_000, 80_000_000,
                         400_000_000, 150_000_000,
                         500_000_000, 180_000_000,
                         'CANADA', 'AAA', 'CAD', 'RBCGRP'))
    # BCMC — FX Forward (facility 76830, CSA=Y, Netting=Y)
    rows.append(make_row(date, 'FX Forward', 'RBC', 'Royal Bank of Canada', 10,
                         'BCMC', 76830, 'RBC_AGR_001', 'Y', 'Y',
                         150_000_000, 45_000_000,
                         400_000_000, 150_000_000,
                         500_000_000, 180_000_000,
                         'CANADA', 'AAA', 'CAD', 'RBCGRP'))
    # BCMC — Interest Rate Products
    rows.append(make_row(date, 'Interest Rate Products', 'RBC', 'Royal Bank of Canada', 10,
                         'BCMC', 76832, 'RBC_AGR_001', 'Y', 'Y',
                         100_000_000, 25_000_000,
                         400_000_000, 150_000_000,
                         500_000_000, 180_000_000,
                         'CANADA', 'AAA', 'CAD', 'RBCGRP'))
    # BMO (secondary LE) — Equity Products
    rows.append(make_row(date, 'Equity Products', 'RBC', 'Royal Bank of Canada', 10,
                         'BMO', 76833, 'RBC_AGR_002', 'N', 'N',
                         50_000_000, 10_000_000,
                         100_000_000, 20_000_000,
                         500_000_000, 180_000_000,
                         'CANADA', 'AAA', 'CAD', 'RBCGRP'))

# ============================================================
# TD — FX Forward exposure trends up: Jan $20M -> Feb $25M -> Mar25 $30M -> Mar26 $35M -> Mar27 $40M
# ============================================================
td_fx_exp = {'2026-01-27': 20_000_000, '2026-02-27': 25_000_000,
             '2026-03-25': 30_000_000, '2026-03-26': 35_000_000, '2026-03-27': 40_000_000}
for date in DATES:
    fx_exp = td_fx_exp[date]
    rows.append(make_row(date, 'FX Forward', 'TD', 'Toronto-Dominion Bank', 9,
                         'BCMC', 77100, 'TD_AGR_001', 'Y', 'Y',
                         60_000_000, fx_exp,
                         250_000_000, fx_exp + 50_000_000,
                         300_000_000, fx_exp + 70_000_000,
                         'CANADA', 'AAA', 'CAD', 'TDGRP'))
    rows.append(make_row(date, 'Derivative Products', 'TD', 'Toronto-Dominion Bank', 9,
                         'BCMC', 77101, 'TD_AGR_001', 'N', 'N',
                         80_000_000, 30_000_000,
                         250_000_000, fx_exp + 50_000_000,
                         300_000_000, fx_exp + 70_000_000,
                         'CANADA', 'AAA', 'CAD', 'TDGRP'))
    rows.append(make_row(date, 'Interest Rate Products', 'TD', 'Toronto-Dominion Bank', 9,
                         'BNBI', 77102, 'TD_AGR_002', 'Y', 'N',
                         40_000_000, 15_000_000,
                         120_000_000, 45_000_000,
                         300_000_000, fx_exp + 70_000_000,
                         'CANADA', 'AAA', 'CAD', 'TDGRP'))

# ============================================================
# BMO_CP — Bank of Montreal, rating 8, CAD
# ============================================================
for date in DATES:
    rows.append(make_row(date, 'Derivative Products', 'BMO_CP', 'Bank of Montreal', 8,
                         'BCMC', 78000, 'BMO_AGR_001', 'Y', 'Y',
                         120_000_000, 55_000_000,
                         300_000_000, 110_000_000,
                         400_000_000, 140_000_000,
                         'CANADA', 'AAA', 'CAD', 'BMOGRP'))
    rows.append(make_row(date, 'FX Forward', 'BMO_CP', 'Bank of Montreal', 8,
                         'BCMC', 78001, 'BMO_AGR_001', 'Y', 'Y',
                         80_000_000, 30_000_000,
                         300_000_000, 110_000_000,
                         400_000_000, 140_000_000,
                         'CANADA', 'AAA', 'CAD', 'BMOGRP'))

# ============================================================
# GS — Goldman Sachs, rating 7, USD
#       FX Forward: Product Exposure > Product Limit on 2026-03-27 (breach)
#       Exposure ~$55M, Limit $50M
# ============================================================
gs_fx_exp = {'2026-01-27': 35_000_000, '2026-02-27': 40_000_000,
             '2026-03-25': 44_000_000, '2026-03-26': 48_000_000, '2026-03-27': 55_000_000}
for date in DATES:
    fx_exp = gs_fx_exp[date]
    rows.append(make_row(date, 'FX Forward', 'GS', 'Goldman Sachs', 7,
                         'BCMC', 79000, 'GS_AGR_001', 'Y', 'Y',
                         50_000_000, fx_exp,
                         200_000_000, fx_exp + 60_000_000,
                         250_000_000, fx_exp + 80_000_000,
                         'USA', 'AA', 'USD', 'GSGRP'))
    rows.append(make_row(date, 'Derivative Products', 'GS', 'Goldman Sachs', 7,
                         'BCMC', 79001, 'GS_AGR_001', 'N', 'N',
                         100_000_000, 60_000_000,
                         200_000_000, fx_exp + 60_000_000,
                         250_000_000, fx_exp + 80_000_000,
                         'USA', 'AA', 'USD', 'GSGRP'))
    rows.append(make_row(date, 'Interest Rate Products', 'GS', 'Goldman Sachs', 7,
                         'BMO', 79002, 'GS_AGR_002', 'N', 'N',
                         75_000_000, 20_000_000,
                         80_000_000, 25_000_000,
                         250_000_000, fx_exp + 80_000_000,
                         'USA', 'AA', 'USD', 'GSGRP'))

# ============================================================
# JPM — JP Morgan Chase, rating 7, USD
#        Derivative Products exposure decreases: $100M -> $90M -> $80M -> $70M -> $60M
# ============================================================
jpm_deriv_exp = {'2026-01-27': 100_000_000, '2026-02-27': 90_000_000,
                 '2026-03-25': 80_000_000, '2026-03-26': 70_000_000, '2026-03-27': 60_000_000}
for date in DATES:
    d_exp = jpm_deriv_exp[date]
    rows.append(make_row(date, 'Derivative Products', 'JPM', 'JP Morgan Chase', 7,
                         'BCMC', 80000, 'JPM_AGR_001', 'Y', 'Y',
                         120_000_000, d_exp,
                         350_000_000, d_exp + 80_000_000,
                         400_000_000, d_exp + 100_000_000,
                         'USA', 'AA', 'USD', 'JPMGRP'))
    rows.append(make_row(date, 'FX Forward', 'JPM', 'JP Morgan Chase', 7,
                         'BCMC', 80001, 'JPM_AGR_001', 'Y', 'N',
                         90_000_000, 50_000_000,
                         350_000_000, d_exp + 80_000_000,
                         400_000_000, d_exp + 100_000_000,
                         'USA', 'AA', 'USD', 'JPMGRP'))
    rows.append(make_row(date, 'Equity Products', 'JPM', 'JP Morgan Chase', 7,
                         'BNBI', 80002, 'JPM_AGR_002', 'N', 'N',
                         60_000_000, 30_000_000,
                         150_000_000, 55_000_000,
                         400_000_000, d_exp + 100_000_000,
                         'USA', 'AA', 'USD', 'JPMGRP'))

# ============================================================
# DB — Deutsche Bank, rating 5, EUR (use USD)
#       Cust Exposure > Cust Limit on 2026-03-27
#       Cust Limit $80M, Cust Exposure $90M
# ============================================================
db_cust_exp = {'2026-01-27': 60_000_000, '2026-02-27': 65_000_000,
               '2026-03-25': 72_000_000, '2026-03-26': 78_000_000, '2026-03-27': 90_000_000}
for date in DATES:
    c_exp = db_cust_exp[date]
    rows.append(make_row(date, 'Derivative Products', 'DB', 'Deutsche Bank', 5,
                         'BCMC', 81000, 'DB_AGR_001', 'Y', 'Y',
                         50_000_000, 35_000_000,
                         80_000_000, c_exp,
                         120_000_000, c_exp + 10_000_000,
                         'GERMANY', 'A', 'USD', 'DBGRP'))
    rows.append(make_row(date, 'FX Forward', 'DB', 'Deutsche Bank', 5,
                         'BCMC', 81001, 'DB_AGR_001', 'Y', 'Y',
                         40_000_000, 25_000_000,
                         80_000_000, c_exp,
                         120_000_000, c_exp + 10_000_000,
                         'GERMANY', 'A', 'USD', 'DBGRP'))

# ============================================================
# CS — Credit Suisse, rating 4, CHF (use USD)
#       High exposure relative to limit
# ============================================================
for date in DATES:
    rows.append(make_row(date, 'Derivative Products', 'CS', 'Credit Suisse', 4,
                         'BCMC', 82000, 'CS_AGR_001', 'Y', 'N',
                         60_000_000, 58_000_000,   # close to limit
                         100_000_000, 95_000_000,  # close to limit
                         130_000_000, 118_000_000,
                         'SWITZERLAND', 'BBB', 'USD', 'CSGRP'))
    rows.append(make_row(date, 'FX Forward', 'CS', 'Credit Suisse', 4,
                         'BCMC', 82001, 'CS_AGR_001', 'N', 'N',
                         30_000_000, 28_000_000,   # close to limit
                         100_000_000, 95_000_000,
                         130_000_000, 118_000_000,
                         'SWITZERLAND', 'BBB', 'USD', 'CSGRP'))

# ============================================================
# RISK_CP — Risky Corp Ltd, rating 3, CAYMAN ISLANDS
#            2+ product limit breaches on latest date (2026-03-27)
# ============================================================
risk_prod_exp = {
    'Derivative Products': {'2026-01-27': 30_000_000, '2026-02-27': 35_000_000,
                            '2026-03-25': 38_000_000, '2026-03-26': 42_000_000, '2026-03-27': 52_000_000},
    'FX Forward':          {'2026-01-27': 15_000_000, '2026-02-27': 18_000_000,
                            '2026-03-25': 20_000_000, '2026-03-26': 23_000_000, '2026-03-27': 33_000_000},
    'Commodity Products':  {'2026-01-27': 8_000_000,  '2026-02-27': 10_000_000,
                            '2026-03-25': 11_000_000, '2026-03-26': 14_000_000, '2026-03-27': 22_000_000},
}
risk_prod_limits = {
    'Derivative Products': 40_000_000,
    'FX Forward':          25_000_000,
    'Commodity Products':  20_000_000,
}
for date in DATES:
    for prod, exps in risk_prod_exp.items():
        exp = exps[date]
        lim = risk_prod_limits[prod]
        rows.append(make_row(date, prod, 'RISK_CP', 'Risky Corp Ltd', 3,
                             'BCMC', 83000, 'RISK_AGR_001', 'N', 'N',
                             lim, exp,
                             80_000_000, sum(exps[date] for exps in risk_prod_exp.values()),
                             100_000_000, sum(exps[date] for exps in risk_prod_exp.values()) + 5_000_000,
                             'CAYMAN ISLANDS', 'BB', 'USD', 'RISKGRP'))

# ============================================================
# Build DataFrame
# ============================================================
df_all = pd.DataFrame(rows)

# Ensure column order
COLS = [
    'Date', 'Product', 'Customer Code', 'Customer Name', 'Customer Internal Rating',
    'Legal Entity', 'Facility ID', 'Agreement', 'Term', 'Term End Date', 'Max Avail',
    'Product Limit', 'Product Exposure', 'Product Avail',
    'Cust Limit', 'Cust Exposure', 'Cust Avail',
    'Conn Limit', 'Conn Exposure', 'Conn Avail',
    'Facility Limit (Cust Level)', 'Facility Exposure (Cust Level)', 'Facility Avail (Cust Level)',
    'Agreement Limit (Cust Level)', 'Agreement Exposure (Cust Level)', 'Agreement Avail (Cust Level)',
    'Facility Limit (Conn Level)', 'Facility Exposure (Conn Level)', 'Facility Avail (Conn Level)',
    'Country', 'Country Rating', 'CSA Agreement', 'Netting Agreement', 'Measure',
    'Product Limit Currency', 'Agreement Limit Currency', 'Customer Limit Currency',
    'Connection Limit Currency', 'Facility Cust Currency', 'Facility Conn Currency', 'Connection Code'
]
df_all = df_all[COLS]

# Write iris_combined.csv (with Date column)
out_combined = os.path.join(BASE, 'iris_combined.csv')
df_all.to_csv(out_combined, index=False, encoding='latin1')
print(f'Written {len(df_all)} rows to iris_combined.csv')

# Write per-date CSVs (without Date column)
DATE_FILES = {
    '2026-03-27': 'IRIS_ALL_PROD_UTIL_2026-03-27.csv',
    '2026-03-26': 'IRIS_ALL_PROD_UTIL_2026-03-26.csv',
    '2026-02-27': 'IRIS_ALL_PROD_UTIL_2026-02-27.csv',
}
COLS_NO_DATE = [c for c in COLS if c != 'Date']
for date_val, fname in DATE_FILES.items():
    sub = df_all[df_all['Date'] == date_val][COLS_NO_DATE]
    out = os.path.join(BASE, fname)
    sub.to_csv(out, index=False, encoding='latin1')
    print(f'Written {len(sub)} rows to {fname}')

print('Done.')
