"""
ConnectorsRegistry — singleton that loads config/connectors.json,
decrypts credentials on demand, and provides token acquisition.

Credential values in connectors.json may use ${VAR_NAME} syntax to reference
environment variables (e.g. ${AZURE_CLIENT_SECRET}). These are expanded at
load time so that secrets stay out of the committed config file.
"""
import json
import os
import re
import threading
import time
from typing import Optional

try:
    from dotenv import load_dotenv as _load_dotenv
    # Load .env from project root (two levels above sajhamcpserver/sajha/core/)
    _env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
    _load_dotenv(os.path.abspath(_env_path), override=False)
except ImportError:
    pass  # python-dotenv not installed — rely on shell environment


def _expand_env(value: str) -> str:
    """Replace ${VAR_NAME} placeholders with environment variable values."""
    return re.sub(r'\$\{([^}]+)\}', lambda m: os.environ.get(m.group(1), m.group(0)), value)

from sajha.core.encryption import decrypt
from sajha.core.token_cache import token_cache


_CONFIG_PATH_DEFAULT = os.path.join(
    os.path.dirname(__file__), '..', '..', 'config', 'connectors.json'
)


class ConnectorsRegistry:

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._connectors = {}
                inst._file_lock = threading.Lock()
                inst._config_path = os.path.abspath(_CONFIG_PATH_DEFAULT)
                inst._load()
                cls._instance = inst
            return cls._instance

    def _load(self):
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with self._file_lock:
                self._connectors = {c['connector_type']: c for c in data.get('connectors', [])}
        except FileNotFoundError:
            with self._file_lock:
                self._connectors = {}

    def reload(self):
        self._load()

    def get_connector(self, connector_type: str) -> Optional[dict]:
        """Return connector config (with encrypted credentials) or None."""
        with self._file_lock:
            return self._connectors.get(connector_type)

    def get_credentials(self, connector_type: str) -> dict:
        """Return credentials with env-var placeholders expanded and values decrypted."""
        connector = self.get_connector(connector_type)
        if not connector:
            return {}
        creds = connector.get('credentials', {})
        return {
            k: decrypt(_expand_env(v)) if isinstance(v, str) else v
            for k, v in creds.items()
        }

    def is_enabled(self, connector_type: str) -> bool:
        connector = self.get_connector(connector_type)
        return bool(connector and connector.get('status') == 'connected' and connector.get('enabled', True))

    def get_token(self, connector_id: str, connector_type: str) -> Optional[str]:
        """Return cached token or None (caller must fetch fresh token)."""
        return token_cache.get(connector_id)

    def save_token(self, connector_id: str, access_token: str, expires_in: int = 3600):
        token_cache.set(connector_id, access_token, expires_in)

    def save_connector(self, connector_data: dict) -> None:
        """Upsert a connector config to connectors.json."""
        ct = connector_data['connector_type']
        with self._file_lock:
            self._connectors[ct] = connector_data
            self._persist()

    def delete_connector(self, connector_type: str) -> bool:
        with self._file_lock:
            if connector_type not in self._connectors:
                return False
            del self._connectors[connector_type]
            self._persist()
            return True

    def list_connectors(self) -> list:
        """Return all connectors with credentials REDACTED."""
        with self._file_lock:
            result = []
            for c in self._connectors.values():
                safe = {k: v for k, v in c.items() if k != 'credentials'}
                safe['has_credentials'] = bool(c.get('credentials'))
                result.append(safe)
            return result

    def _persist(self):
        """Write current state to connectors.json."""
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        data = {'connectors': list(self._connectors.values())}
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
