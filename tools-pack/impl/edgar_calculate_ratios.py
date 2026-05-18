"""
EDGAR — Derived financial ratios (margins, FCF, growth) — compliant port.

Ported from sajhamcpserver/sajha/tools/impl/edgar_metric_tools.py:EdgarCalculateRatiosTool.
"""
import datetime
from typing import Dict, Any

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._edgar_helpers import (
    resolve_cik,
    fetch_best_concept,
    filter_and_sort_records,
)


class EdgarCalculateRatios(BaseMCPTool):
    """Calculate derived financial ratios from SEC XBRL data."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string', 'description': 'Stock ticker symbol'},
                'ratios': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of ratios: gross_margin, operating_margin, net_margin, fcf, revenue_growth_yoy',
                },
                'periods': {
                    'type': 'integer', 'description': 'Number of periods (default 4)',
                    'default': 4, 'minimum': 1, 'maximum': 12,
                },
                'form_type': {'type': 'string', 'enum': ['10-Q', '10-K'], 'default': '10-Q'},
            },
            'required': ['ticker', 'ratios'],
        })

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'ratios': {'type': 'array'},
            },
        }

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
                    try:
                        dt = datetime.date.fromisoformat(p)
                        prior_year = dt.replace(year=dt.year - 1)
                        prior_keys = sorted(rev.keys())
                        prior_val = next(
                            (rev[k] for k in prior_keys
                             if abs((datetime.date.fromisoformat(k) - prior_year).days) < 45),
                            None,
                        )
                        if prior_val and prior_val != 0 and r is not None:
                            val = round((r - prior_val) / abs(prior_val) * 100, 2)
                    except Exception:
                        pass
                values.append({'period_end': p, 'value': val})
            result_ratios.append({
                'name': ratio,
                'unit': '%' if ('margin' in ratio or 'growth' in ratio) else 'USD',
                'values': values,
            })

        return {'success': True, 'ticker': ticker, 'form_type': form_type, 'ratios': result_ratios}
