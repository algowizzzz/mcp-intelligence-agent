"""
Thread-safe OAuth token cache for connector tools.
Prevents re-fetching tokens on every tool call.
"""
import time
import threading
from typing import Optional


class TokenCache:
    """Module-level token cache keyed by connector_id."""

    def __init__(self):
        self._cache: dict = {}  # {connector_id: {'access_token': str, 'expires_at': float}}
        self._locks: dict = {}  # {connector_id: threading.Lock}
        self._global_lock = threading.Lock()

    def _get_lock(self, connector_id: str) -> threading.Lock:
        with self._global_lock:
            if connector_id not in self._locks:
                self._locks[connector_id] = threading.Lock()
            return self._locks[connector_id]

    def get(self, connector_id: str) -> Optional[str]:
        """Return cached token if valid (>60s remaining). None otherwise."""
        entry = self._cache.get(connector_id)
        if not entry:
            return None
        if entry['expires_at'] - time.time() < 60:
            return None
        return entry['access_token']

    def set(self, connector_id: str, access_token: str, expires_in: int) -> None:
        """Store token with TTL."""
        self._cache[connector_id] = {
            'access_token': access_token,
            'expires_at': time.time() + expires_in,
        }

    def invalidate(self, connector_id: str) -> None:
        """Remove cached token for a connector."""
        self._cache.pop(connector_id, None)


# Module-level singleton
token_cache = TokenCache()
