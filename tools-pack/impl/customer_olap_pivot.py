"""
customer_olap_pivot — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/duckdb_olap_advanced.py
(CustomerOLAPTool).

The original tool joined customers.csv / orders.csv / products.csv via
read_csv_auto() and applied a fixed-dimension/measure semantic layer. We
preserve the same DIMENSIONS/MEASURES dictionaries; the only change is that
the data root comes from the worker context's `domain_data_path/duckdb`
subfolder instead of a globally-configured PropertiesConfigurator value.
"""

import logging
import os
import time
from typing import Any, Dict, List

import duckdb

from sajha.tools.base_mcp_tool import BaseMCPTool

logger = logging.getLogger(__name__)


# Mirror the original — keep in sync with sajhamcpserver/...duckdb_olap_advanced.py
DIMENSIONS: Dict[str, str] = {
    "customer_segment":     "customers.customer_segment",
    "customer_tier":        "customers.customer_tier",
    "region":               "customers.region",
    "country":              "customers.country",
    "acquisition_channel":  "customers.acquisition_channel",
    "age_group":            "customers.age_group",
    "product_category":     "orders.product_category",
    "product_name":         "orders.product_name",
    "payment_method":       "orders.payment_method",
    "sales_rep":            "orders.sales_rep",
    "order_date":           "orders.order_date",
    "signup_date":          "customers.signup_date",
    "order_year":           "EXTRACT(YEAR FROM orders.order_date::DATE)",
    "order_month":          "EXTRACT(MONTH FROM orders.order_date::DATE)",
    "order_quarter":        "CONCAT('Q', EXTRACT(QUARTER FROM orders.order_date::DATE))",
}

MEASURES: Dict[str, str] = {
    "order_count":     "COUNT(DISTINCT orders.order_id)",
    "customer_count":  "COUNT(DISTINCT customers.customer_id)",
    "total_revenue":   "COALESCE(SUM(orders.quantity * orders.unit_price * (1 - orders.discount_pct/100.0)), 0)",
    "total_quantity":  "COALESCE(SUM(orders.quantity), 0)",
    "avg_order_value": "COALESCE(AVG(orders.quantity * orders.unit_price * (1 - orders.discount_pct/100.0)), 0)",
    "total_discount":  "COALESCE(SUM(orders.quantity * orders.unit_price * orders.discount_pct/100.0), 0)",
    "total_shipping":  "COALESCE(SUM(orders.shipping_cost), 0)",
    "avg_discount_pct": "COALESCE(AVG(orders.discount_pct), 0)",
    "gross_profit":    "COALESCE(SUM((orders.unit_price - COALESCE(products.unit_cost, 0)) * orders.quantity * (1 - orders.discount_pct/100.0)), 0)",
    "profit_margin":   "COALESCE(AVG((orders.unit_price - COALESCE(products.unit_cost, 0)) / NULLIF(orders.unit_price, 0) * 100), 0)",
}


def _duckdb_root(ctx: Dict[str, str]) -> str:
    """Return worker-scoped `<domain_data>/duckdb` directory if present."""
    domain = (ctx.get('domain_data_path') or '').rstrip('/')
    if not domain:
        return ''
    candidate = os.path.join(domain, 'duckdb')
    return candidate if os.path.isdir(candidate) else domain


def _normalise_list(value, default=None) -> List:
    """Convert string/comma-separated string/list-of-str into a list."""
    if value is None:
        return default or []
    if isinstance(value, list):
        if len(value) == 1 and isinstance(value[0], str) and ',' in value[0]:
            return [item.strip() for item in value[0].split(',')]
        return value
    if isinstance(value, str):
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        return [value.strip()] if value.strip() else (default or [])
    return default or []


def _build_filter_clause(filters: Dict) -> str:
    if not filters:
        return ''
    conditions = []
    for key, value in filters.items():
        if key not in DIMENSIONS:
            continue
        col = DIMENSIONS[key]
        if isinstance(value, list):
            values_str = ", ".join(
                f"'{v}'" if isinstance(v, str) else str(v) for v in value
            )
            conditions.append(f"{col} IN ({values_str})")
        elif isinstance(value, str):
            conditions.append(f"{col} = '{value}'")
        else:
            conditions.append(f"{col} = {value}")
    return "WHERE " + " AND ".join(conditions) if conditions else ''


class CustomerOlapPivot(BaseMCPTool):
    """Customer-OLAP pivot over customers/orders/products CSVs (joins all three)."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'rows':     {'type': 'array', 'items': {'type': 'string'}},
                'columns':  {'type': 'array', 'items': {'type': 'string'}},
                'measures': {'type': 'array', 'items': {'type': 'string'}},
                'filters':  {'type': 'object'},
                'order_by': {'type': 'string'},
                'limit':    {'type': 'integer', 'default': 100},
            },
            'required': ['rows', 'measures'],
        })

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {
            'type': 'object',
            'properties': {
                'success':          {'type': 'boolean'},
                'columns':          {'type': 'array'},
                'data':             {'type': 'array'},
                'row_count':        {'type': 'integer'},
                'query':            {'type': 'string'},
                'execution_time_ms': {'type': 'number'},
            },
        })

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()

        rows = _normalise_list(arguments.get('rows'), [])
        columns = _normalise_list(arguments.get('columns'), [])
        measures = _normalise_list(arguments.get('measures'), ['total_revenue'])
        filters = arguments.get('filters') or {}
        order_by = arguments.get('order_by')
        limit = int(arguments.get('limit', 100))

        if not rows:
            return {
                'success': False,
                'error':   "At least one row dimension is required. Available: " + ", ".join(DIMENSIONS.keys()),
            }

        all_dims = list(rows) + list(columns)
        for dim in all_dims:
            if dim not in DIMENSIONS:
                return {
                    'success': False,
                    'error':   f"Unknown dimension: {dim}. Available: {list(DIMENSIONS.keys())}",
                }
        for m in measures:
            if m not in MEASURES:
                return {
                    'success': False,
                    'error':   f"Unknown measure: {m}. Available: {list(MEASURES.keys())}",
                }

        ctx = arguments.get('_worker_context') or {}
        root = _duckdb_root(ctx)
        if not root:
            return {
                'success': False,
                'error':   'No domain_data_path on the worker context; cannot locate customers/orders/products CSVs.',
            }

        c_path = os.path.join(root, 'customers.csv')
        o_path = os.path.join(root, 'orders.csv')
        p_path = os.path.join(root, 'products.csv')
        for fp in (c_path, o_path, p_path):
            if not os.path.isfile(fp):
                return {
                    'success': False,
                    'error':   f"Required CSV not found: {fp}",
                }

        # Build query
        select_parts = []
        for dim in all_dims:
            select_parts.append(f"{DIMENSIONS[dim]} AS {dim}")
        for m in measures:
            select_parts.append(f"{MEASURES[m]} AS {m}")

        group_by_parts = [DIMENSIONS[d] for d in all_dims]

        select_clause = ", ".join(select_parts)
        base_query = f"""
        FROM read_csv_auto('{c_path}') AS customers
        LEFT JOIN read_csv_auto('{o_path}') AS orders
            ON customers.customer_id = orders.customer_id
        LEFT JOIN read_csv_auto('{p_path}') AS products
            ON orders.product_name = products.product_name
        """
        filter_clause = _build_filter_clause(filters)
        group_by_clause = f"GROUP BY {', '.join(group_by_parts)}" if group_by_parts else ''

        if order_by:
            if order_by.startswith('-'):
                order_clause = f"ORDER BY {order_by[1:]} DESC"
            else:
                order_clause = f"ORDER BY {order_by} ASC"
        elif measures:
            order_clause = f"ORDER BY {measures[0]} DESC"
        else:
            order_clause = ''

        query = f"""
        SELECT {select_clause}
        {base_query}
        {filter_clause}
        {group_by_clause}
        {order_clause}
        LIMIT {limit}
        """

        conn = duckdb.connect(':memory:')
        try:
            result = conn.execute(query)
            result_columns = [desc[0] for desc in result.description]
            rows_data = result.fetchall()

            data: List[Dict[str, Any]] = []
            for row in rows_data:
                row_dict: Dict[str, Any] = {}
                for i, col in enumerate(result_columns):
                    val = row[i]
                    row_dict[col] = round(val, 2) if isinstance(val, float) else val
                data.append(row_dict)

            execution_ms = (time.time() - start) * 1000

            return {
                'success':            True,
                'columns':            result_columns,
                'data':               data,
                'row_count':          len(data),
                'query':              query.strip(),
                'execution_time_ms':  round(execution_ms, 2),
                'available_dimensions': list(DIMENSIONS.keys()),
                'available_measures':   list(MEASURES.keys()),
                '_source':              root,
            }
        except Exception as exc:
            logger.error("customer_olap_pivot failed: %s", exc)
            return {'success': False, 'error': str(exc), '_source': root}
        finally:
            conn.close()
