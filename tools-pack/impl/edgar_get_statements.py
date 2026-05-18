"""
EDGAR — Full financial statement (income, balance sheet, cash flow) — compliant port.

Ported from sajhamcpserver/sajha/tools/impl/edgar_metric_tools.py:EdgarGetStatementsTool.
"""
from typing import Dict, Any

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._edgar_helpers import (
    resolve_cik,
    fetch_best_concept,
    filter_and_sort_records,
    INCOME_STATEMENT_ITEMS,
    BALANCE_SHEET_ITEMS,
    CASH_FLOW_ITEMS,
)


class EdgarGetStatements(BaseMCPTool):
    """Get a complete financial statement for a company from SEC XBRL."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'statement': {
                    'type': 'string',
                    'description': 'Statement type',
                    'enum': ['income_statement', 'balance_sheet', 'cash_flow'],
                },
                'periods': {
                    'type': 'integer', 'description': 'Number of periods (default 2)',
                    'default': 2, 'minimum': 1, 'maximum': 8,
                },
                'form_type': {
                    'type': 'string',
                    'description': '10-Q or 10-K',
                    'enum': ['10-Q', '10-K'],
                    'default': '10-Q',
                },
            },
            'required': ['ticker', 'statement'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'statement': {'type': 'string'},
                'line_items': {'type': 'array'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        statement = arguments.get('statement', 'income_statement')
        periods = int(arguments.get('periods') or 2)
        form_type = arguments.get('form_type') or '10-Q'

        if not ticker:
            return {'success': False, 'error': 'ticker is required'}

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        items_map = {
            'income_statement': INCOME_STATEMENT_ITEMS,
            'balance_sheet': BALANCE_SHEET_ITEMS,
            'cash_flow': CASH_FLOW_ITEMS,
        }
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
                'values': [
                    {
                        'period_end': r.get('end'),
                        'value': r.get('val'),
                        'fiscal_period': r.get('fp'),
                        'fiscal_year': r.get('fy'),
                    }
                    for r in filtered
                ],
            })

        return {
            'success': True,
            'ticker': ticker, 'statement': statement, 'form_type': form_type,
            'periods': period_set or [], 'line_items': line_items,
        }
