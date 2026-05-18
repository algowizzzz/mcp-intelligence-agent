# B-Pulse Digital Workers

> **Source:** Converted from `Deployment_Guide.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**B-Pulse Digital Workers**

Enterprise Cloud Deployment Guide

April 2026 · AWS / Azure / GCP

**1. Deployment Overview**

B-Pulse Digital Workers is a containerised platform supporting deployment on AWS ECS/EKS, Azure AKS, or any Kubernetes-compatible environment. The platform has two components: the Agent Server (FastAPI) and the SAJHA MCP Server (Flask), which must run in the same private network.

|  |
|----|
| The agent-server is the only service that should be publicly accessible. The sajha-mcp service must remain internal-only. |

**1.1 Production Architecture Components**

|  |  |  |
|----|----|----|
| **Component** | **Type** | **Notes** |
| HTTPS Load Balancer | ALB / AGW / Cloud LB | TLS termination; forwards to agent-server:8000 |
| agent-server container | Python FastAPI | 2 tasks minimum (HA); 1 vCPU / 2 GB RAM per task |
| sajha-mcp container | Python Flask | 1-2 tasks; 2 vCPU / 4 GB RAM per task (tool execution) |
| Shared Config Storage | EFS / Azure Files / GCS | Config JSON files; mounted read-write |
| Audit Storage | S3 / Blob / GCS | Append-only audit JSONL; WORM policy recommended |
| PostgreSQL (future) | RDS / Cloud SQL / Azure DB | REQ-07 migration; conversation history + users |

**2. Docker Build**

**2.1 Agent Server Dockerfile**

```
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "agent_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

**2.2 SAJHA MCP Server Dockerfile**

```
FROM python:3.11-slim
WORKDIR /app
COPY sajhamcpserver/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sajhamcpserver/ .
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser
EXPOSE 3002
CMD ["python3", "run_server.py"]
```

**2.3 Docker Compose (Staging / Dev)**

> version: '3.9'
> services:
> agent-server:
> build: .
> ports: ["8000:8000"]
> environment:
> - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
> - TAVILY_API_KEY=${TAVILY_API_KEY}
> - AGENT_API_KEYS=${AGENT_API_KEYS}
> - SAJHA_BASE_URL=http://sajha-mcp:3002
> volumes:
> - config-data:/app/sajhamcpserver/config
> - audit-data:/app/sajhamcpserver/data/audit
> depends_on: [sajha-mcp]
> sajha-mcp:
> build:
> context: .
> dockerfile: sajhamcpserver/Dockerfile
> expose: ["3002"]
> volumes:
> - config-data:/app/config
> - domain-data:/app/data/domain_data
> - audit-data:/app/data/audit
> volumes:
> config-data:
> domain-data:
> audit-data:

**3. Secret Management**

|  |
|----|
| NEVER store secrets in Docker images, committed config files, or environment variable files in source control. Use a dedicated secret manager. |

|  |  |  |
|----|----|----|
| **Secret Name** | **Description** | **Rotation** |
| ANTHROPIC_API_KEY | Claude model API key | Quarterly |
| TAVILY_API_KEY | Web search API key | Quarterly |
| AGENT_API_KEYS | Internal service auth key (min 32 chars) | Monthly |
| JWT_SECRET | JWT signing secret (min 64 chars random) | Monthly |
| CONNECTOR_M365_CLIENT_SECRET | Azure AD app client secret | 90 days |
| CONNECTOR_ATLASSIAN_API_TOKEN | Atlassian personal API token | 180 days |
| DB_PASSWORD | PostgreSQL password (REQ-07) | Quarterly |

**4. AWS ECS Reference Deployment**

**4.1 Key Configuration**

- Launch type: Fargate (serverless; recommended for simplicity)

- Task CPU/Memory: agent-server 1024/2048; sajha-mcp 2048/4096

- Service discovery: AWS Cloud Map (service.local DNS) for internal communication

- Log driver: awslogs to CloudWatch Log Group /bpulse/{service}

- Secrets: inject via Secrets Manager ARNs in task definition secrets\[\] array

- IAM task role: secretsmanager:GetSecretValue, s3:PutObject (audit), efs:ClientMount

**4.2 Auto-Scaling Policy**

- Scale metric: ECS service CPU utilisation (target 70%)

- Scale-out cooldown: 60 seconds

- Scale-in cooldown: 300 seconds (conversations are stateful)

- Min tasks: 2 (across 2 AZs); Max tasks: 10

**5. Health Checks & Monitoring**

|  |  |  |
|----|----|----|
| **Endpoint** | **Expected Response** | **Use** |
| GET /health (agent-server:8000) | {"status":"ok"} | ALB target group health check; 30s interval |
| GET /health (sajha-mcp:3002) | 200 OK | Internal ECS health check |

**5.1 Alerts (Recommended)**

- 5xx error rate \> 1% over 5 minutes → PagerDuty P2

- Tool execution p95 latency \> 30 seconds → CloudWatch alarm

- Container memory \> 80% → scale trigger

- Audit log write failures → P1 alert (compliance event)

- Anthropic API error rate \> 5% → P1 alert (platform inoperable)

**6. Pre-Production Security Checklist**

- \[ \] Remove /api/dev/screenshot endpoint from agent_server.py before build

- \[ \] Implement AES-256-GCM encryption for connector credentials (BUG-CONN-001 / REQ-07)

- \[ \] Verify token_cache.py expiry handling (BUG-CONN-002)

- \[ \] HTTPS only on load balancer — disable HTTP

- \[ \] WAF with OWASP rule set enabled

- \[ \] Port 3002 not reachable from internet or untrusted VPCs

- \[ \] Container image vulnerability scan passes (Trivy)

- \[ \] Non-root user in both Dockerfiles

- \[ \] S3 audit bucket: object lock (WORM) enabled

- \[ \] Load test: 50 concurrent sessions; p95 response \< 5 seconds

- \[ \] Disaster recovery test: AZ failover confirmed \< 60 seconds

- \[ \] Penetration test completed by internal security team
