# B-Pulse Digital Workers

> **Source:** Converted from `Technical_Documentation.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**B-Pulse Digital Workers**

Technical Documentation

Version 2.9.8 · April 2026

**FOR INTERNAL DEVELOPER USE ONLY**

**1. System Overview**

B-Pulse Digital Workers is an enterprise-grade AI-powered digital worker platform purpose-built for capital markets risk management. It combines a LangGraph-based agentic reasoning layer with a modular MCP (Model Context Protocol) tool server, enabling risk analysts to interact with live market data, regulatory documents, counterparty portfolios, and enterprise connectors (Microsoft 365, Atlassian) through a conversational interface.

**1.1 Architecture**

The platform operates as a three-layer system:

- Frontend — Single-page HTML/JS application served from /public. Two interfaces: admin.html (Admin Console) and mcp-agent.html (Digital Worker chat). Authentication via JWT stored in sessionStorage.

- Agent Server — FastAPI application (agent_server.py) running on port 8000. Manages authentication, user/worker configuration, SSE streaming of agent responses, and all admin API endpoints.

- SAJHA MCP Server — Flask-based Model Context Protocol server running on port 3002. Hosts 74+ tools across domains: market data, counterparty credit risk, SEC filings, OSFI regulatory docs, Microsoft 365 (Teams/Outlook), Atlassian (Confluence/Jira), and code execution.

|  |
|----|
| The Agent Server and SAJHA MCP Server communicate internally over HTTP. External clients only interact with port 8000. Port 3002 must NOT be exposed externally. |

**1.2 Technology Stack**

|  |  |  |  |
|----|----|----|----|
| **Layer** | **Technology** | **Version** | **Purpose** |
| Agent Server | FastAPI + Uvicorn | 0.115 / 0.32 | REST API, SSE streaming, JWT auth |
| Agent Runtime | LangGraph + LangChain | 0.2.x | Agentic reasoning, tool orchestration, memory |
| AI Model | Claude (claude-sonnet-4-5) | via Anthropic API | LLM backbone for all agent reasoning |
| MCP Server | Flask + Werkzeug | 3.1 / 3.1 | Tool registry and execution engine |
| Data Storage | JSON/JSONL flat files | — | Users, workers, audit, workflows, connectors |
| Analytics DB | DuckDB | 1.x | In-process SQL for financial data queries |
| Search | Tavily API | Cloud | Web search for market intelligence |
| Frontend | Vanilla JS + HTML5 | — | Admin console and chat UI |
| Auth | JWT (python-jose) | 3.3 | Stateless bearer token auth |
| HTTP Client | httpx (async) | 0.27 | Agent → SAJHA inter-service calls |

**2. Repository Structure**

> react_agent/
> ├── agent_server.py # FastAPI entry point (1,800+ lines)
> ├── agent/
> │ ├── graph.py # LangGraph agent graph definition
> │ ├── prompt.py # System prompt with worker context injection
> │ ├── tools.py # Tool client (calls SAJHA MCP server)
> │ └── summariser.py # Rolling context summarisation middleware
> ├── public/
> │ ├── admin.html # Admin Console SPA (7,000+ lines)
> │ ├── mcp-agent.html # Digital Worker chat UI (6,800+ lines)
> │ └── login.html # Authentication page
> ├── sajhamcpserver/
> │ ├── run_server.py # SAJHA Flask server entry point
> │ ├── config/
> │ │ ├── tools/ # JSON config for each tool (name, schema, impl)
> │ │ ├── workers.json # Worker definitions + connector scopes
> │ │ ├── connectors.json # Connector registry (MS365, Atlassian)
> │ │ ├── users.json # User accounts (hashed passwords, roles, tools)
> │ │ └── server.properties # SAJHA server config (port 3002, timeouts, etc.)
> │ ├── sajha/
> │ │ ├── web/ # Flask routes and SSE handling
> │ │ ├── tools/
> │ │ │ └── impl/ # Tool implementation classes
> │ │ └── core/
> │ │ ├── registry.py # Hot-reload tool registry
> │ │ ├── connectors_registry.py # MS365 + Atlassian clients
> │ │ └── token_cache.py # OAuth2 token cache
> │ └── data/
> │ ├── domain_data/ # Counterparty, IRIS CCR, exposure data
> │ ├── uploads/ # Per-user file uploads
> │ ├── workflows/ # Verified workflow Markdown files
> │ └── audit/
> │ └── tool_calls.jsonl # Immutable audit trail
> ├── Documentation/ # All documentation (this folder)
> └── requirements/ # Feature requirements docs

**3. Authentication & Authorisation**

The platform uses a two-tier authentication model. All API calls to the agent server require a valid JWT bearer token. The SAJHA MCP server uses a service-to-service internal token for agent → tool calls.

**3.1 JWT Authentication Flow**

- Client POSTs credentials to POST /api/auth/login

- Agent server validates password against bcrypt hash in config/users.json

- On success: returns { token, user_id, role, worker_id }

- Client stores token in sessionStorage; included in Authorization: Bearer \<token\> header

- Token expiry: 1 hour (configurable via security.token.expiry.hours in server.properties)

- Failed logins: tracked per-user; account locked after 5 attempts for 5 minutes

**3.2 Role-Based Access Control**

|  |  |  |
|----|----|----|
| **Role** | **Description** | **Access Level** |
| super_admin | Full platform access | All endpoints including /api/super/\* |
| admin | Worker-scoped admin | /api/admin/\* endpoints for their assigned worker |
| user | End user / analyst | /api/mcp/\* chat endpoints; read-only admin data |

**3.3 Service-to-Service Auth**

The agent server authenticates with SAJHA using a fixed API key set in the AGENT_API_KEYS environment variable. If this variable is empty, inter-service auth is disabled (development mode only). In production, always set a strong random key.

**4. Agent Runtime (LangGraph)**

The agent runtime is built on LangGraph with a ReAct-style reasoning loop. The agent receives a system prompt containing the worker context (name, tools, connector scope, OSFI guidance) and conversation history, then iteratively calls tools until it can produce a final answer.

**4.1 Agent Graph**

- State: MessagesState — a list of messages (HumanMessage, AIMessage, ToolMessage)

- Memory: MemorySaver (in-memory checkpointing; thread_id = user_id). NOTE: State is lost on server restart. PostgresSaver migration is planned in REQ-07.

- Tool binding: All 74+ SAJHA tools are fetched at startup and bound to the Claude model

- Streaming: SSE events streamed to client as agent thinks and calls tools

- Summarisation: SummarisationMiddleware triggers at 80% context usage (160k tokens), compresses to ≤18%

**4.2 System Prompt Injection**

The system prompt (agent/prompt.py) is dynamically constructed per request with:

- Worker identity: name, description, tools list

- Connector scope: Teams team ID, Confluence space key, Jira project key, Outlook mailbox

- OSFI regulatory guidance (fetched from SAJHA on each session start)

- Current date and timestamp

- HITL (Human-In-The-Loop) instructions for write operations

**4.3 SSE Streaming Protocol**

The agent server streams responses via Server-Sent Events (SSE) at /api/mcp/chat. Each event has a type field:

|                |                     |                                       |
|----------------|---------------------|---------------------------------------|
| **Event Type** | **Payload**         | **Frontend Action**                   |
| thinking       | { content: str }    | Display in collapsible thinking panel |
| tool_call      | { name, input }     | Show tool chip with spinner           |
| tool_result    | { name, result }    | Update tool chip to complete/error    |
| content        | { content: str }    | Append to message bubble              |
| hitl_request   | { action, details } | Show confirmation modal               |
| hitl_response  | { approved: bool }  | Resume or cancel action               |
| error          | { message }         | Show error toast                      |
| done           | {}                  | Mark message complete                 |

**5. Tool System (SAJHA MCP Server)**

The SAJHA MCP server hosts 74+ tools organised into categories. Tools are hot-reloaded every 5 minutes from config/tools/ — no server restart required to add or modify a tool.

**5.1 Tool Architecture**

- Each tool has a JSON config file in sajhamcpserver/config/tools/\<tool_name\>.json

- The JSON defines: name, description, input_schema (JSON Schema), and implementation (Python dotted class path)

- The registry loads the implementation class via importlib and calls its execute(input, context) method

- Context contains: user_id, worker_id, connector_scope (Teams/Confluence/Jira/Outlook IDs)

**5.2 Tool Categories**

|  |  |  |
|----|----|----|
| **Category** | **Tool Count** | **Key Tools** |
| Counterparty Credit Risk (CCR) | 8 | get_counterparty_exposure, get_credit_limits, get_var_contribution, get_trade_inventory |
| Market Data | 12 | get_stock_quote, get_historical_prices, fred_get_series, ecb_get_data, bank_of_canada_rate |
| SEC / EDGAR | 8 | edgar_get_mda, edgar_get_earnings, edgar_get_risk_factors, edgar_get_xbrl_metrics |
| OSFI Regulatory | 4 | osfi_search, osfi_get_document, osfi_list_guidelines |
| Microsoft Teams | 6 | teams_list_channels, teams_get_messages, teams_send_message, teams_list_members, teams_get_meetings, teams_get_channel_files |
| Microsoft Outlook | 6 | outlook_read_email, outlook_search_email, outlook_send_email, outlook_reply_email, outlook_list_folders, outlook_get_email |
| Atlassian Confluence | 5 | confluence_list_spaces, confluence_search, confluence_get_page, confluence_list_pages, confluence_create_page |
| Atlassian Jira | 7 | jira_list_projects, jira_search_issues, jira_create_issue, jira_get_issue, jira_update_issue, jira_add_comment, jira_list_sprints |
| IRIS CCR Data | 6 | iris_search, iris_get_counterparty, iris_get_sector_exposure |
| Visualisation | 3 | generate_chart, generate_heatmap, generate_time_series |
| Python Execution | 2 | python_execute, python_run_script (pending REQ-04) |
| File / Domain Data | 5 | list_domain_files, read_domain_file, upload_file, create_workflow, run_workflow |

**5.3 Adding a New Tool**

To add a new tool without restarting the server:

- Create a Python class in sajhamcpserver/sajha/tools/impl/\<module\>.py with an execute(self, input: dict, context: dict) -\> dict method

- Create sajhamcpserver/config/tools/\<tool_name\>.json with name, description, input_schema, and implementation fields

- The hot-reload system detects the new file within 5 seconds and registers the tool

- Test via POST /api/tools/execute with { tool_name, input, context } payload

**6. Data Layer**

The platform currently uses flat files for all operational data. A PostgreSQL migration is planned in REQ-07, with Apache Iceberg for time-series financial data in REQ-08.

**6.1 Configuration Files**

|  |  |  |  |
|----|----|----|----|
| **File** | **Format** | **Contents** | **Notes** |
| config/users.json | JSON array | User accounts: user_id, role, password_hash, worker_id, tools | bcrypt hashed passwords; never commit with real credentials |
| config/workers.json | JSON array | Worker definitions: worker_id, name, tools, connector_scope | Hot-reloaded; connector_scope is per-worker tenant configuration |
| config/connectors.json | JSON object | Connector credentials: tenant_id, client_id, client_secret, api_token | PLAINTEXT — BUG-CONN-001 — must not be committed; see REQ-07 for AES-256-GCM encryption |
| config/api_keys.json | JSON array | Agent server API keys for service auth | Matches AGENT_API_KEYS env var |
| server.properties | Properties | SAJHA server: port, auth, rate limits, logging | server.port=3002 |

**6.2 Audit Log**

All tool calls are written to sajhamcpserver/data/audit/tool_calls.jsonl as append-only JSONL. Each record contains:

```
{"timestamp": "2026-04-04T10:00:00Z", "user_id": "risk_agent", "worker_id": "w-market-risk",
"tool_name": "teams_send_message", "input": {...}, "result_summary": "...",
"confirmation_required": true, "approved": true, "duration_ms": 432}
```

**6.3 DuckDB Analytics**

Financial data queries (counterparty exposure, IRIS CCR, VaR) run against DuckDB databases stored in sajhamcpserver/data/duckdb/. DuckDB is embedded in-process — no separate database server required. Schema is defined per tool in the tool config JSON.

**7. Connector Framework**

External integrations (Microsoft 365 and Atlassian) are managed by the ConnectorsRegistry class in sajha/core/connectors_registry.py. Credentials are stored in config/connectors.json and injected into tool context at execution time.

**7.1 Microsoft Graph (MS365)**

- Client: MSGraphClient — OAuth2 client credentials flow (app-level permissions)

- Token cache: token_cache.py — caches access tokens with automatic expiry refresh

- Scopes required: Mail.Read, Mail.Send, Team.ReadBasic.All, ChannelMessage.Read.All, ChannelMessage.Send, Calendars.Read

- All scopes must be granted as Application permissions with Admin consent in Azure AD

- Known issue: token_cache.py expiry logic needs verification before production (BUG-CONN-002)

**7.2 Atlassian (Confluence + Jira)**

- Client: AtlassianClient — HTTP Basic auth (email:api_token)

- Token: Personal API token from id.atlassian.com (not a password)

- Confluence API: REST v2 at /wiki/rest/api/

- Jira API: REST v3 at /rest/api/3/

- Worker scope: confluence_space_key, jira_project_key, jira_board_id, confluence_parent_page_id

**7.3 Worker Connector Scope**

Each digital worker has a connector_scope in workers.json that limits which Teams channels, Confluence spaces, and Jira projects it can access. This enforces data isolation between workers:

> "connector_scope": {
> "microsoft_azure": {
> "teams_team_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
> "outlook_user_email": "mrrisk@company.com",
> "sharepoint_site_url": "https://company.sharepoint.com/sites/MarketRisk"
> },
> "atlassian": {
> "confluence_space_key": "MRISK",
> "jira_project_key": "MRISK",
> "jira_board_id": 42,
> "confluence_parent_page_id": "123456"
> }
> }

**8. Running Locally (Development)**

**8.1 Prerequisites**

- Python 3.10+ (system Python; the venv/bin/python symlink may be broken if Python 3.13 is not installed)

- Node.js 18+ (for frontend tooling)

- ANTHROPIC_API_KEY and TAVILY_API_KEY in .env

- Ports 8000 and 3002 free

**8.2 Startup Sequence**

The SAJHA MCP server must start before the Agent server (tool discovery at startup):

```
# Terminal 1 — SAJHA MCP Server
cd sajhamcpserver
python3 run_server.py
# Terminal 2 — Agent Server
cd react_agent
python3 -m uvicorn agent_server:app --port 8000
# Frontend: open http://localhost:8000/admin.html or mcp-agent.html
# Default credentials: risk_agent / RiskAgent2025!
```

|  |
|----|
| If venv/bin/python is a broken symlink (Python 3.13 not found), use system python3 directly. The system Python 3.10.12 has all required packages installed. |

**8.3 Environment Variables**

|  |  |  |
|----|----|----|
| **Variable** | **Required** | **Description** |
| ANTHROPIC_API_KEY | Yes | Anthropic API key for Claude model access |
| TAVILY_API_KEY | Yes | Tavily API key for web search and IR tools |
| AGENT_API_KEYS | No | Comma-separated service API keys. Empty = auth disabled (dev only) |
| SAJHA_BASE_URL | No | Override SAJHA server URL (default: http://localhost:3002) |

**9. Known Issues & Open Bugs**

|  |  |  |  |  |
|----|----|----|----|----|
| **ID** | **Severity** | **Component** | **Description** | **Tracking** |
| BUG-CONN-001 | HIGH | connectors_registry.py:60 | decrypt() function is stubbed — credentials stored plaintext in connectors.json | REQ-07 |
| BUG-CONN-002 | MED | token_cache.py | Token refresh logic for MS Graph not fully verified — may fail on expiry | REQ-02b |
| BUG-CONN-003 | LOW | workers.json | outlook_user_email missing from w-market-risk connector_scope | REQ-02b |
| BUG-ADMIN-001 | HIGH | admin.html | Admin write operations (worker create, user update) call /api/super/\* — requires super_admin role even for admins | REQ-01 UAT |
| BUG-VIZ-001 | HIGH | agent/tools.py | Chart HTML truncated at 12,000 chars; rendered via textContent not innerHTML | REQ-03 |
| BUG-MEM-001 | MED | graph.py | MemorySaver loses all conversation history on server restart | REQ-07 |
| BUG-AUDIT-001 | LOW | agent_server.py | Audit log dashboard shows dashes (—) for some fields due to inconsistent schema | REQ-07 |

**10. Security Considerations**

|  |
|----|
| These notes apply to the current development build. Several items MUST be resolved before production deployment. |

- config/connectors.json MUST be added to .gitignore — it contains plaintext credentials (BUG-CONN-001)

- JWT secrets must be rotated before production — default secret is hard-coded in config

- Port 3002 (SAJHA) must be firewall-blocked; only port 8000 should be externally accessible

- HITL confirmation is required for all write operations (Teams/Outlook/Confluence/Jira) — never bypass

- AES-256-GCM credential encryption is tracked in REQ-07 (PostgreSQL migration)

- The /api/dev/screenshot endpoint added for documentation must be removed before production

- Rate limiting is enforced per IP at 100 requests/minute (configurable in server.properties)

**11. Pending Requirements Summary**

|  |  |  |  |
|----|----|----|----|
| **REQ ID** | **Title** | **Priority** | **Status** |
| REQ-01 | Common Domain Data Path Component (file tree refactor) | HIGH | Pending |
| REQ-02a | Connector External Setup Guide | HIGH | Pending |
| REQ-02b | Connector MR Worker Integration & Testing | HIGH | Pending |
| REQ-03 | Visualization Tool Debug & Rendering | HIGH | Pending |
| REQ-04 | Python Execution Tool | MED | Pending |
| REQ-05 | Summarisation Engine Improvement | MED | Pending |
| REQ-06 | B-Pulse Branding | LOW | Pending |
| REQ-07 | PostgreSQL Database Migration | HIGH | Pending |
| REQ-08 | Apache Iceberg / S3 Data Strategy | MED | Pending |
