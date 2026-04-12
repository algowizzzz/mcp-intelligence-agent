# B-Pulse — Cloud Deployment Guide (DevOps)
**Version:** 1.0 | **Date:** 2026-04-11

This is a one-page reference for enterprise deployment. Two requirements cover the full migration: **REQ-08a** (S3 storage) must complete before **REQ-08b** (Iceberg analytical tables).

---

## What You Need to Provision

| Service | Purpose | REQ |
|---|---|---|
| **PostgreSQL** (RDS db.t3.medium or equivalent) | Users, workers, audit logs, conversation history, file metadata index | REQ-07 |
| **S3 Bucket** (`bpulse-data-{env}`) | All binary files — documents, uploads, charts, workflows | REQ-08a |
| **AWS Glue Data Catalog** | Iceberg table catalog for analytical data | REQ-08b |

That's it. No additional servers. The application (SAJHA + Agent) runs as a single Docker container.

---

## Environment Variables (set in your container/orchestrator)

```bash
# Database (REQ-07)
DATABASE_URL=postgresql://user:pass@host:5432/bpulse

# Storage (REQ-08a)
STORAGE_BACKEND=s3
S3_BUCKET=bpulse-data-prod
AWS_REGION=us-east-1
# Use IAM role in production — no keys needed if running on EC2/ECS/EKS
AWS_ACCESS_KEY_ID=...          # only if not using IAM role
AWS_SECRET_ACCESS_KEY=...      # only if not using IAM role

# Iceberg (REQ-08b)
ICEBERG_CATALOG=glue           # or 'nessie' for non-AWS
ICEBERG_CATALOG_DB=bpulse_catalog
# S3_ENDPOINT_URL=             # leave blank for real AWS; set to MinIO URL for local dev

# Application
LLM_PROVIDER=anthropic         # or xai | huggingface | bedrock
ANTHROPIC_API_KEY=...
JWT_SECRET=<generate-random-256-bit>
CORS_ORIGINS=https://your-domain.com
AGENT_API_KEYS=<optional-comma-separated-keys>
```

---

## S3 Bucket Setup (one-time)

```bash
# Create bucket
aws s3api create-bucket --bucket bpulse-data-prod --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket bpulse-data-prod \
  --versioning-configuration Status=Enabled

# Block all public access
aws s3api put-public-access-block \
  --bucket bpulse-data-prod \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket bpulse-data-prod \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Migrate existing local data
aws s3 sync sajhamcpserver/data/workers/ s3://bpulse-data-prod/workers/ --sse AES256
aws s3 sync sajhamcpserver/data/common/  s3://bpulse-data-prod/common/  --sse AES256
```

**Minimum IAM permissions for the application role:**
```json
{
  "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket","s3:GetObjectVersion"],
  "Resource": ["arn:aws:s3:::bpulse-data-*","arn:aws:s3:::bpulse-data-*/*"]
}
```

---

## Database Setup (one-time)

```bash
# Run migrations (creates all tables including file_metadata, threads, audit)
docker run --rm -e DATABASE_URL=$DATABASE_URL bpulse:latest python migrate.py

# After S3 sync, rebuild file index from S3 into file_metadata table
curl -X POST https://your-domain.com/api/admin/fs/reindex \
  -H "Authorization: Bearer <super-admin-token>"
```

---

## Local Dev Stack (no AWS needed)

To test Iceberg locally before production:

```bash
# Start MinIO (S3-compatible) + Nessie (Iceberg catalog)
docker-compose -f docker-compose.local.yml up -d

# Override env for local dev
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET=bpulse-dev
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
ICEBERG_CATALOG=nessie
ICEBERG_CATALOG_URI=http://localhost:19120/api/v1
```

When switching to production: remove `S3_ENDPOINT_URL` and update credentials. No code changes.

---

## Health Checks

| Endpoint | Expected | Notes |
|---|---|---|
| `GET /health` | `{"status":"ok"}` | Agent server (port 8000) |
| `GET http://sajha:3002/health` | `{"status":"healthy","tools_count":122}` | SAJHA MCP server |

---

## Ports

| Service | Port | Exposed |
|---|---|---|
| Agent Server (FastAPI) | 8000 | via nginx (port 80/443) |
| SAJHA MCP Server (Flask) | 3002 | internal only |
| nginx reverse proxy | 80 / 443 | public |

nginx routes: `/api/*` → FastAPI, `/mcp-studio/*` → Flask, `/*.html` → static files.

---

## Checklist

- [ ] PostgreSQL provisioned and `DATABASE_URL` set
- [ ] S3 bucket created with versioning + encryption
- [ ] IAM role attached to application with S3 permissions
- [ ] Existing local data synced to S3 (`aws s3 sync`)
- [ ] File metadata index rebuilt (`POST /api/admin/fs/reindex`)
- [ ] AWS Glue catalog created (REQ-08b)
- [ ] Iceberg tables created and seeded (REQ-08b)
- [ ] `JWT_SECRET` set to a unique value per environment
- [ ] `CORS_ORIGINS` set to your production domain
- [ ] Health checks passing on both ports
