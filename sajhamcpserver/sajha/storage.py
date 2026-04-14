"""
Storage abstraction layer for RiskGPT.
Local backend: pathlib.Path (default).
S3 backend: boto3 (stub only — not activated locally).
Switch via STORAGE_BACKEND env var: 'local' (default) or 's3'.
"""
import os
import pathlib
from typing import Optional


class LocalStorageBackend:
    """File system storage backend using pathlib."""

    def read_bytes(self, path: str) -> bytes:
        return pathlib.Path(path).read_bytes()

    def write_bytes(self, path: str, data: bytes) -> None:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        return pathlib.Path(path).read_text(encoding=encoding)

    def write_text(self, path: str, text: str, encoding: str = 'utf-8') -> None:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding=encoding)

    def list_prefix(self, prefix: str) -> list:
        """List all file paths under prefix. Returns relative paths."""
        root = pathlib.Path(prefix)
        if not root.exists():
            return []
        result = []
        for p in root.rglob('*'):
            if p.is_file():
                result.append(str(p.relative_to(root)))
        return sorted(result)

    def exists(self, path: str) -> bool:
        return pathlib.Path(path).exists()

    def delete(self, path: str) -> None:
        try:
            pathlib.Path(path).unlink()
        except FileNotFoundError:
            pass

    def copy(self, src: str, dst: str) -> None:
        import shutil
        dst_path = pathlib.Path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def get_size(self, path: str) -> int:
        try:
            return pathlib.Path(path).stat().st_size
        except Exception:
            return 0

    async def write_stream(self, path: str, stream, chunk_size: int = 65536) -> int:
        """Write from async file-like stream. Returns bytes written. (REQ-11)"""
        import aiofiles
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        async with aiofiles.open(p, 'wb') as f:
            while True:
                chunk = await stream.read(chunk_size)
                if not chunk:
                    break
                await f.write(chunk)
                total += len(chunk)
        return total


class S3StorageBackend:
    """S3 storage backend. REQ-08a: fully implemented.
    Activated when STORAGE_BACKEND=s3.
    For local dev, set S3_ENDPOINT_URL=http://localhost:9000 (MinIO).
    For production AWS, leave S3_ENDPOINT_URL unset — IAM role auth is preferred.
    """

    def __init__(self):
        import boto3
        self.bucket = os.environ.get('S3_BUCKET', 'bpulse-data')
        endpoint = os.environ.get('S3_ENDPOINT_URL') or None   # None = real AWS
        region   = os.environ.get('AWS_REGION', 'us-east-1')
        key_id   = os.environ.get('AWS_ACCESS_KEY_ID') or None
        secret   = os.environ.get('AWS_SECRET_ACCESS_KEY') or None
        self.client = boto3.client(
            's3',
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )
        # Track endpoint for path-style forcing (MinIO requires it)
        self._path_style = endpoint is not None
        # DATA_ROOT prefix to strip so S3 keys are clean relative paths
        # e.g. /app/sajhamcpserver/data/common/foo.md → common/foo.md
        data_root = os.environ.get('DATA_ROOT', '')
        self._data_root = data_root.rstrip('/') + '/' if data_root else ''

    def _key(self, path: str) -> str:
        """Normalise a path to a clean S3 key.

        Handles three input forms:
          s3://bucket/key/path  → key/path   (path_resolver S3 URIs)
          ./data/workers/...    → data/workers/...  (relative local paths)
          /abs/data/root/...    → stripped of DATA_ROOT prefix then relative
        """
        # 1. Strip s3://bucket/ prefix (path_resolver returns these in S3 mode)
        if path.startswith('s3://'):
            rest = path[len('s3://'):]
            slash = rest.find('/')
            return rest[slash + 1:] if slash >= 0 else ''
        # 2. Strip relative ./ prefix then any leading /
        norm = path.lstrip('./')
        # 3. Strip absolute DATA_ROOT prefix (e.g. /app/sajhamcpserver/data/)
        if self._data_root and norm.startswith(self._data_root.lstrip('/')):
            norm = norm[len(self._data_root.lstrip('/')):]
        return norm.lstrip('/')

    def read_bytes(self, path: str) -> bytes:
        resp = self.client.get_object(Bucket=self.bucket, Key=self._key(path))
        return resp['Body'].read()

    def write_bytes(self, path: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=self._key(path), Body=data)

    def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        return self.read_bytes(path).decode(encoding)

    def write_text(self, path: str, text: str, encoding: str = 'utf-8') -> None:
        self.write_bytes(path, text.encode(encoding))

    def list_prefix(self, prefix: str) -> list:
        """List all keys under prefix. Returns relative paths (key minus prefix)."""
        key_prefix = self._key(prefix)
        if key_prefix and not key_prefix.endswith('/'):
            key_prefix += '/'
        paginator = self.client.get_paginator('list_objects_v2')
        keys = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=key_prefix):
            for obj in page.get('Contents', []):
                rel = obj['Key'][len(key_prefix):]
                if rel:
                    keys.append(rel)
        return sorted(keys)

    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(path))
            return True
        except Exception:
            return False

    def delete(self, path: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=self._key(path))
        except Exception:
            pass

    def copy(self, src: str, dst: str) -> None:
        self.client.copy_object(
            Bucket=self.bucket,
            CopySource={'Bucket': self.bucket, 'Key': self._key(src)},
            Key=self._key(dst),
        )

    def generate_presigned_url(self, path: str, expiry: int = 300) -> str:
        """Return a pre-signed GET URL valid for `expiry` seconds."""
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': self._key(path)},
            ExpiresIn=expiry,
        )

    def get_size(self, path: str) -> int:
        """Return object size in bytes, or 0 if not found."""
        try:
            resp = self.client.head_object(Bucket=self.bucket, Key=self._key(path))
            return resp['ContentLength']
        except Exception:
            return 0

    async def write_stream(self, path: str, stream, chunk_size: int = 65536) -> int:
        """Buffer stream into memory then PUT to S3. Safe for files up to 20 MB."""
        key = self._key(path)
        buf = b''
        while True:
            chunk = await stream.read(chunk_size)
            if not chunk:
                break
            buf += chunk
        self.client.put_object(Bucket=self.bucket, Key=key, Body=buf)
        return len(buf)


_STORAGE_BACKEND_TYPE = os.environ.get('STORAGE_BACKEND', 'local')

_storage_instance: Optional[LocalStorageBackend] = None


def get_storage() -> LocalStorageBackend:
    """Return the active storage backend singleton."""
    global _storage_instance
    if _storage_instance is None:
        if _STORAGE_BACKEND_TYPE == 's3':
            _storage_instance = S3StorageBackend()
        else:
            _storage_instance = LocalStorageBackend()
    return _storage_instance


# Convenience module-level instance
storage = get_storage()
