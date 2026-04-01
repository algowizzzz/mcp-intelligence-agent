"""
EDGAR numeric tools — T-03, T-04, T-05, T-09
All SEC data fetched via Tavily (no direct urllib to sec.gov).
"""
import json
from typing import Dict, Any, List, Optional
from sajha.tools.base_mcp_tool import BaseMCPTool
from .edgar_concept_map import (fetch_best_concept, filter_and_sort_records,
                                  INCOME_STATEMENT_ITEMS, BALANCE_SHEET_ITEMS, CASH_FLOW_ITEMS)
from .edgar_cik_resolver import resolve_cik


class EdgarGetMetricTool(BaseMCPTool):
    """T-03: Get a single financial metric for a company, filtered to N recent periods."""

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'edgar_get_metric',
            'description': 'Get a specific financial metric (EPS, revenue, net income, etc.) for a company from SEC XBRL filings. Returns last N quarterly or annual records. Use for: numeric analyst queries like "AAPL EPS last 4 quarters".',
            'version': '1.0.0', 'enabled': True
        }
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol (e.g. AAPL, MSFT)'},
                'metric': {'type': 'string', 'description': 'Human-readable metric name: revenue, net income, eps, eps diluted, gross profit, operating income, total assets, total debt, cash, operating cash flow, capex, r&d, etc.'},
                'periods': {'type': 'integer', 'description': 'Number of periods to return (default 4, max 20)', 'default': 4, 'minimum': 1, 'maximum': 20},
                'form_type': {'type': 'string', 'description': 'Filing type: 10-Q (quarterly), 10-K (annual), or both', 'enum': ['10-Q', '10-K', 'both'], 'default': '10-Q'},
            },
            'required': ['ticker', 'metric']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'ticker': {'type': 'string'}, 'metric': {'type': 'string'}, 'records': {'type': 'array'}}}

    # Non-US filers that use IFRS/local GAAP and don't file US-GAAP XBRL with SEC
    NON_US_XBRL_TICKERS = {
        'TD', 'RY', 'BMO', 'BNS', 'CM', 'NA', 'CWB', 'EQB',  # Canadian banks
        'HSBC', 'BARC', 'LLOY', 'NWG', 'STAN',                 # UK banks
        'SAN', 'BBVA', 'BNP', 'ACA', 'DBK', 'UBS', 'CS',       # European banks
        'MFG', 'SMFG', 'NMR',                                    # Japanese
    }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        metric = arguments.get('metric', '')
        periods = int(arguments.get('periods') or 4)
        form_type = arguments.get('form_type') or '10-Q'

        if not ticker or not metric:
            return {'success': False, 'error': 'ticker and metric are required'}

        if ticker in self.NON_US_XBRL_TICKERS:
            return {'success': False, 'error': f'{ticker} is not a US GAAP XBRL filer. Use edgar_extract_section or edgar_earnings_brief for qualitative data, or tavily_research_search for financial metrics from press releases.', 'suggestion': 'edgar_extract_section'}

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        concept, records = fetch_best_concept(cik, metric)
        if not records:
            return {'success': False, 'error': f'No XBRL data found for {ticker} metric "{metric}". Try: revenue, eps, net income, gross profit, operating income, total assets, cash, operating cash flow'}

        filtered = filter_and_sort_records(records, form_type, periods)
        result_records = [{'period_end': r.get('end'), 'period_start': r.get('start'), 'value': r.get('val'), 'fiscal_year': r.get('fy'), 'fiscal_period': r.get('fp'), 'form': r.get('form'), 'filed': r.get('filed')} for r in filtered]

        return {
            'success': True,
            'ticker': ticker, 'metric': metric, 'xbrl_concept': concept,
            'form_type': form_type, 'periods_returned': len(result_records),
            'records': result_records,
        }


class EdgarGetStatementsTool(BaseMCPTool):
    """T-04: Get a complete financial statement (income, balance sheet, cash flow) for a specific period."""

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'edgar_get_statements',
            'description': 'Get a complete financial statement (income statement, balance sheet, or cash flow statement) for a company. Returns all standard line items for a specific period. Use instead of fetching individual metrics one by one.',
            'version': '1.0.0', 'enabled': True
        }
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'statement': {'type': 'string', 'description': 'Statement type', 'enum': ['income_statement', 'balance_sheet', 'cash_flow']},
                'periods': {'type': 'integer', 'description': 'Number of periods (default 2)', 'default': 2, 'minimum': 1, 'maximum': 8},
                'form_type': {'type': 'string', 'description': '10-Q or 10-K', 'enum': ['10-Q', '10-K'], 'default': '10-Q'},
            },
            'required': ['ticker', 'statement']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'ticker': {'type': 'string'}, 'statement': {'type': 'string'}, 'line_items': {'type': 'array'}}}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        statement = arguments.get('statement', 'income_statement')
        periods = int(arguments.get('periods') or 2)
        form_type = arguments.get('form_type') or '10-Q'

        if not ticker:
            return {'success': False, 'error': 'ticker is required'}

        if ticker in EdgarGetMetricTool.NON_US_XBRL_TICKERS:
            return {'success': False, 'error': f'{ticker} is not a US GAAP XBRL filer. Use edgar_extract_section or edgar_earnings_brief instead.', 'suggestion': 'edgar_earnings_brief'}

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        items_map = {'income_statement': INCOME_STATEMENT_ITEMS, 'balance_sheet': BALANCE_SHEET_ITEMS, 'cash_flow': CASH_FLOW_ITEMS}
        items = items_map.get(statement, INCOME_STATEMENT_ITEMS)

        line_items = []
        period_set = None
        for label, metric in items:
            concept, records = fetch_best_concept(cik, metric)
            if not records:
                line_items.append({'label': label, 'xbrl_concept': None, 'values': [], 'note': 'no data'})
                continue
            filtered = filter_and_sort_records(records, form_type, periods)
            if period_set is None and filtered:
                period_set = [r.get('end') for r in filtered]
            line_items.append({
                'label': label, 'xbrl_concept': concept,
                'values': [{'period_end': r.get('end'), 'value': r.get('val'), 'fiscal_period': r.get('fp'), 'fiscal_year': r.get('fy')} for r in filtered]
            })

        return {
            'success': True,
            'ticker': ticker, 'statement': statement, 'form_type': form_type,
            'periods': period_set or [], 'line_items': line_items,
        }


class EdgarCalculateRatiosTool(BaseMCPTool):
    """T-05: Calculate derived financial ratios from XBRL data."""

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'edgar_calculate_ratios',
            'description': 'Calculate financial ratios (gross margin, operating margin, net margin, FCF, revenue growth) for a company over multiple periods. Use for margin analysis, growth trends, and ratio comparisons.',
            'version': '1.0.0', 'enabled': True
        }
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'ratios': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of ratios: gross_margin, operating_margin, net_margin, fcf, revenue_growth_yoy'},
                'periods': {'type': 'integer', 'description': 'Number of periods (default 4)', 'default': 4, 'minimum': 1, 'maximum': 12},
                'form_type': {'type': 'string', 'enum': ['10-Q', '10-K'], 'default': '10-Q'},
            },
            'required': ['ticker', 'ratios']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'ticker': {'type': 'string'}, 'ratios': {'type': 'array'}}}

    def _fetch_metric(self, cik, metric, form_type, periods):
        _, records = fetch_best_concept(cik, metric)
        filtered = filter_and_sort_records(records, form_type, periods + 4)
        return {r['end']: r['val'] for r in filtered if r.get('val') is not None}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        ratios = arguments.get('ratios', [])
        periods = int(arguments.get('periods') or 4)
        form_type = arguments.get('form_type') or '10-Q'

        if not ticker or not ratios:
            return {'success': False, 'error': 'ticker and ratios are required'}

        if ticker in EdgarGetMetricTool.NON_US_XBRL_TICKERS:
            return {'success': False, 'error': f'{ticker} is not a US GAAP XBRL filer. Use edgar_extract_section or edgar_earnings_brief instead.', 'suggestion': 'edgar_earnings_brief'}

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        rev = self._fetch_metric(cik, 'revenue', form_type, periods + 4)
        gp  = self._fetch_metric(cik, 'gross profit', form_type, periods)
        oi  = self._fetch_metric(cik, 'operating income', form_type, periods)
        ni  = self._fetch_metric(cik, 'net income', form_type, periods)
        ocf = self._fetch_metric(cik, 'operating cash flow', form_type, periods)
        cx  = self._fetch_metric(cik, 'capex', form_type, periods)

        periods_list = sorted(rev.keys(), reverse=True)[:periods]

        result_ratios = []
        for ratio in ratios:
            values = []
            for p in periods_list:
                val = None
                r = rev.get(p)
                if ratio == 'gross_margin' and r and gp.get(p) is not None:
                    val = round(gp[p] / r * 100, 2) if r != 0 else None
                elif ratio == 'operating_margin' and r and oi.get(p) is not None:
                    val = round(oi[p] / r * 100, 2) if r != 0 else None
                elif ratio == 'net_margin' and r and ni.get(p) is not None:
                    val = round(ni[p] / r * 100, 2) if r != 0 else None
                elif ratio == 'fcf' and ocf.get(p) is not None and cx.get(p) is not None:
                    val = ocf[p] - abs(cx[p])
                elif ratio == 'revenue_growth_yoy':
                    # Find same period ~1 year ago
                    import datetime
                    try:
                        dt = datetime.date.fromisoformat(p)
                        prior_year = dt.replace(year=dt.year - 1)
                        prior_keys = sorted(rev.keys())
                        prior_val = next((rev[k] for k in prior_keys if abs((datetime.date.fromisoformat(k) - prior_year).days) < 45), None)
                        if prior_val and prior_val != 0 and r is not None:
                            val = round((r - prior_val) / abs(prior_val) * 100, 2)
                    except Exception:
                        pass
                values.append({'period_end': p, 'value': val})
            result_ratios.append({'name': ratio, 'unit': '%' if 'margin' in ratio or 'growth' in ratio else 'USD', 'values': values})

        return {'success': True, 'ticker': ticker, 'form_type': form_type, 'ratios': result_ratios}


class EdgarPeerComparisonTool(BaseMCPTool):
    """T-09: Compare the same metric across multiple companies."""

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'edgar_peer_comparison',
            'description': 'Compare the same financial metric across multiple companies for the same periods. Use for competitive analysis: compare revenue, gross margin, EPS across peers.',
            'version': '1.0.0', 'enabled': True
        }
        if config: default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'tickers': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of ticker symbols (max 5)'},
                'metric': {'type': 'string', 'description': 'Metric to compare (e.g. revenue, gross profit, eps)'},
                'periods': {'type': 'integer', 'description': 'Number of periods (default 4)', 'default': 4},
                'form_type': {'type': 'string', 'enum': ['10-Q', '10-K'], 'default': '10-Q'},
            },
            'required': ['tickers', 'metric']
        }

    def get_output_schema(self) -> Dict:
        return {'type': 'object', 'properties': {'metric': {'type': 'string'}, 'companies': {'type': 'array'}}}

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        tickers = [t.upper() for t in arguments.get('tickers', [])[:5]]
        metric = arguments.get('metric', '')
        periods = int(arguments.get('periods') or 4)
        form_type = arguments.get('form_type') or '10-Q'

        if not tickers or not metric:
            return {'success': False, 'error': 'tickers and metric are required'}

        companies = []
        all_periods = set()
        for ticker in tickers:
            try:
                cik = resolve_cik(ticker)
                concept, records = fetch_best_concept(cik, metric)
                filtered = filter_and_sort_records(records, form_type, periods)
                ticker_data = {r['end']: r['val'] for r in filtered}
                all_periods.update(ticker_data.keys())
                companies.append({'ticker': ticker, 'xbrl_concept': concept, 'data': ticker_data})
            except Exception as e:
                companies.append({'ticker': ticker, 'error': str(e), 'data': {}})

        sorted_periods = sorted(all_periods, reverse=True)[:periods]
        result = []
        for c in companies:
            result.append({
                'ticker': c['ticker'],
                'xbrl_concept': c.get('xbrl_concept'),
                'error': c.get('error'),
                'values': [{'period_end': p, 'value': c['data'].get(p)} for p in sorted_periods],
            })

        return {'success': True, 'metric': metric, 'form_type': form_type, 'periods': sorted_periods, 'companies': result}
