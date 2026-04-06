# MCP Intelligence Agent — Developer Reference

## Architecture
Three-layer system:
- **Frontend** (`public/login.html`, `index.html`, `mcp-agent.html`, `admin.html`) — HTML/JS chat UI, admin panel, login/onboarding
- **Agent Server** (`agent_server.py`, ~2,876 lines) — FastAPI on port 8000, LangGraph agent with 9-middleware stack, SSE streaming, RBAC
- **SAJHA MCP Server** (`sajhamcpserver/`) — Flask MCP server on port 3002, 121+ tools, hot-reload every 5s

## Running Locally
```bash
# Terminal 1 — SAJHA MCP server (must start first)
cd sajhamcpserver
../venv/bin/python run_server.py

# Terminal 2 — Agent server
uvicorn agent_server:app --port 8000 --reload

# Or use the dev script (starts both):
./dev.sh

# Frontend URLs:
#   Login:  http://localhost:8000/login.html
#   Chat:   http://localhost:8000/mcp-agent.html
#   Admin:  http://localhost:8000/admin.html
#   Studio: http://localhost:3002 (super_admin only)
```

## Key Directories
```
agent/                    # LangGraph agent, prompt, tools client
  agent.py                # Agent factory (create_agent_for_worker)
  prompt.py               # System prompts + Python/multi-agent addenda
  tools.py                # 5 static tools + dynamic SAJHA tool discovery
  llm_factory.py          # Multi-provider LLM selection (Anthropic, xAI, HF, Bedrock)
  sub_agent_tool.py       # task() tool for multi-agent orchestration
  sub_agent_executor.py   # Sub-agent lifecycle (2-pool threading: 4 sched + 8 exec)
  workflow_parser.py      # YAML frontmatter parser for multi-agent workflows
  summariser.py           # Context compression middleware (180k token trigger)
  middlewares/            # 9 middleware classes (see Middleware Stack below)
agent_server.py           # FastAPI entrypoint (~85 endpoints), SSE, RBAC, file mgmt
sajhamcpserver/
  run_server.py           # Flask MCP server entry (411 lines)
  config/
    tools/                # 121 JSON tool configs (name, implementation, schema)
    workers.json          # Worker definitions, enabled_tools, connector_scope
    users.json            # User accounts with bcrypt hashes, roles
    apikeys.json          # API key definitions with rate limits
    llm_config.json       # LLM provider settings (hot-swappable)
    application.properties  # Data paths, feature flags, external API URLs
    server.properties     # Server config (port, hot-reload, rate limits)
  sajha/tools/impl/       # 41 tool implementation modules
  data/                   # Runtime data (worker-scoped, see Data Paths)
public/
  login.html              # Auth + 3-step onboarding wizard
  index.html              # Basic chat UI (87KB)
  mcp-agent.html          # Market risk chat UI with canvas (273KB)
  admin.html              # Admin panel — workers, users, tools, files, audit, LLM config (138KB)
  js/file-tree.js         # Reusable BPulseFileTree component (1,200 lines)
requirements/             # Requirements docs (completed/ and pending/)
handover/                 # Structured handover package (6 subdirectories)
Documentation/            # Word docs (Admin, Deployment, Technical, Connectors, QA guides)
```

## Data Paths (Worker-Scoped)
All data follows worker isolation: `./data/workers/{worker_id}/`
```
IRIS CCR:       ./data/workers/w-market-risk/domain_data/iris/iris_combined.csv
DuckDB:         ./data/workers/w-market-risk/domain_data/duckdb/
SQL Select:     ./data/workers/w-market-risk/domain_data/sqlselect/
MsDocs:         ./data/workers/w-market-risk/domain_data/msdocs/
Counterparties: ./data/workers/w-market-risk/domain_data/counterparties/
OSFI:           ./data/workers/w-market-risk/domain_data/osfi/
Workflows:      ./data/workers/w-market-risk/workflows/verified/
Templates:      ./data/workers/w-market-risk/templates/
My Data:        ./data/workers/w-market-risk/my_data/{user_id}/
Common (shared): ./data/common/
Checkpoints:    ./data/checkpoints.db  (AsyncSqliteSaver, persistent)
Audit:          ./data/audit/tool_calls.jsonl
```

## Adding a New Tool
1. Create implementation class in `sajhamcpserver/sajha/tools/impl/`
2. Create JSON config in `sajhamcpserver/config/tools/<tool_name>.json`
3. Set `"implementation": "sajha.tools.impl.<module>.<ClassName>"`
4. Hot-reload picks it up within 5 seconds — no restart needed

Tool JSON config structure:
```json
{
  "name": "tool_name",
  "description": "What the tool does",
  "category": "Category Name",
  "version": "1.0.0",
  "enabled": true,
  "implementation": "sajha.tools.impl.module_name.ClassName",
  "inputSchema": { "type": "object", "properties": {...}, "required": [...] },
  "outputSchema": { "type": "object", "properties": {...} }
}
```

## Key Tool Modules (121+ tools across 41 files)
- `edgar_tavily_tools.py` — SEC EDGAR qualitative extraction (MD&A, earnings, segments, risk) — 6 tools
- `edgar_metric_tools.py` — XBRL financial metrics, ratios, peer comparison — 4 tools
- `tavily_ir_tool.py` — Universal IR tools (any public company, Tavily-native) — 9 tools
- `iris_ccr_tools.py` — IRIS counterparty credit risk (pandas-based CSV analytics) — 9 tools
- `tavily_yahoo_finance_tool.py` — Stock quotes, history, symbol search — 3 tools
- `tavily_tool_refactored.py` — Web/research/news/domain search — 4 tools
- `duckdb_olap_tools_refactored.py` — SQL on CSV/Parquet/JSON — 7 tools
- `duckdb_olap_advanced.py` — Advanced OLAP, pivot tables — 3 tools
- `sqlselect_tool_refactored.py` — Database query interface — 6 tools
- `msdoc_tools_tool_refactored.py` — Word/Excel read/search/metadata — 10 tools
- `python_executor.py` — Sandboxed Python (pandas, numpy, plotly, arch, riskfolio, QuantLib) — 2 tools
- `visualisation_tools.py` — Chart generation (Plotly HTML) — 1 tool
- `bm25_search_tool.py` — Full-text document search across all data layers — 1 tool
- `outlook_tools.py` — Outlook email (list, read, search, reply, send) — 6 tools
- `teams_tools.py` — Teams channels (list, messages, files, meetings, send) — 6 tools
- `sharepoint_tools_connector.py` — SharePoint (sites, docs, search, upload/download) — 6 tools
- `confluence_tools.py` — Confluence wiki (spaces, pages, search, create) — 5 tools
- `jira_tools.py` — Jira issues (projects, sprints, CRUD, comments) — 7 tools
- `powerbi_tools.py` — Power BI (workspaces, datasets, reports, refresh) — 6 tools
- `workflow_tools.py` — Workflow discovery and execution — 2 tools
- `operational_tools.py` — File read, PDF read, search, templates, md-to-docx — 7 tools
- `data_transform_tools.py` — Data export, transform, parquet read — 3 tools

## Agent Middleware Stack (execution order)
```
1. DanglingToolCallMiddleware  — repairs orphaned tool_calls after summarisation
2. SummarisationMiddleware     — compresses context at 180k tokens (90% of 200k window)
3. MessageTrimmer              — hard fallback at 800k chars
4. SubagentLimitMiddleware     — caps parallel sub-agents (default 3, range 2-4)
5. LoopDetectionMiddleware     — warns at 3 repeats, hard-stops at 5 (MD5 fingerprint)
6. ToolErrorHandlingMiddleware — catches exceptions, returns error ToolMessage
7. RetryMiddleware             — exponential backoff 1s/2s/4s for 429/503/502
8. TokenBudgetMiddleware       — per-query token budget with 80% warning
9. AuditMiddleware             — logs all events to JSONL with sensitive field redaction
```

Optional (per-worker config):
- `MemoryMiddleware` — cross-session memory (SQLite, Jaccard similarity, 90-day TTL)
- `HumanInTheLoopMiddleware` — HITL approval gates (fnmatch patterns, 5-min timeout)

## LLM Providers
Configured via `/api/super/llm-config` or `sajhamcpserver/config/llm_config.json`:

| Provider | Default Model | Env Vars |
|----------|--------------|----------|
| anthropic (default) | claude-sonnet-4-20250514 | ANTHROPIC_API_KEY, ANTHROPIC_MODEL |
| xai | grok-3 | XAI_API_KEY, XAI_MODEL |
| huggingface | meta-llama/Llama-3.3-70B-Instruct | HF_API_KEY, HF_MODEL |
| bedrock | us.anthropic.claude-sonnet-4-20250514-v1:0 | BEDROCK_MODEL_ID, AWS_REGION |

All providers: temperature=0, streaming=true, max_tokens configurable (default 8192).

## API Endpoints (~85 routes)

### Authentication
- `POST /api/auth/login` — JWT login (rate limited: 10 attempts/60s)
- `GET  /api/auth/me` — current user from JWT
- `POST /api/auth/onboarding` — 3-step new user setup (display_name, password)
- `POST /api/auth/change-password` — requires min 10 chars

### Agent Execution
- `POST /api/agent/run` — execute agent with SSE streaming
- `POST /api/chat/hitl-response` — submit HITL approval/rejection
- `GET  /api/agent/threads` — list conversation threads (per user+worker)

### Super Admin — Workers
- `GET|POST /api/super/workers` — list/create workers
- `GET|PUT|DELETE /api/super/workers/{id}` — CRUD worker
- `POST /api/super/workers/{id}/assign` — assign user to worker
- `DELETE /api/super/workers/{id}/assign/{user_id}` — unassign user

### Super Admin — Users
- `GET|POST /api/super/users` — list/create users
- `PUT|DELETE /api/super/users/{id}` — update/delete user
- `POST /api/super/users/{id}/reset-password` — admin password reset

### Super Admin — LLM, Connectors, Audit
- `GET|PUT /api/super/llm-config` — get/set LLM provider+model
- `GET /api/super/connectors` — list connectors (credentials redacted)
- `PUT|POST|DELETE /api/super/connectors/{type}` — upsert/test/delete connector
- `GET|PUT /api/super/workers/{id}/connector-scope/{type}` — worker connector access
- `GET /api/super/audit` — paginated audit log (filter by worker/user)

### Admin — Own Worker
- `GET|PUT /api/admin/worker` — view/update own worker
- `PUT /api/admin/worker/prompt` — update system prompt
- `PUT /api/admin/worker/tools` — enable/disable tools
- `GET|POST|PUT|DELETE /api/admin/worker/users/*` — manage worker's users

### File System (Worker-Scoped)
- `GET /api/fs/quota` — storage quota (default 5GB)
- `GET /api/fs/{section}/tree` — BM25-indexed file tree
- `GET|PATCH /api/fs/{section}/file` — read/update file
- `POST /api/fs/{section}/upload` — upload (streaming, 50MB limit)
- `POST /api/fs/{section}/folder|move|rename|copy|batch-delete|reindex` — file ops
- `DELETE /api/fs/{section}/file|folder` — delete
- `GET /api/fs/charts` — list generated charts
- `GET /api/fs/charts/{filename}` — serve chart (supports iframe token auth)

Sections: `uploads`, `domain_data`, `verified`, `my_workflows`, `templates`, `my_data`, `common`

### Admin File Browser
- `GET|POST|DELETE|PATCH /api/admin/tree|upload|folder|item|rename|move|file|validate`
- `GET|POST|DELETE|PATCH /api/super/workers/{id}/files/{section}/*` — super admin file ops
- `GET|POST|DELETE|PATCH /api/admin/worker/files/{section}/*` — admin file ops
- `POST /api/admin/common/upload` — upload to shared library

### Tools
- `GET /api/mcp/tools` — all tool configs (admin)
- `GET /api/workers/{id}/tools` — tools filtered by worker allowlist
- `GET /api/admin/tools` — fetch tools from SAJHA service

### Workflows
- `GET|POST /api/workflows` — list/create workflows
- `GET|DELETE /api/workflows/{filename}` — read/delete workflow
- `PATCH /api/workflows/{filename}/used` — mark as recently used

### Health
- `GET /health` — returns `{'status': 'ok'}`

## SSE Streaming Protocol
The `/api/agent/run` endpoint returns Server-Sent Events:

| Event Type | Payload | Description |
|-----------|---------|-------------|
| `session` | `{thread_id}` | Thread ID for conversation continuity |
| `text` | `{content}` | Streaming agent text output |
| `tool_start` | `{tool, args, run_id}` | Tool execution begins |
| `tool_end` | `{tool, result, run_id, duration_ms}` | Tool execution complete |
| `canvas` | `{chart_url, chart_type}` | Chart/visualization ready for iframe |
| `hitl` | `{hitl_id, tool, args, timeout}` | Human approval required |
| `usage` | `{input_tokens, output_tokens}` | Token consumption |
| `context_gauge` | `{tokens_used, tokens_max}` | Context window utilization |
| `summary_occurred` | `{exchanges_compressed, tokens_before, tokens_after}` | Context was compressed |
| `budget_exceeded` | `{limit, used}` | Token budget hit |
| `error` | `{message}` | Error occurred |
| `task_started` | `{task_id, description}` | Sub-agent spawned |
| `task_running` | `{task_id, message}` | Sub-agent progress |
| `task_completed` | `{task_id, result}` | Sub-agent finished |
| `task_failed` | `{task_id, error}` | Sub-agent failed |
| `task_timed_out` | `{task_id}` | Sub-agent timed out |

## Multi-Agent Orchestration
Triggered by workflow files with YAML frontmatter (`agent_mode: multi`):
```yaml
---
agent_mode: multi
agents:
  - id: risk_summary
    description: Risk snapshot
    task: Get VaR for all desks
    order: 1
  - id: reg_check
    description: Regulatory limits
    task: Compare {risk_summary.result_summary} vs FRTB limits
    order: 2
---
```

- Same `order` = parallel execution; ascending order = sequential groups
- `{id.result_summary}` placeholders resolved from completed agent results (truncated at 500 chars)
- Sub-agents cannot call `task()` (no recursion)
- Defaults: 20 max turns, 120s timeout, 8KB result truncation per sub-agent

## Worker Configuration Options
Configurable per-worker via admin API or `workers.json`:
```
name, description, system_prompt, enabled (bool)
enabled_tools          — tool allowlist (["*"] = all, or specific names)
agent_mode             — "single" or "multi"
max_concurrent_subagents — default 3, range [2, 4]
enable_memory          — cross-session memory (default false)
memory_ttl_days        — memory expiration (default 90)
max_memories_per_query — injected per call (default 5)
min_memory_similarity  — Jaccard threshold (default 0.75)
max_tokens_per_query   — token budget (default: unlimited)
hitl_triggers          — fnmatch patterns for HITL gates (e.g., ["delete_*", "send_*"])
hitl_timeout_seconds   — human approval timeout (default 300)
connector_scope        — per-connector access (microsoft_azure, atlassian)
```

## Authentication & Authorization
- **JWT**: HS256, 7-day expiry, payload: user_id, role, worker_id, display_name
- **Roles**: `super_admin` (platform-wide), `admin` (own worker), `user` (agent access)
- **Agent API keys**: `AGENT_API_KEYS` env var (comma-separated); empty = auth disabled
- **SAJHA API keys**: defined in `config/apikeys.json` with rate limits and tool filtering
- **Default super_admin**: `risk_agent` / `RiskAgent2025!`
- **Login rate limit**: 10 attempts per 60 seconds per user_id
- **Path traversal protection**: all file paths validated via `startswith()` against root
- **Sensitive field redaction**: passwords, api_keys, tokens, secrets, credentials auto-redacted in audit logs

## SEC/EDGAR Notes
- Use `direct_sec_json()` for all SEC JSON API endpoints (not Tavily)
- Use `stream_sec_section()` for large SEC Archives HTML filings (>2 MB)
- BMO and other Canadian banks file 6-K (not 10-Q) — EDGAR tools target 10-K/10-Q only
- `_validate_sources()` blocks synthesis from wrong-company or stale-year sources

## Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | — | Anthropic Claude API key |
| `ANTHROPIC_MODEL` | claude-sonnet-4-20250514 | Claude model |
| `LLM_PROVIDER` | anthropic | LLM provider (anthropic/xai/huggingface/bedrock) |
| `LLM_MAX_TOKENS` | 8192 | Max output tokens |
| `XAI_API_KEY` | — | xAI Grok API key |
| `HF_API_KEY` | — | HuggingFace API key |
| `BEDROCK_MODEL_ID` | us.anthropic.claude-sonnet-4-20250514-v1:0 | AWS Bedrock model |
| `AWS_REGION` | us-east-1 | AWS region for Bedrock |
| `JWT_SECRET` | sajha-dev-secret-change-in-prod | JWT signing secret |
| `CORS_ORIGINS` | http://localhost:8080 | Comma-separated CORS origins |
| `STORAGE_BACKEND` | local | Storage backend (local or s3) |
| `CHECKPOINT_DB_PATH` | ./sajhamcpserver/data/checkpoints.db | LangGraph checkpoint DB |
| `AGENT_API_KEYS` | (empty = disabled) | Comma-separated agent API keys |
| `SAJHA_BASE_URL` | http://localhost:3002 | SAJHA MCP server URL |
| `SAJHA_API_KEY` | sja_full_access_admin | SAJHA authorization key |
| `TAVILY_API_KEY` | — | Tavily search API key |
| `CONTEXT_TRIGGER_TOKENS` | 180000 | Summarisation trigger (90% of 200k) |
| `CONTEXT_TARGET_PCT` | 0.18 | Post-compression target (~36k tokens) |

## Deployment (Docker)
Single container with 3 processes managed by supervisord:
```
1. SAJHA (priority 1) — Flask on 127.0.0.1:3002
2. Agent (priority 2) — uvicorn on 127.0.0.1:8000
3. nginx  (priority 3) — reverse proxy on $PORT (default 80)
```

nginx routes: `/api/*` → FastAPI, `/mcp-studio/*` → Flask, `/*.html` → static files.
SSE streaming config: `proxy_buffering off`, `proxy_read_timeout 300s`, `chunked_transfer_encoding on`.
Railway deployment via `railway.toml` with `/health` check.

## External API Integrations
SEC EDGAR, Tavily Search, Yahoo Finance, FRED, ECB, IMF, World Bank,
Bank of Canada, Bank of Japan, RBI, PBoC, Banque de France, Wikipedia,
Google Custom Search. Base URLs configured in `config/server.properties`.

## Tool Output Handling
- Max tool output: 12,000 chars (~3k tokens), truncated if exceeded
- HTML-output tools (generate_chart, python_execute, etc.): strip `html` field, set `_chart_ready: true` for SSE canvas events
- File upload: streaming 64KB chunks, 50MB limit, allowed extensions: pdf, docx, xlsx, csv, txt, parquet, md, json, png, jpg, jpeg
- Storage quota: 5GB default per user
