"""
SQLAlchemy ORM models.
REQ-07: PostgreSQL schema — users, workers, api_keys, connectors,
        conversation_threads, audit_events, file_metadata, flask_sessions.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, BigInteger, Integer, String, Text, DateTime, LargeBinary,
    ForeignKey, Index, func, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .engine import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = 'users'

    user_id:             Mapped[str]            = mapped_column(String(64),  primary_key=True)
    username:            Mapped[str]            = mapped_column(String(64),  nullable=False, unique=True)
    display_name:        Mapped[str]            = mapped_column(String(128), nullable=False)
    password_hash:       Mapped[str]            = mapped_column(String(128), nullable=False)
    role:                Mapped[str]            = mapped_column(String(32),  nullable=False, default='user')
    worker_id:           Mapped[str | None]     = mapped_column(String(64),  ForeignKey('workers.worker_id'), nullable=True)
    enabled:             Mapped[bool]           = mapped_column(Boolean,     nullable=False, default=True)
    onboarding_complete: Mapped[bool]           = mapped_column(Boolean,     nullable=False, default=False)
    created_at:          Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=_now)
    updated_at:          Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    last_login_at:       Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by:          Mapped[str | None]     = mapped_column(String(64),  nullable=True)

    __table_args__ = (
        Index('idx_users_username',  'username'),
        Index('idx_users_role',      'role'),
        Index('idx_users_worker_id', 'worker_id'),
    )

    def to_dict(self) -> dict:
        return {
            'user_id':             self.user_id,
            'username':            self.username,
            'display_name':        self.display_name,
            'password_hash':       self.password_hash,
            'role':                self.role,
            'worker_id':           self.worker_id,
            'enabled':             self.enabled,
            'onboarding_complete': self.onboarding_complete,
            'created_at':          self.created_at.isoformat() if self.created_at else None,
            'last_login_at':       self.last_login_at.isoformat() if self.last_login_at else None,
        }


class Worker(Base):
    __tablename__ = 'workers'

    worker_id:        Mapped[str]      = mapped_column(String(64),  primary_key=True)
    name:             Mapped[str]      = mapped_column(String(128), nullable=False)
    description:      Mapped[str | None] = mapped_column(Text,       nullable=True)
    system_prompt:    Mapped[str | None] = mapped_column(Text,       nullable=True)
    enabled_tools:    Mapped[dict]     = mapped_column(JSONB,       nullable=False, default=lambda: ['*'])
    domain_data_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verified_wf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    connector_scope:  Mapped[dict]     = mapped_column(JSONB,       nullable=False, default=dict)
    enabled:          Mapped[bool]     = mapped_column(Boolean,     nullable=False, default=True)
    created_at:       Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at:       Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            'worker_id':        self.worker_id,
            'name':             self.name,
            'description':      self.description,
            'system_prompt':    self.system_prompt,
            'enabled_tools':    self.enabled_tools,
            'domain_data_path': self.domain_data_path,
            'verified_wf_path': self.verified_wf_path,
            'connector_scope':  self.connector_scope,
            'enabled':          self.enabled,
        }


class ApiKey(Base):
    __tablename__ = 'api_keys'

    key_id:      Mapped[int]           = mapped_column(Integer,     primary_key=True, autoincrement=True)
    key_hash:    Mapped[str]           = mapped_column(String(128), nullable=False, unique=True)
    key_prefix:  Mapped[str]           = mapped_column(String(16),  nullable=False)
    label:       Mapped[str | None]    = mapped_column(String(128), nullable=True)
    created_by:  Mapped[str | None]    = mapped_column(String(64),  ForeignKey('users.user_id'), nullable=True)
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked:     Mapped[bool]          = mapped_column(Boolean,     nullable=False, default=False)


class Connector(Base):
    __tablename__ = 'connectors'

    connector_type:  Mapped[str]       = mapped_column(String(64),  primary_key=True)
    display_name:    Mapped[str]       = mapped_column(String(128), nullable=False)
    status:          Mapped[str]       = mapped_column(String(32),  nullable=False, default='not_configured')
    enabled:         Mapped[bool]      = mapped_column(Boolean,     nullable=False, default=False)
    credentials_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    credentials_iv:  Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    has_credentials: Mapped[bool]      = mapped_column(Boolean,     nullable=False, default=False)
    created_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now)
    updated_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ConversationThread(Base):
    __tablename__ = 'conversation_threads'

    thread_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:         Mapped[str]       = mapped_column(String(64), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    worker_id:       Mapped[str]       = mapped_column(String(64), ForeignKey('workers.worker_id'), nullable=False)
    title:           Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=_now)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    archived_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count:   Mapped[int]       = mapped_column(Integer, nullable=False, default=0)
    token_count_est: Mapped[int]       = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index('idx_threads_user_worker', 'user_id', 'worker_id'),
        Index('idx_threads_active', 'user_id', 'archived_at'),
    )

    def to_dict(self) -> dict:
        return {
            'thread_id':        str(self.thread_id),
            'user_id':          self.user_id,
            'worker_id':        self.worker_id,
            'title':            self.title,
            'created_at':       self.created_at.isoformat() if self.created_at else None,
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'archived_at':      self.archived_at.isoformat() if self.archived_at else None,
            'message_count':    self.message_count,
        }


class AuditEvent(Base):
    __tablename__ = 'audit_events'

    event_id:       Mapped[int]         = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type:     Mapped[str]         = mapped_column(String(64), nullable=False)
    user_id:        Mapped[str | None]  = mapped_column(String(64), nullable=True)
    worker_id:      Mapped[str | None]  = mapped_column(String(64), nullable=True)
    thread_id:      Mapped[str | None]  = mapped_column(String(64), nullable=True)  # stored as string for flexibility
    tool_name:      Mapped[str | None]  = mapped_column(String(128), nullable=True)
    tool_result_ok: Mapped[bool | None] = mapped_column(Boolean,    nullable=True)
    file_path:      Mapped[str | None]  = mapped_column(String(512), nullable=True)
    file_section:   Mapped[str | None]  = mapped_column(String(64),  nullable=True)
    detail:         Mapped[dict | None] = mapped_column(JSONB,       nullable=True)
    elapsed_ms:     Mapped[int | None]  = mapped_column(Integer,     nullable=True)
    created_at:     Mapped[datetime]    = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index('idx_audit_user',   'user_id',   'created_at'),
        Index('idx_audit_worker', 'worker_id', 'created_at'),
        Index('idx_audit_tool',   'tool_name', 'created_at'),
        Index('idx_audit_type',   'event_type', 'created_at'),
    )

    def to_dict(self) -> dict:
        return {
            'event_id':      self.event_id,
            'event_type':    self.event_type,
            'user_id':       self.user_id,
            'worker_id':     self.worker_id,
            'tool_name':     self.tool_name,
            'tool_result_ok': self.tool_result_ok,
            'elapsed_ms':    self.elapsed_ms,
            'detail':        self.detail,
            'created_at':    self.created_at.isoformat() if self.created_at else None,
        }


class FileMetadata(Base):
    __tablename__ = 'file_metadata'

    file_id:      Mapped[int]          = mapped_column(BigInteger,   primary_key=True, autoincrement=True)
    worker_id:    Mapped[str]          = mapped_column(String(64),   nullable=False)
    user_id:      Mapped[str | None]   = mapped_column(String(64),   nullable=True)
    section:      Mapped[str]          = mapped_column(String(64),   nullable=False)
    s3_key:       Mapped[str]          = mapped_column(Text,         nullable=False)
    rel_path:     Mapped[str]          = mapped_column(Text,         nullable=False)
    file_name:    Mapped[str]          = mapped_column(String(512),  nullable=False)
    mime_type:    Mapped[str | None]   = mapped_column(String(128),  nullable=True)
    size_bytes:   Mapped[int | None]   = mapped_column(BigInteger,   nullable=True)
    is_folder:    Mapped[bool]         = mapped_column(Boolean,      nullable=False, default=False)
    bm25_indexed: Mapped[bool]         = mapped_column(Boolean,      nullable=False, default=False)
    created_at:   Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=_now)
    updated_at:   Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    created_by:   Mapped[str | None]   = mapped_column(String(64),   nullable=True)

    __table_args__ = (
        Index('idx_file_meta_tree',   'worker_id', 'section', 'rel_path'),
        Index('idx_file_meta_search', 'worker_id', 'file_name'),
    )

    def to_dict(self) -> dict:
        return {
            'file_id':    self.file_id,
            'worker_id':  self.worker_id,
            'user_id':    self.user_id,
            'section':    self.section,
            's3_key':     self.s3_key,
            'rel_path':   self.rel_path,
            'file_name':  self.file_name,
            'mime_type':  self.mime_type,
            'size_bytes': self.size_bytes,
            'is_folder':  self.is_folder,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class FlaskSession(Base):
    __tablename__ = 'flask_sessions'

    session_id: Mapped[str]      = mapped_column(String(256), primary_key=True)
    user_id:    Mapped[str | None] = mapped_column(String(64), nullable=True)
    data:       Mapped[bytes]    = mapped_column(LargeBinary,  nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_sessions_expires', 'expires_at'),
    )
