## B-Pulse Digital Workers — AWS Enterprise Deployment Guide

**Version:** 1.0 · April 2026  
**Audience:** DevOps / Platform engineers onboarding a new enterprise client  
**Scope:** Current stack only — self-hosted PostgreSQL (RDS), no Redshift, no S3 migration yet

---

## Quick Reference — Read This First

### What Actually Changes (the 4 swaps)

> The application is already infrastructure-agnostic. Zero application code changes required. You are replacing four infrastructure pieces underneath an app that doesn't know what cloud it's on.

| Hetzner | AWS | Change required |
|---|---|---|
| Postgres in Docker container | RDS PostgreSQL 16 | Connection string only |
| Docker named volume (`/opt/sajha/data/app`) | EFS mounted at same path | Zero — POSIX filesystem preserved |
| `.env` file written by SSH | Secrets Manager → ECS injects as env vars | ECS task definition JSON |
| SSH + `docker compose pull` in CI | `aws ecs update-service` | deploy.yml only |

**Total application code changes: zero.**

---

### The 9 Deployment Steps

1. **VPC + security groups** — private subnets for RDS and EFS, ECS task in private subnet behind ALB
2. **RDS PostgreSQL 16** — `db.t3.medium`, Multi-AZ, private subnet, no public access
3. **EFS** — create filesystem + mount target in same VPC, allow NFS from ECS security group
4. **Secrets Manager** — store all env vars (Anthropic key, JWT secret, DB password, Tavily key)
5. **ECR** — create repo, push same Docker image (IAM auth, no PAT needed)
6. **ECS Fargate** — task definition with EFS mount at `/app/sajhamcpserver/data` + Secrets Manager injection
7. **ALB** — internet-facing, HTTPS with ACM cert, health check hits `/health`
8. **GitHub Actions** — replace SSH deploy step with `aws ecs update-service`
9. **Data migration** — `pg_dump` → `pg_restore` to RDS; rsync file volume → EFS via EC2 bastion

---

### Critical Gotchas

1. **`SAJHA_BASE_URL` stays `http://127.0.0.1:3002`** — single container, localhost works inside ECS task
2. **EFS mount target must be in the same VPC as ECS** — container starts but data path is empty if wrong
3. **Watchtower doesn't exist in ECS** — remove it, ECS rolling updates replace it
4. **Fargate needs NAT gateway** if placed in a private subnet (to pull ECR images)

---

### Multi-Client Scale (CDK)

Once one manual deploy works, parameterize it as a CDK stack. Each enterprise client gets: isolated RDS, isolated EFS, ALB with their subdomain, their own Secrets Manager entries — all pointing at the **same Docker image**. `cdk deploy sajha-client-bmo` provisions everything in one command.

---

## Mental Model First

Before touching AWS, make sure everyone on the team understands **why this is easy**:

> The application is already infrastructure-agnostic. It runs in a single Docker container, reads all configuration from environment variables, and uses standard Postgres drivers. You are not migrating application code. You are replacing four infrastructure pieces underneath an app that doesn't know what cloud it's on.

What we're swapping:

| Hetzner Today | AWS Enterprise | Code changes? |
|---|---|---|
| Docker Compose on VPS | ECS Fargate (serverless containers) | None |
| Postgres in Docker container | RDS PostgreSQL 16 | None — connection string only |
| Docker named volume (`app_data`) | EFS (network filesystem, same mount path) | None |
| `.env` file written by SSH | Secrets Manager → ECS env vars | None |
| SSH + `docker compose pull` in CI | `aws ecs update-service` in CI | deploy.yml only |

**Total application code changes: zero.**

---

## Architecture: What You're Building

```
GitHub (source code)
        │
        ▼
GitHub Actions (CI/CD)
  ├── Build Docker image (same Dockerfile as Hetzner)
  ├── Push to ECR (AWS container registry)
  └── aws ecs update-service → rolling deploy
                │
                ▼
        ┌─────────────────────────────────────────┐
        │           AWS (us-east-1)                │
        │                                          │
        │  VPC (private network)                   │
        │  ┌────────────────────────────────────┐  │
        │  │  ECS Fargate Cluster               │  │
        │  │                                    │  │
Internet──► ALB (port 443 HTTPS)                │  │
        │  │   │                                │  │
        │  │   ▼                                │  │
        │  │  ECS Task (single container)       │  │
        │  │  ┌──────────────────────────────┐  │  │
        │  │  │ nginx :80                    │  │  │
        │  │  │ FastAPI :8000 (loopback)     │  │  │
        │  │  │ Flask/SAJHA :3002 (loopback) │  │  │
        │  │  └──────────────┬───────────────┘  │  │
        │  │                 │                  │  │
        │  │    ┌────────────┴──────────┐       │  │
        │  │    ▼                       ▼       │  │
        │  │  RDS PostgreSQL 16        EFS      │  │
        │  │  (checkpoints, users)     (tool data, uploads,
        │  │                           BM25 index, charts)
        │  └────────────────────────────────────┘  │
        │                                          │
        │  Secrets Manager (all env vars)          │
        │  ECR (Docker image registry)             │
        └─────────────────────────────────────────┘
```

Key design decisions:
- **Single container** — no need to split the app into microservices. supervisord manages nginx, FastAPI, and Flask inside one container. This is intentional.
- **ALB terminates TLS** — the container only needs to serve HTTP on port 80. HTTPS is handled by ALB + ACM certificate.
- **EFS replaces Docker volume** — not S3, because 15 tool files use `os.walk` / `shutil` / local paths. EFS is a network filesystem with the same POSIX interface — zero code changes. S3 is a future migration (REQ-16).
- **RDS is just managed Postgres** — not Aurora, not Redshift. The app uses psycopg with standard SQL. It works on any PostgreSQL 16 instance.

---

## Prerequisites

Before starting, the team needs:

1. **AWS Account** with admin access (for initial setup; tighten IAM after)
2. **AWS CLI v2** configured: `aws configure`
3. **GitHub repository access** — to update `deploy.yml`
4. **Domain name** (optional but recommended for enterprise) — for ALB HTTPS certificate via ACM
5. **Existing Hetzner access** — for data migration (SSH key for `root@62.238.3.148`)

Tools to install:
```bash
# AWS CLI
brew install awscli
aws configure  # enter Access Key, Secret Key, region (us-east-1), output (json)

# Verify
aws sts get-caller-identity
```

---

## Step 1 — VPC and Networking

Use the **default VPC** for initial enterprise deployments — it exists in every AWS account and has public/private subnets in multiple AZs.

If the client requires a private VPC:
```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=sajha-prod}]'

# Create subnets (2 AZs minimum for RDS Multi-AZ and ALB)
aws ec2 create-subnet --vpc-id vpc-xxxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxxx --cidr-block 10.0.2.0/24 --availability-zone us-east-1b
```

For internal services (RDS, EFS), use **private subnets** (no route to internet gateway). The ECS task goes in a **private subnet** behind the ALB.

---

## Step 2 — RDS PostgreSQL 16

This replaces `sajha-postgres` from `docker-compose.prod.yml`. It is PostgreSQL 16 — exact same database engine, just managed.

```bash
# Create subnet group (RDS needs 2+ AZs)
aws rds create-db-subnet-group \
  --db-subnet-group-name sajha-prod-sg \
  --db-subnet-group-description "Sajha prod DB" \
  --subnet-ids subnet-xxxx subnet-yyyy

# Create security group for RDS (allow Postgres from ECS SG only)
aws ec2 create-security-group \
  --group-name sajha-rds-sg \
  --description "Sajha RDS access" \
  --vpc-id vpc-xxxx

# Allow port 5432 from the ECS task security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-rds-xxxx \
  --protocol tcp \
  --port 5432 \
  --source-group sg-ecs-xxxx

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier sajha-prod \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16 \
  --master-username sajha \
  --master-user-password <strong-password-here> \
  --allocated-storage 20 \
  --max-allocated-storage 100 \
  --db-subnet-group-name sajha-prod-sg \
  --vpc-security-group-ids sg-rds-xxxx \
  --multi-az \
  --no-publicly-accessible \
  --deletion-protection \
  --backup-retention-period 7
```

Wait for it to become available (~10 minutes):
```bash
aws rds wait db-instance-available --db-instance-identifier sajha-prod

# Get the endpoint
aws rds describe-db-instances \
  --db-instance-identifier sajha-prod \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text
# → sajha-prod.xxxxxxxxx.us-east-1.rds.amazonaws.com
```

**Connection string that goes into Secrets Manager later:**
```
postgresql+psycopg://sajha:<password>@sajha-prod.xxxxxxxxx.us-east-1.rds.amazonaws.com:5432/sajha
```

---

## Step 3 — EFS (Elastic File System)

This replaces the `app_data` Docker named volume. It mounts at the **same path** the app already uses: `/app/sajhamcpserver/data`.

```bash
# Create filesystem
EFS_ID=$(aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=sajha-prod-data \
  --query 'FileSystemId' \
  --output text)

echo "EFS ID: $EFS_ID"

# Create mount target in each private subnet
aws efs create-mount-target \
  --file-system-id $EFS_ID \
  --subnet-id subnet-xxxx \
  --security-groups sg-efs-xxxx

aws efs create-mount-target \
  --file-system-id $EFS_ID \
  --subnet-id subnet-yyyy \
  --security-groups sg-efs-xxxx
```

EFS security group rule — allow NFS (port 2049) from ECS task SG:
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-efs-xxxx \
  --protocol tcp \
  --port 2049 \
  --source-group sg-ecs-xxxx
```

---

## Step 4 — Secrets Manager

Every environment variable that was in the Hetzner `.env` file goes here.

```bash
# Store each secret individually — easier to rotate and audit
aws secretsmanager create-secret --name sajha/ANTHROPIC_API_KEY    --secret-string "sk-ant-..."
aws secretsmanager create-secret --name sajha/JWT_SECRET           --secret-string "$(openssl rand -base64 64)"
aws secretsmanager create-secret --name sajha/POSTGRES_PASSWORD    --secret-string "<rds-password>"
aws secretsmanager create-secret --name sajha/TAVILY_API_KEY       --secret-string "tvly-..."
aws secretsmanager create-secret --name sajha/SAJHA_API_KEY        --secret-string "sja_full_access_admin"
aws secretsmanager create-secret --name sajha/AGENT_API_KEYS       --secret-string ""

# Optional connectors
aws secretsmanager create-secret --name sajha/XAI_API_KEY          --secret-string ""
aws secretsmanager create-secret --name sajha/HF_API_KEY           --secret-string ""
```

Get the ARNs (you'll need them in the task definition):
```bash
aws secretsmanager list-secrets \
  --filter Key=name,Values=sajha/ \
  --query 'SecretList[].{Name:Name,ARN:ARN}' \
  --output table
```

---

## Step 5 — ECR (Container Registry)

ECR replaces GHCR for enterprise deployments. Simpler auth — IAM handles it, no PAT needed.

```bash
# Create repository
aws ecr create-repository \
  --repository-name sajha-agent \
  --image-scanning-configuration scanOnPush=true

# Get the URI
ECR_URI=$(aws ecr describe-repositories \
  --repository-names sajha-agent \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "ECR URI: $ECR_URI"
# → 123456789.dkr.ecr.us-east-1.amazonaws.com/sajha-agent
```

---

## Step 6 — ECS Cluster and Task Definition

### 6a. Create ECS Cluster
```bash
aws ecs create-cluster \
  --cluster-name sajha-prod \
  --capacity-providers FARGATE \
  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1
```

### 6b. IAM Role for ECS Task
The task needs permission to read from Secrets Manager and ECR.

```bash
# Create task execution role
aws iam create-role \
  --role-name sajha-ecs-task-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach managed policies
aws iam attach-role-policy \
  --role-name sajha-ecs-task-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Allow Secrets Manager reads (inline policy)
aws iam put-role-policy \
  --role-name sajha-ecs-task-role \
  --policy-name SecretsManagerRead \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:sajha/*"
    }]
  }'
```

### 6c. Task Definition (save as `ecs-task-def.json`)

Replace `ACCOUNT_ID`, `EFS_ID`, and RDS endpoint with your values:

```json
{
  "family": "sajha-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/sajha-ecs-task-role",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/sajha-ecs-task-role",

  "containerDefinitions": [{
    "name": "sajha-app",
    "image": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/sajha-agent:latest",
    "portMappings": [{"containerPort": 80, "protocol": "tcp"}],

    "environment": [
      {"name": "PORT",                  "value": "80"},
      {"name": "PYTHONUNBUFFERED",      "value": "1"},
      {"name": "LLM_PROVIDER",          "value": "anthropic"},
      {"name": "ANTHROPIC_MODEL",       "value": "claude-sonnet-4-20250514"},
      {"name": "LLM_MAX_TOKENS",        "value": "8192"},
      {"name": "DATABASE_URL",          "value": "postgresql+psycopg://sajha:REPLACED_BY_SECRET@sajha-prod.xxxx.rds.amazonaws.com:5432/sajha"},
      {"name": "DATABASE_URL_SYNC",     "value": "postgresql+psycopg2://sajha:REPLACED_BY_SECRET@sajha-prod.xxxx.rds.amazonaws.com:5432/sajha"},
      {"name": "SAJHA_BASE_URL",        "value": "http://127.0.0.1:3002"},
      {"name": "STORAGE_BACKEND",       "value": "local"},
      {"name": "DATA_ROOT",             "value": "/app/sajhamcpserver/data"},
      {"name": "CONTEXT_TRIGGER_TOKENS","value": "180000"},
      {"name": "CONTEXT_TARGET_PCT",    "value": "0.18"}
    ],

    "secrets": [
      {"name": "ANTHROPIC_API_KEY",  "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:sajha/ANTHROPIC_API_KEY"},
      {"name": "JWT_SECRET",         "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:sajha/JWT_SECRET"},
      {"name": "POSTGRES_PASSWORD",  "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:sajha/POSTGRES_PASSWORD"},
      {"name": "TAVILY_API_KEY",     "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:sajha/TAVILY_API_KEY"},
      {"name": "SAJHA_API_KEY",      "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:sajha/SAJHA_API_KEY"},
      {"name": "AGENT_API_KEYS",     "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:sajha/AGENT_API_KEYS"}
    ],

    "mountPoints": [{
      "sourceVolume": "sajha-data",
      "containerPath": "/app/sajhamcpserver/data",
      "readOnly": false
    }],

    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/sajha-agent",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    },

    "healthCheck": {
      "command": ["CMD-SHELL", "curl -sf http://localhost/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3,
      "startPeriod": 60
    }
  }],

  "volumes": [{
    "name": "sajha-data",
    "efsVolumeConfiguration": {
      "fileSystemId": "EFS_ID",
      "transitEncryption": "ENABLED"
    }
  }]
}
```

Register the task definition:
```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-def.json

# Create CloudWatch log group first
aws logs create-log-group --log-group-name /ecs/sajha-agent
```

---

## Step 7 — ALB (Application Load Balancer)

The ALB terminates HTTPS and forwards HTTP to the container on port 80.

```bash
# Create target group (health check hits /health)
aws elbv2 create-target-group \
  --name sajha-prod-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-xxxx \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Create ALB
aws elbv2 create-load-balancer \
  --name sajha-prod-alb \
  --subnets subnet-xxxx subnet-yyyy \
  --security-groups sg-alb-xxxx \
  --scheme internet-facing

# Create HTTPS listener (requires ACM certificate)
aws elbv2 create-listener \
  --load-balancer-arn <alb-arn> \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=<acm-cert-arn> \
  --default-actions Type=forward,TargetGroupArn=<tg-arn>

# HTTP → HTTPS redirect
aws elbv2 create-listener \
  --load-balancer-arn <alb-arn> \
  --protocol HTTP \
  --port 80 \
  --default-actions '[{"Type":"redirect","RedirectConfig":{"Protocol":"HTTPS","Port":"443","StatusCode":"HTTP_301"}}]'
```

**ACM Certificate (HTTPS):**
```bash
aws acm request-certificate \
  --domain-name app.yourclient.com \
  --validation-method DNS
# Follow DNS validation in Route 53 or your DNS provider
```

---

## Step 8 — ECS Service

```bash
aws ecs create-service \
  --cluster sajha-prod \
  --service-name sajha-app \
  --task-definition sajha-agent \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-xxxx,subnet-yyyy],
    securityGroups=[sg-ecs-xxxx],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=<tg-arn>,containerName=sajha-app,containerPort=80" \
  --health-check-grace-period-seconds 120 \
  --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100"
```

Watch the service start:
```bash
aws ecs describe-services \
  --cluster sajha-prod \
  --services sajha-app \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

---

## Step 9 — Update GitHub Actions (CI/CD)

Replace the SSH/docker-compose deploy step in `.github/workflows/deploy.yml`.

**Add these GitHub Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` = `us-east-1`
- `ECR_REGISTRY` = `ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com`
- `ECS_CLUSTER` = `sajha-prod`
- `ECS_SERVICE` = `sajha-app`

**New deploy.yml:**
```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  ECR_REPOSITORY: sajha-agent

jobs:
  build-and-push:
    name: Build & Push to ECR
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push to ECR
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}
            ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    name: Deploy to ECS
    needs: build-and-push
    runs-on: ubuntu-latest

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Force new ECS deployment
        run: |
          aws ecs update-service \
            --cluster ${{ secrets.ECS_CLUSTER }} \
            --service ${{ secrets.ECS_SERVICE }} \
            --force-new-deployment

      - name: Wait for deployment to complete
        run: |
          aws ecs wait services-stable \
            --cluster ${{ secrets.ECS_CLUSTER }} \
            --services ${{ secrets.ECS_SERVICE }}
          echo "Deployment complete."
```

---

## Step 10 — Migrate Existing Data

This is a one-time step when moving a live Hetzner deployment to AWS.

### 10a. Migrate PostgreSQL

```bash
# On Hetzner — dump the database
ssh root@62.238.3.148
docker exec sajha-postgres pg_dump -U sajha -Fc sajha > /opt/sajha/sajha_backup.dump

# Copy dump locally
scp root@62.238.3.148:/opt/sajha/sajha_backup.dump ./sajha_backup.dump

# Restore to RDS
# (must be run from a machine with network access to RDS — use an EC2 bastion or temporarily allow your IP)
pg_restore \
  -h sajha-prod.xxxxxxxxx.us-east-1.rds.amazonaws.com \
  -U sajha \
  -d sajha \
  --no-owner \
  sajha_backup.dump
```

### 10b. Migrate File Data (volume → EFS)

The `app_data` volume holds tool data, uploads, BM25 index, charts, and domain data. Mount the EFS on a temporary EC2 instance and rsync from Hetzner.

```bash
# Launch a small EC2 instance in the same VPC
# Mount EFS on it:
sudo mount -t nfs4 \
  -o nfsvers=4.1,rsize=1048576,wsize=1048576 \
  $EFS_ID.efs.us-east-1.amazonaws.com:/ \
  /mnt/efs

# Rsync from Hetzner
rsync -avz --progress \
  -e "ssh -i ~/.ssh/hetzner_key" \
  root@62.238.3.148:/opt/sajha/data/app/ \
  ec2-user@<ec2-ip>:/mnt/efs/

# Verify
ls /mnt/efs/workers/
# → w-market-risk/  (and any other workers)
```

---

## Step 11 — Verify the Deployment

```bash
# 1. Check ECS service is stable
aws ecs describe-services \
  --cluster sajha-prod \
  --services sajha-app \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,TaskDef:taskDefinition}'

# 2. Check task is running (get task ARN)
TASK_ARN=$(aws ecs list-tasks \
  --cluster sajha-prod \
  --service-name sajha-app \
  --query 'taskArns[0]' \
  --output text)

# 3. Stream logs
aws logs tail /ecs/sajha-agent --follow

# 4. Health check via ALB
curl -sf https://app.yourclient.com/health
# → {"status": "ok"}

# 5. Login test
curl -X POST https://app.yourclient.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id": "risk_agent", "password": "RiskAgent2025!"}'
# → {"token": "...", "role": "super_admin", ...}
```

---

## Common Mistakes to Avoid

| Mistake | What happens | How to avoid |
|---|---|---|
| EFS mount target not in same VPC as ECS | Task can't mount EFS — starts but data path is empty | Create mount target in same VPC, allow NFS port 2049 from ECS SG |
| RDS security group doesn't allow ECS SG | `psycopg` connection refused — agent fails | Add inbound rule: TCP 5432 from ECS task security group |
| Secrets Manager ARN wrong in task def | Container won't start — `ResourceNotFoundException` | ARN format: `arn:aws:secretsmanager:REGION:ACCOUNT:secret:NAME-SUFFIX` |
| DATABASE_URL still pointing at `postgres:5432` | Connects to non-existent Docker DNS name | Replace with full RDS endpoint in task def or Secrets Manager |
| Fargate task in public subnet with `assignPublicIp=DISABLED` | Can't pull ECR image | Use private subnet with NAT gateway, or enable `assignPublicIp=ENABLED` temporarily |
| Missing `SAJHA_BASE_URL=http://127.0.0.1:3002` | Agent can't reach SAJHA MCP server | Keep this as `127.0.0.1` — single container, localhost still valid in ECS |
| Watchtower service in ECS | No Docker socket in Fargate — Watchtower is useless | Remove Watchtower — ECS rolling updates replace it |

---

## Multi-Client (Enterprise CDK Pattern)

Once you've done one manual deployment above, the next step is automating it per-client with CDK.

The Docker image is shared — only the environment variables differ per client.

```
CDK Stack: sajha-client-bmo
├── VPC (or use existing client VPC)
├── RDS PostgreSQL 16 (client-isolated)
├── EFS (client-isolated mount)
├── ECS Cluster + Service
├── ALB + ACM cert for bmo.bpulse.ai
├── Secrets Manager (BMO API keys)
└── CloudWatch dashboard + alarms

CDK Stack: sajha-client-td
└── ... (same stack, different env vars + subdomain)
```

```typescript
// cdk/lib/sajha-stack.ts (simplified)
export class SajhaStack extends Stack {
  constructor(scope: Construct, id: string, props: SajhaStackProps) {
    // props: { clientId, domain, anthropicKeyArn, postgresPassword }
    
    const cluster = new ecs.Cluster(this, 'Cluster', { vpc: props.vpc });
    
    const taskDef = new ecs.FargateTaskDefinition(this, 'Task', {
      cpu: 2048,
      memoryLimitMiB: 4096,
    });
    
    taskDef.addContainer('sajha-app', {
      image: ecs.ContainerImage.fromEcrRepository(repo, 'latest'),
      environment: {
        LLM_PROVIDER: 'anthropic',
        SAJHA_BASE_URL: 'http://127.0.0.1:3002',
        DATABASE_URL: `postgresql+psycopg://.../${props.clientId}`,
      },
      secrets: {
        ANTHROPIC_API_KEY: ecs.Secret.fromSecretsManager(props.anthropicKeySecret),
        JWT_SECRET: ecs.Secret.fromSecretsManager(jwtSecret),
      },
    });
    
    // ALB + HTTPS listener pointing to client domain
    // ...
  }
}
```

`cdk deploy sajha-client-bmo` provisions everything for BMO in one command. Same Docker image, different secrets, isolated database, isolated file storage.

---

## Key Differences: Hetzner vs AWS for the Team

| Question | Hetzner | AWS |
|---|---|---|
| How do I check if the app is running? | `ssh root@VPS "docker ps"` | `aws ecs describe-services --cluster sajha-prod --services sajha-app` |
| How do I see logs? | `docker compose logs -f app` | `aws logs tail /ecs/sajha-agent --follow` |
| How do I deploy a new version? | Push to main → GitHub Actions SSHes in | Push to main → GitHub Actions runs `ecs update-service` |
| How do I restart the app? | `docker compose restart app` | `aws ecs update-service --cluster sajha-prod --service sajha-app --force-new-deployment` |
| How do I update a secret/env var? | Edit `.env` on server, restart | Update in Secrets Manager, redeploy |
| How do I access the database? | `docker exec -it sajha-postgres psql -U sajha` | `psql -h <rds-endpoint> -U sajha` (from bastion or VPN) |
| Where is the data? | `/opt/sajha/data/app` on VPS | EFS, mounted at same path inside container |
| How do I scale? | Upgrade VPS plan | Change ECS desired count or Fargate task CPU/memory |

---

## References

| Document | Location |
|---|---|
| Infra-Agnostic Strategy | `Documentation/Infra_Agnostic_Strategy.md` |
| Current Hetzner CI/CD | `.github/workflows/deploy.yml` |
| Current docker-compose | `docker-compose.prod.yml` |
| S3 Migration (future) | `requirements/pending/REQ-16_Hetzner_S3_Migration.md` |
| All env variables | `Documentation/Deployment_Guide.docx` Section 4 |
| Health endpoint | `GET /health → {"status": "ok"}` |
| Default super admin | `risk_agent` / `RiskAgent2025!` |
