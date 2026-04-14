"""
One-time migration — upload all local data files to Hetzner S3.

S3 key layout mirrors what path_resolver generates:
  local:  sajhamcpserver/data/workers/w-market-risk/domain_data/iris/iris_combined.csv
  S3 key: data/workers/w-market-risk/domain_data/iris/iris_combined.csv

This matches storage._key() output for path_resolver S3 URIs like
  s3://sajha-storage/data/workers/w-market-risk/domain_data/...

Usage (run from project root):
  AWS_ACCESS_KEY_ID=<key> AWS_SECRET_ACCESS_KEY=<secret> python3 scripts/migrate_to_s3.py

Safe to re-run — skips objects already in bucket at the same size.
"""
import os
import sys
import pathlib

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Installing boto3...")
    os.system("pip3 install boto3 --quiet --break-system-packages 2>/dev/null || pip3 install boto3 --quiet")
    import boto3
    from botocore.exceptions import ClientError

# ── Config ──────────────────────────────────────────────────────────────────

BUCKET   = os.environ.get('S3_BUCKET', 'sajha-storage')
ENDPOINT = os.environ.get('S3_ENDPOINT_URL', 'https://hel1.your-objectstorage.com')
REGION   = os.environ.get('AWS_REGION', 'hel1')
KEY_ID   = os.environ.get('AWS_ACCESS_KEY_ID')
SECRET   = os.environ.get('AWS_SECRET_ACCESS_KEY')

# Source: sajhamcpserver/data/ (relative to project root)
# Key prefix: "data/" so that key = "data/" + relative_path_under_data_dir
# Source: prefer the Hetzner server bind-mount path (/opt/sajha/data/app),
# fall back to local dev path (sajhamcpserver/data/ relative to project root).
_SERVER_PATH = pathlib.Path('/opt/sajha/data/app')
SCRIPT_DIR   = pathlib.Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
_LOCAL_PATH  = PROJECT_ROOT / 'sajhamcpserver' / 'data'
SRC = _SERVER_PATH if _SERVER_PATH.exists() else _LOCAL_PATH
KEY_PREFIX = 'data'   # keys will be data/workers/..., data/common/...

# Files to skip (non-data or binary DB files that DuckDB re-creates)
SKIP_NAMES = {'.DS_Store', '.gitkeep', '.gitignore'}
SKIP_SUFFIXES = {'.db', '.db-shm', '.db-wal', '.pyc'}
SKIP_DIRS = {'__pycache__', 'python_sandbox_venv', 'audit', 'checkpoints.db'}

# ── Validate ─────────────────────────────────────────────────────────────────

if not KEY_ID or not SECRET:
    print("ERROR: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set")
    print("  export AWS_ACCESS_KEY_ID=<your-key>")
    print("  export AWS_SECRET_ACCESS_KEY=<your-secret>")
    sys.exit(1)

if not SRC.exists():
    print(f"ERROR: Source directory not found: {SRC}")
    sys.exit(1)

# ── S3 client ────────────────────────────────────────────────────────────────

s3 = boto3.client(
    's3',
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id=KEY_ID,
    aws_secret_access_key=SECRET,
)

# ── Collect files ─────────────────────────────────────────────────────────────

def should_skip(fpath: pathlib.Path) -> bool:
    if fpath.name in SKIP_NAMES:
        return True
    if fpath.suffix in SKIP_SUFFIXES:
        return True
    for part in fpath.parts:
        if part in SKIP_DIRS:
            return True
    return False

all_files = [f for f in SRC.rglob('*') if f.is_file() and not should_skip(f)]
print(f"Found {len(all_files)} files to sync from {SRC}")
print(f"Target: s3://{BUCKET}/{KEY_PREFIX}/")
print()

# ── Upload ────────────────────────────────────────────────────────────────────

uploaded = skipped = errors = 0

for fpath in sorted(all_files):
    rel = fpath.relative_to(SRC)
    key = f"{KEY_PREFIX}/{rel}"
    local_size = fpath.stat().st_size

    # Skip if already in bucket at same size
    try:
        head = s3.head_object(Bucket=BUCKET, Key=key)
        if head['ContentLength'] == local_size:
            skipped += 1
            continue
    except ClientError:
        pass  # not in bucket yet — upload it

    try:
        print(f"  upload: {key}  ({local_size:,} bytes)")
        s3.upload_file(str(fpath), BUCKET, key)
        uploaded += 1
    except Exception as e:
        print(f"  ERROR: {key}: {e}")
        errors += 1

print()
print(f"Done.  uploaded={uploaded}  skipped={skipped}  errors={errors}")

# Show bucket summary
try:
    resp = s3.list_objects_v2(Bucket=BUCKET, MaxKeys=1000)
    print(f"Total objects in bucket: {resp.get('KeyCount', '?')}")
except Exception as e:
    print(f"(Could not list bucket: {e})")

if errors:
    sys.exit(1)
