"""
Copyright All rights Reserved 2025-2030, Ashutosh Sinha, Email: ajsinha@gmail.com
DuckDB OLAP Analytics MCP Tool Implementation - Refactored with Individual Tools
With Auto-Refresh Support
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.core.properties_configurator import PropertiesConfigurator
from sajha.storage import storage
from sajha.path_resolver import resolve as path_resolve


def _get_worker_ctx():
    try:
        from flask import g as _g
        # Prefer explicit worker_ctx dict; fall back to building one from flat g attributes
        ctx = getattr(_g, 'worker_ctx', None)
        if ctx:
            return ctx
        # SAJHA sets g.worker_data_root / g.worker_id directly via request headers
        worker_data_root = getattr(_g, 'worker_data_root', '') or ''
        worker_id = getattr(_g, 'worker_id', '') or ''
        if worker_data_root or worker_id:
            return {
                'worker_id': worker_id,
                'domain_data_path': worker_data_root,
                'my_data_path': getattr(_g, 'worker_my_data_root', '') or '',
                'common_data_path': getattr(_g, 'worker_common_root', '') or '',
            }
        return {}
    except RuntimeError:
        return {}

try:
    import duckdb
except ImportError:
    raise ImportError("DuckDB is required. Install with: pip install duckdb --break-system-packages")


class DuckDbBaseTool(BaseMCPTool):
    """
    Base class for DuckDB tools with shared functionality
    """

    def __init__(self, config: Dict = None):
        """Initialize DuckDB base tool"""
        super().__init__(config)

        # Data directories for CSV, Parquet, JSON files.
        # Searches all three data layers: domain_data, my_data, common.
        # REQ-PREP-04: resolved per-request from worker context via path_resolver;
        # static config used only as fallback at init time.
        self.data_directories = []  # list of (section_name, path)
        self.data_directory = ''    # primary dir (domain_data) for backward compat

        worker_ctx = _get_worker_ctx()
        props = PropertiesConfigurator()

        # domain_data (primary)
        dd = ''
        if worker_ctx:
            try:
                dd = path_resolve('domain_data', worker_ctx)
            except Exception:
                pass
        if not dd:
            dd = self.config.get('data_directory', props.get('tool.duckdb.data_directory', './data/duckdb'))
        self.data_directory = dd
        self.data_directories.append(('domain_data', dd))

        # my_data
        if worker_ctx:
            try:
                user_id = None
                try:
                    from flask import g as _g
                    user_id = getattr(_g, 'user_id', None)
                except RuntimeError:
                    pass
                if user_id:
                    md = path_resolve('my_data', worker_ctx, user_id=user_id)
                    self.data_directories.append(('my_data', md))
            except Exception:
                pass

        # common
        if worker_ctx:
            try:
                cd = path_resolve('common_data', worker_ctx)
                self.data_directories.append(('common', cd))
            except Exception:
                pass
        else:
            cd = props.get('data.common_dir', './data/common')
            if cd:
                self.data_directories.append(('common', cd))

        # Ensure all data directories exist
        for _, d in self.data_directories:
            os.makedirs(d, exist_ok=True)

        # REQ-PREP-04: in-memory DuckDB connection (no persistent db_path)
        # S3/httpfs stub: to activate S3 reads, uncomment and configure:
        # conn.execute("INSTALL httpfs; LOAD httpfs;")
        # conn.execute("SET s3_region='us-east-1';")
        self.conn = None

        # Track file states for change detection
        self._file_states = {}  # {filename: {'mtime': timestamp, 'size': bytes, 'view_name': str}}

        # Cache key for last successful view init — avoids re-scanning on every request
        self._last_init_worker_key = None

        # REQ-PREP-04: auto-refresh thread removed (was _start_auto_refresh / _auto_refresh_worker)

        # Initialize views from data files
        self._initialize_views_from_files()

    def _get_connection(self):
        """Get or create DuckDB in-memory connection (REQ-PREP-04)."""
        if self.conn is None:
            # REQ-PREP-04: in-memory only — no persistent db file
            # S3/httpfs stub (not activated): configure AWS credentials + httpfs here for S3 reads
            self.conn = duckdb.connect()
            # Enable automatic CSV/Parquet detection
            self.conn.execute("SET enable_object_cache=true")
        return self.conn

    def _execute_query(self, query: str) -> duckdb.DuckDBPyRelation:
        """
        Execute a query and return results

        Args:
            query: SQL query string

        Returns:
            Query results
        """
        conn = self._get_connection()
        try:
            result = conn.execute(query)
            return result
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            raise ValueError(f"Query failed: {str(e)}")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def _scan_data_files(self, file_type: str = 'all') -> List[Dict]:
        """Scan all data layers (domain_data, my_data, common) for supported file types.
        REQ-PREP-04: data directories resolved per-request from worker context.
        """
        # Re-resolve data directories from current worker context if available
        worker_ctx = _get_worker_ctx()
        if worker_ctx:
            try:
                self.data_directory = path_resolve('domain_data', worker_ctx)
                # Update domain_data entry in data_directories
                self.data_directories = [(n, p) if n != 'domain_data' else ('domain_data', self.data_directory)
                                         for n, p in self.data_directories]
            except Exception:
                pass  # Keep existing data_directory

        supported_extensions = {
            'csv': ['.csv'],
            'parquet': ['.parquet', '.pq'],
            'json': ['.json', '.jsonl'],
            'tsv': ['.tsv']
        }

        if file_type != 'all':
            extensions = supported_extensions.get(file_type, [])
        else:
            extensions = [ext for exts in supported_extensions.values() for ext in exts]

        files = []
        seen_filenames = set()  # Avoid duplicate view names across layers

        for section_name, data_dir in self.data_directories:
            if not os.path.isdir(data_dir):
                continue

            # REQ-PREP-04: use storage.list_prefix instead of os.listdir
            # storage.list_prefix uses rglob — returns relative paths including subfolders.
            # We include subfolder files and encode the subfolder into the view name so
            # "iris/iris_combined.csv" becomes view "iris__iris_combined".
            relative_paths = storage.list_prefix(data_dir)
            for rel_path in relative_paths:
                filename = os.path.basename(rel_path)
                if filename.startswith('.') or filename.endswith('.db'):
                    continue

                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in extensions:
                    continue

                # Build a unique view key that encodes the subfolder path.
                # "iris/iris_combined.csv" → unique_key "iris__iris_combined"
                # Top-level "data.csv" → unique_key "data"
                rel_no_ext = os.path.splitext(rel_path)[0]
                # Normalise path separators and replace with double-underscore
                safe_key = rel_no_ext.replace('\\', '/').replace('/', '__').replace(' ', '_').replace('-', '_')
                unique_key = f"{section_name}__{safe_key}" if safe_key in seen_filenames else safe_key

                file_path = os.path.join(data_dir, rel_path)

                # Determine file type
                if file_ext in ['.csv']:
                    ftype = 'csv'
                elif file_ext in ['.parquet', '.pq']:
                    ftype = 'parquet'
                elif file_ext in ['.json', '.jsonl']:
                    ftype = 'json'
                elif file_ext in ['.tsv']:
                    ftype = 'tsv'
                else:
                    continue

                file_info = {
                    'filename': rel_path,   # full relative path including subfolder
                    'unique_key': unique_key,
                    'section': section_name,
                    'file_type': ftype,
                    'file_path': file_path
                }

                try:
                    stat = os.stat(file_path)
                    file_info['file_size_bytes'] = stat.st_size
                    file_info['file_size_human'] = self._format_file_size(stat.st_size)
                    file_info['modified_date'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                except Exception:
                    pass

                files.append(file_info)
                seen_filenames.add(safe_key)

        return files

    def _worker_init_key(self) -> str:
        """Return a cache key representing the current worker context data directories."""
        try:
            from flask import g as _g
            r = getattr(_g, 'worker_data_root', '') or ''
            r2 = getattr(_g, 'worker_my_data_root', '') or ''
            r3 = getattr(_g, 'worker_common_root', '') or ''
            return f"{r}|{r2}|{r3}"
        except RuntimeError:
            return ''

    def _initialize_views_from_files(self):
        """Initialize DuckDB views for all data files.

        Skips re-initialization when the worker context (data directories) has
        not changed since the last call — avoids re-scanning on every request.
        Views are lazy (no data loaded at creation); sample_size=100 keeps
        schema detection fast.
        """
        # Guard: skip if worker context unchanged
        current_key = self._worker_init_key()
        if current_key and current_key == self._last_init_worker_key:
            return
        # Re-resolve data directories from current worker context before scanning
        worker_ctx = _get_worker_ctx()
        if worker_ctx:
            try:
                new_dd = path_resolve('domain_data', worker_ctx)
                if new_dd:
                    self.data_directory = new_dd
                    self.data_directories = [
                        (n, p) if n != 'domain_data' else ('domain_data', new_dd)
                        for n, p in self.data_directories
                    ]
            except Exception:
                pass

        try:
            conn = self._get_connection()
            files = self._scan_data_files()

            if not files:
                self.logger.info(f"No data files found in {self.data_directory}")
                self._last_init_worker_key = current_key
                return

            self.logger.info(f"Initialising {len(files)} DuckDB views")

            for file_info in files:
                try:
                    filename = file_info['filename']
                    file_path = file_info['file_path']
                    file_type = file_info['file_type']
                    unique_key = file_info.get('unique_key', filename)

                    # Sanitise view name: strip extension, replace non-alnum with _
                    view_name = os.path.splitext(unique_key)[0]
                    view_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in view_name)

                    try:
                        conn.execute(f"DROP VIEW IF EXISTS {view_name}")
                    except Exception:
                        pass

                    # Create lazy view — no data loaded at creation time.
                    # sample_size=100 is sufficient for schema detection and is fast.
                    if file_type == 'csv':
                        create_view_sql = (
                            f"CREATE VIEW {view_name} AS "
                            f"SELECT * FROM read_csv_auto('{file_path}', "
                            f"header=true, auto_detect=true, sample_size=100)"
                        )
                    elif file_type == 'parquet':
                        create_view_sql = (
                            f"CREATE VIEW {view_name} AS "
                            f"SELECT * FROM read_parquet('{file_path}')"
                        )
                    elif file_type == 'json':
                        create_view_sql = (
                            f"CREATE VIEW {view_name} AS "
                            f"SELECT * FROM read_json_auto('{file_path}')"
                        )
                    elif file_type == 'tsv':
                        create_view_sql = (
                            f"CREATE VIEW {view_name} AS "
                            f"SELECT * FROM read_csv_auto('{file_path}', "
                            f"header=true, delim='\\t', auto_detect=true, sample_size=100)"
                        )
                    else:
                        continue

                    conn.execute(create_view_sql)

                    try:
                        stat = os.stat(file_path)
                        self._file_states[filename] = {
                            'mtime': stat.st_mtime,
                            'size': stat.st_size,
                            'view_name': view_name,
                            'file_type': file_type,
                            'file_path': file_path
                        }
                    except Exception:
                        pass

                    self.logger.info(f"✓ View '{view_name}' ← {filename}")

                except Exception as e:
                    self.logger.error(f"Failed to create view for {filename}: {e}")
                    continue

            self._last_init_worker_key = current_key

        except Exception as e:
            self.logger.error(f"Failed to initialize views from files: {e}")

    # REQ-PREP-04: _start_auto_refresh, _stop_auto_refresh, and _auto_refresh_worker
    # removed — background refresh thread is not compatible with stateless/S3 deployment.
    # Views are initialized fresh per-connection at startup.

    def _check_and_sync_views(self):
        """
        Check for file changes and sync views accordingly:
        - Add views for new files
        - Remove views for deleted files
        - Reload views for modified files
        """
        try:
            conn = self._get_connection()

            # Scan current files in directory
            current_files = self._scan_data_files()
            current_filenames = {f['filename'] for f in current_files}
            current_file_map = {f['filename']: f for f in current_files}

            # Track what we tracked before
            tracked_filenames = set(self._file_states.keys())

            changes_made = False

            # 1. Detect and handle DELETED files
            deleted_files = tracked_filenames - current_filenames
            for filename in deleted_files:
                try:
                    view_name = self._file_states[filename]['view_name']
                    conn.execute(f"DROP VIEW IF EXISTS {view_name}")
                    del self._file_states[filename]
                    self.logger.info(f"🗑️  Removed view '{view_name}' (file deleted: {filename})")
                    changes_made = True
                except Exception as e:
                    self.logger.error(f"Failed to remove view for {filename}: {e}")

            # 2. Detect and handle NEW files
            new_files = current_filenames - tracked_filenames
            for filename in new_files:
                try:
                    file_info = current_file_map[filename]
                    file_path = file_info['file_path']
                    file_type = file_info['file_type']

                    # Generate view name
                    view_name = os.path.splitext(filename)[0]
                    view_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in view_name)

                    # Create view based on file type
                    if file_type == 'csv':
                        create_view_sql = f"""
                            CREATE VIEW {view_name} AS 
                            SELECT * FROM read_csv_auto('{file_path}', 
                                header=true, auto_detect=true, sample_size=-1)
                        """
                    elif file_type == 'parquet':
                        create_view_sql = f"""
                            CREATE VIEW {view_name} AS 
                            SELECT * FROM read_parquet('{file_path}')
                        """
                    elif file_type == 'json':
                        create_view_sql = f"""
                            CREATE VIEW {view_name} AS 
                            SELECT * FROM read_json_auto('{file_path}')
                        """
                    elif file_type == 'tsv':
                        create_view_sql = f"""
                            CREATE VIEW {view_name} AS 
                            SELECT * FROM read_csv_auto('{file_path}', 
                                header=true, delim='\\t', auto_detect=true, sample_size=-1)
                        """
                    else:
                        continue

                    # Create the view
                    conn.execute(create_view_sql)

                    # Track the new file
                    stat = os.stat(file_path)
                    self._file_states[filename] = {
                        'mtime': stat.st_mtime,
                        'size': stat.st_size,
                        'view_name': view_name,
                        'file_type': file_type,
                        'file_path': file_path
                    }

                    self.logger.info(f"➕ Created view '{view_name}' (new file: {filename})")
                    changes_made = True

                except Exception as e:
                    self.logger.error(f"Failed to create view for new file {filename}: {e}")

            # 3. Detect and handle MODIFIED files
            existing_files = current_filenames & tracked_filenames
            for filename in existing_files:
                try:
                    file_info = current_file_map[filename]
                    file_path = file_info['file_path']

                    # Check if file was modified
                    stat = os.stat(file_path)
                    old_state = self._file_states[filename]

                    if stat.st_mtime != old_state['mtime'] or stat.st_size != old_state['size']:
                        # File was modified - reload the view
                        view_name = old_state['view_name']
                        file_type = old_state['file_type']

                        # Drop and recreate the view
                        conn.execute(f"DROP VIEW IF EXISTS {view_name}")

                        if file_type == 'csv':
                            create_view_sql = f"""
                                CREATE VIEW {view_name} AS 
                                SELECT * FROM read_csv_auto('{file_path}', 
                                    header=true, auto_detect=true, sample_size=-1)
                            """
                        elif file_type == 'parquet':
                            create_view_sql = f"""
                                CREATE VIEW {view_name} AS 
                                SELECT * FROM read_parquet('{file_path}')
                            """
                        elif file_type == 'json':
                            create_view_sql = f"""
                                CREATE VIEW {view_name} AS 
                                SELECT * FROM read_json_auto('{file_path}')
                            """
                        elif file_type == 'tsv':
                            create_view_sql = f"""
                                CREATE VIEW {view_name} AS 
                                SELECT * FROM read_csv_auto('{file_path}', 
                                    header=true, delim='\\t', auto_detect=true, sample_size=-1)
                            """
                        else:
                            continue

                        conn.execute(create_view_sql)

                        # Update tracked state
                        self._file_states[filename]['mtime'] = stat.st_mtime
                        self._file_states[filename]['size'] = stat.st_size

                        self.logger.info(f"🔄 Reloaded view '{view_name}' (file modified: {filename})")
                        changes_made = True

                except Exception as e:
                    self.logger.error(f"Failed to reload view for modified file {filename}: {e}")

            # Log summary if changes were made
            if changes_made:
                views_result = conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_type = 'VIEW'").fetchone()
                total_views = views_result[0] if views_result else 0
                self.logger.info(f"Auto-refresh complete: {total_views} views available")

        except Exception as e:
            self.logger.error(f"Failed to check and sync views: {e}")

    def close(self):
        """Close DuckDB in-memory connection (REQ-PREP-04: auto-refresh thread removed)."""
        if self.conn:
            self.conn.close()
            self.conn = None


class DuckDbListTablesTool(DuckDbBaseTool):
    """
    Tool to list all available tables and views
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'duckdb_list_tables',
            'description': 'List all available tables and views in the DuckDB database',
            'version': '1.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {})

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {})

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        """Execute list tables operation"""
        include_system = arguments.get('include_system_tables', False)

        try:
            conn = self._get_connection()

            # Get all tables and views
            query = """
                SELECT 
                    table_name as name,
                    table_type as type,
                    'main' as schema
                FROM information_schema.tables
            """

            if not include_system:
                query += " WHERE table_schema = 'main'"

            result = conn.execute(query).fetchall()

            tables = []
            for row in result:
                table_info = {
                    'name': row[0],
                    'type': 'view' if row[1].lower() == 'view' else 'table',
                    'schema': row[2]
                }

                # Try to get row count
                try:
                    count_query = f"SELECT COUNT(*) FROM {row[0]}"
                    count_result = conn.execute(count_query).fetchone()
                    table_info['row_count'] = count_result[0] if count_result else 0
                except:
                    table_info['row_count'] = None

                tables.append(table_info)

            return {
                'tables': tables,
                'total_count': len(tables),
                '_source': self.data_directory
            }

        except Exception as e:
            self.logger.error(f"Failed to list tables: {e}")
            raise


class DuckDbDescribeTableTool(DuckDbBaseTool):
    """
    Tool to describe table schema and structure
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'duckdb_describe_table',
            'description': 'Get detailed schema information for a specific table or view',
            'version': '1.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {})

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {})

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        """Execute describe table operation"""
        table_name = arguments['table_name']
        include_sample = arguments.get('include_sample_data', False)
        sample_size = arguments.get('sample_size', 5)

        try:
            conn = self._get_connection()

            # Get table type
            table_type_query = f"""
                SELECT table_type 
                FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            """
            table_type_result = conn.execute(table_type_query).fetchone()
            table_type = 'view' if table_type_result and table_type_result[0].lower() == 'view' else 'table'

            # Get column information
            describe_query = f"DESCRIBE {table_name}"
            describe_result = conn.execute(describe_query).fetchall()

            columns = []
            for row in describe_result:
                column_info = {
                    'column_name': row[0],
                    'data_type': row[1],
                    'nullable': row[2] == 'YES' if len(row) > 2 else True,
                    'is_primary_key': False
                }

                if len(row) > 3 and row[3]:
                    column_info['default_value'] = str(row[3])

                columns.append(column_info)

            # Get row count
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            row_count = conn.execute(count_query).fetchone()[0]

            result = {
                'table_name': table_name,
                'table_type': table_type,
                'columns': columns,
                'row_count': row_count,
                '_source': self.data_directory
            }

            # Get sample data if requested
            if include_sample:
                sample_query = f"SELECT * FROM {table_name} LIMIT {sample_size}"
                sample_result = conn.execute(sample_query).fetchdf()
                result['sample_data'] = sample_result.to_dict(orient='records')

            return result

        except Exception as e:
            self.logger.error(f"Failed to describe table: {e}")
            raise


class DuckDbQueryTool(DuckDbBaseTool):
    """
    Tool to execute SQL queries
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'duckdb_query',
            'description': (
                'Execute SQL queries on data files using DuckDB. '
                'Always call duckdb_list_files first to get view_name for each file, '
                'then query using: SELECT * FROM <view_name> LIMIT 10. '
                'Do NOT use read_csv_auto() with raw file paths — views are already registered.'
            ),
            'version': '1.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {})

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {})

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        """Execute SQL query using a fresh per-request DuckDB connection.

        A shared connection causes crashes when eventlet yields during CSV I/O
        and another greenlet hits the same connection concurrently.  A fresh
        in-memory connection per request is safe and fast — views are lazy SQL
        strings, so creation takes < 1 ms regardless of file size.
        """
        import duckdb as _duckdb

        sql_query = arguments['sql_query']
        limit = arguments.get('limit', 100)

        # Prevent destructive operations
        forbidden_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'INSERT', 'UPDATE']
        query_upper = sql_query.upper()
        for keyword in forbidden_keywords:
            if keyword in query_upper:
                return {'error': f'Forbidden operation: {keyword}. Only SELECT queries allowed.', 'success': False}

        # Add LIMIT if not already present and not a COUNT/aggregation query
        if 'LIMIT' not in query_upper and 'COUNT(' not in query_upper:
            sql_query = f"{sql_query.rstrip(';')} LIMIT {limit}"

        # Build fresh connection and register views for all known data files.
        # Do NOT call _initialize_views_from_files() — that uses the shared
        # connection which blocks eventlet.  _scan_data_files() is pure filesystem
        # I/O (rglob + stat) and is safe to call directly.
        conn = _duckdb.connect(':memory:')
        try:
            files = self._scan_data_files()
            for file_info in files:
                unique_key = file_info.get('unique_key', file_info['filename'])
                view_name = os.path.splitext(unique_key)[0]
                view_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in view_name)
                fp = file_info['file_path']
                ft = file_info['file_type']
                try:
                    if ft == 'csv':
                        conn.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_csv_auto('{fp}', header=true, sample_size=100)")
                    elif ft == 'parquet':
                        conn.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_parquet('{fp}')")
                    elif ft == 'json':
                        conn.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_json_auto('{fp}')")
                    elif ft == 'tsv':
                        conn.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_csv_auto('{fp}', header=true, delim='\\t', sample_size=100)")
                except Exception:
                    pass  # skip files that can't be viewed

            start_time = time.time()
            result = conn.execute(sql_query)
            df = result.fetchdf()
            execution_time = (time.time() - start_time) * 1000

            return {
                'query': sql_query,
                'columns': list(df.columns),
                'rows': df.to_dict(orient='records'),
                'row_count': len(df),
                'execution_time_ms': round(execution_time, 2),
                'limited': 'LIMIT' in sql_query.upper() and len(df) >= limit,
                '_source': self.data_directory,
                'success': True,
            }

        except Exception as e:
            self.logger.error(f"duckdb_query failed: {e}")
            return {'error': str(e), 'success': False}
        finally:
            conn.close()


class DuckDbRefreshViewsTool(DuckDbBaseTool):
    """
    Tool to refresh materialized views
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'duckdb_refresh_views',
            'description': 'Refresh materialized views or reload external data files',
            'version': '1.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {})

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {})

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        """Execute refresh views operation"""
        view_name = arguments.get('view_name')
        reload_external = arguments.get('reload_external_files', False)

        try:
            conn = self._get_connection()
            refreshed_views = []

            # Reload external files if requested
            if reload_external:
                self.logger.info("Reloading external data files...")
                self._initialize_views_from_files()

            # Get list of views to refresh
            if view_name:
                views = [view_name]
            else:
                views_query = """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_type = 'VIEW'
                """
                views = [row[0] for row in conn.execute(views_query).fetchall()]

            # Refresh each view
            for view in views:
                try:
                    start_time = time.time()

                    # For standard views, just query to validate
                    count_result = conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()
                    row_count = count_result[0] if count_result else 0

                    refresh_time = (time.time() - start_time) * 1000

                    refreshed_views.append({
                        'view_name': view,
                        'status': 'success',
                        'row_count': row_count,
                        'refresh_time_ms': round(refresh_time, 2)
                    })

                except Exception as e:
                    refreshed_views.append({
                        'view_name': view,
                        'status': 'failed',
                        'error_message': str(e)
                    })

            return {
                'refreshed_views': refreshed_views,
                'total_refreshed': len([v for v in refreshed_views if v['status'] == 'success']),
                'external_files_reloaded': reload_external,
                '_source': self.data_directory
            }

        except Exception as e:
            self.logger.error(f"Failed to refresh views: {e}")
            raise


class DuckDbGetStatsTool(DuckDbBaseTool):
    """
    Tool to get statistical summary for table columns
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'duckdb_get_stats',
            'description': 'Get statistical summary for numeric columns in a table',
            'version': '1.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {})

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {})

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        """Execute get stats operation"""
        table_name = arguments['table_name']
        columns = arguments.get('columns', [])
        include_percentiles = arguments.get('include_percentiles', True)

        try:
            conn = self._get_connection()

            # Get all columns if not specified
            if not columns:
                describe_result = conn.execute(f"DESCRIBE {table_name}").fetchall()
                all_columns = [row[0] for row in describe_result]
            else:
                all_columns = columns

            # Get total row count
            total_rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            column_statistics = {}

            for col in all_columns:
                try:
                    # Build statistics query
                    stats_parts = [
                        f"COUNT({col}) as count",
                        f"COUNT(*) - COUNT({col}) as null_count",
                        f"MIN({col}) as min",
                        f"MAX({col}) as max",
                        f"COUNT(DISTINCT {col}) as unique_count"
                    ]

                    # Try numeric statistics
                    try:
                        numeric_stats = [
                            f"AVG({col}) as mean",
                            f"STDDEV({col}) as std_dev"
                        ]

                        if include_percentiles:
                            numeric_stats.extend([
                                f"PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {col}) as percentile_25",
                                f"PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {col}) as median",
                                f"PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {col}) as percentile_75"
                            ])

                        stats_query = f"SELECT {', '.join(stats_parts + numeric_stats)} FROM {table_name}"
                        stats = conn.execute(stats_query).fetchone()

                        column_statistics[col] = {
                            'count': stats[0],
                            'null_count': stats[1],
                            'min': stats[2],
                            'max': stats[3],
                            'unique_count': stats[4],
                            'mean': float(stats[5]) if stats[5] is not None else None,
                            'std_dev': float(stats[6]) if stats[6] is not None else None,
                            'data_type': 'numeric'
                        }

                        if include_percentiles:
                            column_statistics[col].update({
                                'percentile_25': float(stats[7]) if stats[7] is not None else None,
                                'median': float(stats[8]) if stats[8] is not None else None,
                                'percentile_75': float(stats[9]) if stats[9] is not None else None
                            })

                    except:
                        # Non-numeric column
                        stats_query = f"SELECT {', '.join(stats_parts)} FROM {table_name}"
                        stats = conn.execute(stats_query).fetchone()

                        column_statistics[col] = {
                            'count': stats[0],
                            'null_count': stats[1],
                            'min': stats[2],
                            'max': stats[3],
                            'unique_count': stats[4],
                            'data_type': 'non-numeric'
                        }

                except Exception as e:
                    self.logger.warning(f"Failed to get stats for column {col}: {e}")
                    continue

            return {
                'table_name': table_name,
                'total_rows': total_rows,
                'column_statistics': column_statistics,
                '_source': self.data_directory
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            raise


class DuckDbAggregateTool(DuckDbBaseTool):
    """
    Tool to perform aggregation operations
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'duckdb_aggregate',
            'description': 'Perform aggregation operations with grouping',
            'version': '1.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {})

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {})

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        """Execute aggregation operation"""
        table_name = arguments['table_name']
        aggregations = arguments['aggregations']
        group_by = arguments.get('group_by', [])
        having = arguments.get('having')
        order_by = arguments.get('order_by', [])
        limit = arguments.get('limit', 100)

        try:
            start_time = time.time()

            # Build aggregation expressions
            agg_expressions = []
            for col, func in aggregations.items():
                func_upper = func.upper()
                if func_upper in ['SUM', 'AVG', 'COUNT', 'MIN', 'MAX']:
                    agg_expressions.append(f"{func_upper}({col}) as {func}_{col}")
                elif func_upper == 'COUNT_DISTINCT':
                    agg_expressions.append(f"COUNT(DISTINCT {col}) as count_distinct_{col}")

            # Build SELECT clause
            if group_by:
                select_clause = f"SELECT {', '.join(group_by)}, {', '.join(agg_expressions)}"
            else:
                select_clause = f"SELECT {', '.join(agg_expressions)}"

            # Build query
            query = f"{select_clause} FROM {table_name}"

            if group_by:
                query += f" GROUP BY {', '.join(group_by)}"

            if having:
                query += f" HAVING {having}"

            if order_by:
                order_clauses = []
                for order in order_by:
                    col = order.get('column')
                    direction = order.get('direction', 'asc').upper()
                    order_clauses.append(f"{col} {direction}")
                query += f" ORDER BY {', '.join(order_clauses)}"

            query += f" LIMIT {limit}"

            conn = self._get_connection()
            result = conn.execute(query)
            df = result.fetchdf()

            execution_time = (time.time() - start_time) * 1000

            return {
                'table_name': table_name,
                'aggregations_applied': aggregations,
                'grouped_by': group_by,
                'results': df.to_dict(orient='records'),
                'row_count': len(df),
                'execution_time_ms': round(execution_time, 2),
                '_source': self.data_directory
            }

        except Exception as e:
            self.logger.error(f"Failed to perform aggregation: {e}")
            raise


class DuckDbListFilesTool(DuckDbBaseTool):
    """
    Tool to list available data files
    """

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'duckdb_list_files',
            'description': (
                'List all queryable data files (CSV, Parquet, JSON) across domain_data, my_data, and common. '
                'Each file has a view_name field — use that in duckdb_query SQL: '
                'SELECT COUNT(*) FROM <view_name>. '
                'Do NOT use read_csv_auto() with file paths — use the view_name instead.'
            ),
            'version': '1.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return self.config.get('inputSchema', {})

    def get_output_schema(self) -> Dict:
        return self.config.get('outputSchema', {})

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        """Execute list files operation.

        Only scans the filesystem — does NOT call _initialize_views_from_files()
        because that creates a DuckDB shared connection which blocks eventlet.
        The view_name field is derived from the same sanitisation logic so the
        agent can pass it directly to duckdb_query without a separate init step.
        """
        file_type = arguments.get('file_type', 'all')

        try:
            files = self._scan_data_files(file_type)

            # Calculate summary
            summary = {
                'csv_count': len([f for f in files if f['file_type'] == 'csv']),
                'parquet_count': len([f for f in files if f['file_type'] == 'parquet']),
                'json_count': len([f for f in files if f['file_type'] == 'json']),
                'tsv_count': len([f for f in files if f['file_type'] == 'tsv']),
                'total_size_bytes': sum(f.get('file_size_bytes', 0) for f in files)
            }

            # Derive view_name using the same sanitisation as duckdb_query —
            # no DuckDB connection needed here.
            for file_info in files:
                unique_key = file_info.get('unique_key', file_info['filename'])
                view_name = os.path.splitext(unique_key)[0]
                view_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in view_name)
                file_info['view_name'] = view_name

            return {
                'data_directory': self.data_directory,
                'files': files,
                'total_files': len(files),
                'summary': summary,
                '_source': self.data_directory,
                '_usage': 'Use view_name in SQL: SELECT COUNT(*) FROM <view_name>',
            }

        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            raise


# Tool registry for easy access
DUCKDB_TOOLS = {
    'duckdb_list_tables': DuckDbListTablesTool,
    'duckdb_describe_table': DuckDbDescribeTableTool,
    'duckdb_query': DuckDbQueryTool,
    'duckdb_refresh_views': DuckDbRefreshViewsTool,
    'duckdb_get_stats': DuckDbGetStatsTool,
    'duckdb_aggregate': DuckDbAggregateTool,
    'duckdb_list_files': DuckDbListFilesTool
}