"""
IRIS CCR — portfolio-wide breach scan.

Ported from sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py
(`IrisPortfolioBreachScanTool`). Reads worker scope from
`arguments['_worker_context']`.
"""

import math
from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.iris_base import (
    clean,
    get_df,
    make_limit_key,
    validate_date,
    validate_legal_entity,
)


class IrisPortfolioBreachScan(BaseMCPTool):
    """Return ALL limit records in breach across the book on a given date.

    `min_overage` is REQUIRED to prevent full-book dumps.
    """

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'date':            {'type': 'string'},
                'min_overage':     {'type': 'number'},
                'legal_entity':    {'type': 'string'},
                'country':         {'type': 'string'},
                'internal_rating': {'type': 'integer'},
                'level':           {'type': 'string', 'enum': ['product', 'customer', 'connection']},
                '_worker_context': {'type': 'object'},
            },
            'required': ['date', 'min_overage'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'breaches':       {'type': 'array'},
                'total_breaches': {'type': 'integer'},
                'total_overage':  {'type': 'number'},
                'date_used':      {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ctx = arguments.get('_worker_context') or {}

        date            = arguments.get('date', '')
        min_overage     = arguments.get('min_overage', None)
        legal_entity    = arguments.get('legal_entity', '')
        country         = arguments.get('country', '')
        internal_rating = arguments.get('internal_rating', None)
        level           = arguments.get('level', '')

        if not date:
            return {'error': True, 'error_code': 'MISSING_PARAM', 'message': 'date is required'}
        if min_overage is None:
            return {'error': True, 'error_code': 'MISSING_PARAM',
                    'message': 'min_overage is required. Specify a threshold (e.g. 1000000) to prevent full-book dumps.'}

        err = validate_date(ctx, date)
        if err:
            return err
        err = validate_legal_entity(legal_entity)
        if err:
            return err

        df = get_df(ctx)
        df = df[df['Date'] == date]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if country:
            df = df[df['Country'].str.contains(country, case=False, na=False)]
        if internal_rating is not None:
            df = df[df['Customer Internal Rating'] <= int(internal_rating)]

        min_overage = float(min_overage)
        check_levels = [level] if level else ['product', 'customer', 'connection']
        limit_map = {
            'product':    ('Product Limit', 'Product Exposure'),
            'customer':   ('Cust Limit',    'Cust Exposure'),
            'connection': ('Conn Limit',    'Conn Exposure'),
        }

        breaches = []
        for _, row in df.iterrows():
            lk = make_limit_key(row)
            for lvl in check_levels:
                lim_col, exp_col = limit_map[lvl]
                lim = row.get(lim_col)
                exp = row.get(exp_col)
                if lim is None or exp is None:
                    continue
                try:
                    lim, exp = float(lim), float(exp)
                except (ValueError, TypeError):
                    continue
                if math.isnan(lim) or math.isnan(exp):
                    continue
                if exp > lim:
                    overage = exp - lim
                    if overage >= min_overage:
                        breaches.append({
                            'limit_key':         lk,
                            'counterparty':      clean(row.get('Customer Code')),
                            'counterparty_name': clean(row.get('Customer Name')),
                            'rating':            clean(row.get('Customer Internal Rating')),
                            'country':           clean(row.get('Country')),
                            'legal_entity':      clean(row.get('Legal Entity')),
                            'product':           clean(row.get('Product')),
                            'level':             lvl,
                            'limit':             lim,
                            'exposure':          exp,
                            'overage':           overage,
                            'overage_pct':       round(overage / lim * 100, 2),
                            'date_used':         date,
                        })

        total_overage = sum(b['overage'] for b in breaches)
        return {'breaches': breaches, 'total_breaches': len(breaches),
                'total_overage': total_overage, 'date_used': date}
