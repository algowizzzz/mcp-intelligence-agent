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
    """S3 storage backend (stub — not activated locally).
    Activated when STORAGE_BACKEND=s3.
    Requires: AWS_BUCKET, AWS_REGION env vars.
    """

    def __init__(self):
        raise NotImplementedError(
            "S3 backend not activated. Set STORAGE_BACKEND=s3 and configure "
            "AWS_BUCKET and AWS_REGION environment variables."
        )

    def read_bytes(self, path: str) -> bytes:
        raise NotImplementedError

    def write_bytes(self, path: str, data: bytes) -> None:
        raise NotImplementedError

    def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        raise NotImplementedError

    def write_text(self, path: str, text: str, encoding: str = 'utf-8') -> None:
        raise NotImplementedError

    def list_prefix(self, prefix: str) -> list:
        raise NotImplementedError

    def exists(self, path: str) -> bool:
        raise NotImplementedError

    def delete(self, path: str) -> None:
        raise NotImplementedError

    def copy(self, src: str, dst: str) -> None:
        raise NotImplementedError

    async def write_stream(self, path: str, stream, chunk_size: int = 5242880) -> int:
        """S3 multipart upload stub. 5 MB parts (S3 minimum for multipart). (REQ-11)"""
        raise NotImplementedError(
            "S3 streaming upload not yet implemented. "
            "Set STORAGE_BACKEND=s3 and implement boto3 multipart upload."
        )


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
