"""
WorkerRepository — abstraction for all workers.json access.
Local implementation reads from JSON file.
PostgresWorkerRepository stub is present for future migration.
"""
import json
import os
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
    """Postgres implementation stub — not instantiated locally.
    Drop-in swap when migrating to Postgres.
    """

    def find(self, worker_id: str) -> Optional[dict]:
        raise NotImplementedError("PostgresWorkerRepository not implemented")

    def list(self) -> list:
        raise NotImplementedError("PostgresWorkerRepository not implemented")

    def find_by_user(self, user_id: str) -> Optional[dict]:
        raise NotImplementedError("PostgresWorkerRepository not implemented")
