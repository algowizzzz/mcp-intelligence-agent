"""
IRIS CCR — portfolio-wide rating screen.

Ported from sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py
(`IrisRatingScreenTool`). Reads worker scope from `arguments['_worker_context']`.
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


class IrisRatingScreen(BaseMCPTool):
    """Portfolio-wide screen — filter counterparties by rating band, country, exposure."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'date':            {'type': 'string'},
                'min_rating':      {'type': 'integer'},
                'max_rating':      {'type': 'integer'},
                'country_rating':  {'type': 'string'},
                'legal_entity':    {'type': 'string'},
                'country':         {'type': 'string'},
                'min_exposure':    {'type': 'number'},
                '_worker_context': {'type': 'object'},
            },
            'required': [],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'counterparties': {'type': 'array'},
                'count':          {'type': 'integer'},
                'date_used':      {'type': 'string'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ctx = arguments.get('_worker_context') or {}
        try:
            default_date = latest_date(ctx)
        except FileNotFoundError as exc:
            return {'error': True, 'error_code': 'NO_DATA', 'message': str(exc)}

        date           = arguments.get('date', default_date)
        min_rating     = arguments.get('min_rating', None)
        max_rating     = arguments.get('max_rating', None)
        country_rating = arguments.get('country_rating', '')
        legal_entity   = arguments.get('legal_entity', '')
        country        = arguments.get('country', '')
        min_exposure   = arguments.get('min_exposure', None)

        err = validate_date(ctx, date)
        if err:
            return err
        err = validate_legal_entity(legal_entity)
        if err:
            return err

        df = get_df(ctx)
        df = df[df['Date'] == date]
        if min_rating is not None:
            df = df[df['Customer Internal Rating'] >= int(min_rating)]
        if max_rating is not None:
            df = df[df['Customer Internal Rating'] <= int(max_rating)]
        if country_rating:
            df = df[df['Country Rating'] == country_rating]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if country:
            df = df[df['Country'].str.contains(country, case=False, na=False)]
        if min_exposure is not None:
            df = df[df['Product Exposure'] >= float(min_exposure)]

        cols = ['Customer Code', 'Customer Name', 'Customer Internal Rating', 'Country',
                'Country Rating', 'Legal Entity', 'Product', 'Facility ID',
                'Product Exposure', 'Product Avail']
        df = df[cols].drop_duplicates()

        results = []
        for _, row in df.iterrows():
            results.append({
                'limit_key':      make_limit_key(row),
                'name':           clean(row.get('Customer Name')),
                'code':           clean(row.get('Customer Code')),
                'rating':         clean(row.get('Customer Internal Rating')),
                'country':        clean(row.get('Country')),
                'country_rating': clean(row.get('Country Rating')),
                'legal_entity':   clean(row.get('Legal Entity')),
                'product':        clean(row.get('Product')),
                'exposure':       clean(row.get('Product Exposure')),
                'headroom':       clean(row.get('Product Avail')),
            })

        return {'counterparties': results, 'count': len(results), 'date_used': date}
