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
| `03_requirements/` | Gap analysis. Live in-flight requirements (REQ-06, 08b, 14, 15, 16) live in `requirements/pending/`. Completed REQs are in `archive/completed-requirements/`. |
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

Status verified against code as of 2026-05-17. Specs for in-flight items live in `requirements/pending/`.

| REQ | Feature | Status | Notes |
|-----|---------|--------|-------|
| REQ-06 | Branding — B-Pulse Digital Workers | Pending | `public/login.html` still says "RiskGPT"; no B-Pulse strings in HTML. Not started. |
| REQ-08b | Apache Iceberg analytical tables | Pending | Architecture-only doc; no DuckDB Iceberg / Glue catalog code yet. |
| REQ-14 | Bug fixes: sub-agent audit, EDGAR Canadian coverage | Partial | Sub-agent timeout still hardcoded 120s; audit success=None not fully handled; EDGAR CA coverage gap open. |
| REQ-15 | Supabase persistent storage | Stubbed | Storage abstraction in `sajha/storage.py` exists but `agent_server.py` file ops still use raw `pathlib.Path`. |
| REQ-16 | Hetzner S3 migration (tool layer) | Partial | S3 backend complete; ~11 tool modules (DuckDB OLAP advanced, msdoc tools, workflow tools, IRIS, etc.) still use direct `pathlib`/`open()` calls. |

### What's Completed (previously listed as pending) ✅

Confirmed implemented and verified against code; specs moved to `archive/completed-requirements/`.

| REQ | Feature | Evidence |
|-----|---------|----------|
| REQ-01a / 01b | Shared FileTree Library + Phase 2 | `public/js/file-tree.js` ≈1,200 lines, fully wired |
| REQ-02a / 02b | Connectors + MR worker integration | All connector modules in `sajhamcpserver/sajha/tools/impl/{outlook,teams,jira,confluence,sharepoint,powerbi}_tools.py` |
| REQ-03 | Visualization tool | `sajha/tools/impl/visualisation_tools.py` |
| REQ-04a / 04b | Python execution tool (basic + heavy quant) | `python_executor.py` with sandbox venv (pandas, numpy, scipy, arch, riskfolio, etc.) |
| REQ-05 | Summarisation engine | `agent/summariser.py` + `SummarisationMiddleware` |
| REQ-07 | PostgreSQL migration | `worker_repository.py` PostgresWorkerRepository, `AsyncPostgresSaver` checkpointing |
| REQ-08 | DevOps deployment guide | Docker + supervisord + nginx + GitHub Actions all in repo |
| REQ-08a | S3 object storage integration | `sajha/storage.py` `S3StorageBackend` complete |
| REQ-10 | Common Data Path | `path_resolver.py` common_data category |
| REQ-11 | Multi-file parallel upload | `file-tree.js` `_checkBatchComplete()` + agent SSE batch events |

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
