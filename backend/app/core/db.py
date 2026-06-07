"""Database engine and session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the shared SQLAlchemy engine; creates it on first call.

    Pool is sized for pipeline parallelism (pool_size workers + overflow).
    pool_recycle prevents stale connections during multi-hour batch runs.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=1800,
            pool_timeout=30,
            echo=(settings.log_level.lower() == "debug"),
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the shared session factory; creates it on first call."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session."""
    session_local = get_session_factory()
    session = session_local()
    try:
        yield session
    finally:
        session.close()
