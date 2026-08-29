# app/db/database.py
"""
Async Database Engine and Session Management
=============================================
This module owns the SQLAlchemy async engine and session factory.

Why async SQLAlchemy?
---------------------
FastAPI runs on an async event loop (via uvicorn + anyio). A synchronous
database call (e.g., traditional SQLAlchemy with psycopg2) would block the
entire event loop for the duration of the query. While one request waits for
the database, no other requests can be handled.

Async SQLAlchemy with the asyncpg driver executes queries asynchronously —
the event loop can handle other requests while waiting for the DB to respond.

Go analogy: this is like using goroutines instead of blocking threads for
database calls in a Go HTTP server.

Connection Pooling:
-------------------
SQLAlchemy manages a connection pool automatically. Rather than opening a new
TCP connection to PostgreSQL on every request (expensive), it reuses connections
from the pool.

Key pool parameters:
  pool_size        = number of connections to maintain in the pool
  max_overflow     = additional connections allowed above pool_size
  pool_recycle     = seconds before a connection is recycled (prevents stale connections)
  pool_pre_ping    = send a lightweight ping before using a connection (detects dead connections)

Session per Request pattern:
-----------------------------
    request → get_db() opens a session
            → your route/service does queries
            → get_db() commits and closes the session
            → response sent to client

If an exception is raised, the session is rolled back automatically.
This ensures each request is an atomic unit of work.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level engine and session factory
# These are created once at startup and reused across all requests
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


# =============================================================================
# ORM Base class
# =============================================================================
# All ORM models (app/db/models.py) inherit from this Base.
# SQLAlchemy uses it to discover and manage table metadata.
# =============================================================================
class Base(DeclarativeBase):
    pass


# =============================================================================
# Engine initialisation
# =============================================================================


def get_engine() -> AsyncEngine:
    """Return the module-level async engine (created lazily)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. "
                "Add it to your .env file: "
                "DATABASE_URL=postgresql+asyncpg://raguser:ragpassword@localhost:5432/ragdb"
            )
        _engine = create_async_engine(
            settings.database_url,
            # Echo=True logs every SQL statement — useful in development, too noisy for production
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
        )
        logger.info("Database engine created: url=%s", settings.database_url.split("@")[-1])
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the module-level session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            # expire_on_commit=False means ORM objects remain usable after commit.
            # With True (default), accessing an attribute after commit would trigger
            # a lazy reload — which is problematic in async code.
            expire_on_commit=False,
            autoflush=False,  # We control when to flush manually
            autocommit=False,
        )
    return _async_session_factory


# =============================================================================
# Database initialisation
# =============================================================================


async def init_db() -> None:
    """
    Create all tables defined by ORM models.

    Called once at application startup (in main.py's lifespan).

    WHY NOT just use this instead of Alembic migrations?
    In development, create_all() is convenient — it creates tables if they
    don't exist. But it does NOT handle schema changes (adding a column,
    dropping an index). Alembic generates migration scripts that can be
    applied incrementally to an existing database without losing data.

    In production, you ALWAYS run Alembic. In development, create_all() is
    acceptable for quick iteration (we'll add Alembic too).
    """
    from app.db.models import DocumentModel  # noqa: F401 — import so Base sees the table

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def close_db() -> None:
    """Dispose the engine connection pool. Called at application shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")


# =============================================================================
# Dependency: per-request session
# =============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession for the duration of a request.

    Usage in a route:
        async def my_route(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(DocumentModel))

    What happens:
    1. A session is acquired from the pool
    2. Your route handler runs (queries, inserts, etc.)
    3. If no exception: the session is committed
    4. If exception: the session is rolled back
    5. The session is always closed (returned to pool)

    This is a generator (yield) function — the code after yield runs after
    the request is complete, even if an exception was raised. Equivalent to
    Go's defer statement for cleanup.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
