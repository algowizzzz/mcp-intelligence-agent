"""Human-to-XBRL concept mapping for edgar_get_metric and related tools."""
import json
from typing import List, Optional
from .edgar_tavily_client import tavily_extract, fix_tavily_json

# Maps human-readable metric names to ordered list of XBRL concepts (try in order)
HUMAN_TO_XBRL = {
    'revenue':              ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax'],
    'sales':                ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet'],
    'net income':           ['NetIncomeLoss', 'NetIncomeLossAttributableToParent', 'ProfitLoss'],
    'eps':                  ['EarningsPerShareDiluted', 'EarningsPerShareBasic'],
    'eps diluted':          ['EarningsPerShareDiluted'],
    'eps basic':            ['EarningsPerShareBasic'],
    'gross profit':         ['GrossProfit'],
    'operating income':     ['OperatingIncomeLoss'],
    'total assets':         ['Assets'],
    'total liabilities':    ['Liabilities'],
    'total equity':         ['StockholdersEquity', 'StockholdersEquityAttributableToParent'],
    'cash':                 ['CashAndCashEquivalentsAtCarryingValue', 'Cash', 'CashCashEquivalentsAndShortTermInvestments'],
    'total debt':           ['LongTermDebt', 'LongTermDebtAndCapitalLeaseObligations', 'DebtCurrent'],
    'long term debt':       ['LongTermDebt', 'LongTermDebtAndCapitalLeaseObligations'],
    'operating cash flow':  ['NetCashProvidedByUsedInOperatingActivities'],
    'capex':                ['PaymentsToAcquirePropertyPlantAndEquipment', 'CapitalExpendituresIncurredButNotYetPaid'],
    'depreciation':         ['DepreciationDepletionAndAmortization', 'Depreciation'],
    'shares outstanding':   ['WeightedAverageNumberOfDilutedSharesOutstanding', 'CommonStockSharesOutstanding'],
    'dividends':            ['PaymentsOfDividends', 'PaymentsOfDividendsCommonStock'],
    'research development': ['ResearchAndDevelopmentExpense'],
    'r&d':                  ['ResearchAndDevelopmentExpense'],
    'selling general administrative': ['SellingGeneralAndAdministrativeExpense'],
    'sg&a':                 ['SellingGeneralAndAdministrativeExpense'],
    'income tax':           ['IncomeTaxExpenseBenefit'],
    'interest expense':     ['InterestExpense', 'InterestAndDebtExpense'],
    'current assets':       ['AssetsCurrent'],
    'current liabilities':  ['LiabilitiesCurrent'],
    'inventory':            ['InventoryNet'],
    'accounts receivable':  ['AccountsReceivableNetCurrent'],
}

# Standard line items for financial statements
INCOME_STATEMENT_ITEMS = [
    ('Revenue', 'revenue'),
    ('Gross Profit', 'gross profit'),
    ('Operating Income', 'operating income'),
    ('Net Income', 'net income'),
    ('EPS Diluted', 'eps diluted'),
    ('R&D Expense', 'r&d'),
    ('SG&A Expense', 'sg&a'),
    ('Income Tax', 'income tax'),
]

BALANCE_SHEET_ITEMS = [
    ('Total Assets', 'total assets'),
    ('Current Assets', 'current assets'),
    ('Cash & Equivalents', 'cash'),
    ('Accounts Receivable', 'accounts receivable'),
    ('Inventory', 'inventory'),
    ('Total Liabilities', 'total liabilities'),
    ('Current Liabilities', 'current liabilities'),
    ('Total Equity', 'total equity'),
    ('Long-Term Debt', 'long term debt'),
]

CASH_FLOW_ITEMS = [
    ('Operating Cash Flow', 'operating cash flow'),
    ('Capital Expenditure', 'capex'),
    ('Dividends Paid', 'dividends'),
    ('Depreciation & Amortization', 'depreciation'),
]

def get_xbrl_concepts(human_term: str) -> List[str]:
    """Return ordered list of XBRL concepts for a human metric name."""
    term = human_term.lower().strip()
    if term in HUMAN_TO_XBRL:
        return HUMAN_TO_XBRL[term]
    # Partial match
    for k, v in HUMAN_TO_XBRL.items():
        if term in k or k in term:
            return v
    return []

def fetch_xbrl_records(cik: str, concept: str) -> List[dict]:
    """Fetch all records for a single XBRL concept via Tavily extract."""
    url = f'https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json'
    results = tavily_extract([url])
    if not results:
        return []
    raw = fix_tavily_json(results[0].get('raw_content', ''))
    try:
        data = json.loads(raw)
    except Exception:
        return []
    units = data.get('units', {})
    for key in ['USD/shares', 'USD', 'shares', 'pure']:
        if key in units:
            return units[key]
    return []

def fetch_best_concept(cik: str, human_term: str) -> tuple:
    """
    Try all XBRL concepts for a human term and return (concept_name, records)
    for the concept with the most recent data. Fixes company-specific tag changes
    (e.g. MSFT switched revenue concepts after 2011).
    """
    concepts = get_xbrl_concepts(human_term)
    if not concepts:
        return None, []

    best_concept = None
    best_records = []
    best_date = ''

    for concept in concepts:
        records = fetch_xbrl_records(cik, concept)
        if records:
            latest = max((r.get('end', '') for r in records), default='')
            if latest > best_date:
                best_date = latest
                best_concept = concept
                best_records = records

    return best_concept, best_records

def filter_and_sort_records(records: List[dict], form_type: str, periods: int) -> List[dict]:
    """Filter by form_type, deduplicate by end date, sort descending, take top N."""
    if form_type and form_type.upper() not in ('BOTH', 'ALL'):
        records = [r for r in records if r.get('form', '') == form_type.upper()]
    # Deduplicate by end date — keep most recently filed
    seen = {}
    for r in records:
        end = r.get('end', '')
        if end not in seen or r.get('filed', '') > seen[end].get('filed', ''):
            seen[end] = r
    records = list(seen.values())
    records.sort(key=lambda x: x.get('end', ''), reverse=True)
    return records[:min(periods, 20)]
