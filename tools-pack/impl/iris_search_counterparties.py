"""
IRIS CCR — search counterparties by name, code, or UEN.

Ported from sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py
(`IrisSearchCounterpartiesTool`). Reads worker scope from
`arguments['_worker_context']`.
"""

from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.iris_base import (
    clean_row,
    get_df,
    latest_date,
    validate_date,
)


class IrisSearchCounterparties(BaseMCPTool):
    """Resolve a counterparty by name, code, or UEN/Facility ID."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'search_term':       {'type': 'string'},
                'counterparty_code': {'type': 'string'},
                'uen':               {'type': 'string'},
                'date':              {'type': 'string'},
                'limit':             {'type': 'integer', 'default': 50, 'maximum': 500},
                '_worker_context':   {'type': 'object'},
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

        search_term       = arguments.get('search_term', '')
        counterparty_code = arguments.get('counterparty_code', '')
        uen               = arguments.get('uen', '')
        date              = arguments.get('date', default_date)
        limit             = int(arguments.get('limit', 50))

        err = validate_date(ctx, date)
        if err:
            return err

        df = get_df(ctx)
        df = df[df['Date'] == date]

        if counterparty_code:
            df = df[df['Customer Code'] == counterparty_code]
        elif uen:
            df = df[df['Facility ID'].astype(str) == str(uen)]
        elif search_term:
            mask = (df['Customer Code'].str.contains(search_term, case=False, na=False) |
                    df['Customer Name'].str.contains(search_term, case=False, na=False))
            df = df[mask]
        else:
            return {'error': True, 'error_code': 'MISSING_PARAM',
                    'message': 'Provide at least one of: search_term, counterparty_code, uen'}

        cols = ['Customer Code', 'Customer Name', 'Customer Internal Rating',
                'Legal Entity', 'Facility ID', 'Country', 'Country Rating', 'Connection Code']
        df = df[cols].drop_duplicates().head(limit)
        results = [clean_row(r) for r in df.to_dict('records')]
        return {'counterparties': results, 'count': len(results), 'date_used': date}
