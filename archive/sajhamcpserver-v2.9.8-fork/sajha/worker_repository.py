"""
WorkerRepository — abstraction for all workers.json access.
Local implementation reads from JSON file.
PostgresWorkerRepository uses psycopg3 sync API when DATABASE_URL is set.
"""
import json
import os
import re
import threading
from typing import Optional


class WorkerRepository:
    """Reads and caches workers from a JSON file."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default: look relative to sajhamcpserver/config/workers.json
            base = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base, '..', 'config', 'workers.json')
        self._config_path = os.path.abspath(config_path)
        self._workers: list = []
        self._lock = threading.Lock()
        self.reload()

    def reload(self) -> None:
        """Re-read workers.json from disk."""
        with self._lock:
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._workers = data if isinstance(data, list) else data.get('workers', [])
            except FileNotFoundError:
                self._workers = []
            except Exception as e:
                # Keep existing data on error
                pass

    def find(self, worker_id: str) -> Optional[dict]:
        """Return worker config dict or None if not found."""
        with self._lock:
            for w in self._workers:
                if w.get('worker_id') == worker_id or w.get('id') == worker_id:
                    return w
        return None

    def list(self) -> list:
        """Return all worker configs."""
        with self._lock:
            return list(self._workers)

    def find_by_user(self, user_id: str) -> Optional[dict]:
        """Return the worker a user is assigned to, or None."""
        with self._lock:
            for w in self._workers:
                users = w.get('assigned_users', w.get('users', []))
                if user_id in users:
                    return w
                # Also check user objects with user_id field
                for u in users:
                    if isinstance(u, dict) and u.get('user_id') == user_id:
                        return w
        return None


class PostgresWorkerRepository:
    """Postgres-backed worker repository using psycopg3 (sync API).
    Activated in agent_server.py when DATABASE_URL is set (REQ-07 P1).
    Drop-in replacement for WorkerRepository — same interface.
    """

    # Columns to SELECT from the workers table (order must match _row_to_dict)
    _COLS = (
        "worker_id, name, description, system_prompt, enabled_tools, "
        "domain_data_path, verified_wf_path, connector_scope, enabled, "
        "COALESCE(my_workflows_path,''), COALESCE(templates_path,''), "
        "COALESCE(my_data_path,''), COALESCE(common_data_path,'')"
    )

    def __init__(self):
        raw = os.getenv('DATABASE_URL', '')
        # Strip async driver prefix so psycopg3 sync connect() accepts the URL
        self._dsn = re.sub(
            r'^postgresql(\+asyncpg|\+psycopg2?|\+psycopg)?://',
            'postgresql://',
            raw,
        )
        self._ensure_table_and_seed()

    def _connect(self):
        import psycopg  # psycopg3 — in main requirements.txt as psycopg[binary]
        return psycopg.connect(self._dsn)

    def _ensure_table_and_seed(self) -> None:
        """Create workers table if missing, then seed from workers.json if empty."""
        try:
            import psycopg
            with psycopg.connect(self._dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS workers (
                            worker_id          TEXT PRIMARY KEY,
                            name               TEXT NOT NULL,
                            description        TEXT DEFAULT '',
                            system_prompt      TEXT DEFAULT '',
                            enabled_tools      JSONB DEFAULT '["*"]',
                            domain_data_path   TEXT DEFAULT '',
                            verified_wf_path   TEXT DEFAULT '',
                            connector_scope    JSONB DEFAULT '{}',
                            enabled            BOOLEAN DEFAULT true,
                            my_workflows_path  TEXT DEFAULT '',
                            templates_path     TEXT DEFAULT '',
                            my_data_path       TEXT DEFAULT '',
                            common_data_path   TEXT DEFAULT '',
                            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                    """)
                    # Add columns for existing installs that pre-date this migration
                    for _col, _type in [
                        ('my_workflows_path', 'TEXT DEFAULT \'\''),
                        ('templates_path',    'TEXT DEFAULT \'\''),
                        ('my_data_path',      'TEXT DEFAULT \'\''),
                        ('common_data_path',  'TEXT DEFAULT \'\''),
                    ]:
                        try:
                            cur.execute(
                                f"ALTER TABLE workers ADD COLUMN IF NOT EXISTS "
                                f"{_col} {_type}"
                            )
                        except Exception:
                            pass
                    conn.commit()

                    # Seed from workers.json if table is empty
                    cur.execute("SELECT COUNT(*) FROM workers")
                    count = cur.fetchone()[0]
                    if count == 0:
                        self._seed_from_json(cur)
                        conn.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("workers table init failed: %s", e)

    def _seed_from_json(self, cur) -> None:
        """Insert workers from workers.json into the workers table."""
        import json as _json
        base = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base, '..', 'config', 'workers.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = _json.load(f)
            workers = data if isinstance(data, list) else data.get('workers', [])
        except Exception:
            return
        for w in workers:
            wid = w.get('worker_id') or w.get('id', '')
            if not wid:
                continue
            cur.execute(
                """
                INSERT INTO workers
                    (worker_id, name, description, system_prompt,
                     enabled_tools, domain_data_path, verified_wf_path,
                     connector_scope, enabled,
                     my_workflows_path, templates_path, my_data_path, common_data_path)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                ON CONFLICT (worker_id) DO NOTHING
                """,
                (
                    wid,
                    w.get('name', wid),
                    w.get('description', ''),
                    w.get('system_prompt', ''),
                    _json.dumps(w.get('enabled_tools', ['*'])),
                    w.get('domain_data_path', ''),
                    w.get('verified_wf_path') or w.get('workflows_path', ''),
                    _json.dumps(w.get('connector_scope', {})),
                    bool(w.get('enabled', True)),
                    w.get('my_workflows_path', ''),
                    w.get('templates_path', ''),
                    w.get('my_data_path', ''),
                    w.get('common_data_path', ''),
                ),
            )

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            'worker_id':          row[0],
            'name':               row[1],
            'description':        row[2],
            'system_prompt':      row[3],
            'enabled_tools':      row[4] if row[4] is not None else ['*'],
            'domain_data_path':   row[5] or '',
            # verified_wf_path is the Postgres column name; expose as both
            # keys so _resolve_worker_path (which uses 'workflows_path') works
            # whether the worker came from Postgres or workers.json.
            'verified_wf_path':   row[6] or '',
            'workflows_path':     row[6] or '',
            'connector_scope':    row[7] if row[7] is not None else {},
            'enabled':            row[8],
            'my_workflows_path':  row[9]  or '',
            'templates_path':     row[10] or '',
            'my_data_path':       row[11] or '',
            'common_data_path':   row[12] or '',
        }

    def find(self, worker_id: str) -> Optional[dict]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {self._COLS} FROM workers WHERE worker_id = %s",
                    (worker_id,),
                )
                row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def list(self) -> list:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {self._COLS} FROM workers ORDER BY name"
                )
                rows = cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

    def find_by_user(self, user_id: str) -> Optional[dict]:
        """Return the worker a user is assigned to via users.worker_id FK."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {self._COLS} FROM workers w "
                    "JOIN users u ON u.worker_id = w.worker_id "
                    "WHERE u.user_id = %s "
                    "LIMIT 1",
                    (user_id,),
                )
                row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def reload(self) -> None:
        """No-op — Postgres always reads fresh data per query."""
        pass
