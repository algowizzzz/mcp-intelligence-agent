# Documentation Index

This is the canonical index for active documentation in the repo. Every `.md` and `.docx` file under `/`, `handover/`, and `requirements/` is listed below with a one-line summary derived from its actual contents. For archived/legacy docs, see [archive/INDEX.md](archive/INDEX.md).

Last updated: 2026-05-17 (post-cleanup pass).

---

## Repo Root

| File | Summary |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Developer reference for the three-layer system: HTML frontend, FastAPI agent server, SAJHA MCP server — run commands, key dirs, middleware stack, env vars. |
| [LOCAL_DEV_SETUP.md](LOCAL_DEV_SETUP.md) | Local macOS setup notes (2026-05-15): venv install, switch to xAI Grok, disable polluted Postgres, migrate orphaned worker files. |
| [DOCS_INDEX.md](DOCS_INDEX.md) | This file — canonical index for every active `.md` and `.docx` under root, `handover/`, and `requirements/`. |

---

## handover/

### handover/00_START_HERE.md

Handover entry point: platform purpose, run commands, folder map (01–06). Includes a "What's Completed" table (REQ-01a/01b/02a/02b/03/04a/04b/05/07/08/08a/10/11 verified against code) and an active backlog table (REQ-06 Pending, REQ-08b Pending, REQ-14 Partial, REQ-15 Stubbed, REQ-16 Partial — verified 2026-05-17).

### handover/01_project_overview/

| File | Summary |
|---|---|
| [CREDENTIALS.md](handover/01_project_overview/CREDENTIALS.md) | Master credentials reference: Azure/M365, Atlassian, Teams/Outlook/Jira/Confluence IDs, B-Pulse platform accounts (kept private, not committed). |
| [NEXT_STEPS.md](handover/01_project_overview/NEXT_STEPS.md) | Market Risk connector handoff (through 2026-04-05): Teams RSC v1.0.1 installed, Outlook licensed, Confluence pending; next-step terminal commands. |

### handover/02_architecture/

| File | Summary |
|---|---|
| [Glossary.md](handover/02_architecture/Glossary.md) | Alphabetical glossary of SAJHA MCP Server v2.9.0 terms, acronyms, and concepts — reference document. |
| [SAJHA_MCP_Server_Architecture.md](handover/02_architecture/SAJHA_MCP_Server_Architecture.md) | SAJHA v2.9.0 system architecture: package structure, tools framework, MCP Studio, OLAP, IR module, config, security, hot-reload, deployment. |
| [RiskGPT_Connector_ERD.docx](handover/02_architecture/RiskGPT_Connector_ERD.docx) | Connector ERD for five enterprise integrations (Teams, Power BI, SharePoint, Outlook, Jira) — architecture, credentials, tool ops, request flow. |
| [RiskGPT_Digital_Worker_Platform_ERD.docx](handover/02_architecture/RiskGPT_Digital_Worker_Platform_ERD.docx) | Conversion of single-tenant RiskGPT to multi-tenant Digital Worker platform: per-worker prompts, data, tools, users, role hierarchy. |
| [RiskGPT_MultiWorker_Platform_Scope_ERD.docx](handover/02_architecture/RiskGPT_MultiWorker_Platform_Scope_ERD.docx) | Multi-worker isolation requirements: target three-zone file layout, worker clone behaviour, runtime enforcement, gap remediation. |
| [RiskGPT_Platform_Infrastructure_ERD.docx](handover/02_architecture/RiskGPT_Platform_Infrastructure_ERD.docx) | Infrastructure ERD: Docker consolidation across three processes and unified authentication replacing the dual JWT path. |
| [Sajha_Admin_Panel_ERD.docx](handover/02_architecture/Sajha_Admin_Panel_ERD.docx) | Admin Panel ERD: new top-level tab in `mcp-agent.html` for shared data governance, `is_admin` JWT claim, RBAC layout. |
| [Sajha_Data_Workflows_FileTree_ERD.docx](handover/02_architecture/Sajha_Data_Workflows_FileTree_ERD.docx) | File-tree panel ERD: VS Code-style tree replacing the flat list, four sections (domain/my data, verified/my workflows), preview, indexing. |
| [mcp-agent-trd-final.docx](handover/02_architecture/mcp-agent-trd-final.docx) | Final TRD for the MCP Intelligence Agent: three-layer architecture, tool wrappers, SSE contract, FastAPI backend, env vars. |

### handover/03_requirements/

| File | Summary |
|---|---|
| [Requirements_Gap_Analysis.md](handover/03_requirements/Requirements_Gap_Analysis.md) | Historical snapshot (2026-04-05) of `requirements/completed/` vs live code; superseded by the backlog table in `handover/00_START_HERE.md` updated 2026-05-17. |

### handover/04_uat_and_testing/

| File | Summary |
|---|---|
| [Functional_Test_Results.md](handover/04_uat_and_testing/Functional_Test_Results.md) | Full admin + agent regression: 113/113 PASS across 52 admin and 61 agent tests, all 21 bugs closed by 2026-04-05. |
| [GAP_Fixes_UAT_Results.md](handover/04_uat_and_testing/GAP_Fixes_UAT_Results.md) | 19/19 PASS architectural gap-fix verifications: msdoc storage migration, WorkerRepository wiring, serve_file consolidation, workflow/domain dir retirement. |
| [UAT_Master_Index.md](handover/04_uat_and_testing/UAT_Master_Index.md) | Master UAT index: 236 total tests across functional regression, UI audit, regression v2, gap fixes, BM25, common data, parallel upload. |
| [SAJHA_Regression_Test_Report_v2_2026-04-06.docx](handover/04_uat_and_testing/SAJHA_Regression_Test_Report_v2_2026-04-06.docx) | Regression suite v2 report: 132 tests in 18 groups across all roles, 6 bugs (5 test-contract, 1 production) found and fixed. |
| [SAJHA_Regression_Test_Results_2026-04-05.docx](handover/04_uat_and_testing/SAJHA_Regression_Test_Results_2026-04-05.docx) | First-pass automated regression: 76 tests across 15 areas, 67 PASS / 9 FAIL (missing tool API routes, contract mismatches, worker-delete guard). |

### handover/04_uat_and_testing/uat_plans/

| File | Summary |
|---|---|
| [PLATFORM_UAT_Plan.md](handover/04_uat_and_testing/uat_plans/PLATFORM_UAT_Plan.md) | End-to-end production UAT on Hetzner CPX32 VPS: S3, Postgres, worker lifecycle, tools, workflows, connectors, admin UI. |
| [REQ-01a_UAT_Plan.md](handover/04_uat_and_testing/uat_plans/REQ-01a_UAT_Plan.md) | UAT plan for the BPulseFileTree library swap covering admin and chat instances (`_bpft_dd`, `_bpft_wf`, `_bpftInstB`, `_bpftInstC`). |
| [REQ-01b_UAT_Plan.md](handover/04_uat_and_testing/uat_plans/REQ-01b_UAT_Plan.md) | UAT plan for Phase 2 file-tree backend: size/modified, copy, batch-delete, quota endpoints plus FE size/search/quota. |
| [REQ-01b_backend_test_results.md](handover/04_uat_and_testing/uat_plans/REQ-01b_backend_test_results.md) | Phase 2 backend curl results: tree size_bytes/modified_at PASS, quota PASS, copy PASS, batch-delete PASS — 4/4. |
| [REQ-03_UAT_Plan.md](handover/04_uat_and_testing/uat_plans/REQ-03_UAT_Plan.md) | UAT plan for visualization six fixes — strip-html, chart serve endpoint, canvas SSE, iframe render, tool card badge, PNG fallback. |
| [REQ-04a_UAT_Plan.md](handover/04_uat_and_testing/uat_plans/REQ-04a_UAT_Plan.md) | UAT plan for `python_execute` / `python_run_script`: AST security scan, timeout, figure capture, basic venv libs. |
| [REQ-04b_UAT_Plan.md](handover/04_uat_and_testing/uat_plans/REQ-04b_UAT_Plan.md) | UAT plan for heavy quant libs in sandbox venv: scikit-learn, arch, riskfolio-lib, QuantLib, xarray, networkx. |
| [REQ-04b_backend_test_results.md](handover/04_uat_and_testing/uat_plans/REQ-04b_backend_test_results.md) | Heavy-quant venv install verification: scikit-learn 1.8, arch 8.0, riskfolio-lib 7.2.1, QuantLib 1.41, xarray, networkx all OK. |
| [REQ-09_UAT_Plan.md](handover/04_uat_and_testing/uat_plans/REQ-09_UAT_Plan.md) | UAT plan for BM25 `document_search` across domain_data + my_data using rank_bm25 + pdfplumber, direct SAJHA API. |
| [REQ-09_UAT_Results.md](handover/04_uat_and_testing/uat_plans/REQ-09_UAT_Results.md) | 10/10 CI PASS for BM25 document retrieval: import, chunking, MD extraction, excerpt matching, ranking. |
| [REQ-10_UAT_Plan.md](handover/04_uat_and_testing/uat_plans/REQ-10_UAT_Plan.md) | Common Data Path UAT plan: browse, read, upload role restrictions, BM25 search, frontend sidebar/admin panel. |
| [REQ-10_UAT_Results.md](handover/04_uat_and_testing/uat_plans/REQ-10_UAT_Results.md) | 13/13 CI PASS common data path: user browse/read, role-gated uploads, super-admin/admin permission matrix. |
| [REQ-11_UAT_Plan.md](handover/04_uat_and_testing/uat_plans/REQ-11_UAT_Plan.md) | Parallel upload UAT plan: streaming backend, batch_id deferred reindex, concurrent frontend, cancel/retry/progress. |
| [REQ-11_UAT_Results.md](handover/04_uat_and_testing/uat_plans/REQ-11_UAT_Results.md) | 14/14 CI PASS parallel upload: single/batch reindex behaviour, 413 cap, path traversal block, 5-way concurrent upload. |

### handover/05_user_guides/

| File | Summary |
|---|---|
| [Admin_User_Guide.docx](handover/05_user_guides/Admin_User_Guide.docx) | Team-admin guide for the B-Pulse Admin Console: dashboard, worker config, data freshness, workflow and user management. |
| [Connectors_Guide.docx](handover/05_user_guides/Connectors_Guide.docx) | Per-worker connector configuration: Microsoft 365 (Teams, Outlook) and Atlassian (Confluence, Jira) credentials and Azure AD app permissions. |
| [Deployment_Guide.docx](handover/05_user_guides/Deployment_Guide.docx) | Enterprise cloud deployment on AWS ECS/EKS, Azure AKS, or Kubernetes: Docker builds, secret management, AWS ECS reference config. |
| [End_User_Guide_Market_Risk.docx](handover/05_user_guides/End_User_Guide_Market_Risk.docx) | Market Risk analyst end-user guide: how to chat with your Digital Worker, no technical knowledge required, login through everyday usage. |
| [RiskGPT_Connector_Setup_Guide.docx](handover/05_user_guides/RiskGPT_Connector_Setup_Guide.docx) | Step-by-step Azure AD App Registration walkthrough for Teams/Power BI/SharePoint connectors, plus glossary of M365 terms. |
| [Super_Admin_Guide.docx](handover/05_user_guides/Super_Admin_Guide.docx) | Super-admin guide for full platform administration: creating workers, adding users, uploading data, managing tools and connectors. |
| [Technical_Documentation.docx](handover/05_user_guides/Technical_Documentation.docx) | Internal developer documentation v2.9.8: three-layer architecture, LangGraph reasoning, 74+ MCP tools across risk/regulatory domains. |

### handover/06_tools_reference/

| File | Summary |
|---|---|
| [Bank_of_Canada_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/Bank_of_Canada_MCP_Tool_Reference_Guide.md) | Bank of Canada MCP tools reference v1.0.0: architecture, API auth, tool catalog, install, code samples, error handling, best practices. |
| [DuckDB_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/DuckDB_MCP_Tool_Reference_Guide.md) | DuckDB MCP tools reference: architecture, system requirements, install, tool details, schema definitions, troubleshooting. |
| [Enhanced EDGAR MCP Tools - Reference Guide.md](handover/06_tools_reference/Enhanced%20EDGAR%20MCP%20Tools%20-%20Reference%20Guide.md) | Enhanced EDGAR MCP tools v1.0.0 (Nov 2025): 20 tools across SEC filings retrieval, API keys, rate limits, detailed schemas. |
| [Federal_Reserve_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/Federal_Reserve_MCP_Tool_Reference_Guide.md) | Federal Reserve MCP tools: FRED-backed indicators, API auth, common economic series, usage examples, schema reference, error handling. |
| [Investor_Relations_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/Investor_Relations_MCP_Tool_Reference_Guide.md) | Investor Relations MCP tools reference: supported companies, document types (10-K/Q, presentations), schemas, usage examples, limitations. |
| [MCP_Studio_Python_Code_Tool_Creator_Guide.md](handover/06_tools_reference/MCP_Studio_Python_Code_Tool_Creator_Guide.md) | MCP Studio Python Tool Creator v2.9.8: build MCP tools that run Python code — dependencies, I/O, security config, testing, examples. |
| [MCP_Studio_REST_Tool_Creator_Guide.md](handover/06_tools_reference/MCP_Studio_REST_Tool_Creator_Guide.md) | MCP Studio REST Tool Creator v2.9.8: wrap any REST endpoint as an MCP tool — auth methods, request/response handling, validation, examples. |
| [MCP_Studio_User_Guide.md](handover/06_tools_reference/MCP_Studio_User_Guide.md) | MCP Studio v2.9.0 user guide covering all eight tool-creation methods (Python, REST, DB, Script, PowerBI report/DAX, LiveLink, OLAP). |
| [SEC_Edgar_Search_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/SEC_Edgar_Search_MCP_Tool_Reference_Guide.md) | SEC EDGAR Search MCP tool reference: architecture, tool inventory, detailed specs, schemas, working mechanism, auth, code samples. |
| [SQL_Select_Search_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/SQL_Select_Search_MCP_Tool_Reference_Guide.md) | SQL Select Search MCP tool reference v2.3.0: data sources configuration, tool details, API reference, schema specs, examples. |
| [Tavily_Search_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/Tavily_Search_MCP_Tool_Reference_Guide.md) | Tavily Search MCP tool reference v2.3.0: authentication, tool details, API reference, schema specs, usage examples, limitations. |
| [Yahoo_Finance_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/Yahoo_Finance_MCP_Tool_Reference_Guide.md) | Yahoo Finance MCP tool reference: auth, tool details, technical implementation, schemas, examples, limitations and error handling. |

---

## requirements/

### requirements/ (top-level)

| File | Summary |
|---|---|
| [INSTRUCTIONS.md](requirements/INSTRUCTIONS.md) | Build instructions and progress tracker for the three-layer MCP Intelligence Agent (HTML frontend, LangGraph FastAPI backend, SAJHA MCP). |
| [PLAN.md](requirements/PLAN.md) | Engineering plan with four work streams: summarisation middleware, property-file governance, source-attribution redesign, Tavily coverage. |
| [PRIORITY.md](requirements/PRIORITY.md) | Priority list (2026-04-14): REQ-07/08a/13/14-middleware/16 complete; REQ-14 bugs and REQ-06 branding queued next; REQ-08/REQ-15 killed. |
| [PROMPTS.md](requirements/PROMPTS.md) | Catalog of every prompt used in the system — agent system prompt, Python and multi-agent addenda, sub-agent instructions. |
| [REQ-13_Multi_Agent_Framework.docx](requirements/REQ-13_Multi_Agent_Framework.docx) | Multi-agent framework v2.0 inspired by DeerFlow 2.0: sub-agent orchestration via `task()`, middleware hardening, default-single agent_mode. |
| [REQ-14_Middleware_Phase2_Persistent_Memory.docx](requirements/REQ-14_Middleware_Phase2_Persistent_Memory.docx) | Five middlewares deferred from REQ-13 (Phase 2) plus persistent memory via PostgreSQL; depends on REQ-13 and REQ-07. |

### requirements/drafts/

| File | Summary |
|---|---|
| [LEFT_PANEL_UX.md](requirements/drafts/LEFT_PANEL_UX.md) | Left-sidebar UX spec: two-tab layout (Chats / Data & Workflows) with persistent admin/theme bottom bar; tabs, rename, delete implemented. |
| [Sajha_MCP_QA_Test_Plan.docx](requirements/drafts/Sajha_MCP_QA_Test_Plan.docx) | QA test plan and acceptance criteria for every active SAJHA tool — happy path, edge cases, universal response/timing/JSON contract rules. |

### requirements/pending/

| File | Summary |
|---|---|
| [REQ-06_Branding_BPulse_Digital_Workers.md](requirements/pending/REQ-06_Branding_BPulse_Digital_Workers.md) | **Pending — Not Started** (verified 2026-05-17). Rebrand audit and migration plan from RiskGPT / SAJHA / Market Risk Worker to "B-Pulse Digital Workers" across HTML, config, system prompt, favicon. |
| [REQ-08b_Apache_Iceberg_Analytical_Tables.md](requirements/pending/REQ-08b_Apache_Iceberg_Analytical_Tables.md) | **Pending — Architectural planning only** (verified 2026-05-17). Migrate trades/exposure/VaR/IRIS to Apache Iceberg on S3 with DuckDB queries; catalog choice (Glue vs Nessie vs Polaris) still open. |
| [REQ-14_Bug_Fixes_SubAgent_Audit_EDGAR.md](requirements/pending/REQ-14_Bug_Fixes_SubAgent_Audit_EDGAR.md) | **Partial** (verified 2026-05-17). Four live-run bug fixes: sub-agent timeout still hardcoded 120s, dropped sub-agents not surfaced via SSE, audit `success: None` (AuditMiddleware not wired), EDGAR 6-K coverage for Canadian banks missing. |
| [REQ-15_Supabase_Persistent_Storage.md](requirements/pending/REQ-15_Supabase_Persistent_Storage.md) | **Stubbed** (verified 2026-05-17). Supabase Storage + Postgres wiring so uploads and conversation history survive Railway redeploys; storage abstraction exists but `agent_server.py` file routes still use raw `pathlib`. |
| [REQ-16_Hetzner_S3_Migration.md](requirements/pending/REQ-16_Hetzner_S3_Migration.md) | **Partial** (verified 2026-05-17). Storage backend, path resolver, and `STORAGE_BACKEND=s3` switch all done; ~11 tool modules in `sajha/tools/impl/` still call `pathlib`/`open()`/`os.walk` directly. |

---

## See also

- [archive/INDEX.md](archive/INDEX.md) — Index of archived/legacy docs (POC EDGAR code, root-level UAT scripts, ingestion scripts, legacy Word docs, completed requirements, completed pending specs).
