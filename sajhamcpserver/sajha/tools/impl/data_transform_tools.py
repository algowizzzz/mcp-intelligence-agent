"""
Data Transform & Parquet Tools — parquet_read, data_transform, data_export
"""
import os, re, shutil
from datetime import datetime, timezone
from pathlib import Path
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator


def _resolve(path_str):
    p = Path(path_str)
    if p.is_absolute():
        return p.resolve()
    return (Path.cwd() / p).resolve()

def _domain_root():
    v = PropertiesConfigurator().get('data.domain_data.dir', './data/domain_data')
    return _resolve(v)

def _my_data_root():
    v = PropertiesConfigurator().get('data.my_data.dir', './data/uploads')
    return _resolve(v)

def _safe_path(path_str):
    try:
        p = Path(path_str).resolve()
    except Exception:
        return None
    for root in (_domain_root(), _my_data_root()):
        try:
            p.relative_to(root)
            return p
        except ValueError:
            pass
    return None

def _pq_to_df(path):
    """Read parquet avoiding pandas extension type conflicts."""
    import pyarrow.parquet as pq_mod
    import pandas as pd
    table = pq_mod.read_table(str(path))
    # Convert column by column to basic pandas types to avoid extension conflicts
    data = {}
    for i, col in enumerate(table.schema.names):
        arr = table.column(i)
        try:
            data[col] = arr.to_pylist()
        except Exception:
            data[col] = [None] * len(arr)
    return pd.DataFrame(data)

def _df_to_pq(df, path, compression='snappy'):
    """Write parquet avoiding pandas extension type conflicts."""
    import pyarrow as pa, pyarrow.parquet as pq_mod
    arrays, fields = [], []
    for col in df.columns:
        vals = df[col].tolist()
        try:
            arr = pa.array(vals)
        except Exception:
            arr = pa.array([str(v) if v is not None else None for v in vals], type=pa.string())
        arrays.append(arr)
        fields.append(pa.field(str(col), arr.type))
    table = pa.table(arrays, schema=pa.schema(fields))
    pq_mod.write_table(table, str(path), compression=compression)

def _load_df(file_path):
    import pandas as pd
    ext = Path(file_path).suffix.lower()
    if ext in ('.parquet', '.pq'):
        return _pq_to_df(file_path), 'parquet'
    if ext in ('.csv',):
        return pd.read_csv(str(file_path), sep=None, engine='python'), 'csv'
    if ext in ('.tsv',):
        return pd.read_csv(str(file_path), sep='\t'), 'tsv'
    raise ValueError(f"Unsupported extension: {ext}")

def _df_schema(df):
    schema = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        nullable = bool(df[col].isna().any())
        schema.append({'column': col, 'dtype': dtype, 'nullable': nullable})
    return schema

def _df_stats(df, columns=None):
    import pandas as pd
    cols = columns if columns else list(df.columns)
    stats = {}
    for col in cols:
        if col not in df.columns:
            continue
        s = df[col]
        entry = {'null_count': int(s.isna().sum()), 'unique_count': int(s.nunique())}
        if pd.api.types.is_numeric_dtype(s):
            entry['min'] = float(s.min()) if not s.empty else None
            entry['max'] = float(s.max()) if not s.empty else None
            entry['mean'] = float(s.mean()) if not s.empty else None
        stats[col] = entry
    return stats

def _safe_val(v):
    """Convert numpy/pandas scalar to Python native for JSON."""
    if hasattr(v, 'item'):
        return v.item()
    if hasattr(v, '__float__'):
        try:
            return float(v)
        except Exception:
            pass
    return v

def _rows_to_list(df, limit=500):
    rows = []
    for _, row in df.head(limit).iterrows():
        rows.append({k: _safe_val(v) for k, v in row.items()})
    return rows


# ─────────────────────────── parquet_read ────────────────────────────────────

class ParquetReadTool(BaseMCPTool):
    def __init__(self, config=None):
        cfg = {
            'name': 'parquet_read',
            'description': (
                'Inspect and preview a Parquet or CSV file: schema, row count, sample rows, '
                'and per-column statistics. Pass file_path from list_data_files. '
                'Use sample_rows and columns to limit output size for large files.'
            ),
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            cfg.update(config)
        super().__init__(cfg)

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'file_path': {'type': 'string', 'description': 'Absolute path to .parquet, .pq, .csv, or .tsv file.'},
                'sample_rows': {'type': 'integer', 'description': 'Rows to return in sample. Default: 10. Max: 100.'},
                'include_stats': {'type': 'boolean', 'description': 'Include per-column stats. Default: true.'},
                'columns': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Limit schema/stats/sample to these columns.'},
            },
            'required': ['file_path'],
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, arguments):
        import pandas as pd
        file_path = arguments.get('file_path', '')
        sample_rows = min(int(arguments.get('sample_rows', 10)), 100)
        include_stats = arguments.get('include_stats', True)
        columns = arguments.get('columns') or None

        safe = _safe_path(file_path)
        if not safe:
            return {'error': f'File not found or access denied: {file_path}'}
        if not safe.exists():
            return {'error': f'File not found or access denied: {file_path}'}
        ext = safe.suffix.lower()
        if ext not in ('.parquet', '.pq', '.csv', '.tsv'):
            return {'error': 'parquet_read supports .parquet, .pq, .csv, .tsv only.'}

        size_bytes = safe.stat().st_size
        large_file = size_bytes > 500 * 1024 * 1024  # 500 MB

        try:
            if large_file and ext in ('.parquet', '.pq'):
                import pyarrow.parquet as pq
                pf = pq.read_metadata(str(safe))
                row_count = pf.num_rows
                schema_arrow = pq.read_schema(str(safe))
                col_names = schema_arrow.names
                schema = [{'column': n, 'dtype': str(schema_arrow.field(n).type), 'nullable': True}
                          for n in col_names]
                df_sample = _pq_to_df(str(safe)).head(sample_rows)
            else:
                df, fmt = _load_df(safe)
                row_count = len(df)
                if columns:
                    missing = [c for c in columns if c not in df.columns]
                    if missing:
                        return {'error': f'Columns not found: {missing}. Available: {list(df.columns)}'}
                    df = df[columns]
                schema = _df_schema(df)
                df_sample = df.head(sample_rows)
        except Exception as e:
            return {'error': f'Could not read file: {e}'}

        fmt = 'parquet' if ext in ('.parquet', '.pq') else ext.lstrip('.')
        result = {
            'filename': safe.name,
            'format': fmt,
            'row_count': int(row_count),
            'column_count': len(schema),
            'size_bytes': size_bytes,
            'schema': schema,
            'sample': _rows_to_list(df_sample, sample_rows),
            '_source': str(safe),
        }
        if large_file:
            result['large_file'] = True
        if include_stats and not large_file:
            result['stats'] = _df_stats(df, columns)
        return result


# ─────────────────────────── data_transform ──────────────────────────────────

SUPPORTED_AGG = {'sum', 'mean', 'median', 'min', 'max', 'count', 'count_distinct', 'std', 'first', 'last'}

class DataTransformTool(BaseMCPTool):
    def __init__(self, config=None):
        cfg = {
            'name': 'data_transform',
            'description': (
                'Filter, group-by/aggregate, pivot, and sort a CSV or Parquet file using '
                'declarative parameters. No Python code required — specify column names, '
                'filter conditions, aggregation functions, and sort order as structured params. '
                'Result is a list of row dicts ready for fill_template or data_export.'
            ),
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            cfg.update(config)
        super().__init__(cfg)

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'file_path': {'type': 'string', 'description': 'Absolute path to .csv, .tsv, .parquet, or .pq file.'},
                'filters': {'type': 'array', 'description': 'Filter conditions (ANDed). Each: {column, operator, value}.'},
                'group_by': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Columns to group by. Requires aggregations.'},
                'aggregations': {'type': 'object', 'description': 'Map of column -> agg function (sum/mean/count/etc).'},
                'pivot': {'type': 'object', 'description': 'Pivot spec: {index, columns, values, aggfunc, fill_value}. Mutually exclusive with group_by.'},
                'sort': {'type': 'array', 'description': 'Sort spec: [{column, direction}].'},
                'limit': {'type': 'integer', 'description': 'Max rows to return. Default: 500.'},
                'output_columns': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Select only these columns in output.'},
            },
            'required': ['file_path'],
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, arguments):
        import pandas as pd

        file_path = arguments.get('file_path', '')
        filters = arguments.get('filters') or []
        group_by = arguments.get('group_by') or []
        aggregations = arguments.get('aggregations') or {}
        pivot = arguments.get('pivot') or {}
        sort = arguments.get('sort') or []
        limit = min(int(arguments.get('limit', 500)), 5000)
        output_columns = arguments.get('output_columns') or []

        if group_by and pivot:
            return {'error': 'group_by and pivot are mutually exclusive. Use one per call.'}
        if group_by and not aggregations:
            return {'error': 'aggregations required when group_by is specified.'}

        safe = _safe_path(file_path)
        if not safe or not safe.exists():
            return {'error': f'File not found or access denied: {file_path}'}

        try:
            df, fmt = _load_df(safe)
        except ValueError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Could not read file: {e}'}

        source_rows = len(df)

        # Apply filters
        for f in filters:
            col = f.get('column', '')
            op = f.get('operator', '')
            val = f.get('value')
            if col not in df.columns:
                return {'error': f"Column '{col}' not found in file. Available columns: {list(df.columns)}"}
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
            except TypeError as e:
                return {'error': f"Cannot apply '{op}' to column '{col}': {e}"}

        rows_after_filter = len(df)
        operation = 'filter'

        # Group by + aggregations
        if group_by:
            operation = 'group_by'
            missing_cols = [c for c in group_by if c not in df.columns]
            if missing_cols:
                return {'error': f"group_by columns not found: {missing_cols}. Available: {list(df.columns)}"}
            agg_map = {}
            for col, func in aggregations.items():
                if func not in SUPPORTED_AGG:
                    return {'error': f"Unsupported aggregation '{func}'. Supported: {sorted(SUPPORTED_AGG)}"}
                if col not in df.columns:
                    return {'error': f"Aggregation column '{col}' not found. Available: {list(df.columns)}"}
                pd_func = 'nunique' if func == 'count_distinct' else func
                agg_map[col] = pd_func
            try:
                df = df.groupby(group_by).agg(agg_map).reset_index()
                # Rename agg columns: col -> col_funcname
                rename = {}
                for col, func in aggregations.items():
                    new_name = f"{col}_{func}"
                    if col in df.columns and new_name != col:
                        rename[col] = new_name
                df = df.rename(columns=rename)
            except TypeError as e:
                return {'error': f"Aggregation error: {e}"}

        # Pivot
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
                    return {'error': f"Pivot would produce >{50} columns (found {n_unique} unique values in column '{cols}'). Filter first to reduce cardinality."}
            try:
                pivot_df = df.pivot_table(index=idx, columns=cols, values=vals,
                                          aggfunc=aggfunc, fill_value=fill_value)
                pivot_df.columns = [f"{vals}_{c}" for c in pivot_df.columns]
                df = pivot_df.reset_index()
            except Exception as e:
                return {'error': f"Pivot error: {e}"}

        # Sort
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

        # Output columns
        if output_columns:
            valid = [c for c in output_columns if c in df.columns]
            df = df[valid]

        truncated = len(df) > limit
        result_df = df.head(limit)

        return {
            'operation': operation,
            'source_file': safe.name,
            'source_rows': source_rows,
            'filters_applied': len(filters),
            'rows_after_filter': rows_after_filter,
            'result_rows': len(result_df),
            'truncated': truncated,
            'columns': list(result_df.columns),
            'data': _rows_to_list(result_df, limit),
            '_source': str(safe),
        }


# ─────────────────────────── data_export ─────────────────────────────────────

class DataExportTool(BaseMCPTool):
    def __init__(self, config=None):
        cfg = {
            'name': 'data_export',
            'description': (
                'Save a data_transform result (or any dict with "columns" and "data") '
                'as a CSV or Parquet file in my_data/. '
                'Exported files are immediately discoverable by list_data_files and '
                'queryable by data_transform or duckdb_sql in subsequent workflow steps.'
            ),
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            cfg.update(config)
        super().__init__(cfg)

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'data': {'type': 'object', 'description': 'Dict with "columns" (list) and "data" (list of row dicts). Accepts data_transform output directly.'},
                'filename': {'type': 'string', 'description': 'Output filename with .csv or .parquet extension.'},
                'subfolder': {'type': 'string', 'description': 'Sub-folder within my_data/. Default: "exports".'},
                'format': {'type': 'string', 'enum': ['csv', 'parquet'], 'description': 'Output format. Inferred from filename if omitted.'},
                'versioning': {'type': 'boolean', 'description': 'Archive existing file before overwriting. Default: true.'},
                'include_index': {'type': 'boolean', 'description': 'Include DataFrame index as column. Default: false.'},
            },
            'required': ['data', 'filename'],
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, arguments):
        import pandas as pd

        data = arguments.get('data', {})
        filename = Path(arguments.get('filename', 'export.csv')).name
        subfolder = arguments.get('subfolder', 'exports')
        versioning = arguments.get('versioning', True)
        include_index = arguments.get('include_index', False)

        # Determine format
        ext = Path(filename).suffix.lower()
        fmt = arguments.get('format')
        if not fmt:
            fmt = 'parquet' if ext in ('.parquet', '.pq') else 'csv'

        # data may be a list of row dicts directly, or a dict with a 'data' key (from data_transform output)
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get('data', [])
        else:
            rows = []
        if not rows:
            return {'error': 'data is empty — nothing to export.'}

        df = pd.DataFrame(rows)

        root = _my_data_root()
        folder = root / subfolder if subfolder else root
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / filename

        # Versioning
        archived_as = None
        if dest.exists() and versioning:
            mtime = datetime.fromtimestamp(dest.stat().st_mtime, tz=timezone.utc)
            ts = mtime.strftime('%Y-%m-%d_%H%M%S')
            stem = dest.stem
            archive_name = f"{stem}_{ts}{dest.suffix}"
            shutil.move(str(dest), str(folder / archive_name))
            archived_as = archive_name

        # Write
        try:
            if fmt == 'parquet':
                _df_to_pq(df, dest)
            else:
                df.to_csv(str(dest), index=include_index, encoding='utf-8')
        except Exception as e:
            return {'error': f'Export failed: {e}'}

        stat = dest.stat()
        return {
            'path': str(dest),
            'filename': filename,
            'format': fmt,
            'rows_written': len(df),
            'size_bytes': stat.st_size,
            'versioned': archived_as is not None,
            'archived_as': archived_as,
            'written_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            '_source': str(dest),
        }
