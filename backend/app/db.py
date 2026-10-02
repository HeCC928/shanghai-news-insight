from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import uuid
from sqlalchemy import JSON, DateTime, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.config import settings


def utcnow():
    return datetime.now(timezone.utc)


def uid(prefix=''):
    return prefix + uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class Snapshot(Base):
    __tablename__ = 'snapshots'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, index=True)
    mode: Mapped[str] = mapped_column(String, index=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WatchlistItem(Base):
    __tablename__ = 'watchlist'
    __table_args__ = (UniqueConstraint('mode', 'symbol'),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uid('wl_'))
    mode: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CacheEpoch(Base):
    __tablename__ = 'cache_epochs'
    mode: Mapped[str] = mapped_column(String, primary_key=True)
    invalidated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Prompt(Base):
    __tablename__ = 'prompts'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uid('p_'))
    kind: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('kind', 'version'),)


class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uid('j_'))
    kind: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String, default='')
    idempotency_key: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, default='queued', index=True)
    step: Mapped[str] = mapped_column(String, default='等待处理')
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def make_engine(url=None):
    url = url or settings().resolved_database_url
    engine = create_engine(url, connect_args={'check_same_thread': False, 'timeout': 20} if url.startswith('sqlite') else {})
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def configure(dbapi, _):
            dbapi.execute('PRAGMA journal_mode=WAL')
            dbapi.execute('PRAGMA foreign_keys=ON')
    return engine


engine = make_engine()
Session = sessionmaker(engine, expire_on_commit=False)


@contextmanager
def transaction():
    with Session() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def save_snapshot(kind, mode, symbol, payload, snapshot_id=None):
    snapshot_id = snapshot_id or uid(kind + '_')
    with transaction() as session:
        existing = session.get(Snapshot, snapshot_id)
        if existing:
            if existing.payload != payload:
                raise ValueError('不可覆盖已有快照')
        else:
            session.add(Snapshot(id=snapshot_id, kind=kind, mode=mode, symbol=symbol, payload=payload))
    return snapshot_id


def load_snapshot(snapshot_id, mode=None, kind=None):
    with Session() as session:
        snapshot = session.get(Snapshot, snapshot_id)
        if not snapshot or (mode and snapshot.mode != mode) or (kind and snapshot.kind != kind):
            return None
        return snapshot.payload
