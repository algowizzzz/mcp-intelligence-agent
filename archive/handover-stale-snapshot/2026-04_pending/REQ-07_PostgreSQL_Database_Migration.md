# REQ-07 — PostgreSQL: Database Migration for User Config & Conversation History
**Status:** Pending Implementation
**Version:** 1.0
**Date:** 2026-04-04
**Scope:** Migrate user configuration, conversation history, audit logs, and worker config from JSON/JSONL flat files to a PostgreSQL relational database. Domain data (financial files, documents) remains on the filesystem / S3 (see REQ-08).

---

## 1. Background & Current Storage Architecture

### 1.1 What Is Currently Stored as Files

The platform uses flat files exclusively for all operational data:

| Data Category | Current Location | Format | Size |
|---|---|---|---|
| User accounts | `config/users.json` | JSON array | Small |
| API keys | `config/apikeys.json` | JSON array | Small |
| Worker configs | `config/workers.json` | JSON array | Small |
| Connector credentials | `config/connectors.json` | JSON object | Small |
| Conversation threads (index) | `data/threads.jsonl` | JSONL | Growing (~50KB now) |
| Conversation messages | LangGraph `MemorySaver` | In-memory | Lost on restart |
| Audit log | `data/audit/tool_calls.jsonl` | JSONL | Growing (~167KB now) |
| File-used audit | `data/audit/file_used.jsonl` | JSONL (REQ-01) | New |
| Flask sessions | `data/flask_session/` | Binary files | Growing |
| Token/connector cache | In-memory | Volatile | — |

### 1.2 SQLite Configuration (Disabled)

`config/application.properties` contains:
```properties
db.enabled=false
db.type=sqlite
db.path=data/sajha_mcp.db
db.pool.size=10
```

SQLite is configured but disabled. There is no ORM or migration framework currently in use.

### 1.3 Why PostgreSQL Now

| Reason | Detail |
|---|---|
| Concurrent writes | Multiple requests writing to JSONL simultaneously risks corruption; Postgres handles this safely |
| Query capability | Audit log filtering, user search, and thread listing require full table scans of JSONL today |
| Conversation persistence | MemorySaver loses all history on restart; SQLite checkpoint (REQ-05) is the first step, PostgreSQL is the production target |
| Multi-process safety | FastAPI workers run with multiple processes/threads; shared JSONL files are not safe |
| Future scale | S3 data + PostgreSQL metadata is the standard cloud-native pattern |
| Backup/recovery | PostgreSQL provides WAL-based point-in-time recovery; flat files do not |

---

## 2. Scope: What Goes into PostgreSQL

**IN SCOPE — moves to PostgreSQL:**
- User accounts and authentication data
- Worker configurations
- Connector credentials (encrypted at rest)
- Conversation thread index and message history
- Audit log (tool calls, file access, connector events)
- API keys and session tokens
- Worker-tool assignments

**OUT OF SCOPE — stays on filesystem / moves to S3 (REQ-08):**
- Domain data files (CSV, JSON, DOCX, PDF, XLSX)
- Uploaded user files
- Verified and user workflows (.md files)
- DuckDB analytics files
- Generated charts and output files

---

## 3. Database Schema

### 3.1 Users Table

```sql
CREATE TABLE users (
    user_id         VARCHAR(64) PRIMARY KEY,   -- e.g. "risk_agent", "admin"
    username        VARCHAR(64) NOT NULL UNIQUE,
    display_name    VARCHAR(128) NOT NULL,
    password_hash   VARCHAR(128) NOT NULL,      -- bcrypt hash
    role            VARCHAR(32) NOT NULL,        -- 'super_admin', 'admin', 'user'
    worker_id       VARCHAR(64) REFERENCES workers(worker_id),  -- assigned worker
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ,
    created_by      VARCHAR(64)                 -- user_id of creator
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_worker_id ON users(worker_id);
```

**Migration source:** `config/users.json`

### 3.2 Workers Table

```sql
CREATE TABLE workers (
    worker_id       VARCHAR(64) PRIMARY KEY,   -- e.g. "w-market-risk"
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    system_prompt   TEXT,
    enabled_tools   JSONB NOT NULL DEFAULT '["*"]',  -- tool allow-list
    domain_data_path VARCHAR(512),              -- custom path override
    verified_wf_path VARCHAR(512),
    connector_scope  JSONB NOT NULL DEFAULT '{}',    -- {microsoft_azure: {...}, atlassian: {...}}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Migration source:** `config/workers.json`

### 3.3 API Keys Table

```sql
CREATE TABLE api_keys (
    key_id          SERIAL PRIMARY KEY,
    key_hash        VARCHAR(128) NOT NULL UNIQUE,  -- SHA-256 of the actual key
    key_prefix      VARCHAR(16) NOT NULL,           -- first 8 chars for display
    label           VARCHAR(128),
    created_by      VARCHAR(64) REFERENCES users(user_id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    revoked         BOOLEAN NOT NULL DEFAULT FALSE
);
```

**Migration source:** `config/apikeys.json`

### 3.4 Connectors Table

```sql
CREATE TABLE connectors (
    connector_type  VARCHAR(64) PRIMARY KEY,   -- 'microsoft_azure', 'atlassian'
    display_name    VARCHAR(128) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'not_configured',
    enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    credentials_enc BYTEA,                      -- AES-256-GCM encrypted credential blob
    credentials_iv  BYTEA,                      -- Initialization vector for AES-GCM
    has_credentials BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Encryption:** Credentials are encrypted with AES-256-GCM. The encryption key is stored in an environment variable `CONNECTOR_ENCRYPTION_KEY` (32-byte hex), NOT in the database. Key rotation requires re-encrypting all credential blobs.

### 3.5 Conversation Threads Table

```sql
CREATE TABLE conversation_threads (
    thread_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    worker_id       VARCHAR(64) NOT NULL REFERENCES workers(worker_id),
    title           VARCHAR(256),               -- Auto-generated from first message
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at     TIMESTAMPTZ,                -- NULL = active
    message_count   INTEGER NOT NULL DEFAULT 0,
    token_count_est INTEGER NOT NULL DEFAULT 0  -- Estimated total tokens (updated on each message)
);

CREATE INDEX idx_threads_user_worker ON conversation_threads(user_id, worker_id);
CREATE INDEX idx_threads_active ON conversation_threads(user_id, archived_at) WHERE archived_at IS NULL;
```

**Migration source:** `data/threads.jsonl`

### 3.6 Conversation Messages Table

```sql
CREATE TABLE conversation_messages (
    message_id      BIGSERIAL PRIMARY KEY,
    thread_id       UUID NOT NULL REFERENCES conversation_threads(thread_id) ON DELETE CASCADE,
    sequence_num    INTEGER NOT NULL,           -- Order within thread (1, 2, 3...)
    role            VARCHAR(32) NOT NULL,        -- 'human', 'ai', 'tool', 'system'
    content         TEXT,                        -- Plain text content
    content_blocks  JSONB,                       -- For multi-part messages (tool_use, tool_result arrays)
    tool_name       VARCHAR(128),               -- Set when role='tool'
    tool_call_id    VARCHAR(128),               -- LangChain tool call ID for pairing
    token_count_est INTEGER,                    -- Estimated tokens for this message
    is_summary      BOOLEAN NOT NULL DEFAULT FALSE,  -- True for summarization messages
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_thread ON conversation_messages(thread_id, sequence_num);
CREATE INDEX idx_messages_thread_summary ON conversation_messages(thread_id, is_summary);
```

**LangGraph Integration:** Use `langgraph-checkpoint-postgres` to use this table as the LangGraph state store.

```bash
pip install langgraph-checkpoint-postgres
```

```python
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string(os.getenv('DATABASE_URL'))
```

### 3.7 Audit Log Table

```sql
CREATE TABLE audit_events (
    event_id        BIGSERIAL PRIMARY KEY,
    event_type      VARCHAR(64) NOT NULL,       -- 'tool_call', 'file_access', 'connector_change', 'auth', 'user_change'
    user_id         VARCHAR(64),
    worker_id       VARCHAR(64),
    thread_id       UUID REFERENCES conversation_threads(thread_id) ON DELETE SET NULL,
    tool_name       VARCHAR(128),               -- For tool_call events
    tool_input_hash VARCHAR(64),                -- SHA-256 of input (not stored for security)
    tool_result_ok  BOOLEAN,                    -- True if tool succeeded
    http_status     INTEGER,                    -- For API call events
    file_path       VARCHAR(512),               -- For file_access events
    file_section    VARCHAR(64),
    detail          JSONB,                      -- Flexible additional detail
    ip_address      VARCHAR(45),                -- IPv4 or IPv6
    elapsed_ms      INTEGER,                    -- Execution time in milliseconds
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_events(user_id, created_at DESC);
CREATE INDEX idx_audit_type ON audit_events(event_type, created_at DESC);
CREATE INDEX idx_audit_worker ON audit_events(worker_id, created_at DESC);
CREATE INDEX idx_audit_tool ON audit_events(tool_name, created_at DESC);

-- Partition by month for performance at scale
-- (Implement as range partitioning when data exceeds 1M rows)
```

**Migration source:** `data/audit/tool_calls.jsonl`

### 3.8 Flask Sessions Table (Optional)

Replace `data/flask_session/` file-based sessions with DB-backed sessions:

```sql
CREATE TABLE flask_sessions (
    session_id      VARCHAR(256) PRIMARY KEY,
    user_id         VARCHAR(64),
    data            BYTEA NOT NULL,             -- Pickled session data
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_sessions_expires ON flask_sessions(expires_at);
```

Use `Flask-Session` with `SqlAlchemySessionInterface` or implement custom session backend.

---

## 4. ORM & Migration Framework

### 4.1 SQLAlchemy (Recommended)

Use SQLAlchemy 2.0 with async support:

```bash
pip install sqlalchemy[asyncio] asyncpg alembic
```

**File structure:**
```
sajhamcpserver/
  sajha/
    db/
      __init__.py
      engine.py          # create_async_engine, get_session
      models.py          # SQLAlchemy declarative models (mirrors schema above)
      migrations/        # Alembic migrations directory
        alembic.ini
        env.py
        versions/
          001_initial_schema.py
          002_add_audit_partitioning.py
```

### 4.2 Alembic Migrations

```python
# sajhamcpserver/sajha/db/engine.py
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

### 4.3 Initial Migration

```python
# migrations/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, BYTEA

def upgrade():
    op.create_table('users', ...)  # all tables from section 3
    op.create_table('workers', ...)
    op.create_table('connectors', ...)
    op.create_table('conversation_threads', ...)
    op.create_table('conversation_messages', ...)
    op.create_table('audit_events', ...)
    # Create all indexes

def downgrade():
    op.drop_table('audit_events')
    op.drop_table('conversation_messages')
    op.drop_table('conversation_threads')
    op.drop_table('connectors')
    op.drop_table('api_keys')
    op.drop_table('workers')
    op.drop_table('users')
```

---

## 5. Data Access Layer Changes

### 5.1 Replace Direct JSON File Access

Every place the code currently reads/writes JSON config files must be refactored to use DB queries.

**User management** — replace `config/users.json` reads with:
```python
# Before:
users = json.loads(Path('config/users.json').read_text())
user = next((u for u in users if u['username'] == username), None)

# After:
async with get_session() as db:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
```

**Worker config** — replace `config/workers.json` reads with:
```python
async with get_session() as db:
    result = await db.execute(select(Worker).where(Worker.worker_id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(404, 'Worker not found')
```

**Audit logging** — replace JSONL appends with:
```python
async with get_session() as db:
    event = AuditEvent(
        event_type='tool_call',
        user_id=user_id,
        worker_id=worker_id,
        tool_name=tool_name,
        tool_result_ok=success,
        elapsed_ms=elapsed_ms,
        detail={'input': input_summary, 'error': error_message}
    )
    db.add(event)
    await db.commit()
```

### 5.2 Backward Compatibility During Migration

Run in **dual-write mode** during migration:
1. Write to both JSON files AND PostgreSQL simultaneously
2. Read from JSON files (trusted source) while verifying DB matches
3. Once DB is verified correct, switch reads to DB
4. Remove JSON file writes in final step

This ensures zero data loss and allows rollback.

---

## 6. Connection & Environment Configuration

### 6.1 Environment Variables

```bash
# PostgreSQL connection
DATABASE_URL=postgresql+asyncpg://bpulse:password@localhost:5432/bpulse

# Connection pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600  # Recycle connections after 1 hour

# Encryption
CONNECTOR_ENCRYPTION_KEY=<32-byte hex key>   # NEVER commit to git
CONNECTOR_ENCRYPTION_AAD=bpulse-connectors   # Additional authenticated data

# LangGraph checkpoint
CHECKPOINT_BACKEND=postgres
CHECKPOINT_DB_URL=postgresql://bpulse:password@localhost:5432/bpulse

# Migration
RUN_MIGRATIONS_ON_STARTUP=false   # Only run explicitly via alembic
```

### 6.2 PostgreSQL Deployment Options

| Option | Recommended For | Setup |
|---|---|---|
| Local Docker | Development | `docker run -e POSTGRES_DB=bpulse -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:16` |
| AWS RDS PostgreSQL | Production (AWS) | Use `db.t3.medium` minimum; Multi-AZ for HA |
| AWS Aurora Serverless v2 | Production (variable load) | Auto-scales; compatible with PostgreSQL driver |
| Azure Database for PostgreSQL | Production (Azure) | Flexible Server, Gen5, 2 vCores minimum |
| Supabase | Rapid deployment | Managed PostgreSQL with connection pooling built in |

### 6.3 Connection Pooling

Use `PgBouncer` in transaction-mode pooling when running multiple FastAPI workers:

```
FastAPI workers (4x) → PgBouncer (pool_size=20) → PostgreSQL
```

Without connection pooling, each FastAPI worker holds persistent connections which exhausts PostgreSQL's `max_connections` (default 100).

---

## 7. Migration Plan

### Phase 1 — Schema Creation (Week 1)

1. Deploy PostgreSQL instance (local Docker for dev, RDS for production)
2. Install SQLAlchemy, asyncpg, Alembic
3. Create `sajha/db/` module with models and engine
4. Run initial Alembic migration → create all tables
5. Implement dual-write mode for `users.json`

### Phase 2 — User & Worker Config Migration (Week 1-2)

1. Write migration script: `scripts/migrate_json_to_pg.py`
   - Reads `config/users.json` → inserts into `users` table
   - Reads `config/workers.json` → inserts into `workers` table
   - Reads `config/apikeys.json` → inserts into `api_keys` table (hashed)
   - Reads `config/connectors.json` → encrypts credentials, inserts into `connectors` table
2. Update all user management endpoints to read from PostgreSQL
3. Update all worker config endpoints to read from PostgreSQL
4. Remove JSON file writes

### Phase 3 — Conversation History Migration (Week 2-3)

1. Deploy SQLite checkpointer (REQ-05 interim step) → PostgreSQL checkpointer
2. Migrate `data/threads.jsonl` → `conversation_threads` table
3. LangGraph MemorySaver → `PostgresSaver` (conversation messages stored automatically)
4. Thread list endpoints read from PostgreSQL

### Phase 4 — Audit Log Migration (Week 3-4)

1. Migrate historical `data/audit/tool_calls.jsonl` → `audit_events` table
2. Update audit logging code to write to PostgreSQL
3. Update audit log endpoints (pagination, filtering) to query PostgreSQL
4. Verify admin console audit log display works with PostgreSQL backend
5. Archive original JSONL files (keep for 90 days, then delete)

### Phase 5 — Flask Sessions (Week 4, optional)

1. Replace file-based Flask sessions with PostgreSQL-backed sessions
2. Add session cleanup cron job (delete expired sessions daily)

---

## 8. Audit Log Query Improvements

Once data is in PostgreSQL, the admin audit log UI (currently showing "—" in Time and Tool columns — BUG from phase4 UAT) can be fixed properly. The current bug is a field name mismatch between the JSONL format and the render code. PostgreSQL schema enforces consistent field names.

New queries the audit log UI should support:
- Filter by user_id (exact)
- Filter by tool_name (contains)
- Filter by date range (BETWEEN)
- Filter by event_type
- Full-text search on detail JSONB
- Pagination (LIMIT/OFFSET or keyset)
- Export as CSV

---

## 9. Security Requirements

**SEC-DB-001 — Credentials never stored plaintext**
Connector credentials in the `connectors` table must be encrypted with AES-256-GCM before insert. The encryption key must come from an environment variable or secrets manager, never from the database.

**SEC-DB-002 — Password hashing**
User passwords already use bcrypt. The `password_hash` column stores the bcrypt output. Never store plaintext passwords.

**SEC-DB-003 — Database user least privilege**
The application database user must only have `SELECT, INSERT, UPDATE, DELETE` on application tables. No `CREATE TABLE`, `DROP`, or `SUPERUSER` privileges. A separate migration user has DDL privileges.

**SEC-DB-004 — Connection encryption**
All database connections must use TLS (`sslmode=require` in connection string). Certificate verification required in production.

**SEC-DB-005 — No sensitive data in audit JSONB**
The `detail` JSONB column in `audit_events` must not store raw tool inputs containing API keys, passwords, or full credential objects. Store hashes or truncated summaries only.

---

## 10. Acceptance Criteria

- [ ] All tables created via Alembic migration (no manual SQL)
- [ ] User login works after migration (bcrypt hashes verified correctly)
- [ ] Worker config loads from PostgreSQL (not `config/workers.json`)
- [ ] Conversation threads persist across server restarts (LangGraph → PostgreSQL checkpointer)
- [ ] Audit log entries written to PostgreSQL `audit_events` table
- [ ] Audit log filter by date, user, and tool works in admin UI
- [ ] Admin UI audit log Time and Tool columns show correct values (field name bug fixed)
- [ ] Connector credentials encrypted at rest in `connectors` table
- [ ] No JSONL file writes for any migrated data category
- [ ] Connection pool handles 10 concurrent requests without connection exhaustion
- [ ] Migration script runs idempotently (safe to run twice)

---

## 11. Out of Scope

- Domain data and document storage (stays on filesystem / S3 — see REQ-08)
- Real-time replication or read replicas (Phase 2)
- Database-level full-text search on document content (requires pgvector or Elasticsearch)
- Multi-tenant database isolation (all tenants share one database with row-level filtering by worker_id/user_id)
