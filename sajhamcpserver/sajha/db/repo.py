"""
Database repository — async CRUD helpers for all models.
REQ-07: replaces direct JSON file reads/writes in agent_server.py.
"""
import asyncio
import datetime
import json
import pathlib
from typing import Optional

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from .engine import AsyncSessionLocal, engine
from .models import User, Worker, Connector, ConversationThread, AuditEvent, FileMetadata


async def _ensure_conversation_threads_table() -> None:
    """Create conversation_threads if missing — safe to call on every startup."""
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversation_threads (
                    thread_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id          TEXT NOT NULL,
                    worker_id        TEXT NOT NULL,
                    title            TEXT,
                    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    archived_at      TIMESTAMPTZ,
                    message_count    INTEGER NOT NULL DEFAULT 0,
                    token_count_est  INTEGER NOT NULL DEFAULT 0
                )
            """))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_threads_user_worker "
                "ON conversation_threads (user_id, worker_id)"
            ))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_threads_active "
                "ON conversation_threads (user_id, archived_at)"
            ))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("_ensure_conversation_threads_table failed: %s", e)


# ── Users ──────────────────────────────────────────────────────────────────────

async def get_user(user_id: str) -> Optional[dict]:
    async with AsyncSessionLocal() as db:
        row = await db.get(User, user_id)
        return row.to_dict() if row else None


async def find_user_by_username(username: str) -> Optional[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        row = result.scalar_one_or_none()
        return row.to_dict() if row else None


async def list_users() -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).order_by(User.username))
        return [r.to_dict() for r in result.scalars()]


async def upsert_user(data: dict) -> dict:
    """Insert or update a user row. Returns the saved dict."""
    async with AsyncSessionLocal() as db:
        row = await db.get(User, data['user_id'])
        if row is None:
            row = User(**{k: v for k, v in data.items() if hasattr(User, k)})
            db.add(row)
        else:
            for k, v in data.items():
                if hasattr(User, k) and k != 'user_id':
                    setattr(row, k, v)
            row.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(row)
        return row.to_dict()


async def delete_user(user_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        row = await db.get(User, user_id)
        if row:
            await db.delete(row)
            await db.commit()
            return True
        return False


async def update_last_login(user_id: str):
    async with AsyncSessionLocal() as db:
        row = await db.get(User, user_id)
        if row:
            row.last_login_at = datetime.datetime.now(datetime.timezone.utc)
            await db.commit()


# ── Workers ────────────────────────────────────────────────────────────────────

async def get_worker(worker_id: str) -> Optional[dict]:
    async with AsyncSessionLocal() as db:
        row = await db.get(Worker, worker_id)
        return row.to_dict() if row else None


async def list_workers() -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Worker).order_by(Worker.name))
        return [r.to_dict() for r in result.scalars()]


async def upsert_worker(data: dict) -> dict:
    async with AsyncSessionLocal() as db:
        row = await db.get(Worker, data['worker_id'])
        if row is None:
            row = Worker(**{k: v for k, v in data.items() if hasattr(Worker, k)})
            db.add(row)
        else:
            for k, v in data.items():
                if hasattr(Worker, k) and k != 'worker_id':
                    setattr(row, k, v)
            row.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(row)
        return row.to_dict()


async def delete_worker(worker_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        row = await db.get(Worker, worker_id)
        if row:
            await db.delete(row)
            await db.commit()
            return True
        return False


# ── Connectors ─────────────────────────────────────────────────────────────────

async def get_connector(connector_type: str) -> Optional[dict]:
    async with AsyncSessionLocal() as db:
        row = await db.get(Connector, connector_type)
        if not row:
            return None
        return {
            'connector_type': row.connector_type,
            'display_name':   row.display_name,
            'status':         row.status,
            'enabled':        row.enabled,
            'has_credentials': row.has_credentials,
        }


async def list_connectors() -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Connector))
        return [{'connector_type': r.connector_type, 'display_name': r.display_name,
                 'status': r.status, 'enabled': r.enabled, 'has_credentials': r.has_credentials}
                for r in result.scalars()]


async def upsert_connector(connector_type: str, data: dict) -> dict:
    async with AsyncSessionLocal() as db:
        row = await db.get(Connector, connector_type)
        if row is None:
            row = Connector(connector_type=connector_type, **{k: v for k, v in data.items() if hasattr(Connector, k) and k != 'connector_type'})
            db.add(row)
        else:
            for k, v in data.items():
                if hasattr(Connector, k) and k != 'connector_type':
                    setattr(row, k, v)
            row.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(row)
        return {'connector_type': row.connector_type, 'status': row.status, 'enabled': row.enabled}


# ── Conversation Threads ───────────────────────────────────────────────────────

async def register_thread(thread_id: str, user_id: str, worker_id: str, title: str = None):
    """Register a new thread. No-op if thread_id already exists."""
    import uuid as _uuid
    async with AsyncSessionLocal() as db:
        try:
            tid = _uuid.UUID(thread_id)
        except ValueError:
            tid = _uuid.uuid4()
        existing = await db.get(ConversationThread, tid)
        if existing:
            return
        row = ConversationThread(
            thread_id=tid,
            user_id=user_id,
            worker_id=worker_id,
            title=title,
        )
        db.add(row)
        await db.commit()


async def get_thread(thread_id: str) -> Optional[dict]:
    import uuid as _uuid
    async with AsyncSessionLocal() as db:
        try:
            row = await db.get(ConversationThread, _uuid.UUID(thread_id))
        except ValueError:
            return None
        return row.to_dict() if row else None


async def list_threads(user_id: str, worker_id: str) -> list[dict]:
    import uuid as _uuid
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ConversationThread)
            .where(ConversationThread.user_id == user_id,
                   ConversationThread.worker_id == worker_id,
                   ConversationThread.archived_at.is_(None))
            .order_by(ConversationThread.last_activity_at.desc())
        )
        return [r.to_dict() for r in result.scalars()]


async def touch_thread(thread_id: str):
    """Update last_activity_at and increment message_count."""
    import uuid as _uuid
    async with AsyncSessionLocal() as db:
        try:
            row = await db.get(ConversationThread, _uuid.UUID(thread_id))
        except ValueError:
            return
        if row:
            row.last_activity_at = datetime.datetime.now(datetime.timezone.utc)
            row.message_count = (row.message_count or 0) + 1
            await db.commit()


# ── Audit Events ───────────────────────────────────────────────────────────────

async def log_tool_call(user_id: str, worker_id: str, tool_name: str,
                        elapsed_ms: float, status: str, thread_id: str = None,
                        tool_args: dict = None, result_summary: str = None):
    """Async-safe tool-call audit insert. Errors are swallowed — must not break main flow."""
    try:
        detail: dict = {'status': status}
        if tool_args:
            detail['args'] = tool_args
        if result_summary:
            detail['result'] = result_summary[:500]
        async with AsyncSessionLocal() as db:
            row = AuditEvent(
                event_type='tool_call',
                user_id=user_id,
                worker_id=worker_id,
                thread_id=thread_id,
                tool_name=tool_name,
                tool_result_ok=(status == 'success'),
                elapsed_ms=int(elapsed_ms),
                detail=detail,
            )
            db.add(row)
            await db.commit()
    except Exception:
        pass  # audit must never break the main flow


async def log_event(event_type: str, user_id: str, worker_id: str,
                    thread_id: str = None, detail: dict = None,
                    elapsed_ms: float = None, tool_name: str = None,
                    tool_result_ok: bool = None):
    """Generic audit event insert for query, response, usage, canvas, error events."""
    try:
        async with AsyncSessionLocal() as db:
            row = AuditEvent(
                event_type=event_type,
                user_id=user_id,
                worker_id=worker_id,
                thread_id=thread_id,
                tool_name=tool_name,
                tool_result_ok=tool_result_ok,
                elapsed_ms=int(elapsed_ms) if elapsed_ms is not None else None,
                detail=detail or {},
            )
            db.add(row)
            await db.commit()
    except Exception:
        pass  # audit must never break the main flow


async def log_file_access(user_id: str, worker_id: str, file_path: str,
                          section: str, detail: dict = None):
    try:
        async with AsyncSessionLocal() as db:
            row = AuditEvent(
                event_type='file_access',
                user_id=user_id,
                worker_id=worker_id,
                file_path=file_path,
                file_section=section,
                detail=detail or {},
            )
            db.add(row)
            await db.commit()
    except Exception:
        pass


async def log_auth_event(user_id: str, event: str, detail: dict = None):
    try:
        async with AsyncSessionLocal() as db:
            row = AuditEvent(
                event_type='auth',
                user_id=user_id,
                detail={'event': event, **(detail or {})},
            )
            db.add(row)
            await db.commit()
    except Exception:
        pass


async def query_audit(worker_id: str = None, user_id: str = None,
                      limit: int = 100, offset: int = 0) -> list[dict]:
    async with AsyncSessionLocal() as db:
        q = select(AuditEvent).order_by(AuditEvent.created_at.desc())
        if worker_id:
            q = q.where(AuditEvent.worker_id == worker_id)
        if user_id:
            q = q.where(AuditEvent.user_id == user_id)
        q = q.limit(limit).offset(offset)
        result = await db.execute(q)
        return [r.to_dict() for r in result.scalars()]


# ── File Metadata ──────────────────────────────────────────────────────────────

async def upsert_file_metadata(worker_id: str, section: str, rel_path: str,
                                file_name: str, size_bytes: int = None,
                                mime_type: str = None, is_folder: bool = False,
                                user_id: str = None, created_by: str = None,
                                s3_key: str = None) -> dict:
    """Insert or update file metadata entry."""
    if s3_key is None:
        s3_key = rel_path  # local mode: s3_key == rel_path
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FileMetadata).where(
                FileMetadata.worker_id == worker_id,
                FileMetadata.section == section,
                FileMetadata.rel_path == rel_path,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = FileMetadata(
                worker_id=worker_id, user_id=user_id, section=section,
                s3_key=s3_key, rel_path=rel_path, file_name=file_name,
                mime_type=mime_type, size_bytes=size_bytes, is_folder=is_folder,
                created_by=created_by,
            )
            db.add(row)
        else:
            row.file_name = file_name
            row.size_bytes = size_bytes
            row.mime_type = mime_type
            row.s3_key = s3_key
            row.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(row)
        return row.to_dict()


async def delete_file_metadata(worker_id: str, section: str, rel_path: str):
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(FileMetadata).where(
                FileMetadata.worker_id == worker_id,
                FileMetadata.section == section,
                FileMetadata.rel_path == rel_path,
            )
        )
        await db.commit()


async def list_file_metadata(worker_id: str, section: str,
                              user_id: str = None) -> list[dict]:
    async with AsyncSessionLocal() as db:
        q = select(FileMetadata).where(
            FileMetadata.worker_id == worker_id,
            FileMetadata.section == section,
        ).order_by(FileMetadata.rel_path)
        if user_id:
            q = q.where(FileMetadata.user_id == user_id)
        result = await db.execute(q)
        return [r.to_dict() for r in result.scalars()]


async def get_storage_used_bytes(worker_id: str) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(func.sum(FileMetadata.size_bytes)).where(
                FileMetadata.worker_id == worker_id,
                FileMetadata.is_folder == False,
            )
        )
        total = result.scalar_one_or_none()
        return int(total or 0)
