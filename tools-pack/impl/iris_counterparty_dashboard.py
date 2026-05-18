"""
IRIS CCR — full counterparty dashboard.

Ported from sajhamcpserver/sajha/tools/impl/iris_ccr_tools.py
(`IrisCounterpartyDashboardTool`). Reads worker scope from
`arguments['_worker_context']`.
"""

from typing import Any, Dict

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_lib.iris_base import (
    clean_row,
    get_df,
    latest_date,
    validate_date,
    validate_legal_entity,
)


class IrisCounterpartyDashboard(BaseMCPTool):
    """Pull the full CCR picture for a counterparty across all products / limit levels."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'date':              {'type': 'string'},
                'counterparty_code': {'type': 'string'},
                'uen':               {'type': 'string'},
                'legal_entity':      {'type': 'string'},
                'product':           {'type': 'string'},
                'max_rows':          {'type': 'integer', 'default': 500, 'maximum': 5000},
                '_worker_context':   {'type': 'object'},
            },
            'required': ['counterparty_code'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'rows':             {'type': 'array'},
                'row_count':        {'type': 'integer'},
                'total_matched':    {'type': 'integer'},
                'filters_applied':  {'type': 'object'},
                'date_used':        {'type': 'string'},
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
        uen               = arguments.get('uen', '')
        legal_entity      = arguments.get('legal_entity', '')
        product           = arguments.get('product', '')
        max_rows          = int(arguments.get('max_rows', 500))

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
        df = df[df['Date'] == date]
        df = df[df['Customer Code'] == counterparty_code]
        if uen:
            df = df[df['Facility ID'].astype(str) == str(uen)]
        if legal_entity:
            df = df[df['Legal Entity'] == legal_entity]
        if product:
            df = df[df['Product'].str.contains(product, case=False, na=False)]

        total = len(df)
        df = df.head(max_rows)
        rows = [clean_row(r) for r in df.to_dict('records')]
        filters = {k: v for k, v in {'uen': uen, 'legal_entity': legal_entity, 'product': product}.items() if v}
        return {'rows': rows, 'row_count': len(rows), 'total_matched': total,
                'filters_applied': filters, 'date_used': date}
