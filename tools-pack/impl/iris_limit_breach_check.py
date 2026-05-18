"""
IRIS CCR — check whether a counterparty breaches any limits on a given date.

Ported from sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py
(`IrisLimitBreachCheckTool`). Reads worker scope from
`arguments['_worker_context']`.
"""

import math
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.iris_base import (
    clean,
    get_df,
    latest_date,
    make_limit_key,
    validate_date,
    validate_legal_entity,
)


class IrisLimitBreachCheck(BaseMCPTool):
    """Check breaches for a single counterparty across product/customer/connection levels."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'date':              {'type': 'string'},
                'counterparty_code': {'type': 'string'},
                'legal_entity':      {'type': 'string'},
                'product':           {'type': 'string'},
                'level':             {'type': 'string', 'enum': ['product', 'customer', 'connection']},
                '_worker_context':   {'type': 'object'},
            },
            'required': ['counterparty_code'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'breaches':     {'type': 'array'},
                'breach_count': {'type': 'integer'},
                'date_used':    {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ctx = arguments.get('_worker_context') or {}
        try:
            default_date = latest_date(ctx)
        except FileNotFoundError as exc:
            return {'error': True, 'error_code': 'NO_DATA', 'message': str(exc)}

        date              = arguments.get('date', default_date)
        counterparty_code = arguments.get('counterparty_code', '')
        legal_entity      = arguments.get('legal_entity', '')
        product           = arguments.get('product', '')
        level             = arguments.get('level', '')

        if not counterparty_code:
            return {'error': True, 'error_code': 'MISSING_PARAM',
                    'message': 'counterparty_code is required'}
        err = validate_date(ctx, date)
        if err:
            return err
        err = validate_legal_entity(legal_entity)
        if err:
            return err

        df = get_df(ctx)
        df = df[(df['Date'] == date) & (df['Customer Code'] == counterparty_code)]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if product:
            df = df[df['Product'].str.contains(product, case=False, na=False)]

        breaches = []
        check_levels = [level] if level else ['product', 'customer', 'connection']

        for _, row in df.iterrows():
            lk = make_limit_key(row)
            if 'product' in check_levels:
                lim = row.get('Product Limit')
                exp = row.get('Product Exposure')
                if lim is not None and exp is not None and not math.isnan(float(lim)) and not math.isnan(float(exp)):
                    if float(exp) > float(lim):
                        overage = float(exp) - float(lim)
                        breaches.append({
                            'limit_key': lk, 'counterparty': counterparty_code,
                            'product': clean(row.get('Product')), 'level': 'product',
                            'limit': float(lim), 'exposure': float(exp),
                            'overage': overage, 'overage_pct': round(overage / float(lim) * 100, 2),
                            'date_used': date,
                        })
            if 'customer' in check_levels:
                lim = row.get('Cust Limit')
                exp = row.get('Cust Exposure')
                if lim is not None and exp is not None and not math.isnan(float(lim)) and not math.isnan(float(exp)):
                    if float(exp) > float(lim):
                        overage = float(exp) - float(lim)
                        breaches.append({
                            'limit_key': lk, 'counterparty': counterparty_code,
                            'product': clean(row.get('Product')), 'level': 'customer',
                            'limit': float(lim), 'exposure': float(exp),
                            'overage': overage, 'overage_pct': round(overage / float(lim) * 100, 2),
                            'date_used': date,
                        })
            if 'connection' in check_levels:
                lim = row.get('Conn Limit')
                exp = row.get('Conn Exposure')
                if lim is not None and exp is not None and not math.isnan(float(lim)) and not math.isnan(float(exp)):
                    if float(exp) > float(lim):
                        overage = float(exp) - float(lim)
                        breaches.append({
                            'limit_key': lk, 'counterparty': counterparty_code,
                            'product': clean(row.get('Product')), 'level': 'connection',
                            'limit': float(lim), 'exposure': float(exp),
                            'overage': overage, 'overage_pct': round(overage / float(lim) * 100, 2),
                            'date_used': date,
                        })

        return {'breaches': breaches, 'breach_count': len(breaches), 'date_used': date}
