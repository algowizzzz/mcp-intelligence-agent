# Requirements Priority & Next Steps

_Last updated: 2026-04-14 (REQ-07 + REQ-16 complete)_

---

## Status Overview

| Req | Title | Status |
|-----|-------|--------|
| REQ-08a | S3 Storage Backend (code layer) | ✅ Complete — in production |
| REQ-13 | Multi-Agent Framework | ✅ Complete — in production |
| REQ-14 (middleware) | Middleware Phase 2 + Persistent Memory | ✅ Complete — in production |
| REQ-07 | PostgreSQL Migration | ✅ Complete — all 4 gaps closed |
| REQ-16 | Hetzner S3 Migration (activation) | ✅ Complete — activate via GitHub Secrets |
| REQ-14 (bugs) | Bug Fixes (sub-agent, audit, EDGAR) | Queued — next priority |
| REQ-06 | Branding (RiskGPT → B-Pulse) | Queued |
| QA Test Plan | Run acceptance tests on all active tools | Queued — test execution |
| REQ-02a/b | Connector Setup & Testing | Backlog |
| REQ-08b | Apache Iceberg | On hold — depends on REQ-16 |
| ~~REQ-08~~ | ~~DevOps Cloud Guide~~ | Killed |
| ~~REQ-15~~ | ~~Supabase Persistent Storage~~ | Killed |

---

## What Is Live in Production Today

| Component | State |
|---|---|
| PostgreSQL container | ✅ Running (`sajha-postgres`, postgres:16-alpine sidecar) |
| `DATABASE_URL` wired | ✅ Set in `docker-compose.prod.yml` — app reads from DB |
| Users in Postgres | ✅ 14 users migrated, dual-write active |
| Audit events in Postgres | ✅ Writing to `audit_events` table |
| Conversation threads table | ✅ 454 threads migrated |
| S3 storage code | ✅ `storage.py` complete — `LocalStorageBackend` + `S3StorageBackend` |
| Path resolver | ✅ Routes local ↔ S3 by env var |
| `serve_file()` presigned URLs | ✅ Redirects to S3 presigned URL in S3 mode |
| Hetzner bucket provisioned | ✅ `sajha-storage` / `hel1.your-objectstorage.com` |
| File preview in chat UI | ✅ Fixed (2026-04-14) — `_ftApiPrefix()`, error handling, tab rendering |

---

## REQ-07 — Remaining Gaps (4 items)

Full detail in `requirements/pending/REQ-07_PostgreSQL_Database_Migration.md`.

| Priority | Gap | What to do | Effort |
|---|---|---|---|
| **P0** | LangGraph checkpointer still `AsyncSqliteSaver` — conversation history on Docker volume, lost on rebuild | Swap to `AsyncPostgresSaver` in `agent_server.py` | 1 hour |
| **P1** | `WorkerRepository` still reads `workers.json` — `PostgresWorkerRepository` stub unused | Activate in `agent_server.py` | 30 min |
| **P2** | Admin UI audit log Time + Tool columns show "—" | Field-name fix in `admin.html` | 30 min |
| **P3** | Connector credentials plaintext in `connectors.json` | Encrypt into `connectors` table (AES-256-GCM) | Half day |

P0 is the only data-loss risk. P1–P3 can follow at any time independently.

---

## REQ-16 — Hetzner S3 Migration (Current Priority)

**Bucket:** `sajha-storage` | **Endpoint:** `hel1.your-objectstorage.com` | **Credentials:** `CREDENTIALS.md`

### Checklist

**Phase 1 — Infra** ✅ Done
- [x] Hetzner bucket `sajha-storage` provisioned, credentials in `CREDENTIALS.md`

**Phase 2 — Fix 9 tool files** 🔴 Not started — this is the work
- [ ] `fs_index.py` — unify local path to use `storage.list_prefix()` (S3 path already done)
- [ ] `workflow_tools.py` — `os.walk` → `storage.list_prefix()`
- [ ] `upload_tools.py` — `os.walk` → `storage.list_prefix()`
- [ ] `python_executor.py` — `shutil.copy2` → `storage.write_bytes()`
- [ ] `operational_tools.py` — `shutil.move` + `doc.save` → storage calls
- [ ] `bm25_search_tool.py` — `os.path.getmtime` → `storage.get_size()`
- [ ] `msdoc_tools_tool_refactored.py` — `os.path.isfile` → `storage.exists()`
- [ ] `data_transform_tools.py` — PyArrow paths → buffer + `storage.write_bytes()`
- [ ] `file_read_tool.py` — `pathlib.read_text` → `storage.read_text()`
- [ ] `duckdb_olap_tools_refactored.py` — add `_ensure_local()` interim helper
- [ ] `sqlselect_tool_refactored.py` — add `_ensure_local()` interim helper
- [ ] `duckdb_olap_advanced.py` — add `_ensure_local()` interim helper

**Phase 3 — Data migration** ⏳ Pending Phase 2
- [ ] `aws s3 sync` from VPS Docker volume → `sajha-storage` bucket
- [ ] Verify object count matches

**Phase 4 — Deploy env vars** ⏳ Pending Phase 2
- [ ] Add `S3_ENDPOINT_URL`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` to GitHub Secrets
- [ ] Add `STORAGE_BACKEND=s3` + S3 vars to `.github/workflows/deploy.yml`
- [ ] Add S3 vars to `docker-compose.prod.yml` app service

**Phase 5 — Smoke test** ⏳ Pending Phase 4
- [ ] File tree loads, file preview works, upload stores to S3
- [ ] `duckdb_query` works (via `/tmp` cache)
- [ ] Charts persist across container restart
- [ ] `STORAGE_BACKEND=local` still works locally

**Phase 6 — DuckDB httpfs** 🔵 Deferred (post-cutover, separate PR)
- Replace `_ensure_local()` with direct `s3://` URIs via DuckDB httpfs extension
- Config: `SET s3_endpoint='hel1.your-objectstorage.com'; SET s3_url_style='path';`

### What Does NOT Need Changing for REQ-16
- `storage.py`, `path_resolver.py`, `agent_server.py` serve/upload — already complete
- `visualisation_tools.py`, `iris_ccr_tools.py` — clean, no local disk access
- Postgres — already running, no changes needed

---

## REQ-14 — Bug Fixes (Queued, after REQ-16)

Small, concrete, no infrastructure dependency. Full detail: `requirements/pending/REQ-14_Bug_Fixes_SubAgent_Audit_EDGAR.md`

| # | Bug | Fix |
|---|-----|-----|
| 1 | Sub-agent timeout hardcoded at 120s | Make configurable per-worker in `workers.json` |
| 2 | Dropped/timed-out sub-agents not surfaced to user | Emit SSE event on timeout/failure |
| 3 | Audit log `success: None` | Fix field to emit `true`/`false` |
| 4 | EDGAR returns empty for Canadian companies (BMO, RBC) | Handle 6-K filing type, warn explicitly |

---

## REQ-06 — Branding (Queued)

Rename all user-facing "RiskGPT" / "SAJHA MCP Server" references to "B-Pulse Digital Workers" across `login.html`, `admin.html`, `mcp-agent.html`, `application.properties`, and system prompts. Full spec in `requirements/pending/REQ-06_Branding_BPulse_Digital_Workers.md`.

---

## Queued Work (post REQ-16)

### QA Test Plan (`requirements/drafts/Sajha_MCP_QA_Test_Plan.docx`)
Acceptance test cases for all active tools. Happy Path + Edge + Negative + Boundary per tool. Universal pass criteria: <30s response for external API tools, <2s for in-memory tools, valid JSON output conforming to outputSchema. This is test execution work, not code.

### Left Panel UX Backlog (`requirements/drafts/LEFT_PANEL_UX.md`)
Core is implemented (tabs, file tree, rename/delete, file preview). Documented backlog items still pending: chat search, pin conversations, drag-file-to-chat. Low priority.

---

## Backlog

**REQ-02a** — Connector credential collection guide (Teams, Outlook, Confluence, Jira)  
**REQ-02b** — MR worker connector integration testing (23 tests); known blockers: Teams send permission, Outlook Exchange license

---

## Already Complete — Move to completed/

These docs are in root `requirements/` but the work is shipped:
- `REQ-13_Multi_Agent_Framework.docx` — full multi-agent framework live in production
- `REQ-14_Middleware_Phase2_Persistent_Memory.docx` — all 9 middlewares + MemoryMiddleware + HITL live in production

---

## Killed

**REQ-08** — DevOps cloud deployment guide (superseded by this doc + deploy.yml)  
**REQ-15** — Supabase Persistent Storage (Railway-focused; superseded by Hetzner S3)
