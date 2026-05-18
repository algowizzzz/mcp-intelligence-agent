"""
EDGAR — Single financial metric (revenue, EPS, etc.) from SEC XBRL — compliant port.

Ported from sajhamcpserver/sajha/tools/impl/edgar_metric_tools.py:EdgarGetMetricTool.
"""
from typing import Dict, Any

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._edgar_helpers import (
    resolve_cik,
    fetch_best_concept,
    filter_and_sort_records,
)


class EdgarGetMetric(BaseMCPTool):
    """Get a single financial metric for a company from SEC XBRL data."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'metric': {
                    'type': 'string',
                    'description': 'Human-readable metric name: revenue, net income, eps, etc.',
                },
                'periods': {
                    'type': 'integer', 'description': 'Number of periods (default 4, max 20)',
                    'default': 4, 'minimum': 1, 'maximum': 20,
                },
                'form_type': {
                    'type': 'string',
                    'description': '10-Q, 10-K, or both',
                    'enum': ['10-Q', '10-K', 'both'],
                    'default': '10-Q',
                },
            },
            'required': ['ticker', 'metric'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'metric': {'type': 'string'},
                'records': {'type': 'array'},
            },
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments.get('ticker', '').upper()
        metric = arguments.get('metric', '')
        periods = int(arguments.get('periods') or 4)
        form_type = arguments.get('form_type') or '10-Q'

        if not ticker or not metric:
            return {'success': False, 'error': 'ticker and metric are required'}

        try:
            cik = resolve_cik(ticker)
        except ValueError as e:
            return {'success': False, 'error': str(e)}

        concept, records = fetch_best_concept(cik, metric)
        if not records:
            return {
                'success': False,
                'error': (
                    f'No XBRL data found for {ticker} metric "{metric}". '
                    f'Try: revenue, eps, net income, gross profit, operating income, '
                    f'total assets, cash, operating cash flow'
                ),
            }

        filtered = filter_and_sort_records(records, form_type, periods)
        result_records = [
            {
                'period_end': r.get('end'),
                'period_start': r.get('start'),
                'value': r.get('val'),
                'fiscal_year': r.get('fy'),
                'fiscal_period': r.get('fp'),
                'form': r.get('form'),
                'filed': r.get('filed'),
            }
            for r in filtered
        ]

        return {
            'success': True,
            'ticker': ticker, 'metric': metric, 'xbrl_concept': concept,
            'form_type': form_type, 'periods_returned': len(result_records),
            'records': result_records,
        }
