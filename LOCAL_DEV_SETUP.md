# Local Dev Setup & Bug Fix Notes

**Session:** 2026-05-15
**Goal:** Get the app running locally end-to-end on macOS, switch LLM to xAI Grok, and fix a file-discovery bug.

---

## TL;DR

1. Cloned the repo, set up Python venv + dependencies, started both servers locally (SAJHA on 3002, agent on 8000).
2. Switched LLM provider from Anthropic to xAI Grok (`grok-4-1-fast-non-reasoning`).
3. Diagnosed why the agent's `list_uploaded_files` tool returned 0 files while the UI sidebar showed files. Root cause was **data inconsistency**: a polluted Postgres `bpulse` DB had stale `users.worker_id` rows from a previous project location (`/Users/saadahmed/Desktop/react_agent/`), causing the file panel and the agent to scope their requests to two different workers.
4. Fixed by disabling Postgres (falling back to JSON workers + SQLite checkpoints), migrating orphaned data files to the active worker, and resetting `test_user` for non-super-admin testing.

The only git-tracked change pushed to `origin/main` is the `test_user` password reset (commit `b307bc3`).

---

## What I Changed

### 1. Local environment
- Created `venv/` with Python 3.13.5 and installed both `requirements.txt` (root) and `sajhamcpserver/requirements.txt`. Gitignored.
- Created `.env` from `.env.example`. Gitignored. Contains the xAI API key — **do not commit**.
- Ensured local Postgres `bpulse` DB exists (Homebrew `postgresql@14`). Not strictly needed after the fix below.

### 2. LLM provider switched to xAI Grok
In `.env`:
```
LLM_PROVIDER=xai
XAI_API_KEY=<redacted — see local .env>
XAI_MODEL=grok-4-1-fast-non-reasoning
LLM_MAX_TOKENS=8192
```
No code change required — [agent/llm_factory.py:52-68](agent/llm_factory.py:52) already supports xAI via the OpenAI-compatible client at `https://api.x.ai/v1`.

The model `grok-4-1-fast-non-reasoning` was selected by listing available models against the user's xAI key (`curl https://api.x.ai/v1/models`) and choosing the newest "fast" non-reasoning variant for low-latency tool-calling.

### 3. Disabled PostgreSQL for local dev
The bundled `bpulse` Postgres DB had leftover state from a previous developer's local environment, including:
- `users.worker_id` for `risk_agent` set to `w-e74b5836` (a disabled "CCR Agent" worker), overriding the value in `sajhamcpserver/config/users.json` which had it as `w-market-risk`.
- 70+ rows in `file_metadata` with `rel_path` values pointing at absolute paths under `/Users/saadahmed/Desktop/react_agent/` — a directory that doesn't exist in this clone.

When `DATABASE_URL` is set, [agent_server.py:47](agent_server.py:47) sets `_DB_ENABLED=True` and routes user/worker lookups through Postgres ([agent_server.py:161-179](agent_server.py:161)), so the polluted DB wins over the JSON config.

**Fix:** restart both servers with `DATABASE_URL` unset:
```bash
unset DATABASE_URL
cd sajhamcpserver && ../venv/bin/python run_server.py &
cd .. && ./venv/bin/python -m uvicorn agent_server:app --host 127.0.0.1 --port 8000 &
```
With no `DATABASE_URL`, the app falls back to `users.json` + `workers.json` for identity and `AsyncSqliteSaver` for LangGraph checkpoints ([agent_server.py:622-626](agent_server.py:622)). No source code modified.

### 4. Migrated orphaned data files
Two files existed only under the stale-mapped worker on disk:
- `sajhamcpserver/data/workers/w-e74b5836/domain_data/pbis_intervention_workflow.md`
- `sajhamcpserver/data/workers/w-e74b5836/my_data/risk_agent/pbis_student_mock_data.csv`

After removing the Postgres override, `risk_agent`'s real worker is `w-market-risk` (per `users.json`). Copied the files to the active worker's data tree:
```bash
cp -r sajhamcpserver/data/workers/w-e74b5836/my_data/risk_agent sajhamcpserver/data/workers/w-market-risk/my_data/
cp sajhamcpserver/data/workers/w-e74b5836/domain_data/pbis_intervention_workflow.md sajhamcpserver/data/workers/w-market-risk/domain_data/
rm -f sajhamcpserver/data/workers/w-market-risk/{domain_data,my_data/risk_agent}/.index.json
```
The runtime BM25 indexer regenerates `.index.json` on the next tree read. All paths under `sajhamcpserver/data/workers/*` are gitignored — these files are local only.

### 5. Reset `test_user` password
For testing non-super-admin behavior (no worker dropdown, single-worker scope), reset `test_user` via the admin API:
```
POST /api/super/users/test_user/reset-password   { "new_password": "TestUser123!" }
```
This is the only change captured in git history (commit `b307bc3` on `main`): the bcrypt hash and `onboarding_complete` flag in [sajhamcpserver/config/users.json](sajhamcpserver/config/users.json).

---

## Bug Investigation Walkthrough

### Symptom
User uploaded files appeared in the chat UI sidebar under "Market Risk Worker", but the agent's `list_uploaded_files` tool returned:
```json
{ "count": 0, "output": "_No files found._" }
```

### Hypothesis (user-provided)
"The MCP tools aren't picking up files because of how paths are dynamically provided on the spot — something is wrong with the handoff."

### Findings
The header chain was actually correct:
- [agent/tools.py:39-45](agent/tools.py:39) appends `user_id` to `my_data_path` and sends `X-Worker-My-Data-Root` to SAJHA.
- SAJHA Flask binds the headers to `g.worker_ctx` in `sajhamcpserver_web.py`.
- [sajha/data_context.py:42-66](sajhamcpserver/sajha/data_context.py:42) reads `g.worker_ctx['my_data_path']` and returns the per-section roots.
- [sajha/tools/impl/upload_tools.py:100](sajhamcpserver/sajha/tools/impl/upload_tools.py:100) calls `storage.list_prefix(root)`, which uses `pathlib.Path(prefix).rglob('*')` ([sajha/storage.py:31-40](sajhamcpserver/sajha/storage.py:31)).

Direct end-to-end test with correct headers returned both files immediately — proving the code path is fine:
```bash
curl -X POST http://localhost:3002/api/tools/execute \
  -H "Authorization: sja_full_access_admin" \
  -H "X-Worker-Id: w-e74b5836" \
  -H "X-User-Id: risk_agent" \
  -H "X-Worker-Data-Root: ./data/workers/w-e74b5836/domain_data" \
  -H "X-Worker-My-Data-Root: ./data/workers/w-e74b5836/my_data/risk_agent" \
  -d '{"tool":"list_uploaded_files","arguments":{}}'
# → { "count": 2, files listed correctly }
```

### Root Cause
The file panel and the agent were scoped to **two different workers**:

| Component | Worker resolution | Value |
|---|---|---|
| `/api/auth/me` (JWT) | Postgres `users.worker_id` (stale) | `w-e74b5836` |
| `/api/fs/*/tree` (file sidebar) | JWT's worker | `w-e74b5836` (had the files) |
| `/api/agent/run` chat | Frontend worker-dropdown override | `w-market-risk` (had no files) |
| Tool call from agent | Same as chat | scans `w-market-risk` paths → 0 files |

Audit trail confirmed it ([sajhamcpserver/data/audit/tool_calls.jsonl](sajhamcpserver/data/audit/tool_calls.jsonl)):
```
worker_id: "w-e74b5836"     ← first invocation
worker_id: "w-market-risk"  ← screenshot invocation (no files found)
worker_id: "w-market-risk"  ← repeat
```

### User's Hypothesis Verdict
Directionally right ("path-related"), but the disconnect was **not** in the SAJHA tool's path resolution code. It was upstream: the agent and the file panel were resolving the active worker_id from two different sources that happened to disagree because of the polluted Postgres DB.

---

## Latent Issue (Not Fixed, Worth Flagging)

The frontend chat dropdown lets a super_admin select any worker per chat, and that selection is sent in the request body. The file panel still reads from the JWT-default worker. If those drift, super_admins see the same symptom (files in panel, agent finds nothing).

Mitigations:
- Have the file panel re-fetch when the chat dropdown changes worker.
- Or, restrict super_admin to set worker context via re-auth rather than a per-request override.

Regular users (role=user) are not affected — they have no dropdown.

---

## How to Run Locally

```bash
# 1. Setup (one-time)
git clone https://github.com/algowizzzz/mcp-intelligence-agent
cd mcp-intelligence-agent
python3 -m venv venv
./venv/bin/pip install -r requirements.txt -r sajhamcpserver/requirements.txt
cp .env.example .env
# edit .env: set LLM_PROVIDER=xai, XAI_API_KEY=..., XAI_MODEL=grok-4-1-fast-non-reasoning

# 2. Run (each time)
unset DATABASE_URL   # IMPORTANT: skips polluted Postgres, uses JSON + SQLite
cd sajhamcpserver && ../venv/bin/python run_server.py &
cd .. && ./venv/bin/python -m uvicorn agent_server:app --host 127.0.0.1 --port 8000 &

# 3. Open
open http://localhost:8000/login.html
```

Health checks:
```bash
curl http://localhost:3002/health  # SAJHA
curl http://localhost:8000/health  # Agent server
```

---

## Test Accounts

| user_id | password | role | worker | notes |
|---|---|---|---|---|
| `risk_agent` | `RiskAgent2025!` | super_admin | w-market-risk | Has worker dropdown — exposes latent issue above |
| `admin` | unknown (needs reset) | admin | w-market-risk | Default hash from repo |
| `test_user` | `TestUser123!` | user | w-market-risk | Reset in commit `b307bc3` — cleanest case for testing |

---

## Files NOT in Git

These were created or modified locally and are gitignored:
- `.env` — contains live xAI API key
- `venv/` — Python virtual environment
- `sajhamcpserver/data/workers/*/{domain_data,my_data,workflows}/` — migrated user files, runtime indexes
- `/tmp/sajha_dev.log`, `/tmp/agent_dev.log` — server logs

If you re-clone the repo on a new machine, you need to redo steps 1–5 above. None of the local fix is persisted in git history except the `test_user` credential reset.

---

## Commit Pushed

```
commit b307bc3
Author: Saad Ahmed <saadahmed@example.com>
chore: reset test_user dev credentials
```
