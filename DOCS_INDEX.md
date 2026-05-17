## Documentation Index

This is the canonical index for active documentation in the repo. Every `.md` and `.docx` file under `/`, `handover/`, and `requirements/` is listed below with a one-line summary derived from its actual contents. For archived/legacy docs (POC code, root-level UAT scripts, ingestion scripts, legacy Word docs), see [archive/INDEX.md](archive/INDEX.md).

Last updated: 2026-05-17.

---

## Repo Root

| File | Summary |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Developer reference for the three-layer system: frontend HTML/JS, FastAPI agent server, SAJHA MCP server; run commands, key directories, middleware stack. |
| [LOCAL_DEV_SETUP.md](LOCAL_DEV_SETUP.md) | Local Mac setup session notes: venv install, switch to xAI Grok, disable polluted Postgres, migrate orphaned worker files. |

---

## handover/

### handover/00_START_HERE.md

Handover package entry point: platform purpose, run commands, folder map (01–06), current build/pending status, and test coverage summary as of April 2026.

### handover/01_project_overview/

| File | Summary |
|---|---|
| [CREDENTIALS.md](handover/01_project_overview/CREDENTIALS.md) | Master credentials reference: Azure/M365, Atlassian, Teams/Outlook/Jira/Confluence IDs, B-Pulse platform accounts (kept private, not committed). |
| [NEXT_STEPS.md](handover/01_project_overview/NEXT_STEPS.md) | Market Risk connector handoff: Teams RSC v1.0.1 install confirmed, Outlook ready to test, Confluence pending; next-step terminal commands. |

### handover/02_architecture/

| File | Summary |
|---|---|
| [Glossary.md](handover/02_architecture/Glossary.md) | Alphabetical glossary of SAJHA MCP Server terms, acronyms, and concepts (ABC, AJAX, API, AST, etc.) — reference document v2.9.0. |
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
| [Requirements_Gap_Analysis.md](handover/03_requirements/Requirements_Gap_Analysis.md) | Cross-reference of `requirements/completed/` against live code: REQ-01–04 complete; REQ-PREP-01–07, REQ-WF, REQ-DD, REQ-MD, REQ-CD all closed or noted. |

### handover/03_requirements/pending/

| File | Summary |
|---|---|
| [REQ-01a_Shared_FileTree_Library_Build_and_Swap.md](handover/03_requirements/pending/REQ-01a_Shared_FileTree_Library_Build_and_Swap.md) | Build `public/js/file-tree.js` (`BPulseFileTree`) and swap the three inline file-tree implementations in `admin.html` and `mcp-agent.html` — build-swap-verify-clean. |
| [REQ-01b_FileTree_Phase2_Backend_and_Features.md](handover/03_requirements/pending/REQ-01b_FileTree_Phase2_Backend_and_Features.md) | Phase 2 file-tree backend: add `size_bytes`/`modified_at` in tree response, copy/batch-delete endpoints, quota endpoint, plus FE size/search/quota. |
| [REQ-02a_Connector_External_Setup_Guide.md](handover/03_requirements/pending/REQ-02a_Connector_External_Setup_Guide.md) | External setup steps for Teams/Outlook/Confluence/Jira — install apps, log into browser, defer API tokens until basic interaction is confirmed. |
| [REQ-02b_Connector_MR_Worker_Integration_Testing.md](handover/03_requirements/pending/REQ-02b_Connector_MR_Worker_Integration_Testing.md) | Configure Market Risk worker connector_scope with live credentials and run end-to-end integration tests against Teams, Outlook, Jira, Confluence. |
| [REQ-03_Visualization_Tool_Debug_and_Rendering.md](handover/03_requirements/pending/REQ-03_Visualization_Tool_Debug_and_Rendering.md) | Fix chart pipeline so `generate_chart` Plotly HTML renders in chat and canvas — six fixes covering tool result truncation, serve endpoint, SSE, iframe, badge, PNG fallback. |
| [REQ-04a_Python_Execution_Tool_Basic.md](handover/03_requirements/pending/REQ-04a_Python_Execution_Tool_Basic.md) | Sandboxed Python execution with core data science libs: `python_execute`, `python_run_script`, AST security scan, figure capture into canvas. |
| [REQ-04b_Python_Execution_Tool_Heavy_Quant_Libraries.md](handover/03_requirements/pending/REQ-04b_Python_Execution_Tool_Heavy_Quant_Libraries.md) | Extend the Python sandbox with scikit-learn, statsmodels, arch (GARCH), QuantLib, riskfolio-lib, cvxpy, xarray, networkx. |
| [REQ-05_Summarization_Engine.md](handover/03_requirements/pending/REQ-05_Summarization_Engine.md) | Claude Code-style rolling context compression: 180k trigger, sub-20% post-compression utilisation, SQLite persistence, fullness gauge in both UIs. |
| [REQ-06_Branding_BPulse_Digital_Workers.md](handover/03_requirements/pending/REQ-06_Branding_BPulse_Digital_Workers.md) | Rebrand audit and migration plan from RiskGPT / SAJHA / Market Risk Worker to the unified "B-Pulse Digital Workers" brand across HTML and config. |
| [REQ-07_PostgreSQL_Database_Migration.md](handover/03_requirements/pending/REQ-07_PostgreSQL_Database_Migration.md) | Migrate users, apikeys, workers, threads, audit logs, file metadata, Flask sessions from JSON/JSONL flat files to PostgreSQL (domain data stays on FS/S3). |
| [REQ-08_Apache_Iceberg_S3_Data_Strategy.md](handover/03_requirements/pending/REQ-08_Apache_Iceberg_S3_Data_Strategy.md) | Data-architecture review: where Iceberg (analytical), S3 (object), and Postgres (operational) fit relative to current filesystem storage. |
| [REQ-10_Common_Data_Path.md](handover/03_requirements/pending/REQ-10_Common_Data_Path.md) | Activate `common_data_path` as a real shared layer — admin/super-admin uploads, user read-only browse, BM25 search inclusion, sidebar UI. |
| [REQ-11_Multi_File_Parallel_Upload.md](handover/03_requirements/pending/REQ-11_Multi_File_Parallel_Upload.md) | Concurrent streaming upload engine replacing the serial XHR + per-file reindex pipeline; cancel/retry/progress, batch_id deferred reindex. |

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
| [Bank_of_Canada_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/Bank_of_Canada_MCP_Tool_Reference_Guide.md) | Bank of Canada MCP tools reference: architecture, API auth, tool catalog, install, code samples, error handling, best practices (v1.0.0). |
| [DuckDB_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/DuckDB_MCP_Tool_Reference_Guide.md) | DuckDB MCP tools reference: architecture, system requirements, install, tool details, schema definitions, troubleshooting. |
| [Enhanced EDGAR MCP Tools - Reference Guide.md](handover/06_tools_reference/Enhanced%20EDGAR%20MCP%20Tools%20-%20Reference%20Guide.md) | Enhanced EDGAR MCP tools complete docs: 20 tools across SEC filings retrieval, API keys, rate limits, detailed schemas (v1.0.0, Nov 2025). |
| [Federal_Reserve_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/Federal_Reserve_MCP_Tool_Reference_Guide.md) | Federal Reserve MCP tools: FRED-backed indicators, API auth, common economic series, usage examples, schema reference, error handling. |
| [Investor_Relations_MCP_Tool_Reference_Guide.md](handover/06_tools_reference/Investor_Relations_MCP_Tool_Reference_Guide.md) | Investor Relations MCP tools reference: supported companies, document types (10-K/Q, presentations), schemas, usage examples, limitations. |
| [MCP_Studio_Python_Code_Tool_Creator_Guide.md](handover/06_tools_reference/MCP_Studio_Python_Code_Tool_Creator_Guide.md) | MCP Studio Python Tool Creator: build MCP tools that run Python code — dependencies, I/O, security config, testing, examples (v2.9.8). |
| [MCP_Studio_REST_Tool_Creator_Guide.md](handover/06_tools_reference/MCP_Studio_REST_Tool_Creator_Guide.md) | MCP Studio REST Tool Creator: wrap any REST endpoint as an MCP tool — auth methods, request/response handling, validation, examples (v2.9.8). |
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
| [NEXT_STEPS.md](requirements/NEXT_STEPS.md) | Market Risk connector status duplicate of `handover/01_project_overview/NEXT_STEPS.md` — Teams RSC complete, Outlook ready, Confluence pending. |
| [PLAN.md](requirements/PLAN.md) | Engineering plan with four work streams: summarisation middleware, property-file governance, source-attribution redesign, Tavily coverage. |
| [PRIORITY.md](requirements/PRIORITY.md) | Requirements priority list (2026-04-14): REQ-07/08a/13/14/16 complete; REQ-14 bug fixes and REQ-06 branding queued next. |
| [PROMPTS.md](requirements/PROMPTS.md) | Catalog of every prompt used in the system — agent system prompt, Python and multi-agent addenda, sub-agent instructions. |
| [Requirements_Gap_Analysis.md](requirements/Requirements_Gap_Analysis.md) | Dated 2026-04-06 gap analysis: REQ-01–04, 09, 10, 11 complete; five requirements (REQ-05–08 + REQ-03 Listener) pending. |
| [REQ-13_Multi_Agent_Framework.docx](requirements/REQ-13_Multi_Agent_Framework.docx) | Multi-agent framework v2.0 inspired by DeerFlow 2.0: sub-agent orchestration via `task()`, middleware hardening, default-single agent_mode. |
| [REQ-14_Middleware_Phase2_Persistent_Memory.docx](requirements/REQ-14_Middleware_Phase2_Persistent_Memory.docx) | Five middlewares deferred from REQ-13 (Phase 2) plus persistent memory via PostgreSQL; depends on REQ-13 and REQ-07. |
| [SAJHA_Regression_Test_Report_v2_2026-04-06.docx](requirements/SAJHA_Regression_Test_Report_v2_2026-04-06.docx) | Regression v2 report: 132 tests in 18 functional groups, all roles, 6 bugs found and resolved (duplicate of handover copy). |
| [SAJHA_Regression_Test_Results_2026-04-05.docx](requirements/SAJHA_Regression_Test_Results_2026-04-05.docx) | First regression pass: 76 tests across 15 areas, 67 PASS / 9 FAIL by category (duplicate of handover copy). |

### requirements/completed/

| File | Summary |
|---|---|
| [BMO_Market_Credit_Risk_Intelligence_Brief_Workflow.md](requirements/completed/BMO_Market_Credit_Risk_Intelligence_Brief_Workflow.md) | BMO counterparty workflow spec: `tavily_domain_search` + optional IRIS lookup, per-CP brief + portfolio-level dashboard, canvas markdown output. |
| [BMO_Market_Credit_Risk_Intelligence_Brief_Workflow.docx](requirements/completed/BMO_Market_Credit_Risk_Intelligence_Brief_Workflow.docx) | Word version of the BMO CCR intelligence-brief workflow spec: step 1 input, parallel domain searches, brief assembly. |
| [IRIS_CCR_Claude_Code_Requirements.docx](requirements/completed/IRIS_CCR_Claude_Code_Requirements.docx) | IRIS CCR build requirements: 9 tools, test CSV, literature file, BaseMCPTool registration via JSON config and hot-reload. |
| [REQ-01a_Shared_FileTree_Library_Build_and_Swap.md](requirements/completed/REQ-01a_Shared_FileTree_Library_Build_and_Swap.md) | Completed version of REQ-01a: build `BPulseFileTree` and swap the three inline file-tree implementations one at a time. |
| [REQ-01b_FileTree_Phase2_Backend_and_Features.md](requirements/completed/REQ-01b_FileTree_Phase2_Backend_and_Features.md) | Completed Phase 2 file-tree backend: size/modified, copy, batch-delete, quota, plus FE size/search/quota. |
| [REQ-03_Listener_Workflows.docx](requirements/completed/REQ-03_Listener_Workflows.docx) | Listener Workflows & Event-Driven Agent System: folder-watch, Outlook inbox, Teams channel, cron triggers via Super Admin Automation screen. |
| [REQ-03_Visualization_Tool_Debug_and_Rendering.md](requirements/completed/REQ-03_Visualization_Tool_Debug_and_Rendering.md) | Completed version of REQ-03 chart pipeline fix (six fixes: strip-html, serve endpoint, SSE, iframe, badge, PNG fallback). |
| [REQ-04a_Python_Execution_Tool_Basic.md](requirements/completed/REQ-04a_Python_Execution_Tool_Basic.md) | Completed REQ-04a Python sandbox: `python_execute`, `python_run_script`, AST scan, figure capture, basic libs. |
| [REQ-04b_Python_Execution_Tool_Heavy_Quant_Libraries.md](requirements/completed/REQ-04b_Python_Execution_Tool_Heavy_Quant_Libraries.md) | Completed REQ-04b sandbox extension with heavy quant libs (scikit-learn, arch, riskfolio-lib, QuantLib, xarray, networkx). |
| [REQ-05_Summarization_Engine.md](requirements/completed/REQ-05_Summarization_Engine.md) | Completed REQ-05 Claude Code-style summarization engine: 180k trigger, SQLite persistence, dual-UI fullness gauge. |
| [REQ-10_Common_Data_Path.md](requirements/completed/REQ-10_Common_Data_Path.md) | Completed REQ-10 common_data shared layer: admin uploads, user read-only browse, BM25 inclusion, sidebar UI. |
| [REQ-11_Multi_File_Parallel_Upload.md](requirements/completed/REQ-11_Multi_File_Parallel_Upload.md) | Completed REQ-11 parallel upload engine: streaming, batch_id deferred reindex, concurrent FE, cancel/retry/progress. |
| [RiskGPT_Admin_Panel_Feature_Parity_Update.docx](requirements/completed/RiskGPT_Admin_Panel_Feature_Parity_Update.docx) | Admin Panel feature-parity additions: preview pane, folder rename, bulk operations, folder move, context menu parity with chat UI. |
| [RiskGPT_Bank_Filings_Download_Plan.md](requirements/completed/RiskGPT_Bank_Filings_Download_Plan.md) | Plan to download 5 years of 10-K/10-Q (US banks) and 40-F/6-K/annual reports (Canadian banks) into domain data. |
| [RiskGPT_Connector_ERD.docx](requirements/completed/RiskGPT_Connector_ERD.docx) | Connector ERD (duplicate of handover copy): Teams/Power BI/SharePoint/Outlook/Jira architecture, credentials, request flow. |
| [RiskGPT_Connector_Setup_Guide.docx](requirements/completed/RiskGPT_Connector_Setup_Guide.docx) | Enterprise connector setup guide v1 (April 2026): six connectors share one Azure AD app via OAuth2 client-credentials flow. |
| [RiskGPT_Digital_Worker_Platform_ERD.docx](requirements/completed/RiskGPT_Digital_Worker_Platform_ERD.docx) | Digital Worker Platform ERD (duplicate of handover copy): convert single-tenant agent into multi-tenant configurable workers. |
| [RiskGPT_Enterprise_Migration_Prep_Requirements.md](requirements/completed/RiskGPT_Enterprise_Migration_Prep_Requirements.md) | Local refactor prep for S3 migration: storage seam, path-resolver, config-driven backend, behaviour-preserving. |
| [RiskGPT_MultiWorker_Platform_Scope_ERD.docx](requirements/completed/RiskGPT_MultiWorker_Platform_Scope_ERD.docx) | Multi-worker isolation requirements (duplicate of handover copy): three-zone layout, clone behaviour, runtime enforcement. |
| [RiskGPT_Platform_Infrastructure_ERD.docx](requirements/completed/RiskGPT_Platform_Infrastructure_ERD.docx) | Platform infrastructure ERD (duplicate of handover copy): Docker consolidation and unified authentication. |
| [RiskGPT_Regulatory_Data_Requirements.docx](requirements/completed/RiskGPT_Regulatory_Data_Requirements.docx) | Regulatory data acquisition plan: OSFI CAR/LAR PDFs and B/E-series guidelines mapped to worker domain folders. |
| [RiskGPT_Visualisation_Toolkit_ERD.docx](requirements/completed/RiskGPT_Visualisation_Toolkit_ERD.docx) | `generate_chart` MCP tool ERD: Plotly interactive output, PNG export, chart-type enum, input schema for axes/grouping/themes. |
| [RiskGPT_Worker_Path_Architecture_Requirements.md](requirements/completed/RiskGPT_Worker_Path_Architecture_Requirements.md) | Worker path architecture consolidation: three-category data model, workflow retirement, section-key unification, per-user my_data scoping. |
| [SAJHA_File_Upload_Requirements.docx](requirements/completed/SAJHA_File_Upload_Requirements.docx) | File upload feature spec: upload endpoint, `list_uploaded_files` tool, HTML upload button, config-driven directory roots. |
| [SAJHA_OSFI_Tool_Suite_Requirements.docx](requirements/completed/SAJHA_OSFI_Tool_Suite_Requirements.docx) | OSFI tool suite spec: `osfi_list_docs`, `osfi_read_document`, `osfi_fetch_announcements`, `osfi_search_guidance` — handling large PDFs. |
| [SAJHA_Workflow_Tool_Suite_Requirements.docx](requirements/completed/SAJHA_Workflow_Tool_Suite_Requirements.docx) | Workflow tool suite spec: `op_risk_controls_workflow` and `counterparty_intelligence_workflow` MCP tools. |
| [Sajha_Admin_Panel_ERD.docx](requirements/completed/Sajha_Admin_Panel_ERD.docx) | Admin Panel ERD (duplicate of handover copy): new top-tab governance for shared data, `is_admin` JWT, RBAC. |
| [Sajha_Canvas_PRD.docx](requirements/completed/Sajha_Canvas_PRD.docx) | Canvas Panel PRD: split-screen output rendering inspired by ChatGPT Canvas for long-form structured documents/reports. |
| [Sajha_Data_Toolkit_Test_Plan.docx](requirements/completed/Sajha_Data_Toolkit_Test_Plan.docx) | Data-Agnostic Toolkit test plan: pytest fixtures (domain_data + my_data demo files) and per-tool `execute()` test cases. |
| [Sajha_Data_Transform_Parquet_Tools_ERD.docx](requirements/completed/Sajha_Data_Transform_Parquet_Tools_ERD.docx) | ERD for three new tools: `parquet_read`, `data_transform`, `data_export` — pandas/pyarrow, path-parameterised, single impl file. |
| [Sajha_Data_Workflows_FileTree_ERD.docx](requirements/completed/Sajha_Data_Workflows_FileTree_ERD.docx) | File-tree panel ERD (duplicate of handover copy): four sections, preview, indexing, MD-only editing in My Workflows. |
| [Sajha_EDGAR_Architecture_Plan.docx](requirements/completed/Sajha_EDGAR_Architecture_Plan.docx) | EDGAR intelligence redesign v2.0: Tavily-first analyst-driven retrieval given the no-direct-SEC-HTTP deployment constraint. |
| [Sajha_Operational_Tools_Suite_ERD.docx](requirements/completed/Sajha_Operational_Tools_Suite_ERD.docx) | Operational tools ERD: PDF reader, MD save, MD-to-DOCX, file search, template engine, versioning — six tools in one impl file. |
| [Sajha_Workflow_MD_Migration_Implementation.docx](requirements/completed/Sajha_Workflow_MD_Migration_Implementation.docx) | Migrate JSON workflow tools to MD files with YAML frontmatter; introduce `workflow_list`/`workflow_get` and retire the old WorkflowTool. |
| [Tavily_SEC_MDA_Direct_Fetch_Note.docx](requirements/completed/Tavily_SEC_MDA_Direct_Fetch_Note.docx) | Technical note explaining why Tavily extract/search cannot retrieve large SEC MD&A sections and why direct streaming is the only reliable path. |
| [mcp-agent-trd-final.docx](requirements/completed/mcp-agent-trd-final.docx) | Final MCP Intelligence Agent TRD (duplicate of handover copy): three-layer architecture, LangGraph ReAct backend, SAJHA, SSE contract. |

### requirements/drafts/

| File | Summary |
|---|---|
| [LEFT_PANEL_UX.md](requirements/drafts/LEFT_PANEL_UX.md) | Left-sidebar UX spec: two-tab layout (Chats / Data & Workflows) with persistent admin/theme bottom bar; tabs, rename, delete implemented. |
| [Sajha_MCP_QA_Test_Plan.docx](requirements/drafts/Sajha_MCP_QA_Test_Plan.docx) | QA test plan and acceptance criteria for every active SAJHA tool — happy path, edge cases, universal response/timing/JSON contract rules. |

### requirements/pending/

| File | Summary |
|---|---|
| [REQ-02a_Connector_External_Setup_Guide.md](requirements/pending/REQ-02a_Connector_External_Setup_Guide.md) | Pending REQ-02a (duplicate of handover copy): app/browser setup for Teams/Outlook/Confluence/Jira before tool credentials. |
| [REQ-02b_Connector_MR_Worker_Integration_Testing.md](requirements/pending/REQ-02b_Connector_MR_Worker_Integration_Testing.md) | Pending REQ-02b (duplicate of handover copy): MR worker connector_scope wiring plus end-to-end integration tests. |
| [REQ-06_Branding_BPulse_Digital_Workers.md](requirements/pending/REQ-06_Branding_BPulse_Digital_Workers.md) | Pending REQ-06 (duplicate of handover copy): rebrand RiskGPT / SAJHA / Market Risk Worker to B-Pulse Digital Workers. |
| [REQ-07_PostgreSQL_Database_Migration.md](requirements/pending/REQ-07_PostgreSQL_Database_Migration.md) | REQ-07 v1.3 status: Postgres migration partially complete, 4 production-audit gaps remaining as of 2026-04-14. |
| [REQ-08_DevOps_Cloud_Deployment_Guide.md](requirements/pending/REQ-08_DevOps_Cloud_Deployment_Guide.md) | DevOps cloud-deployment one-pager: RDS Postgres, S3 bucket, AWS Glue catalog (single Docker container); env vars summary. |
| [REQ-08a_S3_Object_Storage_Integration.md](requirements/pending/REQ-08a_S3_Object_Storage_Integration.md) | S3 storage integration: replace local FS for binaries, refactor 28 `build_index()` call sites to write to Postgres `file_metadata`. |
| [REQ-08b_Apache_Iceberg_Analytical_Tables.md](requirements/pending/REQ-08b_Apache_Iceberg_Analytical_Tables.md) | Migrate trades/exposure/VaR/IRIS to Apache Iceberg tables on S3 with ACID, time travel, schema/partition evolution; DuckDB queries Iceberg. |
| [REQ-14_Bug_Fixes_SubAgent_Audit_EDGAR.md](requirements/pending/REQ-14_Bug_Fixes_SubAgent_Audit_EDGAR.md) | Four live-run bug fixes: sub-agent timeout config, silent sub-agent drop, `success: None` audit corruption, EDGAR Canadian coverage. |
| [REQ-15_Supabase_Persistent_Storage.md](requirements/pending/REQ-15_Supabase_Persistent_Storage.md) | Supabase Storage + Postgres wiring so uploads and conversation history survive Railway ephemeral container redeploys (status: killed). |
| [REQ-16_Hetzner_S3_Migration.md](requirements/pending/REQ-16_Hetzner_S3_Migration.md) | Activate the existing storage abstraction against Hetzner S3-compatible object storage; fix 9 bypass tool files, then env-flip and migrate data. |

---

## See also

- [archive/INDEX.md](archive/INDEX.md) — Index of archived/legacy docs (POC EDGAR code, root-level UAT scripts, ingestion scripts, legacy Word docs).
