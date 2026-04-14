# REQ-07 — PostgreSQL: Database Migration for User Config & Conversation History
**Status:** Partially Complete — 4 gaps remaining (see Section 12)
**Version:** 1.3 (Updated 2026-04-14 — live production audit; remaining gaps identified)
**Previous Version:** 1.2 (2026-04-06 — implementation complete, 21/21 tests passing)
**Branch:** merged to main
**Prerequisite:** None
**Scope:** Migrate user configuration, conversation history, audit logs, and worker config from JSON/JSONL flat files to a PostgreSQL relational database. Domain data (financial files, documents) remains on the filesystem / S3 (see REQ-16).

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

## 7. Migration Plan — Status

### Phase 1 — Schema & Infrastructure ✅ COMPLETE
- `postgres:16-alpine` sidecar running in `docker-compose.prod.yml`
- `DATABASE_URL` wired into app container — `_DB_ENABLED = True` in production
- `sajha/db/` module exists: `engine.py`, `models.py`, `repo.py`, `migrations/`
- Alembic migration `001_initial_schema.py` run — all 8 tables exist
- All packages installed: `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `langgraph-checkpoint-postgres`

### Phase 2 — Users, Workers, Config ✅ COMPLETE (partial — see gaps)
- `_load_users()` no-cache pattern replaced — reads from DB when `DATABASE_URL` set
- `scripts/migrate_json_to_pg.py` run: 14 users, 12 workers, 454 threads, 1,516 audit events migrated
- All auth and user management endpoints read from PostgreSQL
- Dual-write active — JSON kept in sync as fallback
- ⚠️ **GAP:** `WorkerRepository` still reads `workers.json` — `PostgresWorkerRepository` stub not activated

### Phase 3 — Conversation History ⚠️ PARTIALLY COMPLETE
- `conversation_threads` table exists and populated (454 threads migrated)
- `/api/agent/threads` reads from PostgreSQL ✅
- ⚠️ **GAP:** LangGraph checkpointer still `AsyncSqliteSaver` → `checkpoints.db` on Docker volume. `AsyncPostgresSaver` tables exist but app was never switched over. Conversation messages lost on container rebuild.

### Phase 4 — Audit Log ✅ COMPLETE (partial — see gaps)
- Historical JSONL migrated (1,516 events in `audit_events` table)
- `agent/tools.py` and `agent_server.py` write audit events to PostgreSQL ✅
- Audit query endpoint (`/api/super/audit`) uses PostgreSQL filters ✅
- ⚠️ **GAP:** Admin UI audit log Time and Tool columns show "—" — frontend field-name mismatch bug

### Phase 5 — Flask Sessions ⏸ DEFERRED
- Still using filesystem sessions (`data/flask_session/`)
- Low impact for single-container deployment — deferred indefinitely

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

### Completed
- [x] All tables created via Alembic (no manual SQL)
- [x] `file_metadata` table exists (required by REQ-16 S3 file tree)
- [x] User login works after migration (bcrypt hashes verified correctly)
- [x] `_load_users()` no-cache pattern replaced — auth reads from DB
- [x] Audit log written to `audit_events` table from both `agent/tools.py` and `agent_server.py`
- [x] Audit log supports filter by worker/user via PostgreSQL queries
- [x] Migration script runs idempotently (safe to run twice)
- [x] Dual-write fallback active — system works without DATABASE_URL set
- [x] Connection pool: asyncpg pool_size=10, max_overflow=5
- [x] Sub-agents still use `checkpointer_override=None` (no regression)

### Remaining Work (prioritised)
- [ ] **P0 — Switch LangGraph checkpointer to `AsyncPostgresSaver`**  
  Conversation messages still in `checkpoints.db` on Docker volume — lost on container rebuild.  
  Change: `agent_server.py` — swap `AsyncSqliteSaver` for `AsyncPostgresSaver`.  
  Keep `checkpointer_override=None` in `sub_agent_executor.py` unchanged.  
  Archive `checkpoints.db` after verified stable (30 days).

- [ ] **P1 — Activate `PostgresWorkerRepository`**  
  `workers.json` is still the live source of truth. `PostgresWorkerRepository` stub exists in  
  `sajhamcpserver/sajha/worker_repository.py` — activate it in `agent_server.py`.  
  Workers table is already populated from migration script.

- [ ] **P2 — Fix admin UI audit log columns**  
  Time and Tool columns show "—" in `/api/super/audit` view.  
  Frontend field-name mismatch — small bug, isolated to `admin.html`.

- [ ] **P3 — Connector credentials encryption at rest**  
  `connectors.json` still holds plaintext credentials (Teams secret, Jira token, etc).  
  `connectors` table has `credentials_enc` bytea + `credentials_iv` bytea columns ready.  
  Requires `CONNECTOR_ENCRYPTION_KEY` env var (32-byte hex) added to deploy.  
  Deferred — no customer data at risk today, single-tenant VPS.

- [ ] ~~Flask sessions~~ — deferred indefinitely (filesystem sessions fine for single container)

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

## 12. Remaining Work Summary (2026-04-14 audit)

| Priority | Work Item | File | Effort |
|---|---|---|---|
| P0 | Switch checkpointer: `AsyncSqliteSaver` → `AsyncPostgresSaver` | `agent_server.py` | 1 hour |
| P1 | Activate `PostgresWorkerRepository` | `agent_server.py` + `worker_repository.py` | 30 min |
| P2 | Fix audit UI columns (Time + Tool show "—") | `public/admin.html` | 30 min |
| P3 | Connector credential encryption at rest | `agent_server.py` connector CRUD endpoints | Half day |

**P0 detail — checkpointer swap:**
```python
# agent_server.py — BEFORE (current)
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH) as cp:
    _agent_module.set_checkpointer(cp)

# AFTER
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
cp = AsyncPostgresSaver.from_conn_string(os.getenv('DATABASE_URL'))
await cp.setup()   # creates checkpoint tables if not exist
_agent_module.set_checkpointer(cp)
```
`sub_agent_executor.py` passes `checkpointer_override=None` — do not touch.

**P1 detail — WorkerRepository:**
```python
# agent_server.py — BEFORE (current)
_worker_repo = WorkerRepository(WORKERS_FILE)   # reads workers.json

# AFTER (when DATABASE_URL set)
if _DB_ENABLED:
    _worker_repo = PostgresWorkerRepository(db_session)
else:
    _worker_repo = WorkerRepository(WORKERS_FILE)   # fallback unchanged
```

---

## 13. Out of Scope

- Domain data and document file storage → REQ-16
- Real-time replication or read replicas
- Database-level full-text search on document content
- Multi-tenant database isolation
- Flask session migration (deferred indefinitely)
