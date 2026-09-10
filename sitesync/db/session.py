"""
SiteSync AI — DB Session Factory

Provides a thread-safe SQLAlchemy engine and session factory.
Creates the data/ directory and all tables on first import if they don't exist.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from sitesync.config import settings
from sitesync.db.models import Base


def _get_engine():
    """Create and configure the SQLAlchemy engine."""
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},  # SQLite only
        echo=False,
    )

    # Enable WAL mode for SQLite — better concurrent read/write
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    Base.metadata.create_all(engine)
    return engine


_engine = _get_engine()
engine = _engine  # public alias used by seed.py and alembic
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager yielding a DB session; auto-commits or rolls back."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_engine():
    return _engine
