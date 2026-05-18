"""
data_transform — compliant with upstream SAJHA.

Ported from sajhamcpserver/sajha/tools/impl/data_transform_tools.py
(DataTransformTool). Worker scope from arguments['_worker_context'].
"""

import logging
from typing import Any, Dict, List

from sajha.tools.base_mcp_tool import BaseMCPTool

from tools_pack_impl._operational_base import get_roots, safe_path, find_file
from tools_pack_impl.parquet_read import _load_df, _rows_to_list

logger = logging.getLogger(__name__)


SUPPORTED_AGG = {'sum', 'mean', 'median', 'min', 'max', 'count', 'count_distinct', 'std', 'first', 'last'}


class DataTransform(BaseMCPTool):
    """Filter / group / pivot / sort a CSV or Parquet file using declarative parameters."""

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {
            'type': 'object',
            'properties': {
                'file_path':      {'type': 'string'},
                'filters':        {'type': 'array'},
                'group_by':       {'type': 'array', 'items': {'type': 'string'}},
                'aggregations':   {'type': 'object'},
                'pivot':          {'type': 'object'},
                'sort':           {'type': 'array'},
                'limit':          {'type': 'integer'},
                'output_columns': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['file_path'],
        })

    def get_output_schema(self) -> Dict:
        return {'type': 'object'}

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        file_path = arguments.get('file_path', '')
        filters = arguments.get('filters') or []
        group_by = arguments.get('group_by') or []
        aggregations = arguments.get('aggregations') or {}
        pivot = arguments.get('pivot') or {}
        sort = arguments.get('sort') or []
        limit = min(int(arguments.get('limit', 500)), 5000)
        output_columns = arguments.get('output_columns') or []

        if group_by and pivot:
            return {'error': 'group_by and pivot are mutually exclusive.'}
        if group_by and not aggregations:
            return {'error': 'aggregations required when group_by is specified.'}

        domain, my_data, common = get_roots(arguments)
        safe = safe_path(file_path, domain, my_data, common)
        if not safe or not safe.exists():
            safe = find_file(file_path, domain, my_data, common)
        if not safe or not safe.exists():
            return {'error': f'File not found or access denied: {file_path}'}

        try:
            df, _ = _load_df(str(safe))
        except ValueError as exc:
            return {'error': str(exc)}
        except Exception as exc:
            return {'error': f'Could not read file: {exc}'}

        source_rows = len(df)

        # Filters
        for f in filters:
            col = f.get('column', '')
            op = f.get('operator', '')
            val = f.get('value')
            if col not in df.columns:
                return {'error': f"Column '{col}' not found. Available: {list(df.columns)}"}
            try:
                if op == '==':
                    df = df[df[col] == val]
                elif op == '!=':
                    df = df[df[col] != val]
                elif op == '>':
                    df = df[df[col] > val]
                elif op == '>=':
                    df = df[df[col] >= val]
                elif op == '<':
                    df = df[df[col] < val]
                elif op == '<=':
                    df = df[df[col] <= val]
                elif op == 'in':
                    df = df[df[col].isin(val)]
                elif op == 'not_in':
                    df = df[~df[col].isin(val)]
                elif op == 'contains':
                    df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
                elif op == 'not_null':
                    df = df[df[col].notna()]
                elif op == 'is_null':
                    df = df[df[col].isna()]
                else:
                    return {'error': f"Unknown operator: '{op}'"}
            except TypeError as exc:
                return {'error': f"Cannot apply '{op}' to column '{col}': {exc}"}

        rows_after_filter = len(df)
        operation = 'filter'

        if group_by:
            operation = 'group_by'
            missing_cols = [c for c in group_by if c not in df.columns]
            if missing_cols:
                return {'error': f'group_by columns not found: {missing_cols}'}
            agg_map = {}
            for col, func in aggregations.items():
                if func not in SUPPORTED_AGG:
                    return {'error': f"Unsupported aggregation '{func}'. Supported: {sorted(SUPPORTED_AGG)}"}
                if col not in df.columns:
                    return {'error': f"Aggregation column '{col}' not found"}
                agg_map[col] = 'nunique' if func == 'count_distinct' else func
            try:
                df = df.groupby(group_by).agg(agg_map).reset_index()
                rename = {}
                for col, func in aggregations.items():
                    new_name = f"{col}_{func}"
                    if col in df.columns and new_name != col:
                        rename[col] = new_name
                df = df.rename(columns=rename)
            except TypeError as exc:
                return {'error': f'Aggregation error: {exc}'}

        elif pivot:
            operation = 'pivot'
            idx = pivot.get('index')
            cols = pivot.get('columns')
            vals = pivot.get('values')
            aggfunc = pivot.get('aggfunc', 'sum')
            fill_value = pivot.get('fill_value', None)
            if cols and cols in df.columns:
                n_unique = df[cols].nunique()
                if n_unique > 50:
                    return {'error': f"Pivot would produce >50 columns (found {n_unique})."}
            try:
                pivot_df = df.pivot_table(
                    index=idx, columns=cols, values=vals,
                    aggfunc=aggfunc, fill_value=fill_value,
                )
                pivot_df.columns = [f"{vals}_{c}" for c in pivot_df.columns]
                df = pivot_df.reset_index()
            except Exception as exc:
                return {'error': f'Pivot error: {exc}'}

        if sort:
            sort_cols = []
            ascending = []
            for s in sort:
                col = s.get('column', '')
                if col in df.columns:
                    sort_cols.append(col)
                    ascending.append(s.get('direction', 'asc').lower() != 'desc')
            if sort_cols:
                df = df.sort_values(sort_cols, ascending=ascending)

        if output_columns:
            valid = [c for c in output_columns if c in df.columns]
            df = df[valid]

        truncated = len(df) > limit
        result_df = df.head(limit)

        return {
            'operation':         operation,
            'source_file':       safe.name,
            'source_rows':       source_rows,
            'filters_applied':   len(filters),
            'rows_after_filter': rows_after_filter,
            'result_rows':       len(result_df),
            'truncated':         truncated,
            'columns':           list(result_df.columns),
            'data':              _rows_to_list(result_df, limit),
            '_source':           str(safe),
        }
