# RiskGPT MCP Server

> **Source:** Converted from `RiskGPT_Digital_Worker_Platform_ERD.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**RiskGPT MCP Server**

**Digital Worker Platform**

Engineering Requirements Document

|             |                       |
|-------------|-----------------------|
| Version     | 1.0                   |
| Status      | Draft — For Review    |
| Date        | 2026-04-03            |
| Prepared by | RiskGPT Platform Team |

**1. Overview & Vision**

RiskGPT MCP Server is currently a single-tenant agent system: one shared prompt, one shared domain data folder, one shared tool list, and one shared workflow library. Every user sees the same agent with the same capabilities.

This document specifies the conversion of that system into a configurable multi-tenant agentic platform built around the concept of a Digital Worker.

**1.1 What is a Digital Worker**

A Digital Worker is a named, configurable AI agent instance with its own isolated configuration:

- System prompt — defines the worker's persona, domain expertise, and behavioural rules

- Domain data — a curated subset of files the worker can access (CSV, JSON, PDF, DOCX, XLSX)

- Verified workflows — the workflow library the worker can discover and execute

- Enabled tools — a per-worker allow-list of MCP tools drawn from the full tool registry

- Assigned users — the set of users who interact with this worker via the chat UI

When a user opens the chat interface they interact exclusively with their assigned Digital Worker. They never see configuration, other workers, or other users' data.

**1.2 Role Hierarchy**

| **Role** | **What They Can Do** |
|----|----|
| Super Admin | Create and delete Digital Workers. Assign admin users to workers. Configure any worker's prompt, data, workflows, and tools. Access all workers. Manage global user accounts. |
| Admin | Configure their own Digital Worker only: edit prompt, upload domain data, manage verified workflows, enable/disable tools. Cannot see other workers or other admins' configurations. |
| User | Access the chat UI only. Interacts with their assigned Digital Worker. No access to configuration, admin panel, or file management. |

**1.3 Current Architecture Baseline**

The following gaps exist in the current system that this document addresses:

- No multi-tenancy — all users share the same data/, workflows/, and agent prompt

- Admin panel is embedded inside the chat page — not a separate application

- No login or onboarding UI — credentials entered in a raw form

- No Digital Worker concept — one agent serves all users identically

- Role model is binary (admin / user) with no worker scoping

- Passwords stored in plaintext in users.json — no hashing

- All file-based persistence — no database, no audit trail

**2. Data Model**

**2.1 Digital Worker Entity**

Each Digital Worker is stored as a record in a new workers.json config file (or database table in future). Fields:

| **Field** | **Type** | **Description** |
|----|----|----|
| worker_id | string (UUID) | Unique identifier. Auto-generated on creation. |
| name | string | Human-readable name shown in admin panel. E.g. "CCR Risk Agent". |
| description | string | Short description of the worker's purpose. |
| created_by | string | user_id of the Super Admin who created it. |
| created_at | ISO timestamp | Creation time. |
| enabled | boolean | If false, assigned users see a "Worker offline" message. |
| system_prompt | string | Full system prompt text. Injected into agent at runtime per worker. |
| domain_data_path | string | Path to this worker's domain data folder. Default: data/workers/{worker_id}/domain_data/ |
| workflows_path | string | Path to this worker's verified workflows folder. Default: data/workers/{worker_id}/workflows/verified/ |
| enabled_tools | array of strings | List of tool names allowed for this worker. \["\*"\] means all tools. |
| assigned_admins | array of user_ids | Admin users who can manage this worker. |
| assigned_users | array of user_ids | User accounts that interact with this worker via chat. |

**2.2 User Entity (Updated)**

Extend the existing user schema with the following new fields:

| **New Field** | **Type** | **Description** |
|----|----|----|
| worker_id | string | For Admin role: the worker they manage. For User role: the worker they chat with. Null for Super Admin (manages all). |
| role | string enum | Replaces the roles array. Values: super_admin \| admin \| user. |
| password_hash | string | bcrypt hash replacing plaintext password field. |
| onboarding_complete | boolean | Set to true after user completes onboarding flow. Controls redirect on login. |
| display_name | string | Name shown in chat UI and admin panel header. |
| avatar_initials | string | Auto-derived from display_name for avatar placeholder (e.g. "SA" for Saad Ahmed). |

**2.3 Folder Structure Per Worker**

Each Digital Worker gets its own isolated directory tree under data/workers/:

> data/workers/{worker_id}/
> domain_data/
> iris/
> osfi/
> counterparties/
> analytics/
> templates/
> workflows/
> verified/ ← admin-curated .md files
> my_data/ ← user uploads scoped to this worker

The global shared data/ folder (current state) becomes the default template populated on worker creation. Admins manage only their own worker's folder tree.

**3. Backend — Agent Server Changes (agent_server.py)**

**3.1 Worker Context Resolution**

Every authenticated request must resolve to a worker context before any agent or file operation. The resolution logic runs after JWT validation:

1.  Decode JWT — extract user_id and role.

2.  Load user record — look up user_id in users store.

3.  Resolve worker_id — for super_admin: use worker_id query param or default. For admin/user: use user.worker_id field.

4.  Load worker record — fetch Digital Worker config by worker_id.

5.  Check worker.enabled — if false, return 503 {"error": "Worker offline"}.

6.  Attach worker context to request state — system_prompt, domain_data_path, workflows_path, enabled_tools.

All downstream handlers (agent run, file tree, workflow CRUD, admin ops) must use the resolved worker context, never global paths.

**3.2 New API Endpoints**

**3.2.1 Super Admin — Worker Management**

| **Method** | **Path** | **Description** |
|----|----|----|
| GET | /api/super/workers | List all Digital Workers with metadata (name, enabled, user count, admin count). |
| POST | /api/super/workers | Create a new Digital Worker. Body: {name, description, system_prompt, enabled_tools}. Auto-generates worker_id, creates folder structure, seeds from global templates. |
| GET | /api/super/workers/{worker_id} | Get full worker config including prompt, tool list, assigned users and admins. |
| PUT | /api/super/workers/{worker_id} | Update any field of a Digital Worker config. |
| DELETE | /api/super/workers/{worker_id} | Delete worker + all associated data. Requires confirmation token. |
| POST | /api/super/workers/{worker_id}/assign | Assign an admin or user to a worker. Body: {user_id, role}. |
| DELETE | /api/super/workers/{worker_id}/assign/{user_id} | Remove user assignment from worker. |
| POST | /api/super/workers/{worker_id}/clone | Clone a worker (prompt + tool list). Does not copy data files. |

**3.2.2 Super Admin — User Management**

| **Method** | **Path** | **Description** |
|----|----|----|
| GET | /api/super/users | List all users across all workers. |
| POST | /api/super/users | Create user. Body: {user_id, display_name, email, password, role, worker_id}. |
| PUT | /api/super/users/{user_id} | Update user fields including role and worker assignment. |
| DELETE | /api/super/users/{user_id} | Delete user and invalidate sessions. |
| POST | /api/super/users/{user_id}/reset-password | Generate temporary password and flag onboarding_complete=false. |

**3.2.3 Admin — Worker Configuration**

| **Method** | **Path** | **Description** |
|----|----|----|
| GET | /api/admin/worker | Get own worker config (prompt, enabled_tools, data summary). |
| PUT | /api/admin/worker/prompt | Update system prompt for own worker. Body: {system_prompt}. |
| GET | /api/admin/worker/tools | List all available tools with enabled/disabled state for this worker. |
| PUT | /api/admin/worker/tools | Update enabled_tools list. Body: {enabled_tools: \["tool_a","tool_b"\]} or \["\*"\]. |
| GET | /api/admin/worker/users | List users assigned to own worker. |
| POST | /api/admin/worker/users/{user_id}/invite | Send onboarding invite link to user (generates temp token). |

All existing /api/admin/\* file and workflow management endpoints remain but are now scoped to the resolved worker's folder paths instead of global paths.

**3.2.4 Auth & Onboarding**

| **Method** | **Path** | **Description** |
|----|----|----|
| POST | /api/auth/login | Existing endpoint. Returns JWT with added claims: role, worker_id, display_name, onboarding_complete. |
| POST | /api/auth/refresh | Refresh JWT before expiry. Returns new token same claims. |
| POST | /api/auth/logout | Invalidate session token server-side. |
| GET | /api/auth/me | Return current user profile from JWT claims. |
| POST | /api/auth/onboarding | Complete onboarding. Body: {display_name, new_password, confirm_password}. Sets onboarding_complete=true. |
| POST | /api/auth/change-password | Change own password. Body: {current_password, new_password}. |
| GET | /api/auth/invite/{token} | Validate invite token. Returns {valid: true, email, worker_name} for pre-filling onboarding form. |

**3.3 Agent Run — Worker Context Injection**

The POST /api/agent/run endpoint must inject the resolved worker context into the LangGraph agent before execution:

- system_prompt from worker.system_prompt replaces the global SYSTEM_PROMPT constant

- Tools filtered to worker.enabled_tools — dynamic tool discovery from SAJHA passes the enabled_tools list as a filter query param: GET /api/mcp?tools=tool_a,tool_b

- Workflow tool (workflow_list, workflow_get) scoped to worker.workflows_path

- Data tools (data_transform, parquet_read, fill_template, md_save) scoped to worker.domain_data_path and worker.my_data_path

- Thread IDs namespaced as {worker_id}:{user_id}:{thread_id} to prevent cross-worker conversation state bleed

**3.4 SAJHA MCP Server Changes**

**3.4.1 Tool Filtering Endpoint**

The existing GET /api/mcp (tools/list) must accept an optional tools query parameter:

- tools=\* or omitted — return all enabled tools (current behaviour)

- tools=tool_a,tool_b,tool_c — return only tools whose name is in the list

- The filtering happens after tool discovery, before JSON serialisation

- Tool configs with "enabled": false in their JSON config are always excluded regardless of the filter list

**3.4.2 Data Path Scoping**

Tools that reference application.properties data paths must accept an optional runtime override passed via request context header X-Worker-Data-Root. When present:

- data.domain_data.dir → {worker_data_root}/domain_data

- data.my_data.dir → {worker_data_root}/my_data

- data.iris_combined_csv → {worker_data_root}/domain_data/iris/iris_combined.csv

- data.osfi_docs_dir → {worker_data_root}/domain_data/osfi

- data.templates_dir → {worker_data_root}/domain_data/templates

The agent_server passes X-Worker-Data-Root on every tool execution call to SAJHA. SAJHA reads this header and overrides PropertiesConfigurator lookups for that request only.

**3.5 Password Security**

Replace plaintext password storage with bcrypt hashing:

- On user creation: bcrypt.hash(password, rounds=12) stored as password_hash. Plaintext field removed.

- On login: bcrypt.verify(input_password, stored_hash).

- On password reset: generate 16-char random temp password, hash it, set onboarding_complete=false.

- Dependency: add bcrypt to requirements (Python: bcrypt package).

**3.6 Persistence — workers.json**

Add a new config/workers.json file alongside users.json. Structure:

> {
> "workers": [
> {
> "worker_id": "w-ccr-001",
> "name": "CCR Risk Agent",
> "description": "Counterparty credit risk intelligence for capital markets.",
> "enabled": true,
> "system_prompt": "You are a senior CCR analyst...",
> "domain_data_path": "./data/workers/w-ccr-001/domain_data",
> "workflows_path": "./data/workers/w-ccr-001/workflows/verified",
> "enabled_tools": ["data_transform","generate_chart","fill_template","tavily_news_search","..."],
> "assigned_admins": ["saad"],
> "assigned_users": ["user1","user2"]
> }
> ]
> }

**4. Frontend Architecture**

The current mcp-agent.html is a single-page application with admin panel embedded inside the chat UI. This architecture is replaced with three distinct pages:

| **Page** | **File** | **Who Sees It** | **Description** |
|----|----|----|----|
| Login & Onboarding | login.html | Everyone | Entry point. Login form + first-time onboarding flow for new users. |
| Chat UI | index.html (or mcp-agent.html simplified) | Users only | Chatbot experience with conversation history. No admin controls. |
| Admin Console | admin.html | Admins + Super Admins | Separate full-page application. Worker configuration, data management, workflow management, tool control, user management. |

**4.1 Login & Onboarding Page (login.html)**

**4.1.1 Login Screen**

The login screen is the first thing every user sees. It must:

- Display the RiskGPT logo and product name centred on a navy/dark background

- Show a clean card with: Email or Username field, Password field, "Sign In" button

- Show "Forgot password?" link (triggers admin-assisted reset flow — displays "Contact your administrator to reset your password.")

- On successful login: decode JWT claims. If onboarding_complete=false → redirect to Onboarding screen. If role=user → redirect to Chat UI. If role=admin or super_admin → redirect to Admin Console.

- On failed login (401): show inline error "Invalid username or password". After 5 failures: show "Account locked. Contact your administrator."

- Persist JWT in sessionStorage (not localStorage — cleared on tab close).

**4.1.2 First-Time Onboarding Screen**

Shown only when onboarding_complete=false in the JWT. A stepper with three steps:

| **Step** | **Title** | **Fields** | **Validation** |
|----|----|----|----|
| 1 | Welcome | Display "Welcome to {worker_name}. Let's set up your profile." Read-only worker name pre-filled. | None — just a welcome message. |
| 2 | Your Profile | Display Name (text, required), Profile Initials (auto-derived, editable). | Display Name min 2 chars. Initials max 3 chars, uppercase auto-applied. |
| 3 | Set Password | New Password (min 10 chars), Confirm Password. Strength indicator bar. | Passwords match. Min length. Must differ from temp password. |

On completing step 3: POST /api/auth/onboarding → set onboarding_complete=true → redirect based on role.

**4.2 Chat UI (index.html — User Experience)**

The chat page is simplified. Admins who accidentally navigate here see a banner: "You are logged in as Admin. Go to Admin Console." with a link.

**4.2.1 Layout**

- Left sidebar: Conversation history (Today, Yesterday, Previous 7 days grouping). Rename and delete on hover. New conversation button at top.

- Top bar: Worker name and avatar on the left. User display name + initials avatar on the right. Logout icon.

- Chat panel: Message thread. Tool execution events shown as collapsible cards (tool name, duration, success/fail indicator). Canvas output rendered in a right panel that slides in.

- Input bar: Text input, file attachment button, send button. No workflow selector or admin controls.

**4.2.2 What is Removed from Current UI**

| **Removed Element** | **Reason** |
|----|----|
| "Data & Workflows" sidebar tab | Users cannot browse domain data or workflows — that is admin territory. |
| Admin zone panel | Admin panel is now a separate page entirely. |
| Workflow context bar (manual workflow loader) | Agent auto-discovers workflows via workflow_list tool — no manual loading needed. |
| File tree panels (domain_data, verified, my_workflows) | Removed from user view. My Data uploads go via a simple Upload button only. |
| Raw tool event details (tool params JSON) | Simplified to just name + duration + status. No raw JSON exposed to users. |

**4.2.3 My Data Uploads**

Users can still upload files to the my_data/ folder of their worker via a simple Upload button in the chat panel footer. The file is uploaded to /api/files/upload and stored at the worker's my_data path. No file browser is shown — uploads are invisible to the user after completion unless the agent references them.

**5. Admin Console (admin.html)**

The Admin Console is a separate HTML page, not embedded in the chat UI. It is a full-page SPA with a top navigation bar and content area. Admins see only their own worker. Super Admins see a worker switcher.

**5.1 Navigation Structure**

| **Nav Item** | **Icon** | **Admin Sees** | **Super Admin Sees** |
|----|----|----|----|
| Dashboard | Grid | Own worker stats: user count, tool count, workflow count, data file count, last activity. | All workers summary table with same stats per worker. |
| Worker Config | Settings cog | Own worker name, description, system prompt editor (full text area), enable/disable toggle. | Same but with a worker switcher dropdown at top of page. |
| Tools | Plug | Full tool list with toggle switches. Grouped by category. Search filter. Save button. | Same per worker. |
| Domain Data | Database | File tree for own worker's domain_data/. Upload, folder create, rename, move, delete, preview panel. | Same per worker. |
| Workflows | Play circle | Verified workflow list for own worker. Upload .md, validate frontmatter, preview, delete. | Same per worker. |
| Users | Users | List of users assigned to own worker. Invite new user, reset password, enable/disable, remove from worker. | Full user management across all workers. Create users, assign to workers, manage roles. |
| Activity | Clock | Recent agent runs for own worker: user, query preview, timestamp, tool count, duration. | Across all workers. |

**5.2 Worker Config Section**

**5.2.1 System Prompt Editor**

- Full-height textarea with monospace font for the system prompt.

- Character count indicator. No hard limit but warn if \> 8000 chars.

- Syntax hints panel on the right: shows available variable tokens like {worker_name}, {today_date}.

- "Save Prompt" button. Confirmation modal: "Updating the prompt will affect all conversations from this point forward. Active sessions will pick up the new prompt on next message. Continue?"

- "Preview" button opens a modal showing the rendered prompt with variables substituted.

- "Reset to Default" button restores the global default system prompt (requires super_admin).

**5.2.2 Worker Enable/Disable**

- Toggle switch at the top of the Worker Config section.

- Disabling shows modal: "Disabling this worker will prevent all assigned users from chatting. Ongoing sessions will receive a 'Worker offline' message. Continue?"

- Disabled workers show a red status badge in Super Admin dashboard.

**5.3 Tools Section**

**5.3.1 Tool List Display**

- Tools grouped by category (Data Analytics, Document Processing, Visualisation, Financial Data, Regulatory, Workflow, Web Search, etc.).

- Each tool shown as a card with: tool name, description (first 100 chars), toggle switch (enabled/disabled).

- Search bar filters by tool name or description.

- "Select All" / "Deselect All" per category.

- "Save Tools" button at bottom. Sends PUT /api/admin/worker/tools with updated list.

- Tools with "enabled": false in their JSON config file are shown greyed out with a "Unavailable" badge — cannot be toggled on.

**5.4 Domain Data Section**

Identical to the existing Admin Panel file management UI (from the Admin Panel Feature Parity ERD) but scoped to the worker's domain_data_path. Full feature set:

- Left file tree with folder expand/collapse, right preview panel (collapsible)

- Upload files (drag and drop, up to 200 files, 20MB per file)

- Create folder, rename file/folder, move via drag-and-drop, delete with confirmation

- Bulk select and delete

- Preview renderers: PDF.js, SheetJS, Mammoth.js, marked.js, JSON/TXT

**5.5 Workflows Section**

Manages the verified workflow library for this worker. Same file tree UX as Domain Data but filtered to .md files only:

- List view showing workflow name (from YAML frontmatter), description, version, last modified date.

- Upload new .md workflow — triggers frontmatter YAML validation (must have name, description, inputs).

- Preview: renders workflow markdown with syntax highlighting.

- "Test" button: opens chat UI in a modal with a pre-filled prompt to run the workflow, allowing admin to verify it before releasing to users.

- Delete with confirmation.

**5.6 Users Section**

**5.6.1 Admin View (own worker users only)**

| **Column** | **Description** |
|----|----|
| User | Display name + initials avatar + username. |
| Status | Active (green) / Disabled (grey) / Onboarding (amber — onboarding_complete=false). |
| Last Active | Last agent run timestamp for this worker. |
| Actions | Reset Password \| Disable \| Remove from worker. |

- "Invite User" button: opens modal with email/username input. Generates a temp password and invite link. Sends POST /api/admin/worker/users/{user_id}/invite.

**5.6.2 Super Admin View**

- Worker switcher at top — select worker or "All Workers" for cross-worker user table.

- Additional columns: Worker (which worker the user is assigned to), Role.

- "Create User" button: full form with display_name, username, email, role (admin/user), worker assignment, temp password.

- "Assign to Worker" action on existing users.

- "Change Role" action — promotes user to admin or demotes to user.

**5.7 Super Admin — Worker Management**

Only visible to super_admin role. Accessible via a "Manage Workers" top-level nav item.

- "Create Worker" button: modal form with name, description, optional clone-from existing worker (copies prompt + tool list).

- Worker cards in a grid: name, description, enabled status, user count, admin count. Click to manage.

- "Delete Worker" — requires typing the worker name to confirm. Permanently deletes folder tree and all assigned user associations. Assigned users retain their accounts but are unassigned.

**6. Migration Plan**

The current system has one shared environment. Migration must be non-destructive and preserve all existing data.

**6.1 Backend Migration Steps**

7.  Create workers.json with a single default worker (worker_id: "w-default") whose paths point to the existing data/domain_data and data/workflows/verified directories. This makes the current system the default worker.

8.  Extend users.json schema: add worker_id="w-default" to all existing users. Add role field mapped from roles array (\["admin"\] → "admin", else "user"). Add password_hash using bcrypt of existing plaintext password. Keep plaintext field during transition only — remove after all users have logged in and changed password.

9.  Add super_admin role to the primary admin user (risk_agent). Super admin is the only role that can manage workers.

10. Update agent_server.py: add worker context resolution middleware. Worker context for all existing requests defaults to w-default if no worker_id in JWT.

11. Update SAJHA tool filtering: add tools query param support to GET /api/mcp. Default w-default worker has enabled_tools: \["\*"\] — no change to existing behaviour.

12. Add X-Worker-Data-Root header passthrough in agent_server tool execution calls. Default worker uses existing paths — no change.

13. New endpoints (super admin, admin worker config, auth onboarding) can be added incrementally without touching existing endpoints.

**6.2 Frontend Migration Steps**

14. Rename existing mcp-agent.html to archive/mcp-agent-v1.html. Keep accessible for rollback.

15. Create login.html as a new standalone page. Update JWT storage from memory to sessionStorage.

16. Create admin.html as a new standalone page. Move all admin panel logic from mcp-agent.html.

17. Simplify mcp-agent.html into the user chat UI: remove admin zone, Data & Workflows tab, raw tool JSON, workflow context bar.

18. Update login redirect logic: role → destination page routing.

|  |
|----|
| *The migration is designed so that step 1-2 (backend worker context) can deploy first with zero user-facing change. Frontend pages (steps 3-5) deploy independently as they are completed.* |

**7. Acceptance Criteria**

**7.1 Digital Worker & Role Model**

| **AC#** | **Acceptance Criterion** |
|----|----|
| AC-DW-01 | Super Admin can create a Digital Worker with name, description, and system prompt via POST /api/super/workers. |
| AC-DW-02 | Creating a worker automatically generates the folder structure at data/workers/{worker_id}/. |
| AC-DW-03 | Super Admin can assign an admin user to a worker. That admin can then manage only that worker's config. |
| AC-DW-04 | Admin cannot see, access, or modify another worker's data, workflows, tools, or prompt. |
| AC-DW-05 | User can only access the chat UI. Navigating to admin.html as a user redirects to index.html. |
| AC-DW-06 | Disabling a worker (enabled=false) causes all subsequent chat requests from assigned users to return "Worker offline" without executing any tool calls. |
| AC-DW-07 | Deleting a worker requires typing the worker name as confirmation and permanently removes the folder tree. |
| AC-DW-08 | Cloning a worker copies the system prompt and enabled_tools list but not data files or workflows. |

**7.2 Agent Context Isolation**

| **AC#** | **Acceptance Criterion** |
|----|----|
| AC-AI-01 | Agent run uses system_prompt from the resolved worker config, not the global SYSTEM_PROMPT constant. |
| AC-AI-02 | Agent tool list contains only tools in worker.enabled_tools. A tool not in the list cannot be called even if the user asks. |
| AC-AI-03 | data_transform, parquet_read, and fill_template resolve file paths relative to the worker's domain_data_path, not the global path. |
| AC-AI-04 | workflow_list and workflow_get return only workflows in the worker's workflows_path. |
| AC-AI-05 | md_save writes files to the worker's my_data path, not a shared global folder. |
| AC-AI-06 | Two users on different workers cannot see each other's conversation threads (thread IDs are namespaced by worker_id). |

**7.3 Login & Onboarding**

| **AC#** | **Acceptance Criterion** |
|----|----|
| AC-LO-01 | Login with valid credentials returns JWT containing role, worker_id, display_name, onboarding_complete claims. |
| AC-LO-02 | A new user with onboarding_complete=false is redirected to the onboarding flow on first login. |
| AC-LO-03 | Onboarding flow collects display_name and new password. Submitting sets onboarding_complete=true. |
| AC-LO-04 | After onboarding, user with role=user is redirected to chat UI. role=admin is redirected to Admin Console. |
| AC-LO-05 | Failed login after 5 attempts locks the account and shows "Contact your administrator." |
| AC-LO-06 | Passwords are stored as bcrypt hashes. Plaintext passwords are never returned by any API endpoint. |
| AC-LO-07 | JWT is stored in sessionStorage, not localStorage. Closing the browser tab requires re-login. |

**7.4 Admin Console**

| **AC#** | **Acceptance Criterion** |
|----|----|
| AC-AC-01 | Admin Console is a standalone HTML page (admin.html), not embedded in the chat UI. |
| AC-AC-02 | Admin can edit own worker's system prompt and save it. Change takes effect on next agent run. |
| AC-AC-03 | Admin can toggle individual tools on/off. Saving updates worker.enabled_tools. Agent respects change immediately. |
| AC-AC-04 | Admin can upload files to own worker's domain_data. Files are accessible to the worker's agent. |
| AC-AC-05 | Admin can upload .md workflow files. YAML frontmatter is validated on upload. Invalid files are rejected with error detail. |
| AC-AC-06 | Admin can invite users to their worker. Invited user receives a temporary password and onboarding_complete=false. |
| AC-AC-07 | Super Admin sees all workers in a dashboard grid and can switch between them in all Admin Console sections. |
| AC-AC-08 | Super Admin can create a new worker, which appears in the dashboard immediately and has a seeded folder structure. |

**7.5 Chat UI**

| **AC#** | **Acceptance Criterion** |
|----|----|
| AC-CU-01 | User chat UI shows worker name in the top bar. No admin controls visible. |
| AC-CU-02 | "Data & Workflows" sidebar tab is not present for users. |
| AC-CU-03 | Tool execution shown as simplified cards: tool name, duration, pass/fail. No raw params JSON. |
| AC-CU-04 | User can upload a file via Upload button. File goes to worker-scoped my_data. No file browser shown. |
| AC-CU-05 | Admin user navigating to chat UI sees a banner linking to Admin Console. |

**8. Out of Scope**

- Database migration — persistence remains file-based (workers.json, users.json). SQL migration is a future phase.

- Email delivery — invite links are generated but not emailed. Admin manually shares the temporary password.

- Audit logging — activity log in Admin Console shows last N agent runs from server logs. Full audit trail is a future phase.

- Multi-worker assignment per user — each user belongs to exactly one worker in this version.

- Worker-to-worker data sharing — workers are fully isolated. Shared domain data templates are a future phase.

- API rate limiting per worker — all workers share the same rate limits in this version.

- Mobile-responsive chat UI — desktop-first in this version.

*RiskGPT MCP Server — Digital Worker Platform ERD v1.0 \| 2026-04-03*
