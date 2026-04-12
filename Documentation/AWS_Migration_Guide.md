# B-Pulse Digital Workers — AWS Migration Guide

**Version:** 1.0 · April 2026  
**Scope:** Current stack (Hetzner → AWS). No new features, no S3/Redshift. Infrastructure swap only.

---

## Core Principle

The application layer is already infrastructure-agnostic. It reads all config from environment variables, uses standard Postgres drivers, and runs in Docker. **No application code changes are required** for the AWS migration — only infrastructure and deployment config changes.

---

## What Needs to Change (5 items)

### 1. File Storage → AWS EFS (replaces Docker volume)

**Problem:** Tools write to `/app/sajhamcpserver/data` via Docker volume on Hetzner. ECS containers have ephemeral storage — data is lost on restart.

**Fix:** Mount AWS EFS at the exact same path. All 15 tool files that use direct disk paths continue working with zero code changes.

```json
// ECS Task Definition
"mountPoints": [{
  "sourceVolume": "sajha-data",
  "containerPath": "/app/sajhamcpserver/data"
}],
"volumes": [{
  "name": "sajha-data",
  "efsVolumeConfiguration": {
    "fileSystemId": "fs-xxxxx",
    "transitEncryption": "ENABLED"
  }
}]
```

**Why EFS and not S3 yet:** 15 tool files use direct filesystem paths (`os.walk`, `read_csv_auto('/path')`, `shutil.copy2`). EFS is a network filesystem — same POSIX interface, zero code changes. Full S3 migration is tracked separately in REQ-16.

---

### 2. PostgreSQL → AWS RDS (connection string swap only)

**Problem:** Current Postgres runs on the same Hetzner VPS as the app. `postgres` hostname resolves via Docker DNS.

**Fix:** Point `DATABASE_URL` at the RDS endpoint. The driver (`psycopg`, `psycopg2`) and query format are identical — Postgres is Postgres.

```bash
# Hetzner (current)
DATABASE_URL=postgresql+psycopg://sajha:pass@postgres:5432/sajha

# AWS (new)
DATABASE_URL=postgresql+psycopg://sajha:pass@sajha-db.xxxxx.rds.amazonaws.com:5432/sajha
```

**RDS config:**
- Engine: PostgreSQL 16
- Instance: `db.t3.medium` (start here, scale as needed)
- Multi-AZ: enabled for production
- Same schema, same LangGraph checkpoint tables — no migration script needed beyond `pg_restore`

---

### 3. Secrets → AWS Secrets Manager (replaces .env file)

**Problem:** GitHub Actions currently writes a `.env` file to the Hetzner server with all secrets. ECS doesn't have a server to SSH into.

**Fix:** Store each secret in AWS Secrets Manager. Reference them in the ECS task definition — they are injected as environment variables at container start. The app reads `os.environ` either way, nothing changes.

```json
// ECS Task Definition — secrets block
"secrets": [
  { "name": "ANTHROPIC_API_KEY",   "valueFrom": "arn:aws:secretsmanager:...:ANTHROPIC_API_KEY::" },
  { "name": "JWT_SECRET",          "valueFrom": "arn:aws:secretsmanager:...:JWT_SECRET::" },
  { "name": "POSTGRES_PASSWORD",   "valueFrom": "arn:aws:secretsmanager:...:POSTGRES_PASSWORD::" },
  { "name": "TAVILY_API_KEY",      "valueFrom": "arn:aws:secretsmanager:...:TAVILY_API_KEY::" }
]
```

**Secrets to migrate from GitHub Secrets → AWS Secrets Manager:**

| Secret | Notes |
|--------|-------|
| `ANTHROPIC_API_KEY` | LLM provider |
| `JWT_SECRET` | Min 64 chars random |
| `POSTGRES_PASSWORD` | RDS master password |
| `TAVILY_API_KEY` | Web search |
| `AGENT_API_KEYS` | Internal service auth |
| `SAJHA_API_KEY` | MCP server auth |
| `XAI_API_KEY` | Optional — xAI Grok |
| `HF_API_KEY` | Optional — HuggingFace |

---

### 4. Container Registry — GHCR or ECR

**Current:** GitHub Container Registry (GHCR) via `ghcr.io/{repo}/sajha-agent:latest`

**Options:**
- **Keep GHCR:** Works with ECS. Add `repositoryCredentials` in task definition pointing to a Secrets Manager secret containing the GHCR PAT.
- **Switch to ECR:** Simpler inside AWS — no external registry auth needed. Update GitHub Actions push step to `aws ecr get-login-password | docker login` then push to ECR URI.

ECR is recommended for production enterprise deployments (no external dependency, IAM-based auth, vulnerability scanning built-in).

---

### 5. GitHub Actions Deploy Step (SSH → ECS)

**Current flow:**
```
push to main → build image → push GHCR → SSH to Hetzner → docker compose pull && up -d
```

**AWS flow:**
```
push to main → build image → push ECR → aws ecs update-service --force-new-deployment
```

The build step is identical. Only the deploy step changes.

```yaml
# .github/workflows/deploy.yml — replace deploy job

- name: Deploy to ECS
  run: |
    aws ecs update-service \
      --cluster sajha-prod \
      --service sajha-app \
      --force-new-deployment \
      --region us-east-1
```

Add these GitHub Secrets for AWS deploy:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `ECS_CLUSTER`
- `ECS_SERVICE`

---

## What Does NOT Change

| Component | Reason |
|-----------|--------|
| Dockerfile | Single container + supervisord works on ECS identically |
| nginx config | SSE timeouts (`proxy_buffering off`, 300s read timeout) carry over |
| `SAJHA_BASE_URL=http://localhost:3002` | Single container — localhost still valid |
| All 122 tool implementations | EFS mount preserves `/app/sajhamcpserver/data` paths |
| Health check `GET /health` | ALB target group uses this endpoint already |
| JWT auth, RBAC, 9-middleware stack | Pure application logic, no infra dependency |
| LangGraph checkpoints | Same psycopg driver, just different host |
| Watchtower | **Remove** — ECS rolling updates replace it |

---

## 5-Step Migration Runbook

```bash
# Step 1 — Create RDS PostgreSQL 16
aws rds create-db-instance \
  --db-instance-identifier sajha-prod \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16 \
  --master-username sajha \
  --master-user-password <password> \
  --allocated-storage 20 \
  --multi-az \
  --no-publicly-accessible

# Step 2 — Create EFS filesystem
aws efs create-file-system --performance-mode generalPurpose --encrypted
# Create mount target in same VPC/subnet as ECS cluster
aws efs create-mount-target \
  --file-system-id fs-xxxxx \
  --subnet-id subnet-xxxxx \
  --security-groups sg-xxxxx

# Step 3 — Migrate data from Hetzner volume to EFS
# Mount EFS on a temporary EC2 instance, then rsync from Hetzner
rsync -avz -e "ssh -i ~/.ssh/hetzner_key" \
  root@62.238.3.148:/opt/sajha/data/app/ \
  ec2-user@<ec2-ip>:/mnt/efs/

# Step 4 — Migrate PostgreSQL
# On Hetzner VPS:
docker exec sajha-postgres pg_dump -U sajha sajha > sajha_backup.sql
# On RDS:
psql -h sajha-prod.xxxxx.rds.amazonaws.com -U sajha sajha < sajha_backup.sql

# Step 5 — Update GitHub Actions + redeploy
# Update deploy.yml (SSH step → ECS update-service)
# Update Secrets Manager with all env vars
# Push to main → CI builds → ECS deploys
```

---

## AWS Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │           AWS (us-east-1)                │
                    │                                          │
Internet ──► ALB ──►│  ECS Fargate Task                        │
            :443    │  ┌─────────────────────────────────────┐ │
                    │  │ Single Container (supervisord)      │ │
                    │  │  nginx :80                          │ │
                    │  │  FastAPI :8000 (loopback)           │ │
                    │  │  Flask/SAJHA :3002 (loopback)       │ │
                    │  └────────────┬────────────────────────┘ │
                    │               │                          │
                    │    ┌──────────┴──────────┐              │
                    │    ▼                     ▼              │
                    │  RDS PostgreSQL 16      EFS             │
                    │  (checkpoints,          /app/sajhamcpserver/data
                    │   users, config)        (all tool data) │
                    │                                          │
                    └─────────────────────────────────────────┘

Container image: ECR or GHCR (same Dockerfile as Hetzner)
Secrets: AWS Secrets Manager → injected as env vars at task start
CI/CD: GitHub Actions → aws ecs update-service (replaces SSH to Hetzner)
```

---

## Verify Before Migrating

Check the `Dockerfile` at the repo root:
- Must NOT copy `sajhamcpserver/data/` into the image (data lives on EFS, not in container)
- Must NOT hardcode any paths or credentials
- Should run as non-root user
- `EXPOSE 80` for ALB health checks

---

## Future: Full S3 Migration (Post AWS Move)

Once running on AWS, the optional next step is replacing EFS with S3 for file storage (REQ-16). This requires fixing the 15 tool files that use direct filesystem paths — see `requirements/pending/REQ-16_Hetzner_S3_Migration.md` for the full spec. EFS can be kept indefinitely if S3 migration is not a priority.

---

## Key Contacts & References

| Resource | Location |
|----------|----------|
| REQ-16 S3 Migration | `requirements/pending/REQ-16_Hetzner_S3_Migration.md` |
| Current docker-compose | `docker-compose.prod.yml` |
| CI/CD pipeline | `.github/workflows/deploy.yml` |
| All env vars | `Documentation/Deployment_Guide.docx` Section 4 |
| Hetzner VPS IP | `62.238.3.148` (GitHub Secret: `SERVER_IP`) |
