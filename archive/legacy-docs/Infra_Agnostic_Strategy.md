# B-Pulse Digital Workers — Infrastructure-Agnostic Build Strategy

**Version:** 1.0 · April 2026  
**Audience:** Engineering leads, DevOps, enterprise deployment teams  

---

## The Core Problem

Personal/startup infrastructure and enterprise infrastructure are fundamentally different. The goal is to make the *application code* not care which one it's running on — so switching is a config change, not a rewrite.

---

## The 3 Things That Must Be Decoupled

### 1. Database
Both Hetzner Postgres and AWS RDS are standard PostgreSQL. If you never use platform-specific features (Supabase Auth, Edge Functions, RLS), your SQL and queries work identically across providers. The transition is a connection string swap.

**What we did:** Standard `psycopg2`/`psycopg` drivers throughout. No ORM magic, no platform SDK. `DATABASE_URL` is an env var — change the host, everything works.

### 2. File Storage
Object storage across all providers (Hetzner, AWS S3, Azure Blob, GCS) is S3-compatible. Using the AWS SDK (boto3) with a custom `endpoint_url` works against any of them — same code, different endpoint.

**What we did:** `storage.py` abstraction layer already implemented with `LocalStorageBackend` and `S3StorageBackend`. Switch via `STORAGE_BACKEND=s3`. Hetzner Object Storage migration tracked in REQ-16.

### 3. Compute
Docker containers are portable by definition. As long as the app reads config from environment variables (never hardcoded), the same Docker image deploys on Hetzner VPS, AWS ECS/Fargate, Azure Container Apps, or GCP Cloud Run.

**What we did:** Single Dockerfile with supervisord. All config via env vars. `EXPOSE 80`. Health check at `GET /health`.

---

## Current State: Hetzner VPS

```
GitHub (source) ──► GitHub Actions ──► GHCR (image registry)
                                              │
                                              ▼
                                    Hetzner CPX32 VPS
                                    ┌─────────────────────────┐
                                    │  Docker Compose          │
                                    │                          │
                                    │  ┌──────────────────┐   │
                                    │  │ sajha-app        │   │
                                    │  │ (single container│   │
                                    │  │  supervisord)    │   │
                                    │  │  nginx :80       │   │
                                    │  │  FastAPI :8000   │   │
                                    │  │  Flask :3002     │   │
                                    │  └────────┬─────────┘   │
                                    │           │             │
                                    │  ┌────────▼─────────┐   │
                                    │  │ sajha-postgres   │   │
                                    │  │ PostgreSQL 16    │   │
                                    │  └──────────────────┘   │
                                    │                          │
                                    │  Docker Volume           │
                                    │  /opt/sajha/data/app     │
                                    │  (tool data, uploads,    │
                                    │   BM25 index, charts)    │
                                    └─────────────────────────┘
```

**What's infra-agnostic today:**
- ✅ All config via environment variables
- ✅ Standard Postgres drivers (psycopg, psycopg2)
- ✅ Single Dockerfile — same image deploys anywhere
- ✅ S3 storage abstraction layer built (boto3, switches on `STORAGE_BACKEND`)
- ✅ Health check endpoint (`GET /health`)
- ✅ JWT auth, no platform-specific auth SDK
- ✅ No hardcoded IPs, hostnames, or credentials in code

**What's not yet infra-agnostic:**
- ⚠️ 15 tool files use direct filesystem paths (`os.walk`, `read_csv_auto('/path')`, `shutil`) — tied to local disk / Docker volume
- ⚠️ DuckDB passes local filesystem paths — needs httpfs for S3
- ⚠️ Secrets in `.env` file written by GitHub Actions SSH — needs Secrets Manager for ECS

---

## Target State: AWS (Current Stack, No New Features)

```
GitHub (source) ──► GitHub Actions ──► ECR (image registry)
                                              │
                                              ▼
                                    AWS (us-east-1)
                                    ┌─────────────────────────┐
                                    │  ECS Fargate             │
                                    │                          │
                                    │  ┌──────────────────┐   │
                                    │  │ Task (single     │   │
                          ALB :443 ─┼─►│  container,      │   │
                                    │  │  supervisord)    │   │
                                    │  │  nginx :80       │   │
                                    │  │  FastAPI :8000   │   │
                                    │  │  Flask :3002     │   │
                                    │  └────────┬─────────┘   │
                                    │           │             │
                                    │  ┌────────┴──────────┐  │
                                    │           │              │
                                    │  ┌────────▼─────────┐   │
                                    │  │ RDS PostgreSQL 16│   │
                                    │  └──────────────────┘   │
                                    │                          │
                                    │  ┌──────────────────┐   │
                                    │  │ EFS              │   │
                                    │  │ mounted at       │   │
                                    │  │ /app/sajhamcp    │   │
                                    │  │ server/data      │   │
                                    │  └──────────────────┘   │
                                    │                          │
                                    │  Secrets Manager         │
                                    │  (all env vars)          │
                                    └─────────────────────────┘
```

**Same Docker image. Same application code. Different infra underneath.**

---

## Transition Gap Analysis

| Component | Hetzner Today | AWS Target | Code Change? |
|-----------|--------------|------------|--------------|
| Compute | Docker Compose on VPS | ECS Fargate | None — same Dockerfile |
| Database | Postgres on same VPS | RDS PostgreSQL 16 | None — connection string only |
| File storage | Docker volume | EFS (same mount path) | None — POSIX filesystem preserved |
| Secrets | `.env` via SSH | Secrets Manager | None — still env vars |
| Container registry | GHCR | ECR | None — image format identical |
| CI/CD deploy step | SSH + docker compose | aws ecs update-service | deploy.yml only |
| Load balancing | nginx in container | ALB + nginx in container | None |
| Auto-update | Watchtower | ECS rolling update | Remove watchtower service |
| Logs | Container stdout | CloudWatch | None — stdout captured automatically |

**Total application code changes: zero.**  
**Infra/config changes: 4** (RDS endpoint, EFS mount, Secrets Manager, deploy.yml)

---

## Habits That Make This Work

These are the practices baked into the codebase that keep it infra-agnostic:

| Practice | Where |
|----------|-------|
| All secrets in env vars, never hardcoded | Enforced via `.gitignore` + `.env` pattern |
| Standard Postgres drivers only | `psycopg`, `psycopg2` throughout — no Supabase SDK |
| S3 SDK for object storage (not provider SDK) | `storage.py` — boto3 with `endpoint_url` override |
| Docker-first compute | Single Dockerfile, supervisord, `EXPOSE 80` |
| Health check endpoint | `GET /health → {"status": "ok"}` |
| Config hot-reload | Tool configs, LLM config, worker config — no restart needed |
| Worker-scoped data paths | All data under `data/workers/{worker_id}/` — clean tenant isolation |

---

## What Comes After AWS Migration

Once running on AWS with EFS, the optional improvements that unlock further scale:

### REQ-16 — S3 for file storage (replaces EFS)
Fix 15 tool files that bypass the storage abstraction. Replaces EFS with S3 — cheaper, no capacity planning, built-in durability. See `requirements/pending/REQ-16_Hetzner_S3_Migration.md`.

### CDK Stack for enterprise clients
When BMO or another enterprise client wants their own deployment, a CDK stack provisions: ECS cluster, RDS, EFS (or S3 after REQ-16), ALB, Secrets Manager, CloudWatch — all pointing at the same Docker image with client-specific env vars. Deployment becomes a `cdk deploy` command.

```
CDK Stack (per enterprise client)
├── ECS Fargate cluster
├── RDS PostgreSQL 16 (client-isolated)
├── EFS or S3 (client-isolated bucket/filesystem)
├── ALB with HTTPS + WAF
├── Secrets Manager (client credentials)
└── CloudWatch dashboards + alarms
```

The application code doesn't change between clients — only the env vars differ.

---

## One-Liner Summary

Build infra-agnostic today (S3 SDK, standard Postgres, env vars, Docker) — then Hetzner → AWS is 4 config changes and a CI/CD update, not a rewrite. Enterprise client onboarding becomes a CDK deploy pointing at the same Docker image with different connection strings.

---

## References

| Document | Location |
|----------|----------|
| AWS Migration Runbook (current stack) | `Documentation/AWS_Migration_Guide.md` |
| S3 Migration Requirements | `requirements/pending/REQ-16_Hetzner_S3_Migration.md` |
| Current docker-compose | `docker-compose.prod.yml` |
| CI/CD pipeline | `.github/workflows/deploy.yml` |
| Deployment Guide | `Documentation/Deployment_Guide.docx` |
| Technical Documentation | `Documentation/Technical_Documentation.docx` |
