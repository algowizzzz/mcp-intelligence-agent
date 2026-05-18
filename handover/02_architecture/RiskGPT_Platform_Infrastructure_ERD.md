# RiskGPT

> **Source:** Converted from `RiskGPT_Platform_Infrastructure_ERD.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**RiskGPT**

**Platform Infrastructure ERD**

Docker Consolidation & Unified Authentication

|                      |                      |
|----------------------|----------------------|
| **Document Version** | 1.0                  |
| **Status**           | DRAFT                |
| **Date**             | 2026-04-03           |
| **Author**           | Platform Engineering |
| **Reviewer**         | DevOps / Security    |
| **Classification**   | Internal             |

**Table of Contents**

**1. Executive Summary**

RiskGPT currently runs across three separate processes and two independent authentication systems. This document specifies two complementary infrastructure changes that resolve an enterprise deployment constraint and a security design gap:

|  |
|----|
| **Infrastructure Change 1 — Docker Port Consolidation** |
| Constraint: Enterprise policy allows one externally exposed port per Docker container. |
| Current state: Three ports in use — port 3002 (SAJHA MCP Server), port 8000 (Agent Server), port 8080 (nginx frontend). |
| Fix: Merge all processes into a single container using supervisord. nginx listens on port 80 as the sole external port. SAJHA binds to 127.0.0.1:3002 (loopback-only). Agent Server binds to 127.0.0.1:8000 (loopback-only). nginx proxies /api/ traffic to the Agent Server. |

|  |
|----|
| **Infrastructure Change 2 — Unified Authentication** |
| Constraint: Two separate authentication systems (SAJHA session auth + Agent JWT) with hardcoded service credentials. |
| Current state: Agent proxies login to SAJHA; tool calls use a hardcoded risk_agent session token; SAJHA is exposed on 0.0.0.0 accepting direct inbound auth. |
| Fix: Agent Server becomes the single authority for all authentication and role management. SAJHA is reclassified as a trusted internal service, protected only by a shared X-Service-Key secret. The hardcoded risk_agent credential pattern is eliminated. SAJHA's full session/JWT subsystem is decommissioned. |

Both changes are required for enterprise deployment. They are independent but complementary — the port fix makes SAJHA unreachable from outside the container, which is a prerequisite for the auth simplification. The two changes are therefore delivered together.

**2. Current State Audit**

**2.1 Port Inventory**

Audit of currently active network ports across all three processes:

|  |  |  |  |  |
|----|----|----|----|----|
| **Process** | **Bind Address** | **Port** | **External?** | **Configured In** |
| SAJHA MCP Server | 0.0.0.0 | 3002 | YES — Problem | sajhamcpserver/config/server.properties: server.host=0.0.0.0 |
| Agent Server (uvicorn) | 0.0.0.0 | 8000 | YES | Dockerfile CMD: uvicorn agent_server:app --port 8000 |
| nginx (frontend) | 0.0.0.0 | 8080 | YES | Dockerfile.frontend: EXPOSE 8080 |

|  |
|----|
| **Problem Statement** |
| Three externally exposed ports violate the enterprise one-port-per-container constraint. |
| SAJHA binding to 0.0.0.0:3002 means it is reachable directly from any client that can reach the host — bypassing the Agent Server entirely. |
| Two separate Dockerfiles (Dockerfile, Dockerfile.frontend) produce two containers requiring orchestration even for single-host deployments. |

**2.2 Authentication Architecture — Current State**

The current system has two authentication paths that overlap and create coupling:

**Path A — User Login**

1\. Browser sends POST /api/auth/login to Agent Server (port 8000).

2\. agent_server.py proxies the request to SAJHA: POST http://localhost:3002/api/auth/login with the user's credentials.

3\. SAJHA validates credentials against sajhamcpserver/config/users.json and returns a SAJHA JWT.

4\. Agent Server discards the SAJHA JWT, reads users.json directly (\_SAJHA_USERS_FILE path hardcoded), and issues its own Agent JWT.

5\. Browser stores the Agent JWT and sends it as Bearer on all subsequent requests.

|  |
|----|
| **Problems in Path A** |
| Tight coupling: Agent login fails completely if SAJHA is unreachable — even before any tool call is made. |
| Redundant validation: users.json is validated twice — once by SAJHA and once by Agent (reading the same file). |
| Fragile path: agent_server.py has \_SAJHA_USERS_FILE = pathlib.Path('sajhamcpserver/config/users.json') hardcoded — breaks if directory layout changes. |
| SAJHA must be running before any user can log in, even on the Agent-only startup path. |

**Path B — Tool Calls (Agent → SAJHA)**

1\. Agent receives a user message, decides to call a tool.

2\. agent/tools.py calls \_get_token() which logs into SAJHA as user 'risk_agent' using os.getenv('SAJHA_PASSWORD').

3\. All tool calls are made with this shared service token: Authorization: Bearer {token}.

4\. The token is cached in a module-level variable \_sajha_token and reused for all users.

|  |
|----|
| **Problems in Path B** |
| Hardcoded service account: risk_agent / SAJHA_PASSWORD — a static credential that cannot be scoped or rotated per user. |
| No user context on tool calls: SAJHA cannot distinguish which end-user triggered a tool — all calls appear as risk_agent. |
| Shared token across all sessions: if SAJHA invalidates the token, all concurrent users are affected simultaneously. |
| SAJHA's full session auth system (730+ lines in AuthManager) exists solely to validate this one service account. |
| SAJHA bound to 0.0.0.0:3002 means risk_agent credentials can be used to call tools directly, bypassing the Agent entirely. |

**2.3 Existing File Locations (Reference)**

The following files are affected by this change and are referenced throughout this document:

|  |  |  |
|----|----|----|
| **File** | **Change Type** | **Description** |
| Dockerfile | **MODIFY** | Currently only runs uvicorn. Will be merged with frontend and SAJHA. |
| Dockerfile.frontend | **DELETE** | nginx frontend container. Merged into single Dockerfile. |
| agent_server.py | **MODIFY** | Remove SAJHA login proxy. Agent owns auth entirely. |
| agent/tools.py | **MODIFY** | Remove \_get_token() / risk_agent pattern. Replace with X-Service-Key header. |
| sajhamcpserver/config/server.properties | **MODIFY** | Change server.host from 0.0.0.0 to 127.0.0.1. |
| sajhamcpserver/config/users.json | **MODIFY** | Passwords to be bcrypt-hashed. Remove duplicate login endpoint dependency. |
| sajhamcpserver/sajha/app.py (or equivalent) | **MODIFY** | Add X-Service-Key middleware. Remove session/JWT auth on tool endpoints. |
| nginx.conf | **NEW** | Single nginx config routing / to static, /api/ to uvicorn. |
| supervisord.conf | **NEW** | Process supervisor starting nginx, uvicorn, SAJHA in one container. |

**3. Docker Port Consolidation**

**3.1 Target Architecture**

All three processes run inside a single Docker container managed by supervisord. Only port 80 (or configurable via PORT env var) is exposed externally. All inter-process communication uses the loopback interface.

|  |
|----|
| **Container Port Map — Target State** |
| External: PORT (default 80) → nginx (listens on 0.0.0.0:\${PORT}) |
| Internal: 127.0.0.1:8000 → Agent Server (uvicorn) |
| Internal: 127.0.0.1:3002 → SAJHA MCP Server (Flask) |
|  |
| Traffic flow: Browser → nginx:80 → /api/\* proxied to uvicorn:8000 → SAJHA:3002 (tool calls) |
| SAJHA is never reachable from outside the container. |

**3.2 supervisord.conf**

A new supervisord.conf is created at the container root. It defines three programs that supervisord starts and supervises:

|                                                               |
|---------------------------------------------------------------|
| **supervisord.conf — Full Specification**                     |
| \[supervisord\]                                               |
| nodaemon=true                                                 |
| logfile=/var/log/supervisord.log                              |
|                                                               |
| \[program:sajha\]                                             |
| command=python sajhamcpserver/run_server.py                   |
| directory=/app                                                |
| autostart=true                                                |
| autorestart=true                                              |
| stdout_logfile=/var/log/sajha.log                             |
| stderr_logfile=/var/log/sajha.err                             |
| priority=1                                                    |
|                                                               |
| \[program:agent\]                                             |
| command=uvicorn agent_server:app --host 127.0.0.1 --port 8000 |
| directory=/app                                                |
| autostart=true                                                |
| autorestart=true                                              |
| stdout_logfile=/var/log/agent.log                             |
| stderr_logfile=/var/log/agent.err                             |
| priority=2                                                    |
|                                                               |
| \[program:nginx\]                                             |
| command=nginx -g 'daemon off;'                                |
| autostart=true                                                |
| autorestart=true                                              |
| stdout_logfile=/var/log/nginx.log                             |
| stderr_logfile=/var/log/nginx.err                             |
| priority=3                                                    |

SAJHA has priority 1 (starts first) so the Agent Server's startup tool discovery request finds SAJHA already listening.

**3.3 nginx.conf**

nginx serves static frontend files and proxies all /api/ requests to the Agent Server. SSE streaming requires specific proxy directives to disable buffering.

|                                                        |
|--------------------------------------------------------|
| **nginx.conf — Key Directives**                        |
| server {                                               |
| listen \${PORT:-80};                                   |
| root /app/public;                                      |
| index mcp-agent.html;                                  |
|                                                        |
| \# Static frontend                                     |
| location / { try_files \$uri \$uri/ /mcp-agent.html; } |
|                                                        |
| \# Agent API + SSE streaming                           |
| location /api/ {                                       |
| proxy_pass http://127.0.0.1:8000;                      |
| proxy_http_version 1.1;                                |
| proxy_set_header Connection '';                        |
| proxy_buffering off; \# REQUIRED for SSE               |
| proxy_cache off; \# REQUIRED for SSE                   |
| proxy_read_timeout 300s; \# Long-running agent tasks   |
| proxy_set_header Host \$host;                          |
| proxy_set_header X-Real-IP \$remote_addr;              |
| }                                                      |
| }                                                      |

|  |
|----|
| **Critical: SSE Streaming** |
| The Agent Server uses Server-Sent Events (SSE) for streaming responses to the browser. |
| proxy_buffering off and proxy_cache off are MANDATORY — without them nginx buffers the entire response before forwarding, breaking real-time streaming. |
| proxy_http_version 1.1 with Connection '' enables HTTP keep-alive, which SSE requires. |
| proxy_read_timeout must be set generously (300s+) because agent tasks may run for several minutes. |

**3.4 Merged Dockerfile**

The existing Dockerfile (agent only) and Dockerfile.frontend (nginx only) are replaced with a single Dockerfile that installs all dependencies and runs supervisord as PID 1.

|  |
|----|
| **Dockerfile — Target Structure** |
| FROM python:3.11-slim |
|  |
| \# System packages: nginx + supervisor |
| RUN apt-get update && apt-get install -y nginx supervisor && rm -rf /var/lib/apt/lists/\* |
|  |
| WORKDIR /app |
| COPY requirements.txt . |
| RUN pip install -r requirements.txt --no-cache-dir |
|  |
| \# Copy application |
| COPY . . |
|  |
| \# nginx config |
| COPY nginx.conf /etc/nginx/conf.d/default.conf |
| RUN rm -f /etc/nginx/sites-enabled/default |
|  |
| \# supervisord config |
| COPY supervisord.conf /etc/supervisor/conf.d/riskgpt.conf |
|  |
| EXPOSE \${PORT:-80} |
|  |
| CMD \["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"\] |

**3.5 server.properties Change**

SAJHA must be prevented from accepting connections from outside the container. A single line change in server.properties achieves this:

|             |                           |
|-------------|---------------------------|
| Setting     | Before                    |
| server.host | 0.0.0.0 (all interfaces)  |
| server.host | 127.0.0.1 (loopback only) |
| server.port | 3002 (unchanged)          |

With server.host=127.0.0.1, any attempt to reach SAJHA from outside the container (e.g., curl host:3002) will receive a connection refused. SAJHA only accepts connections from within the same container.

**4. Unified Authentication**

**4.1 Design Principles**

The redesign follows three principles:

- Single authority: The Agent Server is the only system that validates user identity, issues tokens, and enforces role-based access. SAJHA has no user identity concept.

- Service key pattern: Agent-to-SAJHA calls are authenticated by a shared secret header (X-Service-Key). No user session or JWT is passed to SAJHA. SAJHA trusts any request that carries the correct key — this is safe because SAJHA is not externally reachable after the Docker fix.

- No hardcoded credentials: The risk_agent service account and SAJHA_PASSWORD env var are eliminated. There is no privileged internal user — only the service key, which is scoped to inter-container calls.

**4.2 Target Auth Architecture**

**Login Flow — Target**

|       |                                                                     |
|:-----:|---------------------------------------------------------------------|
| **1** | Browser sends POST /api/auth/login {user_id, password} to nginx:80. |

|  |  |
|:--:|----|
| **2** | nginx proxies to Agent Server (uvicorn:8000). Agent Server handles auth natively — no SAJHA proxy. |

|  |  |
|:--:|----|
| **3** | Agent Server reads sajhamcpserver/config/users.json, verifies bcrypt(password) hash, looks up role (super_admin \| admin \| user). |

|  |  |
|:--:|----|
| **4** | Agent Server issues a signed JWT containing: sub (user_id), role, worker_id (if scoped), onboarding_complete flag, exp. |

|  |  |
|:--:|----|
| **5** | Browser receives JWT. All subsequent API requests include Authorization: Bearer {token}. |

|  |
|----|
| **What is removed from login flow** |
| REMOVED: agent_server.py proxy to POST http://localhost:3002/api/auth/login |
| REMOVED: SAJHA handling of /api/auth/login endpoint (decommissioned) |
| REMOVED: \_SAJHA_USERS_FILE path coupling in agent_server.py |
| RESULT: Agent Server can start and accept logins independently of SAJHA startup state. |

**Tool Call Flow — Target**

|  |  |
|:--:|----|
| **1** | Agent Server processes a user message, decides to call a tool on SAJHA. |

|  |  |
|:--:|----|
| **2** | Agent Server constructs the tool request. It adds two headers: X-Service-Key: {SAJHA_SERVICE_KEY} and X-User-Id: {user_id from JWT}. |

|  |  |
|:--:|----|
| **3** | SAJHA middleware validates X-Service-Key against its configured SAJHA_SERVICE_KEY env var. If missing or wrong: 403 Forbidden. |

|  |  |
|:--:|----|
| **4** | SAJHA executes the tool and returns the result. No session lookup, no JWT validation — just the service key check. |

|  |  |
|:--:|----|
| **5** | Agent Server receives result, incorporates into LLM response, streams back to browser via SSE. |

|  |
|----|
| **What is removed from tool call flow** |
| REMOVED: agent/tools.py \_get_token() function (SAJHA login as risk_agent) |
| REMOVED: agent/tools.py \_sajha_token module-level session variable |
| REMOVED: SAJHA AuthManager.validate_token() for tool endpoint calls |
| REMOVED: SAJHA_PASSWORD environment variable |
| ADDED: SAJHA_SERVICE_KEY environment variable (shared secret, rotate via env) |
| ADDED: X-User-Id header forwarded to SAJHA for audit logging (no auth check) |

**4.3 Role Hierarchy**

All role logic lives in the Agent Server. SAJHA is role-blind — it executes any request from the Agent.

|  |  |  |  |
|----|----|----|----|
| **Role** | **Assigned By** | **Access** | **Scoped To** |
| super_admin | Hardcoded in users.json or first-boot setup | Create/delete Digital Workers, create/delete admin users, full system config | All workers |
| admin | super_admin via Admin Console | Configure their own Digital Worker: tools, prompt, domain data, workflows, assign users | Assigned worker(s) only |
| user | admin or super_admin | Chat interface only. No admin panel access. | Assigned worker only |

**4.4 SAJHA — Service Key Middleware**

SAJHA adds a lightweight middleware layer. Every inbound request to a tool endpoint must carry a valid X-Service-Key header. Requests without the key are rejected immediately — no further processing occurs.

|  |
|----|
| **SAJHA Middleware — Pseudocode** |
| SAJHA_SERVICE_KEY = os.getenv('SAJHA_SERVICE_KEY') \# set at container startup |
|  |
| @app.before_request |
| def require_service_key(): |
| if request.path.startswith('/api/tools'): \# tool endpoints only |
| key = request.headers.get('X-Service-Key') |
| if not key or key != SAJHA_SERVICE_KEY: |
| return jsonify({'error': 'Forbidden'}), 403 |
| \# /api/auth/\* endpoints removed — no longer needed |

The X-Admin header pattern provides SAJHA admin endpoint protection (for system metadata, tool discovery) independently of the service key:

|  |
|----|
| **Admin-Tier Tool Discovery** |
| Agent Server's startup tool discovery: GET /api/tools/list with headers X-Service-Key + X-Admin: true |
| SAJHA returns full tool manifest only when X-Admin: true is present alongside a valid X-Service-Key. |
| Regular tool calls omit X-Admin — SAJHA executes but does not expose internal tool metadata. |

**4.5 users.json — Password Hashing**

Current users.json stores passwords in plaintext. As part of this change, all passwords are migrated to bcrypt hashes:

|  |
|----|
| **users.json — Schema Change** |
| BEFORE: { "user_id": "risk_agent", "password": "RiskAgent2025!", "role": "admin" } |
|  |
| AFTER: { "user_id": "saad", "password_hash": "\$2b\$12\$...", "role": "admin", |
| "assigned_worker": "w-default", "onboarding_complete": true } |
|  |
| Migration: run scripts/migrate_passwords.py — reads existing users.json, bcrypt-hashes each password, |
| writes updated file. Original backed up as users.json.bak. |
| risk_agent service account entry is deleted from users.json entirely. |

**4.6 Environment Variables — Summary**

The following environment variables govern the new auth and service key configuration:

|  |  |  |  |
|----|----|----|----|
| **Variable** | **Used By** | **Required?** | **Description** |
| AGENT_SECRET_KEY | Agent Server | Yes | JWT signing secret. Rotate to invalidate all sessions. |
| AGENT_API_KEYS | Agent Server | Optional | Comma-separated API keys for programmatic access (non-browser). |
| SAJHA_SERVICE_KEY | Agent Server + SAJHA | Yes | Shared secret for agent-to-SAJHA calls. Must match on both sides. |
| SAJHA_BASE_URL | Agent Server | Optional | SAJHA base URL. Default: http://127.0.0.1:3002 |
| PORT | nginx / Docker | Optional | External port. Default: 80. |
| SAJHA_PASSWORD | REMOVED | — | Hardcoded service account password. Eliminated in this change. |

**5. Integration with Digital Worker Platform**

The Digital Worker Platform ERD (separate document) defines workers.json, per-worker enabled_tools, and the X-Worker-Data-Root header. The infrastructure changes in this document are foundational to the Digital Worker architecture:

|  |  |
|----|----|
| **Infrastructure Enabler** | **Digital Worker Benefit** |
| Agent owns auth (Section 4.2) | Agent can enforce per-worker tool restrictions in JWT claims — SAJHA does not need to understand worker concepts. |
| X-Service-Key replaces risk_agent (Section 4.4) | Agent passes X-Worker-Id alongside X-Service-Key on every tool call — SAJHA can log which worker triggered each tool. |
| Single container / loopback SAJHA (Section 3.2) | SAJHA's domain_data_path is controlled via X-Worker-Data-Root header set by Agent — no risk of clients overriding this from outside the container. |
| bcrypt passwords + role in users.json (Section 4.5) | assigned_worker field in users.json provides the worker binding that the Digital Worker Platform requires. |
| nginx /api/ proxy (Section 3.3) | All requests pass through the Agent auth middleware before reaching SAJHA — worker scoping is always enforced. |

|  |
|----|
| **Worker-Scoped Tool Call — Header Set** |
| When Agent calls a SAJHA tool on behalf of a Digital Worker, it sends: |
| X-Service-Key: {SAJHA_SERVICE_KEY} |
| X-User-Id: {user_id} |
| X-Worker-Id: {worker_id} |
| X-Worker-Data-Root: {worker.domain_data_path} |
|  |
| SAJHA validates X-Service-Key only. The remaining headers are trusted context for logging and data path resolution. |

**6. Files Changed**

**6.1 Docker Consolidation — Files**

|  |  |  |
|----|----|----|
| **File** | **Change Type** | **Description** |
| Dockerfile | **MODIFY** | Replace uvicorn-only CMD with supervisord. Add nginx + supervisor apt installs. Copy nginx.conf + supervisord.conf. Single EXPOSE \${PORT:-80}. |
| Dockerfile.frontend | **DELETE** | nginx frontend container entirely replaced by merged Dockerfile. Remove from repo. |
| nginx.conf | **NEW** | nginx config: static root at /app/public, /api/ proxy to 127.0.0.1:8000 with SSE directives (proxy_buffering off, proxy_cache off, proxy_read_timeout 300s). |
| supervisord.conf | **NEW** | Manages three programs: sajha (priority 1), agent (priority 2), nginx (priority 3). All stdout/stderr to /var/log/. nodaemon=true. |
| sajhamcpserver/config/server.properties | **MODIFY** | server.host=0.0.0.0 → server.host=127.0.0.1. SAJHA loopback-only. |
| docker-compose.yml (if present) | **MODIFY** | Remove frontend service. Update agent service to use merged Dockerfile. Expose single port 80. |

**6.2 Auth Unification — Files**

|  |  |  |
|----|----|----|
| **File** | **Change Type** | **Description** |
| agent_server.py | **MODIFY** | Remove SAJHA login proxy (POST /api/auth/login → SAJHA). Agent validates users.json directly. Remove \_SAJHA_USERS_FILE coupling. Add bcrypt.checkpw() call. |
| agent/tools.py | **MODIFY** | Remove \_get_token(), \_sajha_token, SAJHA login call. Replace with \_service_headers() that returns {X-Service-Key, X-User-Id, X-Worker-Id, X-Worker-Data-Root}. |
| sajhamcpserver/sajha/app.py | **MODIFY** | Add before_request middleware: validate X-Service-Key on /api/tools/\* routes. Remove /api/auth/login endpoint. Remove AuthManager session validation from tool routes. |
| sajhamcpserver/config/users.json | **MODIFY** | Replace plaintext password field with password_hash (bcrypt). Add assigned_worker field. Remove risk_agent entry. |
| scripts/migrate_passwords.py | **NEW** | One-time migration script: reads users.json, bcrypt-hashes each password, writes updated file, backs up original. |
| .env / docker-compose environment | **MODIFY** | Remove SAJHA_PASSWORD. Add SAJHA_SERVICE_KEY. Ensure AGENT_SECRET_KEY is set. |

**7. Migration Plan**

The migration is non-destructive. Existing users, workers, and workflows are preserved. The steps below are ordered to allow rollback at each stage.

**7.1 Phase 1 — Auth Migration (no Docker changes)**

Deliver auth changes first, independently of Docker. This keeps existing multi-container setup intact and allows auth to be tested in isolation.

1.  Run scripts/migrate_passwords.py to bcrypt-hash all passwords in users.json. Verify login still works.

2.  Add SAJHA_SERVICE_KEY to environment. Update agent/tools.py to use \_service_headers(). Restart Agent Server only. Verify tool calls succeed.

3.  Add X-Service-Key middleware to SAJHA app.py. Deploy SAJHA only. Confirm tool calls still work (Agent sends key, SAJHA validates).

4.  Remove SAJHA's /api/auth/login endpoint. Remove agent_server.py login proxy. Restart both. Verify user login via Agent-native auth.

5.  Remove risk_agent from users.json. Remove SAJHA_PASSWORD from environment. Confirm no service degradation.

**7.2 Phase 2 — Docker Consolidation**

After Phase 1 is verified, consolidate into a single container.

6.  Create supervisord.conf and nginx.conf. Build merged Dockerfile locally.

7.  Smoke test locally: docker run -p 80:80 riskgpt. Verify login, chat, tool calls, SSE streaming all work through single port.

8.  Change server.properties server.host to 127.0.0.1. Rebuild image. Verify SAJHA is no longer reachable on port 3002 from outside the container.

9.  Retire Dockerfile.frontend. Update CI/CD pipeline to build and push single image.

10. Deploy to enterprise environment. Confirm one-port-per-container constraint is satisfied.

**7.3 Rollback Strategy**

|  |
|----|
| **Rollback Points** |
| Phase 1, Step 1: users.json.bak is preserved — restore original file to revert password migration. |
| Phase 1, Steps 2-5: Each step is independently reversible by reverting the changed file and restarting the affected service. |
| Phase 2: Original Dockerfiles are preserved in git. A single git revert redeploys the three-container setup. |
| Feature flag: SAJHA_SERVICE_KEY absent → SAJHA skips key validation (allows old agent to still call tools during transition). |

**8. Acceptance Criteria**

**8.1 Docker Port Consolidation**

|  |  |  |  |
|----|----|----|----|
| **AC-ID** | **Category** | **Acceptance Criterion** | **Test / Verification** |
| DC-01 | Ports | Running docker run -p 80:80 riskgpt exposes exactly one port (80) on the host. | docker ps shows PORTS 0.0.0.0:80-\>80/tcp and nothing else. |
| DC-02 | Ports | Port 3002 (SAJHA) is not reachable from outside the container. | curl host:3002 from outside container returns connection refused. |
| DC-03 | Ports | Port 8000 (Agent) is not reachable from outside the container. | curl host:8000 from outside container returns connection refused. |
| DC-04 | Startup | supervisord starts all three processes in order: SAJHA first, Agent second, nginx third. | docker logs show all three process startup messages. SAJHA log appears before Agent log. |
| DC-05 | Startup | If SAJHA crashes, supervisord restarts it automatically without restarting Agent or nginx. | Kill SAJHA process inside container; confirm supervisord relaunches it within 5 seconds; Agent remains up. |
| DC-06 | SSE | Streaming responses arrive at the browser in real time (no buffering). | Open chat, send a message, observe partial tokens appearing as they are generated — not appearing all at once after a delay. |
| DC-07 | SSE | Long-running agent tasks (\>60 seconds) do not time out at the nginx layer. | Trigger a workflow with multiple sequential tool calls. Confirm response completes without a 504 Gateway Timeout. |
| DC-08 | Static | Frontend (mcp-agent.html) is served correctly via nginx. | Navigate to http://localhost. Login page loads. No 404 or 502 errors. |
| DC-09 | Config | SAJHA server.properties has server.host=127.0.0.1. | Read server.properties inside running container. Confirm value. |
| DC-10 | Build | Single Dockerfile builds successfully without errors. | docker build -t riskgpt . exits 0. |
| DC-11 | Build | Dockerfile.frontend no longer exists in the repository. | git ls-files Dockerfile.frontend returns empty. |

**8.2 Auth Unification**

|  |  |  |  |
|----|----|----|----|
| **AC-ID** | **Category** | **Acceptance Criterion** | **Test / Verification** |
| AU-01 | Login | User login is handled entirely by Agent Server — no call to SAJHA /api/auth/login. | Stop SAJHA. POST /api/auth/login to Agent Server. Login succeeds and returns JWT. |
| AU-02 | Login | Invalid password is rejected with 401. Valid password returns a signed JWT. | POST with wrong password → 401. POST with correct password → 200 + {token}. |
| AU-03 | Login | JWT contains role, sub, exp, worker_id claims. | Decode returned JWT (no signature verification in test). Confirm all four claims present. |
| AU-04 | Service Key | SAJHA tool calls require X-Service-Key header. Missing key returns 403. | Call SAJHA tool endpoint directly without X-Service-Key. Expect 403 Forbidden. |
| AU-05 | Service Key | SAJHA tool calls with correct X-Service-Key succeed. | Call SAJHA tool endpoint with correct X-Service-Key. Expect 200 and valid tool result. |
| AU-06 | Service Key | Agent Server correctly sets X-Service-Key on all outgoing tool calls to SAJHA. | Intercept agent→SAJHA HTTP calls (mock or logging). Confirm X-Service-Key header is present on every call. |
| AU-07 | Credentials | risk_agent user no longer exists in users.json. | Read users.json. Confirm no entry with user_id=risk_agent. |
| AU-08 | Credentials | SAJHA_PASSWORD environment variable is not referenced anywhere in the codebase. | grep -r SAJHA_PASSWORD . returns no matches (excluding .env.example documentation). |
| AU-09 | Passwords | All passwords in users.json are bcrypt hashes (starting with \$2b\$). | Read users.json. All password_hash values start with \$2b\$12\$. |
| AU-10 | Roles | super_admin can access Admin Console. admin can access their own worker config. user cannot access Admin Console. | Login as each role. Confirm 200 on permitted routes, 403 on forbidden routes. |
| AU-11 | Tool Context | SAJHA receives X-User-Id and X-Worker-Id headers on every tool call. | Enable SAJHA request logging. Trigger a tool call. Confirm both headers appear in SAJHA access log. |
| AU-12 | Session | SAJHA no longer has a /api/auth/login endpoint. | POST /api/auth/login directly to SAJHA (port 3002 inside container). Expect 404. |
| AU-13 | Session | Rotating SAJHA_SERVICE_KEY invalidates all in-flight tool calls without affecting user sessions. | Change SAJHA_SERVICE_KEY, restart SAJHA only. Agent tool calls fail with 403 until Agent is also restarted with new key. User JWT sessions remain valid. |

**9. Out of Scope**

The following items are explicitly deferred to separate work streams:

- OAuth / SSO integration (SAML, OIDC) — external identity provider support is a Phase 3 consideration.

- Kubernetes / Helm chart deployment — this document targets single-container Docker. K8s decomposition (separate pod per process) is a future enhancement.

- mTLS between Agent and SAJHA — the shared X-Service-Key is sufficient while both run in the same container; mTLS is relevant only if processes are separated across pods.

- Audit log persistence — X-User-Id and X-Worker-Id headers are forwarded for logging; the logging infrastructure design is covered in the observability workstream.

- SAJHA tool authorisation (per-user tool allow/deny) — this is defined in the Digital Worker Platform ERD and depends on workers.json, not on the auth infrastructure changes here.

- Password reset / self-service account management — current design requires admin editing users.json directly; a management UI is deferred.

- Token refresh / sliding sessions — current JWT is a fixed-expiry token; refresh token flow is deferred.

**10. Glossary**

|  |  |
|----|----|
| **Term** | **Definition** |
| Agent Server | FastAPI application (agent_server.py) running on port 8000 internally. Manages LangGraph agent loop, SSE streaming, and user auth. |
| SAJHA MCP Server | Flask MCP server (sajhamcpserver/) running on port 3002 internally. Exposes 74+ domain tools to the Agent via HTTP. |
| nginx | Web server acting as reverse proxy. Sole external-facing component. Routes / to static files and /api/ to Agent Server. |
| supervisord | Process supervisor managing all three processes inside the merged Docker container. Provides automatic restart and ordered startup. |
| X-Service-Key | Shared secret HTTP header used by Agent Server to authenticate internal calls to SAJHA. Replaces the risk_agent session token pattern. |
| X-Worker-Id | HTTP header forwarded by Agent on tool calls to identify which Digital Worker triggered the call. Used for audit logging and data path resolution. |
| X-Worker-Data-Root | HTTP header forwarded by Agent on tool calls to scope SAJHA's data access to a specific worker's domain_data_path. |
| bcrypt | Password hashing algorithm used to store password_hash in users.json. Replaces plaintext passwords. |
| SSE | Server-Sent Events. HTTP streaming protocol used by the Agent to push real-time tokens to the browser. Requires nginx proxy_buffering off. |
| DXA | Device-independent XML units used in OOXML (docx). 1 inch = 1440 DXA. |
| risk_agent | Decommissioned internal service account previously used by Agent to call SAJHA tools. Eliminated by the X-Service-Key pattern. |
| Digital Worker | Configurable agent instance with isolated domain data, workflows, tools, and system prompt. Defined in the Digital Worker Platform ERD. |
