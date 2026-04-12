-- SAJHA MCP Agent — PostgreSQL Initialization
-- Runs once on first container start via docker-entrypoint-initdb.d

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- LangGraph checkpoints table (used by langgraph-checkpoint-postgres)
-- The langgraph library auto-creates its schema, but we ensure the DB is ready.

-- Audit log table (replaces JSONL file-based audit)
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    worker_id       TEXT,
    user_id         TEXT,
    thread_id       TEXT,
    event_type      TEXT NOT NULL,
    tool_name       TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    duration_ms     INTEGER,
    status          TEXT,
    details         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_worker ON audit_log (worker_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log (user_id, timestamp DESC);

-- Memory table (cross-session agent memory)
CREATE TABLE IF NOT EXISTS agent_memory (
    id              BIGSERIAL PRIMARY KEY,
    worker_id       TEXT NOT NULL,
    user_id         TEXT,
    thread_id       TEXT,
    content         TEXT NOT NULL,
    keywords        TEXT[] DEFAULT '{}',
    similarity      FLOAT DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    accessed_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_memory_worker ON agent_memory (worker_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_expires ON agent_memory (expires_at) WHERE expires_at IS NOT NULL;

-- Session tracking
CREATE TABLE IF NOT EXISTS sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         TEXT NOT NULL,
    worker_id       TEXT NOT NULL,
    thread_id       TEXT NOT NULL,
    title           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_count   INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id, worker_id, updated_at DESC);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sajha;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sajha;
