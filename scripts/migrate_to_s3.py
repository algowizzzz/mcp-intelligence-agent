"""
REQ-16: One-time migration — sync /opt/sajha/data/app to Hetzner S3 bucket.
Run on the VPS with AWS credentials set in env.
Safe to re-run (skips objects already in bucket at same size).
"""
import os, sys, pathlib

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Installing boto3...")
    os.system("pip3 install boto3 --quiet --break-system-packages 2>/dev/null || pip3 install boto3 --quiet")
    import boto3
    from botocore.exceptions import ClientError

SRC    = pathlib.Path("/opt/sajha/data/app")
BUCKET = "sajha-storage"
ENDPOINT = "https://hel1.your-objectstorage.com"
REGION = "hel1"

KEY_ID  = os.environ.get("AWS_ACCESS_KEY_ID")
SECRET  = os.environ.get("AWS_SECRET_ACCESS_KEY")

if not KEY_ID or not SECRET:
    print("ERROR: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set")
    sys.exit(1)

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id=KEY_ID,
    aws_secret_access_key=SECRET,
)

if not SRC.exists():
    print("Source %s does not exist — nothing to migrate" % SRC)
    sys.exit(0)

all_files = [f for f in SRC.rglob("*") if f.is_file()]
print("Found %d files to sync from %s" % (len(all_files), SRC))

uploaded = skipped = errors = 0

for fpath in all_files:
    key = str(fpath.relative_to(SRC))
    local_size = fpath.stat().st_size

    # Skip if already in bucket at same size
    try:
        head = s3.head_object(Bucket=BUCKET, Key=key)
        if head["ContentLength"] == local_size:
            skipped += 1
            continue
    except ClientError:
        pass  # not in bucket yet

    try:
        print("  upload: %s (%d bytes)" % (key, local_size))
        s3.upload_file(str(fpath), BUCKET, key)
        uploaded += 1
    except Exception as e:
        print("  ERROR uploading %s: %s" % (key, e))
        errors += 1

print("\nDone. uploaded=%d  skipped=%d  errors=%d" % (uploaded, skipped, errors))

# Final count
resp = s3.list_objects_v2(Bucket=BUCKET)
print("Total objects in bucket: %d" % resp.get("KeyCount", 0))

if errors:
    sys.exit(1)
