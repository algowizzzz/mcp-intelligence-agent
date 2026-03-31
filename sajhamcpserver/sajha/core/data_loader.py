"""
DataLoader — loads JSON data files from local disk or S3.
Configure data.root in server.properties:
  data.root=data                        (local, default)
  data.root=s3://my-bucket/prefix       (S3, requires boto3)

A 60-second TTL cache prevents redundant reads on every tool call.
"""
import json
import time
import threading
from pathlib import Path
from typing import Any, Dict


class DataCache:
    def __init__(self, ttl_seconds: int = 60):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._ttl = ttl_seconds
        self._lock = threading.RLock()

    def get(self, key: str):
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self._ttl:
                    return self._cache[key]
        return None

    def set(self, key: str, value: Any):
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()


_cache = DataCache(ttl_seconds=60)


class DataLoader:
    """
    Loads JSON data files from local disk or S3.
    Usage:
        loader = DataLoader()
        data = loader.load('counterparties/exposure.json')
    """

    def __init__(self):
        from sajha.core.properties_configurator import PropertiesConfigurator
        props = PropertiesConfigurator()
        self._root = props.get('data.root', 'data')

    def load(self, relative_path: str) -> Any:
        cache_key = f"{self._root}/{relative_path}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        if self._root.startswith('s3://'):
            data = self._load_s3(relative_path)
        else:
            data = self._load_local(relative_path)

        _cache.set(cache_key, data)
        return data

    def resolve_path(self, relative_path: str) -> str:
        """Return the full path/URI for a relative data path (for _source attribution)."""
        if self._root.startswith('s3://'):
            return f"{self._root.rstrip('/')}/{relative_path}"
        return str(Path(self._root) / relative_path)

    def _load_local(self, relative_path: str) -> Any:
        full_path = Path(self._root) / relative_path
        if not full_path.exists():
            raise FileNotFoundError(
                f"Data file not found: {full_path}. "
                f"Run scripts/generate_data.py to create seed files."
            )
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_s3(self, relative_path: str) -> Any:
        s3_uri = self._root[5:]
        parts = s3_uri.split('/', 1)
        bucket = parts[0]
        prefix = parts[1].rstrip('/') if len(parts) > 1 else ''
        key = f"{prefix}/{relative_path}" if prefix else relative_path

        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 is required for S3 data loading. Install with: pip install boto3")
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response['Body'].read().decode('utf-8'))
