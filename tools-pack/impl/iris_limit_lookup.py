"""
IRIS CCR — pinpoint a specific limit record.

Ported from sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py
(`IrisLimitLookupTool`). Reads worker scope from `arguments['_worker_context']`.
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


class IrisLimitLookup(BaseMCPTool):
    """Pinpoint a limit record using the composite limit key
    (counterparty / facility / legal_entity / product)."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'date':              {'type': 'string'},
                'counterparty_code': {'type': 'string'},
                'facility_id':       {'type': 'string'},
                'legal_entity':      {'type': 'string'},
                'product':           {'type': 'string'},
                '_worker_context':   {'type': 'object'},
            },
            'required': ['counterparty_code'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'records':   {'type': 'array'},
                'count':     {'type': 'integer'},
                'date_used': {'type': 'string'},
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
        facility_id       = arguments.get('facility_id', '')
        legal_entity      = arguments.get('legal_entity', '')
        product           = arguments.get('product', '')

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
        if facility_id:
            df = df[df['Facility ID'].astype(str) == str(facility_id)]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if product:
            df = df[df['Product'].str.contains(product, case=False, na=False)]

        if df.empty:
            return {'error': True, 'error_code': 'NO_DATA',
                    'message': 'No matching limit record found'}

        results = []
        for _, row in df.iterrows():
            results.append({
                'limit_key':       make_limit_key(row),
                'limit':           clean(row.get('Product Limit')),
                'exposure':        clean(row.get('Product Exposure')),
                'headroom':        clean(row.get('Product Avail')),
                'currency':        clean(row.get('Product Limit Currency')),
                'agreement':       clean(row.get('Agreement')),
                'cust_limit':      clean(row.get('Cust Limit')),
                'conn_limit':      clean(row.get('Conn Limit')),
                'internal_rating': clean(row.get('Customer Internal Rating')),
                'date_used':       date,
            })
        return {'records': results, 'count': len(results), 'date_used': date}
