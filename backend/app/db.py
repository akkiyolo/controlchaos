"""Database connection, session management, and connectivity verification."""

import logging
import time
from typing import Any, Dict, Generator
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_engine(database_url: str | None = None):
    url = database_url or settings.DATABASE_URL
    # For SQLite in tests, pool_size / max_overflow do not apply
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})

    return create_engine(
        url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
    )


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to provide a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection(target_url: str | None = None) -> Dict[str, Any]:
    """
    Checks database connectivity, latency, SSL status, and server version.
    Returns a dict with status and diagnostic info or raises an exception.
    """
    check_engine = get_engine(target_url) if target_url else engine
    start_time = time.perf_counter()

    with check_engine.connect() as conn:
        # Check latency and version
        version_result = conn.execute(text("SELECT version();")).scalar()
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Check SSL status in PostgreSQL (psycopg3 connection info or pg_stat_ssl)
        ssl_active = False
        try:
            dbapi_conn = conn.connection.dbapi_connection
            if hasattr(dbapi_conn, "info") and hasattr(dbapi_conn.info, "ssl_in_use"):
                ssl_active = bool(dbapi_conn.info.ssl_in_use)
            elif "sslmode=require" in str(check_engine.url):
                ssl_active = True
        except Exception:
            ssl_active = "sslmode=require" in str(check_engine.url)

    return {
        "status": "connected",
        "latency_ms": round(latency_ms, 2),
        "server_version": version_result,
        "ssl_active": ssl_active,
    }


def assert_safe_test_db(target_url: str) -> None:
    """
    Protects production Render DB from accidental test wiping.
    Raises RuntimeError if target_url appears to point to production Render.
    """
    parsed = urlparse(target_url)
    if "render.com" in parsed.netloc and "test" not in parsed.path.lower():
        raise RuntimeError(
            f"REFUSING to execute destructive test setup against production host: {parsed.netloc}"
        )
