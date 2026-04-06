# SAJHA Intelligence Platform — Handover Package
**Prepared:** April 6, 2026
**Status:** Ready for team handover

---

## What This Is

SAJHA is an enterprise AI platform (MCP-based) that provides a multi-worker digital intelligence system. Each "worker" is a scoped AI agent with its own data, tools, and users. The platform is built on:

- **Agent Server** — FastAPI (port 8000), LangGraph orchestration, SSE streaming
- **SAJHA MCP Server** — Flask (port 3002), 121+ tools across finance, regulatory, data analysis
- **Frontend** — HTML/JS chat UI (`mcp-agent.html`) + Admin panel (`admin.html`)

---

## How to Run

```bash
# 1. SAJHA MCP server (start first)
cd sajhamcpserver
../venv/bin/python run_server.py

# 2. Agent server
venv/bin/uvicorn agent_server:app --port 8000 --reload

# 3. Open in browser
http://localhost:8000
```

**Credentials:** See `01_project_overview/CREDENTIALS.md`

---

## What's in This Handover Package

| Folder | Contents |
|--------|----------|
| `01_project_overview/` | Credentials, next steps, high-level roadmap |
| `02_architecture/` | ERDs, TRD, platform architecture docs |
| `03_requirements/` | Gap analysis + active backlog (REQ-01 through REQ-11) |
| `04_uat_and_testing/` | Regression reports, UAT master index, per-requirement test plans & results |
| `05_user_guides/` | Admin, Super-Admin, End-User, Connectors, Deployment guides |
| `06_tools_reference/` | Per-tool MCP reference guides (121+ tools) |

---

## Current State (April 2026)

### What's Built and Tested ✅
- Multi-worker admin panel with full RBAC (super_admin / admin / user)
- File management across 3 data layers: domain_data, common_data (shared library), verified_workflows
- 121+ MCP tools: SEC EDGAR, OSFI, IRIS CCR, Yahoo Finance, Tavily, DuckDB, Teams, Outlook, Jira, Confluence, PowerBI, and more
- JWT authentication with per-worker user isolation
- Connector framework (external data source integration)
- Audit logging (super_admin)
- Chat interface with canvas support

### What's Pending (Active Backlog) 🔧
See `03_requirements/pending/` for detailed specs on:

| REQ | Feature | Priority |
|-----|---------|----------|
| REQ-01a/b | Shared FileTree Library — build & backend features | High |
| REQ-02a/b | Connector external setup & MR worker integration | High |
| REQ-03 | Visualization tool debug & rendering fixes | High |
| REQ-04a/b | Python execution tool (basic + heavy quant libraries) | Medium |
| REQ-05 | Summarization engine | Medium |
| REQ-06 | Branding — BPulse Digital Workers | Medium |
| REQ-07 | PostgreSQL database migration | Medium |
| REQ-08 | Apache Iceberg / S3 data strategy | Low |
| REQ-10 | Common Data Path refinement | Completed |
| REQ-11 | Multi-file parallel upload | Completed |

---

## Test Coverage

The platform has been fully regression tested. Latest results:

- **Suite v2:** 132/132 tests PASS — zero failures
- **Roles tested:** super_admin, admin, user
- **Coverage:** All UI screens, API endpoints, file upload isolation, RBAC

Full report: `04_uat_and_testing/SAJHA_Regression_Test_Report_v2_2026-04-06.docx`

---

## Key Files at a Glance

| File | Purpose |
|------|---------|
| `agent_server.py` | Main FastAPI server — routes, auth, file APIs, SSE |
| `agent/agent.py` | LangGraph agent definition |
| `agent/prompt.py` | System prompt |
| `sajhamcpserver/sajha/tools/impl/` | All tool implementations |
| `sajhamcpserver/config/tools/` | JSON config per tool |
| `public/admin.html` | Admin panel UI |
| `public/mcp-agent.html` | Chat UI |
| `CLAUDE.md` | Dev instructions (architecture, data paths, how to add tools) |
| `.env` | Environment variables (API keys, paths) |

---

## Who to Contact

Refer to `01_project_overview/CREDENTIALS.md` for service accounts and API key locations.
