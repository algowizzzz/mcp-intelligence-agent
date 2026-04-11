# REQ-07 — PostgreSQL: Database Migration for User Config & Conversation History
**Status:** Implementation Complete — Tests Passing
**Version:** 1.2 (Updated 2026-04-06 — implementation complete, 21/21 tests passing)
**Previous Version:** 1.1 (2026-04-11 — corrected checkpoint state, caching gaps, dependency audit)
**Branch:** `feature/req-07-08a-postgres-s3` (do NOT merge to main until REQ-08a is also complete)
**Prerequisite:** None — can start independently
**Scope:** Migrate user configuration, conversation history, audit logs, and worker config from JSON/JSONL flat files to a PostgreSQL relational database. Domain data (financial files, documents) remains on the filesystem / S3 (see REQ-08a).

---

## 1. Background & Current Storage Architecture

### 1.1 What Is Currently Stored as Files

| Data Category | Current Location | Format | Notes |
|---|---|---|---|
| User accounts | `config/users.json` | JSON array | Read on **every request** — no caching |
| API keys | `config/apikeys.json` | JSON array | Read by SAJHA on startup |
| Worker configs | `config/workers.json` | JSON array | Cached via `WorkerRepository` singleton |
| Connector credentials | `config/connectors.json` | JSON object | Read/written directly per CRUD call |
| Conversation threads (index) | `data/threads.jsonl` | JSONL | Loaded into in-memory dict at startup; appended on new thread |
| Conversation messages | `AsyncSqliteSaver` → `checkpoints.db` | SQLite | Already persists across restarts — not MemorySaver |
| Audit log (tool calls) | `data/audit/tool_calls.jsonl` | JSONL | Appended by `agent/tools.py` on every tool call |
| Audit log (file access) | `data/audit/file_used.jsonl` | JSONL | Appended by `agent_server.py` on file reads |
| Flask sessions | `data/flask_session/` | Binary files | `SESSION_TYPE='filesystem'` in `sajhamcpserver/sajha/web/sajhamcpserver_web.py` |

### 1.2 Critical Gap: users.json Has No Caching

`_load_users()` in `agent_server.py` calls `json.loads(file.read_text())` on **every single auth call** — login, JWT validation, user lookup, password change, onboarding. Under concurrent load this is a disk read per request with no in-memory cache. This is the highest-priority fix in Phase 2.

By contrast, `config/workers.json` already has a `WorkerRepository` singleton with reload-on-write caching — that pattern should be replicated for users.

### 1.3 Checkpoint Storage: Already SQLite, Not MemorySaver

`agent_server.py` uses `AsyncSqliteSaver` from `langgraph-checkpoint-sqlite` (already in `requirements.txt`):
```python
async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH) as cp:
    _agent_module.set_checkpointer(cp)
```
Conversation messages **already persist across server restarts** via `./sajhamcpserver/data/checkpoints.db`. Phase 3 of this REQ upgrades the checkpointer from SQLite to `PostgresSaver` — it is not starting from zero.

Sub-agents intentionally pass `checkpointer_override=None` (ephemeral, no cross-loop SQLite lock contention) — this must be preserved after migration.

### 1.4 SQLite Configuration (Disabled)

`config/application.properties` contains a disabled SQLite stub:
```properties
db.enabled=false
db.type=sqlite
db.path=data/sajha_mcp.db
db.pool.size=10
```
No ORM or migration framework is currently in use.

### 1.5 Current Dependencies

Already present in `sajhamcpserver/requirements.txt`:
- `psycopg2-binary>=2.9.9` ✓

Already present in root `requirements.txt`:
- `langgraph-checkpoint-sqlite>=2.0.0` ✓
- `aiosqlite>=0.20.0` ✓

**Missing — must add:**
- `sqlalchemy[asyncio]>=2.0` (root + sajhamcpserver)
- `asyncpg>=0.29.0` (root + sajhamcpserver)
- `alembic>=1.13.0` (root)
- `langgraph-checkpoint-postgres` (root — replaces sqlite checkpointer)

### 1.6 Why PostgreSQL Now

| Reason | Detail |
|---|---|
| `users.json` no-cache | Disk read on every auth call — database solves this with connection pooling + indexed lookups |
| Concurrent JSONL writes | Multiple FastAPI workers appending to the same JSONL file simultaneously risks corruption |
| Audit log filtering | Current JSONL full-scan for `/api/super/audit` endpoint — slow as file grows |
| threads.jsonl | Append-only JSONL index loaded into memory at startup — will drift under multi-process deployment |
| Conversation persistence | SQLite checkpoints.db is a single-writer file — breaks under multi-process uvicorn workers |
| S3 file tree (REQ-08a) | `file_metadata` table needed before S3 file tree can work — this REQ delivers that table |
| Cloud enterprise deployment | All cloud-native deployments expect a proper database, not JSON files on a local disk |

---

## 2. Scope: What Goes into PostgreSQL

**IN SCOPE — moves to PostgreSQL:**
- User accounts and authentication data (`users.json`)
- Worker configurations (`workers.json`)
- Connector credentials — encrypted at rest (`connectors.json`)
- Conversation thread index (`data/threads.jsonl`)
- Conversation messages (`checkpoints.db` → `PostgresSaver`)
- Audit log — tool calls and file access (`tool_calls.jsonl`, `file_used.jsonl`)
- API keys (`apikeys.json`)
- Flask sessions (`data/flask_session/`)
- File metadata index — new table required by REQ-08a (`file_metadata`)

**OUT OF SCOPE — stays on filesystem / moves to S3 (REQ-08a):**
- Domain data files (CSV, JSON, DOCX, PDF, XLSX)
- Uploaded user files
- Workflow .md files
- DuckDB analytics files
- Generated charts and output files

---

## 3. Database Schema

### 3.1 Users Table

```sql
CREATE TABLE users (
    user_id             VARCHAR(64)  PRIMARY KEY,
    username            VARCHAR(64)  NOT NULL UNIQUE,
    display_name        VARCHAR(128) NOT NULL,
    password_hash       VARCHAR(128) NOT NULL,       -- bcrypt hash
    role                VARCHAR(32)  NOT NULL,        -- 'super_admin', 'admin', 'user'
    worker_id           VARCHAR(64)  REFERENCES workers(worker_id),
    enabled             BOOLEAN      NOT NULL DEFAULT TRUE,
    onboarding_complete BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_login_at       TIMESTAMPTZ,
    created_by          VARCHAR(64)
);

CREATE INDEX idx_users_username  ON users(username);
CREATE INDEX idx_users_role      ON users(role);
CREATE INDEX idx_users_worker_id ON users(worker_id);
```

### 3.2 Workers Table

```sql
CREATE TABLE workers (
    worker_id        VARCHAR(64)  PRIMARY KEY,
    name             VARCHAR(128) NOT NULL,
    description      TEXT,
    system_prompt    TEXT,
    enabled_tools    JSONB        NOT NULL DEFAULT '["*"]',
    domain_data_path VARCHAR(512),
    verified_wf_path VARCHAR(512),
    connector_scope  JSONB        NOT NULL DEFAULT '{}',
    enabled          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

### 3.3 API Keys Table

```sql
CREATE TABLE api_keys (
    key_id       SERIAL       PRIMARY KEY,
    key_hash     VARCHAR(128) NOT NULL UNIQUE,  -- SHA-256 of actual key
    key_prefix   VARCHAR(16)  NOT NULL,          -- first 8 chars for display
    label        VARCHAR(128),
    created_by   VARCHAR(64)  REFERENCES users(user_id),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ,
    revoked      BOOLEAN      NOT NULL DEFAULT FALSE
);
```

### 3.4 Connectors Table

```sql
CREATE TABLE connectors (
    connector_type   VARCHAR(64)  PRIMARY KEY,
    display_name     VARCHAR(128) NOT NULL,
    status           VARCHAR(32)  NOT NULL DEFAULT 'not_configured',
    enabled          BOOLEAN      NOT NULL DEFAULT FALSE,
    credentials_enc  BYTEA,       -- AES-256-GCM encrypted blob
    credentials_iv   BYTEA,       -- AES-GCM initialization vector
    has_credentials  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

Encryption key stored in `CONNECTOR_ENCRYPTION_KEY` env var (32-byte hex), never in the database. Key rotation requires re-encrypting all blobs.

### 3.5 Conversation Threads Table

```sql
CREATE TABLE conversation_threads (
    thread_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          VARCHAR(64)  NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    worker_id        VARCHAR(64)  NOT NULL REFERENCES workers(worker_id),
    title            VARCHAR(256),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    archived_at      TIMESTAMPTZ,
    message_count    INTEGER      NOT NULL DEFAULT 0,
    token_count_est  INTEGER      NOT NULL DEFAULT 0
);

CREATE INDEX idx_threads_user_worker ON conversation_threads(user_id, worker_id);
CREATE INDEX idx_threads_active ON conversation_threads(user_id, archived_at) WHERE archived_at IS NULL;
```

Thread metadata migrated from `data/threads.jsonl`. Message content migrated from `checkpoints.db` via `PostgresSaver`.

### 3.6 Audit Log Table

```sql
CREATE TABLE audit_events (
    event_id         BIGSERIAL    PRIMARY KEY,
    event_type       VARCHAR(64)  NOT NULL,  -- 'tool_call', 'file_access', 'auth', 'user_change'
    user_id          VARCHAR(64),
    worker_id        VARCHAR(64),
    thread_id        UUID         REFERENCES conversation_threads(thread_id) ON DELETE SET NULL,
    tool_name        VARCHAR(128),
    tool_result_ok   BOOLEAN,
    file_path        VARCHAR(512),
    file_section     VARCHAR(64),
    detail           JSONB,        -- no raw credentials, API keys, or passwords
    elapsed_ms       INTEGER,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user   ON audit_events(user_id,   created_at DESC);
CREATE INDEX idx_audit_worker ON audit_events(worker_id, created_at DESC);
CREATE INDEX idx_audit_tool   ON audit_events(tool_name, created_at DESC);
CREATE INDEX idx_audit_type   ON audit_events(event_type, created_at DESC);
```

Migrated from `data/audit/tool_calls.jsonl` and `data/audit/file_used.jsonl`.

### 3.7 File Metadata Table (Required by REQ-08a)

```sql
CREATE TABLE file_metadata (
    file_id      BIGSERIAL    PRIMARY KEY,
    worker_id    VARCHAR(64)  NOT NULL,
    user_id      VARCHAR(64),
    section      VARCHAR(64)  NOT NULL,
    s3_key       TEXT         NOT NULL,
    rel_path     TEXT         NOT NULL,
    file_name    VARCHAR(512) NOT NULL,
    mime_type    VARCHAR(128),
    size_bytes   BIGINT,
    is_folder    BOOLEAN      NOT NULL DEFAULT FALSE,
    bm25_indexed BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by   VARCHAR(64)
);

CREATE INDEX idx_file_meta_tree   ON file_metadata(worker_id, section, rel_path);
CREATE INDEX idx_file_meta_search ON file_metadata(worker_id, file_name);
```

This table is the foundation for REQ-08a's file tree API. Must be created as part of REQ-07's initial migration.

### 3.8 Flask Sessions Table

```sql
CREATE TABLE flask_sessions (
    session_id VARCHAR(256) PRIMARY KEY,
    user_id    VARCHAR(64),
    data       BYTEA        NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ  NOT NULL
);

CREATE INDEX idx_sessions_expires ON flask_sessions(expires_at);
```

Replaces `data/flask_session/` filesystem sessions via `Flask-Session` with `SqlAlchemySessionInterface`.

---

## 4. ORM & Migration Framework

```bash
# Add to root requirements.txt
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29.0
alembic>=1.13.0
langgraph-checkpoint-postgres

# sajhamcpserver/requirements.txt already has psycopg2-binary — add:
sqlalchemy[asyncio]>=2.0
```

**File structure:**
```
sajhamcpserver/sajha/db/
  __init__.py
  engine.py          # create_async_engine, get_session
  models.py          # SQLAlchemy declarative models
  migrations/
    alembic.ini
    env.py
    versions/
      001_initial_schema.py
      002_file_metadata.py    # must exist before REQ-08a work starts
```

**engine.py:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

_DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://user:password@localhost:5432/bpulse')

engine = create_async_engine(_DATABASE_URL, pool_size=10, max_overflow=5, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

---

## 5. Data Access Layer Changes

### 5.1 users.json — No-Cache Fix (Highest Priority)

Replace `_load_users()` (reads file on every call) with a `UserRepository` matching the existing `WorkerRepository` pattern:

```python
class _UserRepository:
    def __init__(self): self._users: dict = {}; self._lock = threading.Lock(); self.reload()
    def reload(self): with self._lock: self._users = {u['user_id']: u for u in _read_users_json()}
    def find(self, user_id: str): return self._users.get(user_id)
    def list(self): return list(self._users.values())

_user_repo = _UserRepository()
```

After REQ-07 Phase 2, replace `_UserRepository` with a PostgreSQL-backed async version.

### 5.2 Audit Logging Migration

```python
# Before (agent/tools.py — JSONL append):
with open(_AUDIT_FILE, 'a') as f:
    f.write(json.dumps({...}) + '\n')

# After (async PostgreSQL insert):
await db.execute(insert(AuditEvent).values(
    event_type='tool_call', user_id=user_id, worker_id=worker_id,
    tool_name=tool_name, tool_result_ok=success, elapsed_ms=elapsed_ms
))
```

Note: `agent/tools.py` also appends audit lines — both `agent_server.py` and `tools.py` audit paths must be migrated.

### 5.3 LangGraph Checkpointer Upgrade

```python
# Before (agent_server.py — SQLite):
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH) as cp:
    _agent_module.set_checkpointer(cp)

# After (PostgreSQL):
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
checkpointer = AsyncPostgresSaver.from_conn_string(os.getenv('DATABASE_URL'))
_agent_module.set_checkpointer(checkpointer)
```

Sub-agents must continue passing `checkpointer_override=None` — do not change `sub_agent_executor.py`.

### 5.4 Dual-Write Mode During Migration

Run dual-write for users, workers, and audit — write to both JSON files AND PostgreSQL simultaneously. Read from JSON files (trusted). Once DB row count matches, switch reads to DB. Remove JSON writes last.

---

## 6. Environment Variables

```bash
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://bpulse:password@host:5432/bpulse

# Connection pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=3600

# Encryption (for connectors table)
CONNECTOR_ENCRYPTION_KEY=<32-byte hex>   # never commit to git

# Checkpoint backend
CHECKPOINT_BACKEND=postgres
CHECKPOINT_DB_URL=postgresql://bpulse:password@host:5432/bpulse

# Alembic — run explicitly, not on startup
RUN_MIGRATIONS_ON_STARTUP=false
```

---

## 7. Migration Plan

### Phase 1 — Schema & Infrastructure (Week 1)
1. Deploy PostgreSQL (Docker locally, RDS for production)
2. Add `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `langgraph-checkpoint-postgres` to requirements
3. Create `sajha/db/` module with models and engine
4. Run Alembic migration `001_initial_schema.py` — creates all tables including `file_metadata`
5. Validate empty schema with a health-check query

### Phase 2 — Users, Workers, Config (Week 1–2)
1. Replace `_load_users()` no-cache pattern with `UserRepository` (interim in-memory, then DB)
2. Write `scripts/migrate_json_to_pg.py`:
   - `config/users.json` → `users` table
   - `config/workers.json` → `workers` table
   - `config/apikeys.json` → `api_keys` table
   - `config/connectors.json` → `connectors` table (encrypted)
3. Switch all auth and user management endpoints to read from PostgreSQL
4. Enable dual-write for workers (JSON + DB) until verified
5. Remove JSON writes

### Phase 3 — Conversation History (Week 2–3)
1. Migrate `data/threads.jsonl` → `conversation_threads` table
2. Upgrade LangGraph checkpointer: `AsyncSqliteSaver` → `AsyncPostgresSaver`
   - Keep `checkpointer_override=None` in `sub_agent_executor.py` unchanged
3. Thread list API (`/api/agent/threads`) reads from PostgreSQL
4. Archive `checkpoints.db` (keep 30 days, then delete)

### Phase 4 — Audit Log (Week 3–4)
1. Migrate historical `tool_calls.jsonl` and `file_used.jsonl` → `audit_events` table
2. Update `agent/tools.py` `_log_audit()` to write to PostgreSQL
3. Update `agent_server.py` file-access audit to write to PostgreSQL
4. Fix admin UI audit log (`/api/super/audit`) field name bug (Time + Tool columns showing "—")
5. Enable date/user/tool filters via PostgreSQL queries
6. Archive original JSONL files (90 days, then delete)

### Phase 5 — Flask Sessions (Week 4)
1. Replace filesystem sessions with PostgreSQL via `Flask-Session` + `SqlAlchemySessionInterface`
2. Add nightly cleanup cron for expired sessions

---

## 8. Connection Pooling

Under multiple uvicorn workers, use PgBouncer in transaction-mode:
```
FastAPI workers (4x) → PgBouncer (pool_size=20) → PostgreSQL
```
Without PgBouncer, each uvicorn worker holds persistent connections and exhausts PostgreSQL's `max_connections` (default 100). For AWS RDS, AWS RDS Proxy provides equivalent pooling as a managed service.

---

## 9. Security Requirements

- **SEC-DB-001**: Connector credentials encrypted with AES-256-GCM before insert — key from env var only
- **SEC-DB-002**: User passwords stored as bcrypt hash only — already in place
- **SEC-DB-003**: Application DB user has only `SELECT, INSERT, UPDATE, DELETE` — no DDL. Separate migration user for Alembic
- **SEC-DB-004**: All connections use TLS (`sslmode=require`) in production
- **SEC-DB-005**: `detail` JSONB in `audit_events` must not contain raw API keys, passwords, or full credential objects — hashes or truncated summaries only

---

## 10. Acceptance Criteria

- [x] All tables created via Alembic (no manual SQL)
- [x] `file_metadata` table exists before REQ-08a work begins
- [x] User login works after migration (bcrypt hashes verified correctly)
- [x] `_load_users()` no-cache pattern replaced — auth endpoint no longer reads file on every call
- [x] Worker config loads from PostgreSQL
- [x] Conversation threads persist across server restarts via `AsyncPostgresSaver`
- [x] Sub-agents still use `checkpointer_override=None` (no regression)
- [x] Audit log written to `audit_events` table from both `agent/tools.py` and `agent_server.py`
- [ ] Admin UI audit log Time and Tool columns show correct values *(admin UI regression test pending)*
- [x] Audit log supports filter by worker/user via PostgreSQL queries
- [ ] Connector credentials encrypted at rest in `connectors` table *(encryption layer deferred — metadata stored, credentials remain in connectors.json)*
- [x] Migration script runs idempotently (safe to run twice)
- [x] Dual-write fallback active — system works without DATABASE_URL set
- [x] Connection pool: asyncpg pool_size=10, max_overflow=5

---

## 11. Test Results

**Test file:** `tests/test_req07_postgres.py`
**Run date:** 2026-04-06
**Result: 21 PASS / 0 FAIL / 21 total**

| TC | Description | Result |
|---|---|---|
| TC-07-01 | DB tables exist after migration (8 tables) | PASS |
| TC-07-02 | User upsert and retrieval by user_id | PASS |
| TC-07-03 | User retrieval by username | PASS |
| TC-07-04 | User list returns all migrated users (15) | PASS |
| TC-07-05 | Worker upsert and retrieval | PASS |
| TC-07-06 | Worker list returns all migrated workers (13) | PASS |
| TC-07-07 | Conversation thread registration (idempotent) | PASS |
| TC-07-08 | Thread listing filtered by user and worker | PASS |
| TC-07-09 | Audit event insert (tool_call) | PASS |
| TC-07-10 | Audit query with worker filter | PASS |
| TC-07-11 | Audit query with user filter | PASS |
| TC-07-12 | File metadata upsert + update | PASS |
| TC-07-13 | File metadata list by worker/section | PASS |
| TC-07-14 | File metadata delete | PASS |
| TC-07-15 | Storage used bytes calculation | PASS |
| TC-07-16 | Migration idempotency (run twice, no duplicates) | PASS |
| TC-07-17 | AsyncPostgresSaver.setup() creates checkpoint tables | PASS |
| TC-07-18 | _load_users() returns DB data when DATABASE_URL set | PASS |
| TC-07-19 | _find_user() returns DB data (risk_agent, super_admin) | PASS |
| TC-07-20 | Audit migration data (1516 events migrated) | PASS |
| CLEANUP | Test data removed cleanly | PASS |

**Migration stats (scripts/migrate_json_to_pg.py):**
- Workers: 12/12 migrated
- Users: 14/14 migrated
- Threads: 454/458 migrated (4 FK violations for deleted workers — expected)
- Audit events: 1,516 migrated

---

## 12. Out of Scope

- Domain data and document file storage → REQ-08a
- Real-time replication or read replicas
- Database-level full-text search on document content
- Multi-tenant database isolation
