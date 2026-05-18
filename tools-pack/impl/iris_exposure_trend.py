"""
IRIS CCR — exposure trend for a counterparty across snapshot dates.

Ported from sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py
(`IrisExposureTrendTool`). Reads worker scope from
`arguments['_worker_context']`.
"""

from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.iris_base import (
    clean,
    get_df,
    latest_date,
    make_limit_key,
)


class IrisExposureTrend(BaseMCPTool):
    """Track exposure changes for a counterparty across multiple snapshot dates.

    Queries each snapshot date independently — never interpolates.
    """

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'date_from':         {'type': 'string'},
                'date_to':           {'type': 'string'},
                'counterparty_code': {'type': 'string'},
                'legal_entity':      {'type': 'string'},
                'product':           {'type': 'string'},
                'level':             {'type': 'string', 'enum': ['product', 'customer', 'connection'], 'default': 'product'},
                '_worker_context':   {'type': 'object'},
            },
            'required': ['date_from', 'counterparty_code'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'trend':                 {'type': 'array'},
                'delta_first_to_last':   {'type': 'number'},
                'date_count':            {'type': 'integer'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ctx = arguments.get('_worker_context') or {}
        try:
            default_date_to = latest_date(ctx)
        except FileNotFoundError as exc:
            return {'error': True, 'error_code': 'NO_DATA', 'message': str(exc)}

        date_from         = arguments.get('date_from', '')
        date_to           = arguments.get('date_to', default_date_to)
        counterparty_code = arguments.get('counterparty_code', '')
        legal_entity      = arguments.get('legal_entity', '')
        product           = arguments.get('product', '')
        level             = arguments.get('level', 'product')

        if not counterparty_code:
            return {'error': True, 'error_code': 'MISSING_PARAM',
                    'message': 'counterparty_code is required'}
        if not date_from:
            return {'error': True, 'error_code': 'MISSING_PARAM',
                    'message': 'date_from is required'}

        df = get_df(ctx)
        dates_in_range = sorted([d for d in df['Date'].unique() if date_from <= d <= date_to])

        if not dates_in_range:
            return {'error': True, 'error_code': 'NO_DATA',
                    'message': 'No dates found in specified range'}

        exp_col = {'product': 'Product Exposure', 'customer': 'Cust Exposure',
                   'connection': 'Conn Exposure'}.get(level, 'Product Exposure')
        lim_col = {'product': 'Product Limit', 'customer': 'Cust Limit',
                   'connection': 'Conn Limit'}.get(level, 'Product Limit')

        trend = []
        for d in dates_in_range:
            sub = df[(df['Date'] == d) & (df['Customer Code'] == counterparty_code)]
            if legal_entity:
                sub = sub[sub['Legal Entity'] == legal_entity]
            if product:
                sub = sub[sub['Product'].str.contains(product, case=False, na=False)]
            for _, row in sub.iterrows():
                exp = clean(row.get(exp_col))
                lim = clean(row.get(lim_col))
                headroom = (float(lim) - float(exp)) if (lim is not None and exp is not None) else None
                trend.append({
                    'date': d, 'limit_key': make_limit_key(row),
                    'exposure': exp, 'limit': lim, 'headroom': headroom,
                })

        delta = None
        if len(trend) >= 2 and trend[0]['exposure'] is not None and trend[-1]['exposure'] is not None:
            delta = float(trend[-1]['exposure']) - float(trend[0]['exposure'])

        return {'trend': trend, 'delta_first_to_last': delta, 'date_count': len(dates_in_range)}
