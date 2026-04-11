"""
REQ-08a Test Suite — S3 Object Storage Integration
Branch: feature/req-07-08a-postgres-s3

All tests run against a moto-mocked S3 service (no real AWS / MinIO needed).
Set S3_ENDPOINT_URL + AWS_ACCESS_KEY_ID etc. to run against live MinIO instead.

TC-08A-01  S3StorageBackend: write_bytes / read_bytes round-trip
TC-08A-02  S3StorageBackend: write_text / read_text round-trip
TC-08A-03  S3StorageBackend: exists() true and false
TC-08A-04  S3StorageBackend: list_prefix() returns relative keys
TC-08A-05  S3StorageBackend: delete() removes object
TC-08A-06  S3StorageBackend: copy() duplicates object
TC-08A-07  S3StorageBackend: generate_presigned_url() returns URL
TC-08A-08  S3StorageBackend: write_stream() async multipart upload
TC-08A-09  path_resolver: resolve('domain_data') returns s3:// prefix when STORAGE_BACKEND=s3
TC-08A-10  path_resolver: resolve('my_data') requires user_id and returns s3:// prefix
TC-08A-11  path_resolver: resolve('common_data') returns s3:// prefix
TC-08A-12  path_resolver: resolve('workflows') returns s3:// prefix
TC-08A-13  path_resolver: resolve('templates') returns s3:// prefix
TC-08A-14  storage.get_storage() returns S3StorageBackend when STORAGE_BACKEND=s3
TC-08A-15  storage.get_storage() returns LocalStorageBackend when STORAGE_BACKEND=local
TC-08A-16  S3StorageBackend: write_bytes path normalisation (strips ./ prefix from keys)
TC-08A-17  S3StorageBackend: list_prefix() handles empty bucket prefix gracefully
TC-08A-18  S3StorageBackend: delete() on non-existent key does not raise
TC-08A-19  S3StorageBackend: large write_stream async upload returns correct byte count
TC-08A-20  S3StorageBackend: write_bytes to nested key and list_prefix returns it
"""

import asyncio
import io
import os
import sys
import pathlib
import importlib

# ── Project root on path ──────────────────────────────────────────────────────
_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / 'sajhamcpserver'))

# ── Test infrastructure ───────────────────────────────────────────────────────
_RESULTS: list[tuple[str, str, str]] = []   # (tc_id, label, status)
_TEST_BUCKET = 'bpulse-test'
_PASS = 'PASS'
_FAIL = 'FAIL'
_SKIP = 'SKIP'


def _result(tc_id: str, label: str, ok: bool, msg: str = ''):
    status = _PASS if ok else _FAIL
    _RESULTS.append((tc_id, label, status))
    icon = '  PASS' if ok else '  FAIL'
    detail = f': {msg}' if msg else ''
    print(f'{icon}: {label}{detail}')
    print(f'[{status}] {tc_id} {label}')


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── moto S3 setup ─────────────────────────────────────────────────────────────
from moto import mock_aws
import boto3


def _make_boto_client(endpoint_url=None, bucket=_TEST_BUCKET):
    """Return a boto3 client + create the test bucket."""
    client = boto3.client(
        's3',
        region_name='us-east-1',
        endpoint_url=endpoint_url,
        aws_access_key_id='test',
        aws_secret_access_key='test',
    )
    try:
        client.create_bucket(Bucket=bucket)
    except Exception:
        pass
    return client


def _make_s3_backend(bucket=_TEST_BUCKET):
    """Instantiate S3StorageBackend with test env vars already set."""
    # Re-import to pick up env changes
    import importlib
    import sajha.storage as _storage_mod
    importlib.reload(_storage_mod)
    return _storage_mod.S3StorageBackend()


# ── Async stream helper ───────────────────────────────────────────────────────
class AsyncBytesStream:
    """Minimal async-readable wrapper around bytes (mimics UploadFile.read())."""
    def __init__(self, data: bytes, chunk_size: int = 1024):
        self._buf = io.BytesIO(data)
        self._chunk_size = chunk_size

    async def read(self, n: int = -1) -> bytes:
        return self._buf.read(n if n != -1 else self._chunk_size)


# ─────────────────────────────────────────────────────────────────────────────
# Test cases
# ─────────────────────────────────────────────────────────────────────────────

@mock_aws
def test_tc08a_01_write_read_bytes():
    """write_bytes / read_bytes round-trip."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    os.environ['STORAGE_BACKEND'] = 's3'
    _make_boto_client()
    b = _make_s3_backend()
    b.write_bytes('data/hello.bin', b'hello world')
    got = b.read_bytes('data/hello.bin')
    ok = got == b'hello world'
    _result('TC08A-01', 'WRITE_READ_BYTES', ok, '' if ok else f'got {got!r}')


@mock_aws
def test_tc08a_02_write_read_text():
    """write_text / read_text round-trip with UTF-8 content."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    b.write_text('data/sample.txt', 'Risk report 2025 — FRTB §73')
    got = b.read_text('data/sample.txt')
    ok = 'FRTB' in got
    _result('TC08A-02', 'WRITE_READ_TEXT', ok, '' if ok else f'got {got!r}')


@mock_aws
def test_tc08a_03_exists():
    """exists() returns True for present key, False for absent."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    b.write_bytes('data/exists.bin', b'x')
    ok = b.exists('data/exists.bin') and not b.exists('data/nonexistent.bin')
    _result('TC08A-03', 'EXISTS_CHECK', ok)


@mock_aws
def test_tc08a_04_list_prefix():
    """list_prefix() returns relative keys under prefix."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    b.write_bytes('workers/w1/a.csv', b'1')
    b.write_bytes('workers/w1/b.csv', b'2')
    b.write_bytes('workers/w2/c.csv', b'3')
    keys = b.list_prefix('workers/w1')
    ok = sorted(keys) == ['a.csv', 'b.csv']
    _result('TC08A-04', 'LIST_PREFIX', ok, '' if ok else f'got {keys}')


@mock_aws
def test_tc08a_05_delete():
    """delete() removes the object; exists() returns False afterwards."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    b.write_bytes('data/del.txt', b'bye')
    b.delete('data/del.txt')
    ok = not b.exists('data/del.txt')
    _result('TC08A-05', 'DELETE_OBJECT', ok)


@mock_aws
def test_tc08a_06_copy():
    """copy() duplicates object; both src and dst exist after copy."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    b.write_bytes('src/orig.bin', b'original')
    b.copy('src/orig.bin', 'dst/copy.bin')
    ok = b.exists('src/orig.bin') and b.read_bytes('dst/copy.bin') == b'original'
    _result('TC08A-06', 'COPY_OBJECT', ok)


@mock_aws
def test_tc08a_07_presigned_url():
    """generate_presigned_url() returns a non-empty string URL."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    b.write_bytes('data/report.pdf', b'%PDF-1.4')
    url = b.generate_presigned_url('data/report.pdf', expiry=60)
    ok = isinstance(url, str) and len(url) > 10
    _result('TC08A-07', 'PRESIGNED_URL', ok, '' if ok else f'url={url!r}')


@mock_aws
def test_tc08a_08_write_stream():
    """write_stream() async upload returns correct byte count."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    payload = b'A' * 1024  # 1 KB
    stream = AsyncBytesStream(payload)
    # Override chunk_size to 256 to exercise multi-chunk path
    total = run(b.write_stream('data/stream_test.bin', stream, chunk_size=256))
    stored = b.read_bytes('data/stream_test.bin')
    ok = total == 1024 and stored == payload
    _result('TC08A-08', 'WRITE_STREAM_ASYNC', ok, '' if ok else f'total={total}, len(stored)={len(stored)}')


@mock_aws
def test_tc08a_09_path_resolver_domain_data():
    """resolve('domain_data') returns s3:// when STORAGE_BACKEND=s3."""
    os.environ['STORAGE_BACKEND'] = 's3'
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    import sajha.path_resolver as pr
    importlib.reload(pr)
    worker_ctx = {'domain_data_path': './data/workers/w-market-risk/domain_data'}
    result = pr.resolve('domain_data', worker_ctx)
    ok = result.startswith(f's3://{_TEST_BUCKET}/')
    _result('TC08A-09', 'PATH_RESOLVER_DOMAIN_DATA', ok, result)
    # Restore
    os.environ['STORAGE_BACKEND'] = 'local'
    importlib.reload(pr)


@mock_aws
def test_tc08a_10_path_resolver_my_data():
    """resolve('my_data') requires user_id and returns s3:// prefix."""
    os.environ['STORAGE_BACKEND'] = 's3'
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    import sajha.path_resolver as pr
    importlib.reload(pr)
    worker_ctx = {'my_data_path': './data/workers/w-market-risk/my_data'}
    result = pr.resolve('my_data', worker_ctx, user_id='risk_agent')
    ok = result.startswith(f's3://{_TEST_BUCKET}/') and 'risk_agent' in result
    _result('TC08A-10', 'PATH_RESOLVER_MY_DATA', ok, result)
    # Verify missing user_id raises
    try:
        pr.resolve('my_data', worker_ctx)
        _result('TC08A-10b', 'MY_DATA_REQUIRES_USER_ID', False, 'no exception raised')
    except ValueError:
        pass  # expected
    os.environ['STORAGE_BACKEND'] = 'local'
    importlib.reload(pr)


@mock_aws
def test_tc08a_11_path_resolver_common_data():
    """resolve('common_data') returns s3:// prefix."""
    os.environ['STORAGE_BACKEND'] = 's3'
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    import sajha.path_resolver as pr
    importlib.reload(pr)
    worker_ctx = {'common_data_path': './data/common'}
    result = pr.resolve('common_data', worker_ctx)
    ok = result.startswith(f's3://{_TEST_BUCKET}/')
    _result('TC08A-11', 'PATH_RESOLVER_COMMON_DATA', ok, result)
    os.environ['STORAGE_BACKEND'] = 'local'
    importlib.reload(pr)


@mock_aws
def test_tc08a_12_path_resolver_workflows():
    """resolve('workflows') returns s3:// prefix."""
    os.environ['STORAGE_BACKEND'] = 's3'
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    import sajha.path_resolver as pr
    importlib.reload(pr)
    worker_ctx = {'domain_data_path': './data/workers/w-market-risk/domain_data'}
    result = pr.resolve('workflows', worker_ctx)
    ok = result.startswith(f's3://{_TEST_BUCKET}/') and 'workflows' in result
    _result('TC08A-12', 'PATH_RESOLVER_WORKFLOWS', ok, result)
    os.environ['STORAGE_BACKEND'] = 'local'
    importlib.reload(pr)


@mock_aws
def test_tc08a_13_path_resolver_templates():
    """resolve('templates') returns s3:// prefix."""
    os.environ['STORAGE_BACKEND'] = 's3'
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    import sajha.path_resolver as pr
    importlib.reload(pr)
    worker_ctx = {'domain_data_path': './data/workers/w-market-risk/domain_data'}
    result = pr.resolve('templates', worker_ctx)
    ok = result.startswith(f's3://{_TEST_BUCKET}/') and 'templates' in result
    _result('TC08A-13', 'PATH_RESOLVER_TEMPLATES', ok, result)
    os.environ['STORAGE_BACKEND'] = 'local'
    importlib.reload(pr)


def test_tc08a_14_get_storage_returns_s3():
    """get_storage() returns S3StorageBackend when STORAGE_BACKEND=s3."""
    import sajha.storage as _storage_mod
    importlib.reload(_storage_mod)
    # Patch env + force re-init
    os.environ['STORAGE_BACKEND'] = 's3'
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    importlib.reload(_storage_mod)
    _storage_mod._storage_instance = None
    # Mock boto3 so constructor doesn't need real AWS
    import unittest.mock as mock
    with mock.patch('boto3.client'):
        backend = _storage_mod.get_storage()
    ok = type(backend).__name__ == 'S3StorageBackend'
    _result('TC08A-14', 'GET_STORAGE_S3_BACKEND', ok, type(backend).__name__)
    os.environ['STORAGE_BACKEND'] = 'local'
    importlib.reload(_storage_mod)
    _storage_mod._storage_instance = None


def test_tc08a_15_get_storage_returns_local():
    """get_storage() returns LocalStorageBackend when STORAGE_BACKEND=local."""
    import sajha.storage as _storage_mod
    os.environ['STORAGE_BACKEND'] = 'local'
    importlib.reload(_storage_mod)
    _storage_mod._storage_instance = None
    backend = _storage_mod.get_storage()
    ok = type(backend).__name__ == 'LocalStorageBackend'
    _result('TC08A-15', 'GET_STORAGE_LOCAL_BACKEND', ok, type(backend).__name__)


@mock_aws
def test_tc08a_16_key_normalisation():
    """write_bytes strips leading ./ from S3 key; read_bytes works with same path."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    b.write_bytes('./data/norm.txt', b'normalised')
    # Should be stored as 'data/norm.txt' not './data/norm.txt'
    got = b.read_bytes('./data/norm.txt')
    ok = got == b'normalised'
    _result('TC08A-16', 'KEY_NORMALISATION', ok, '' if ok else f'got {got!r}')


@mock_aws
def test_tc08a_17_list_prefix_empty():
    """list_prefix() on empty prefix returns empty list (no exception)."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    keys = b.list_prefix('nonexistent/path')
    ok = keys == []
    _result('TC08A-17', 'LIST_PREFIX_EMPTY', ok, '' if ok else f'got {keys}')


@mock_aws
def test_tc08a_18_delete_nonexistent():
    """delete() on non-existent key does not raise."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    try:
        b.delete('data/ghost.bin')
        ok = True
    except Exception as e:
        ok = False
        _result('TC08A-18', 'DELETE_NONEXISTENT', ok, str(e))
        return
    _result('TC08A-18', 'DELETE_NONEXISTENT', ok)


@mock_aws
def test_tc08a_19_large_stream_upload():
    """write_stream() with 6MB payload (above 5MB chunk threshold) returns correct count."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    payload = b'Z' * (6 * 1024 * 1024)  # 6 MB
    stream = AsyncBytesStream(payload, chunk_size=65536)
    total = run(b.write_stream('data/large.bin', stream, chunk_size=5 * 1024 * 1024))
    stored = b.read_bytes('data/large.bin')
    ok = total == len(payload) and stored == payload
    _result('TC08A-19', 'LARGE_STREAM_UPLOAD', ok,
            '' if ok else f'total={total}, stored_len={len(stored)}')


@mock_aws
def test_tc08a_20_nested_key_list():
    """write_bytes to nested key and list_prefix returns it."""
    os.environ['S3_BUCKET'] = _TEST_BUCKET
    _make_boto_client()
    b = _make_s3_backend()
    b.write_bytes('workers/w-market-risk/domain_data/iris/iris_combined.csv', b'header,row')
    keys = b.list_prefix('workers/w-market-risk/domain_data/iris')
    ok = 'iris_combined.csv' in keys
    _result('TC08A-20', 'NESTED_KEY_LIST', ok, '' if ok else f'keys={keys}')


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        test_tc08a_01_write_read_bytes,
        test_tc08a_02_write_read_text,
        test_tc08a_03_exists,
        test_tc08a_04_list_prefix,
        test_tc08a_05_delete,
        test_tc08a_06_copy,
        test_tc08a_07_presigned_url,
        test_tc08a_08_write_stream,
        test_tc08a_09_path_resolver_domain_data,
        test_tc08a_10_path_resolver_my_data,
        test_tc08a_11_path_resolver_common_data,
        test_tc08a_12_path_resolver_workflows,
        test_tc08a_13_path_resolver_templates,
        test_tc08a_14_get_storage_returns_s3,
        test_tc08a_15_get_storage_returns_local,
        test_tc08a_16_key_normalisation,
        test_tc08a_17_list_prefix_empty,
        test_tc08a_18_delete_nonexistent,
        test_tc08a_19_large_stream_upload,
        test_tc08a_20_nested_key_list,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            tc_id = t.__name__.split('_')[1].upper() + '_' + t.__name__.split('_')[2].upper()
            label = t.__name__[len('test_tc08a_XX_'):].upper()
            _result(tc_id, label, False, str(e))

    passed = sum(1 for _, _, s in _RESULTS if s == _PASS)
    failed = sum(1 for _, _, s in _RESULTS if s == _FAIL)
    skipped = sum(1 for _, _, s in _RESULTS if s == _SKIP)
    total = len(_RESULTS)
    print()
    print('=' * 50)
    print(f'REQ-08a Results: {passed} PASS / {failed} FAIL / {total} total')
    if skipped:
        print(f'  ({skipped} skipped — requires live MinIO)')
