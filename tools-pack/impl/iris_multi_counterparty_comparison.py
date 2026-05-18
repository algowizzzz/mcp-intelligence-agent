"""
IRIS CCR — compare two or more counterparties side by side.

Ported from sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py
(`IrisMultiCounterpartyComparisonTool`). Reads worker scope from
`arguments['_worker_context']`.
"""

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


class IrisMultiCounterpartyComparison(BaseMCPTool):
    """Compare 2+ counterparties on limits/exposure/headroom; optional group_by pivot."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'date':                {'type': 'string'},
                'counterparty_codes':  {'type': 'array', 'items': {'type': 'string'}},
                'legal_entity':        {'type': 'string'},
                'product':             {'type': 'string'},
                'group_by':            {'type': 'string',
                                        'enum': ['rating', 'country', 'legal_entity', 'product']},
                '_worker_context':     {'type': 'object'},
            },
            'required': ['counterparty_codes'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'comparison': {'type': 'array'},
                'count':      {'type': 'integer'},
                'date_used':  {'type': 'string'},
                'group_by':   {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ctx = arguments.get('_worker_context') or {}
        try:
            default_date = latest_date(ctx)
        except FileNotFoundError as exc:
            return {'error': True, 'error_code': 'NO_DATA', 'message': str(exc)}

        date                = arguments.get('date', default_date)
        counterparty_codes  = arguments.get('counterparty_codes', [])
        legal_entity        = arguments.get('legal_entity', '')
        product             = arguments.get('product', '')
        group_by            = arguments.get('group_by', '')

        if not counterparty_codes or len(counterparty_codes) < 2:
            return {'error': True, 'error_code': 'MISSING_PARAM',
                    'message': 'counterparty_codes must be a list with 2+ entries'}
        err = validate_date(ctx, date)
        if err:
            return err
        err = validate_legal_entity(legal_entity)
        if err:
            return err

        df = get_df(ctx)
        df = df[(df['Date'] == date) & (df['Customer Code'].isin(counterparty_codes))]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if product:
            df = df[df['Product'].str.contains(product, case=False, na=False)]

        comparison = []
        for _, row in df.iterrows():
            lim = clean(row.get('Product Limit'))
            exp = clean(row.get('Product Exposure'))
            util = (round(float(exp) / float(lim) * 100, 2)
                    if (lim and exp and float(lim) > 0) else None)
            comparison.append({
                'limit_key':         make_limit_key(row),
                'counterparty':      clean(row.get('Customer Code')),
                'counterparty_name': clean(row.get('Customer Name')),
                'rating':            clean(row.get('Customer Internal Rating')),
                'country':           clean(row.get('Country')),
                'product':           clean(row.get('Product')),
                'legal_entity':      clean(row.get('Legal Entity')),
                'limit':             lim,
                'exposure':          exp,
                'headroom':          clean(row.get('Product Avail')),
                'utilization_pct':   util,
            })

        return {'comparison': comparison, 'count': len(comparison),
                'date_used': date, 'group_by': group_by}
