# RiskGPT

> **Source:** Converted from `RiskGPT_MultiWorker_Platform_Scope_ERD.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**RiskGPT**

**Multi-Worker Platform — Scope & Requirements**

Worker Isolation, Folder Scoping, Clone Behaviour & Runtime Enforcement Fixes

|  |  |
|----|----|
| Document Version | 1.0 |
| Status | DRAFT |
| Date | 2026-04-03 |
| Scope | Full multi-worker platform — file system, backend, agent, SAJHA |
| Decisions | Clone = structure + files \| Common regulatory pool \| Archive old globals \| Discard test_ccr |
| Classification | Internal — Confidential |

**Table of Contents**

**1. Overview & Design Decisions**

This document specifies the complete requirements to make RiskGPT a fully functional multi-worker platform. A comprehensive audit of the codebase (April 2026) identified that while the data model for Digital Workers is in place, the runtime enforcement layer is almost entirely absent. Workers share tools, share file system paths, and share the agent's system prompt. This document defines the target state and every change required to reach it.

|  |
|----|
| **Confirmed Design Decisions** |
| Clone behaviour: Copy full folder (structure + all data files, workflow MDs, templates). my_data/ starts empty in clone. |
| Regulatory data: One shared data/common/regulatory/ pool read by all workers. Large PDFs (OSFI CAR, Basel) not duplicated per worker. |
| Old global folders: After MR migration, rename domain_data/{iris,osfi,counterparties,...} to domain_data/\_archive/. Kept as rollback safety net. |
| test_ccr/ folder: Discarded — moved into \_archive/. CCR worker uses its own scoped folder under data/workers/{id}/. |

**2. Current State — Gap Summary**

The following table summarises every gap identified in the audit. Severity ratings: CRITICAL = broken functionality, HIGH = wrong behaviour silently, MEDIUM = missing feature, LOW = technical debt.

|  |  |  |  |  |  |
|----|----|----|----|----|----|
| **Gap ID** | **Area** | **Current Behaviour** | **Target Behaviour** | **Files Affected** | **Severity** |
| G-01 | System Prompt | Prepended as message text prefix — not a true system prompt | Agent rebuilt per-request with worker's system_prompt as the actual system message | agent.py, prompt.py, agent_server.py | **CRITICAL** |
| G-02 | Tool Filtering | All 74+ SAJHA tools available to every worker — enabled_tools never read | AGENT_TOOLS filtered against worker.enabled_tools at request time | agent/tools.py, agent_server.py | **CRITICAL** |
| G-03 | File API Scoping | \_SECTION_ROOTS hardcoded to global paths — worker_id ignored | All /api/fs/\* endpoints derive path from JWT worker_id → workers.json | agent_server.py | **CRITICAL** |
| G-04 | SAJHA Path Resolution | tools.py sends no worker context to SAJHA — file paths not scoped | X-Worker-Data-Root + X-Worker-Id headers sent on every SAJHA call | agent/tools.py, SAJHA app.py | **CRITICAL** |
| G-05 | Folder Strategy | MR uses global paths; CCR uses scoped paths — inconsistent | All workers use data/workers/{id}/ scoped paths. Common data in data/common/ | workers.json, agent_server.py | **CRITICAL** |
| G-06 | Clone API | Clone creates empty folder skeleton only | Clone = shutil.copytree of source worker folder; my_data/ reset to empty | agent_server.py | **HIGH** |
| G-07 | workers.json Schema | No common_data_path field; templates_path missing; my_workflows_path missing | Add common_data_path, templates_path, my_workflows_path fields to schema | workers.json, agent_server.py | **HIGH** |
| G-08 | Thread Isolation | Any user can resume any thread_id from any session | thread_id bound to (user_id, worker_id) tuple; validated on resume | agent_server.py | **HIGH** |
| G-09 | assigned_users Sync | users.json and workers.json are dual source of truth; assigned_users always empty | Single write path: update user.worker_id → sync workers.assigned_users atomically | agent_server.py | **MEDIUM** |
| G-10 | Role Schema | Both role (string) and roles (array) exist in users.json — conflicting | Standardise on role string. Remove roles array. Migration script provided. | users.json, agent_server.py | **MEDIUM** |
| G-11 | Password Security | Plaintext password stored as fallback alongside password_hash | All plaintext passwords migrated to bcrypt. password field removed from schema. | users.json, agent_server.py | **HIGH** |
| G-12 | Workflow Isolation | All workflows in global data/workflows/verified/ — not per-worker | Each worker has data/workers/{id}/workflows/verified/ and /my/ | agent_server.py, workers.json | **MEDIUM** |
| G-13 | Audit Logging | No log of which user/worker/tool executed what and when | Tool call audit log: user_id, worker_id, tool_name, timestamp, duration, status | agent/tools.py, agent_server.py | **MEDIUM** |
| G-14 | Upload Scoping | All uploads go to global data/uploads/ — not worker-scoped | Uploads routed to data/workers/{id}/domain_data/uploads/ | agent_server.py | **MEDIUM** |

**3. Target File System Architecture**

The target structure has three top-level zones inside sajhamcpserver/data/:

- data/workers/{worker_id}/ — fully isolated per-worker folder containing all worker-specific files

- data/common/ — shared pool for large regulatory documents read by multiple workers

- data/domain_data/\_archive/ — old global folders preserved for rollback safety

**3.1 Per-Worker Folder Structure**

Every worker gets the following sub-folder tree created at provisioning time (new worker or clone):

data/workers/{worker_id}/

├── domain_data/ ← worker-specific structured data

│ ├── iris/ ← CSV/Parquet data files

│ ├── counterparties/ ← counterparty JSON/CSV files

│ ├── market_data/ ← market/position data

│ └── uploads/ ← user file uploads (scoped to this worker)

├── workflows/

│ ├── verified/ ← admin-approved workflow MDs

│ └── my/ ← user-created workflow MDs

├── templates/ ← fill_template .md templates

└── my_data/ ← md_save outputs (reports, analyses)

**3.2 Shared Common Pool**

Regulatory PDFs are large (2–20 MB each) and referenced by multiple workers. They live in a single shared location. Workers do not own or modify these files — they are read-only reference data.

data/common/

├── regulatory/

│ ├── osfi/

│ │ ├── car/ ← CAR chapters — 2024 + 2023

│ │ ├── lar/ ← LAR chapters

│ │ └── guidelines/ ← B-series + E-series guidelines

│ ├── bcbs/ ← Basel Framework chapters

│ ├── us/

│ │ ├── occ/ ← OCC Comptroller Handbooks

│ │ ├── fed/ ← SR Letters + CCAR/DFAST

│ │ └── aml/ ← BSA, FFIEC, FinCEN, OFAC

│ ├── ca/ ← Bank Act, FINTRAC, CIRO, OSC

│ └── markets/ ← Volcker, FRTB, Reg BI, FINRA

**3.3 Archive Zone**

Existing global folders are moved (not deleted) to the archive zone after MR migration is verified:

data/domain_data/

└── \_archive/ ← renamed from top-level global folders

├── iris/ ← was: data/domain_data/iris/

├── osfi/ ← was: data/domain_data/osfi/

├── counterparties/ ← was: data/domain_data/counterparties/

├── msdocs/

├── duckdb/

├── sqlselect/

├── templates/ ← was: data/domain_data/templates/

├── test_ccr/ ← discarded — moved here

└── Test/

**3.4 Updated workers.json Schema**

The worker schema gains four new path fields and removes the old inconsistent path values:

|  |
|----|
| **workers.json — Updated Field Set** |
| worker_id string Unique identifier. e.g. w-market-risk |
| name string Display name |
| description string Short description shown in UI |
| system_prompt string Full LLM system prompt for this worker |
| enabled_tools string\[\] Allowlist of SAJHA tool names this worker may call |
| domain_data_path string SCOPED: ./data/workers/{id}/domain_data/ |
| workflows_path string SCOPED: ./data/workers/{id}/workflows/verified/ |
| my_workflows_path string SCOPED: ./data/workers/{id}/workflows/my/ \[NEW\] |
| templates_path string SCOPED: ./data/workers/{id}/templates/ \[NEW\] |
| my_data_path string SCOPED: ./data/workers/{id}/my_data/ |
| common_data_path string SHARED: ./data/common/ \[NEW\] |
| assigned_admins string\[\] Admin user IDs who can manage this worker |
| assigned_users string\[\] User IDs assigned to this worker (synced from users.json) |
| created_by string User ID of creator |
| created_at ISO8601 Creation timestamp |
| enabled boolean Whether worker is active |

**4. Migration Plan — Market Risk Worker**

The existing Market Risk (MR) worker is the only worker with live data in the old global folders. This plan migrates it to a scoped folder without disrupting service.

**4.1 Step-by-Step Migration**

1.  Create the scoped folder tree for MR: mkdir -p data/workers/w-market-risk/{domain_data/{iris,counterparties,market_data,uploads},workflows/{verified,my},templates,my_data}

2.  Copy data files from global folders into MR's scoped folder:

cp -r data/domain_data/iris/\* data/workers/w-market-risk/domain_data/iris/

cp -r data/domain_data/counterparties/\* data/workers/w-market-risk/domain_data/counterparties/

cp -r data/domain_data/templates/\* data/workers/w-market-risk/templates/

cp -r data/workflows/verified/\* data/workers/w-market-risk/workflows/verified/

3.  Copy OSFI and regulatory docs that are MR-specific into common pool (if not already there): cp -r data/domain_data/osfi/\* data/common/regulatory/osfi/

4.  Update workers.json for w-market-risk — replace all three path fields with scoped values and add the four new fields.

5.  Restart Agent Server. Run a smoke test: send a test query to the MR worker and verify it calls data_transform against the scoped iris/ folder.

6.  After smoke test passes, archive old globals:

mkdir -p data/domain_data/\_archive

mv data/domain_data/iris data/domain_data/\_archive/iris

mv data/domain_data/counterparties data/domain_data/\_archive/counterparties

mv data/domain_data/osfi data/domain_data/\_archive/osfi

mv data/domain_data/msdocs data/domain_data/\_archive/msdocs

mv data/domain_data/test_ccr data/domain_data/\_archive/test_ccr

mv data/domain_data/Test data/domain_data/\_archive/Test

mv data/domain_data/templates data/domain_data/\_archive/templates

7.  Update CCR worker (w-e74b5836) paths in workers.json to confirm they follow the same data/workers/{id}/ convention — they already do; verify and leave as-is.

|  |
|----|
| **Rollback Procedure** |
| If anything breaks after archiving: mv data/domain_data/\_archive/{iris,counterparties,...} data/domain_data/ |
| Revert workers.json w-market-risk paths to the original global values. |
| Restart Agent Server. |
| \_archive/ is not deleted until both workers have been running on scoped paths for a minimum of 2 weeks. |

**5. Backend Fixes Required**

**Fix 1 — System Prompt: Per-Request Agent Construction \[G-01\]**

Current state: SYSTEM_PROMPT is loaded once at import time from prompt.py. The worker's prompt is prepended as a user message prefix — not a true system prompt. The LLM treats it as conversation context, not as identity.

Target state: The agent graph is rebuilt per request using the requesting worker's system_prompt. The LangGraph agent receives the correct system prompt as its actual system message on every invocation.

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| agent/prompt.py | **MODIFY** | Remove \_load_prompt_from_workers() startup call. SYSTEM_PROMPT becomes a callable get_system_prompt(worker_id) that reads workers.json at call time. |
| agent/agent.py | **MODIFY** | create_agent() accepts system_prompt parameter. Called at request time, not at module import. |
| agent_server.py | **MODIFY** | POST /api/agent/run: look up worker from JWT → get system_prompt → pass to create_agent(). Remove \_worker_ctx_prefix message-prepend workaround. |

**Fix 2 — Tool Filtering: Enforce enabled_tools \[G-02\]**

Current state: AGENT_TOOLS contains all 74+ SAJHA tools at module level. The enabled_tools list in workers.json is never read during execution.

Target state: At request time, AGENT_TOOLS is filtered to the intersection with worker.enabled_tools before the agent is constructed. If enabled_tools is \["\*"\], all tools are allowed (backward compatible).

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| agent/tools.py | **MODIFY** | Add get_tools_for_worker(enabled_tools: list\[str\]) → list\[StructuredTool\]. Returns filtered subset of discovered SAJHA tools. |
| agent_server.py | **MODIFY** | POST /api/agent/run: call get_tools_for_worker(worker\['enabled_tools'\]) and pass filtered list to create_agent(). |

**Fix 3 — File API Scoping: Worker-Aware Path Resolution \[G-03\]**

Current state: \_SECTION_ROOTS dict is hardcoded with global paths. All /api/fs/{section} endpoints read from these global paths regardless of which worker the user belongs to.

Target state: File endpoints derive the correct root path from the JWT's worker_id → workers.json lookup. The \_SECTION_ROOTS dict is removed and replaced with a function that resolves paths dynamically.

|                                                                 |
|-----------------------------------------------------------------|
| **New Path Resolution Logic**                                   |
| def \_resolve_worker_path(section: str, worker: dict) -\> Path: |
| mapping = {                                                     |
| 'domain_data': worker\['domain_data_path'\],                    |
| 'uploads': worker\['domain_data_path'\] + '/uploads',           |
| 'verified': worker\['workflows_path'\],                         |
| 'my_workflows': worker\['my_workflows_path'\],                  |
| 'templates': worker\['templates_path'\],                        |
| 'my_data': worker\['my_data_path'\],                            |
| 'common': worker\['common_data_path'\], \# read-only            |
| }                                                               |
| return Path('sajhamcpserver') / mapping\[section\]              |

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| agent_server.py | **MODIFY** | Remove \_SECTION_ROOTS dict (lines 159-170). Replace with \_resolve_worker_path(). All /api/fs/\* endpoints: extract worker from JWT, call resolver. |
| agent_server.py | **MODIFY** | Upload endpoints: route files to worker\['domain_data_path'\]/uploads/ instead of global /data/uploads/. |

**Fix 4 — SAJHA Tool Calls: Pass Worker Context Headers \[G-04\]**

Current state: tools.py calls SAJHA with no worker context. SAJHA resolves file paths against its own internal working directory, which is the global domain_data folder.

Target state: Every SAJHA tool call includes X-Worker-Id and X-Worker-Data-Root headers. SAJHA resolves all relative file paths in tool params against X-Worker-Data-Root. The common data path is passed as X-Worker-Common-Root.

|                                                                          |
|--------------------------------------------------------------------------|
| **Header Set on Every SAJHA Tool Call**                                  |
| X-Service-Key: {SAJHA_SERVICE_KEY} (auth)                                |
| X-Worker-Id: {worker_id} (for audit logging)                             |
| X-Worker-Data-Root: {worker.domain_data_path} (file path resolution)     |
| X-Worker-Common-Root: {worker.common_data_path} (shared regulatory data) |

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| agent/tools.py | **MODIFY** | \_call_tool(): add worker_ctx: dict parameter. Build headers dict including X-Worker-Data-Root and X-Worker-Common-Root from worker config. |
| agent_server.py | **MODIFY** | POST /api/agent/run: look up worker → pass worker config to agent → tools receive worker context for header construction. |
| sajhamcpserver/sajha/app.py | **MODIFY** | Tool execution handler: read X-Worker-Data-Root header. Resolve relative file_path params against this root before executing tool. |

**Fix 5 — Clone API: Full Folder Copy \[G-06\]**

Current state: \_seed_worker_folders() creates an empty skeleton. Clone creates a new workers.json entry with empty folders.

Target state: Clone operation does shutil.copytree() from source worker's folder to new worker's folder. my_data/ is excluded from the copy (starts empty). workers.json entry is created with new worker_id and updated scoped paths.

|  |
|----|
| **Clone Behaviour Specification** |
| POST /api/super/workers with body: { ..., clone_from: 'w-market-risk' } |
|  |
| 1\. Generate new worker_id (UUID-based) |
| 2\. shutil.copytree(src=data/workers/{clone_from}/, dst=data/workers/{new_id}/, |
| ignore=shutil.ignore_patterns('my_data/\*')) ← exclude outputs |
| 3\. Create data/workers/{new_id}/my_data/ (empty) |
| 4\. Write new entry to workers.json with new worker_id and scoped paths |
| 5\. Return new worker object to frontend |
|  |
| Clone copies: domain_data/ (all files), workflows/verified/, workflows/my/, templates/ |
| Clone excludes: my_data/ contents (reports are not cloned) |

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| agent_server.py | **MODIFY** | POST /api/super/workers: check for clone_from field. If present, call \_clone_worker_folder() instead of \_seed_worker_folders(). |

**Fix 6 — Thread Isolation \[G-08\]**

Current state: Any authenticated user can resume any thread_id. No ownership validation.

Target state: thread_id is bound to a (user_id, worker_id) tuple stored in a thread registry. Resume attempts validate ownership before allowing access.

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| agent_server.py | **MODIFY** | Add \_thread_registry: dict mapping thread_id → {user_id, worker_id}. POST /api/agent/run: on new thread, register. On resume, validate. |

**Fix 7 — assigned_users Sync \[G-09\]**

Current state: When a user is assigned to a worker, only user.worker_id in users.json is updated. worker.assigned_users in workers.json stays empty.

Target state: A single \_assign_user_to_worker(user_id, worker_id) helper updates both files atomically. Called from all user assignment endpoints.

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| agent_server.py | **MODIFY** | Add \_assign_user_to_worker(). Call from: POST /api/super/users, PUT /api/super/users/{id}, POST /api/super/workers/{id}/assign. |

**Fix 8 — Role Schema Cleanup \[G-10\]**

Current state: users.json has both role (string) and roles (array). Code has fallback logic between the two causing inconsistent behaviour.

Target state: role (string) is the single source of truth. roles array is removed. Valid values: super_admin \| admin \| user.

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| users.json | **MODIFY** | Remove roles array from all user entries. Ensure role string is present on all entries. |
| agent_server.py | **MODIFY** | Remove roles\[\] fallback logic in \_get_role() (lines 121-130). Read role string only. |

**Fix 9 — Password Security \[G-11\]**

Current state: Some users.json entries have plaintext password stored alongside an empty password_hash. Login code falls back to plaintext comparison.

Target state: All passwords bcrypt-hashed. password field removed from schema. Login only uses password_hash. Migration script provided.

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| scripts/migrate_passwords.py | **NEW** | Read users.json → bcrypt.hashpw each plaintext password → write password_hash → remove password field → write back. Backs up to users.json.bak. |
| agent_server.py | **MODIFY** | Login endpoint: remove plaintext fallback. Only compare bcrypt.checkpw(input, user\['password_hash'\]). |
| users.json | **MODIFY** | Run migration script. Remove all password fields. |

**Fix 10 — Audit Logging \[G-13\]**

Current state: No record of which user or worker called which tool.

Target state: Every SAJHA tool call is logged to data/audit/tool_calls.jsonl with: timestamp, user_id, worker_id, tool_name, duration_ms, status (success/error).

|  |  |  |
|----|----|----|
| **File / Path** | **Change** | **Description** |
| agent/tools.py | **MODIFY** | Wrap \_call_tool() with audit logging. Write structured log line to shared audit file after each call. |
| agent_server.py | **NEW** | GET /api/super/audit endpoint: read and return last N audit log lines, filterable by worker_id or user_id. |

**6. New & Modified API Endpoints**

|  |  |  |  |
|----|----|----|----|
| **Method** | **Endpoint** | **Auth** | **Description** |
| POST | /api/super/workers | super_admin | Create worker. Accepts optional clone_from: worker_id for full folder copy. |
| GET | /api/super/workers/{id}/files/{section} | super_admin | Browse worker's scoped file tree. section: domain_data \| workflows \| templates \| my_data \| common |
| POST | /api/super/workers/{id}/files/{section}/upload | super_admin / admin | Upload file into worker's scoped domain_data/uploads/. |
| GET | /api/admin/worker/files/{section} | admin | Browse own worker's scoped file tree. |
| POST | /api/admin/worker/files/{section}/upload | admin | Upload to own worker's scoped domain_data. |
| GET | /api/super/audit | super_admin | Return audit log of tool calls. Query params: worker_id, user_id, limit, from_ts. |
| GET | /api/workers/{id}/tools | admin / super_admin | Return enabled_tools list for a worker, with full SAJHA schema for each tool. |
| DELETE | /api/super/workers/{id} | super_admin | Delete worker + archive folder (mv to \_archive/, not rm). |
| GET | /api/agent/threads | user / admin | List thread IDs owned by calling user+worker. Validates ownership. |

**7. Frontend Changes Required**

**7.1 Admin Panel — worker management**

- File browser component: lists domain_data/, workflows/, templates/ contents for the active worker using /api/admin/worker/files/{section}. Allows upload and delete within scoped folder.

- Tool panel: fetches /api/workers/{id}/tools and renders the enabled_tools list as a toggle checklist. PUT /api/admin/worker/tools on save.

- Clone button: on worker creation form, optionally select a source worker to clone from. Sends clone_from field to POST /api/super/workers.

- Audit tab (super_admin only): table view of recent tool call audit log from /api/super/audit.

**7.2 Chat UI — worker context**

- Worker indicator in header already exists and shows worker name. Add a small badge showing number of enabled tools.

- No worker-switching for regular users — they see only their assigned worker.

- Thread history: list previous thread IDs via /api/agent/threads. Allow user to resume a thread by selecting it.

**7.3 Login / Onboarding — no changes required**

Login flow correctly reads worker_id from JWT and routes to admin or chat. No changes needed here.

**8. Acceptance Criteria**

|  |  |  |  |
|----|----|----|----|
| **AC-ID** | **Category** | **Acceptance Criterion** | **Test / Verification** |
| WS-01 | File System | Each worker has a fully isolated folder at data/workers/{worker_id}/ containing domain_data/, workflows/verified/, workflows/my/, templates/, my_data/. | ls data/workers/ shows one folder per worker. Each contains all 5 sub-folders. |
| WS-02 | File System | Shared regulatory docs exist in data/common/regulatory/ and are not duplicated in individual worker folders. | grep -r 'CAR_2024' data/workers/ returns no matches. data/common/regulatory/osfi/car/ contains all chapter PDFs. |
| WS-03 | File System | Old global folders are archived at data/domain_data/\_archive/ and no longer referenced by any workers.json path. | grep -r 'domain_data/iris' workers.json returns no matches. \_archive/ folder exists. |
| WS-04 | System Prompt | When user A (MR worker) and user B (CCR worker) send identical messages, they receive responses reflecting their distinct worker personas. | Send 'summarise your role' to both workers. Responses must be demonstrably different and match each worker's system_prompt. |
| WS-05 | System Prompt | Updating a worker's system_prompt via the admin panel takes effect on the next message in a new thread without restarting the server. | Change MR system_prompt via admin panel. Start new chat. Confirm persona changed. |
| WS-06 | Tool Filtering | A worker with enabled_tools: \['data_transform','fill_template'\] cannot call tavily_news_search even if the LLM attempts to. | Set CCR worker enabled_tools to \['data_transform'\]. Send a news query. Confirm tool call is blocked and agent reports unavailability. |
| WS-07 | Tool Filtering | A worker with enabled_tools: \['\*'\] has access to all SAJHA tools (backward compatible). | Set MR worker enabled_tools to \['\*'\]. Confirm all tools are callable. |
| WS-08 | File Scoping | GET /api/fs/domain_data returns files from the requesting user's worker folder, not from global domain_data/. | Log in as MR user. Call /api/fs/domain_data. Verify path in response is data/workers/w-market-risk/domain_data/. |
| WS-09 | File Scoping | A user assigned to MR worker cannot access CCR worker's domain_data files via the file API. | Log in as MR user. GET /api/fs/domain_data?worker_id=w-ccr. Expect 403 Forbidden. |
| WS-10 | SAJHA Scoping | data_transform called by MR worker resolves file paths against data/workers/w-market-risk/domain_data/. | Call data_transform with file_path: './iris/iris_combined.csv' as MR worker. Verify SAJHA reads from data/workers/w-market-risk/domain_data/iris/iris_combined.csv. |
| WS-11 | SAJHA Scoping | data_transform called by CCR worker resolves file paths against CCR's domain_data folder. | Call data_transform with same relative path as CCR worker. SAJHA reads from data/workers/w-e74b5836/domain_data/iris/iris_combined.csv. |
| WS-12 | Clone | Cloning worker A creates worker B with identical domain_data/, workflow MDs, and templates. my_data/ is empty. | Clone MR. Diff data/workers/w-market-risk/ vs new worker folder (excluding my_data/). No differences. New worker my_data/ is empty. |
| WS-13 | Clone | Cloned worker has its own workers.json entry with correctly scoped paths pointing to its own folder. | Read workers.json after clone. New entry has domain_data_path: ./data/workers/{new_id}/domain_data/. |
| WS-14 | Thread Isolation | A user cannot resume a thread_id that belongs to a different user. | User A creates thread T1. User B sends resume: T1. Expect 403 Forbidden. |
| WS-15 | Passwords | No plaintext passwords in users.json. All entries have password_hash starting with \$2b\$. | cat users.json \| grep '"password"' returns no matches. All entries have password_hash field. |
| WS-16 | Roles | users.json has no roles array field. All users have role string only. | cat users.json \| grep '"roles"' returns no matches. |
| WS-17 | Audit | Every SAJHA tool call produces an audit log line containing timestamp, user_id, worker_id, tool_name, duration_ms, status. | Trigger any tool call. Read data/audit/tool_calls.jsonl. Last line contains all 6 required fields. |
| WS-18 | Uploads | Files uploaded via the UI are stored in the worker's scoped domain_data/uploads/ folder. | Upload a CSV as MR user. Confirm file appears at data/workers/w-market-risk/domain_data/uploads/{filename}. |
| WS-19 | assigned_users | workers.json assigned_users is always in sync with users.json worker_id assignments. | Assign user X to worker W via admin panel. workers.json W.assigned_users contains X. users.json X.worker_id = W. |
| WS-20 | End-to-End | Full workflow: CCR worker runs cpty_intelligence workflow — data_transform reads CCR iris data, fill_template uses CCR template, md_save writes to CCR my_data/. | Run counterparty intelligence workflow as CCR worker. Verify output file appears at data/workers/w-ccr/my_data/reports/. |

**9. Implementation Order**

The fixes are sequenced to ensure each step is independently testable and can be rolled back without affecting subsequent steps.

|  |  |  |  |  |
|----|----|----|----|----|
| **Phase** | **Fix** | **Description** | **Dependency** | **AC Coverage** |
| 1 — Foundation | G-11 + G-10 | Migrate passwords to bcrypt. Clean roles schema. | None | WS-15, WS-16 |
| 1 — Foundation | G-05 | Migrate MR to scoped folder. Archive globals. | None | WS-01, WS-02, WS-03 |
| 1 — Foundation | G-07 | Update workers.json schema with new path fields. | G-05 | WS-01 |
| 2 — Agent | G-01 | Per-request system prompt injection. | G-07 | WS-04, WS-05 |
| 2 — Agent | G-02 | Tool filtering via enabled_tools. | G-01 | WS-06, WS-07 |
| 3 — SAJHA | G-04 | X-Worker-Data-Root + X-Worker-Common-Root headers to SAJHA. | G-05 | WS-10, WS-11 |
| 3 — SAJHA | G-03 | File API path scoping in agent_server.py. | G-05 | WS-08, WS-09, WS-18 |
| 4 — Data | G-06 | Clone API — full folder copy. | G-05 | WS-12, WS-13 |
| 4 — Data | G-12 + G-14 | Workflow isolation + upload scoping. | G-03 | WS-18 |
| 5 — Integrity | G-08 | Thread isolation — ownership validation. | G-01 | WS-14 |
| 5 — Integrity | G-09 | assigned_users sync. | None | WS-19 |
| 5 — Integrity | G-13 | Audit logging for tool calls. | G-04 | WS-17 |
| 6 — E2E | All | End-to-end test: CCR worker full workflow run. | All above | WS-20 |
