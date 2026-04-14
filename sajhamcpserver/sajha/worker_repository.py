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
        "domain_data_path, verified_wf_path, connector_scope, enabled"
    )

    def __init__(self):
        raw = os.getenv('DATABASE_URL', '')
        # Strip async driver prefix so psycopg3 sync connect() accepts the URL
        self._dsn = re.sub(
            r'^postgresql(\+asyncpg|\+psycopg2?|\+psycopg)?://',
            'postgresql://',
            raw,
        )

    def _connect(self):
        import psycopg  # psycopg3 — in main requirements.txt as psycopg[binary]
        return psycopg.connect(self._dsn)

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            'worker_id':        row[0],
            'name':             row[1],
            'description':      row[2],
            'system_prompt':    row[3],
            'enabled_tools':    row[4] if row[4] is not None else ['*'],
            'domain_data_path': row[5],
            'verified_wf_path': row[6],
            'connector_scope':  row[7] if row[7] is not None else {},
            'enabled':          row[8],
        }

    def find(self, worker_id: str) -> Optional[dict]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT {self._COLS} FROM workers WHERE worker_id = %s",
                        (worker_id,),
                    )
                    row = cur.fetchone()
            return self._row_to_dict(row) if row else None
        except Exception:
            return None

    def list(self) -> list:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT {self._COLS} FROM workers ORDER BY name"
                    )
                    rows = cur.fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception:
            return []

    def find_by_user(self, user_id: str) -> Optional[dict]:
        """Return the worker a user is assigned to via users.worker_id FK."""
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT w.worker_id, w.name, w.description, w.system_prompt, "
                        "w.enabled_tools, w.domain_data_path, w.verified_wf_path, "
                        "w.connector_scope, w.enabled "
                        "FROM workers w "
                        "JOIN users u ON u.worker_id = w.worker_id "
                        "WHERE u.user_id = %s "
                        "LIMIT 1",
                        (user_id,),
                    )
                    row = cur.fetchone()
            return self._row_to_dict(row) if row else None
        except Exception:
            return None

    def reload(self) -> None:
        """No-op — Postgres always reads fresh data per query."""
        pass
