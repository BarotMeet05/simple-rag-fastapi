# app/main.py
"""
FastAPI Application Factory
============================
This is the entry point for the entire application.

Application Factory Pattern:
-----------------------------
We create the FastAPI app inside a function (create_application) rather
than at module level. Benefits:
1. Tests can call create_application() to get a fresh app instance
2. Configuration is injected — no reliance on module-level globals
3. Easy to test with different settings (e.g., test DB URL)

You'll recognise this pattern from Go's http.Handler factory pattern.

ASGI vs WSGI:
--------------
FastAPI is an ASGI (Asynchronous Server Gateway Interface) framework.
WSGI (Flask, Django) is synchronous — one thread per request.
ASGI is async — one event loop handles many concurrent requests.

Uvicorn is the ASGI server that runs the app:
  uvicorn app.main:app --reload

"app.main:app" means: load the `app` object from `app/main.py`.

CORS (Cross-Origin Resource Sharing):
---------------------------------------
See app/api/routes/... for endpoint docs.
CORS explanation lives in main.py because it's a middleware concern.

WHY CORS?
Browsers enforce the Same-Origin Policy: a page served from
http://localhost:5173 (Vite) cannot make XHR requests to
http://localhost:8000 (FastAPI) unless the server explicitly allows it.

The server signals this via response headers:
    Access-Control-Allow-Origin: http://localhost:5173

FastAPI's CORSMiddleware handles this automatically based on the
allowed_origins list in our settings.

Security note: In production, NEVER use allow_origins=["*"] for an API
that handles sensitive data. Always enumerate specific allowed origins.

Lifespan Events:
-----------------
FastAPI supports startup/shutdown lifecycle hooks via the lifespan context
manager. This is where we'll:
- Connect to PostgreSQL (Phase 2)
- Load the embedding model (Phase 4)
- Pre-warm any caches (Phase 18)
For now, it just logs startup/shutdown.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging

settings = get_settings()

# Set up logging as early as possible — before any other module imports
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle.

    Code before `yield` runs on startup.
    Code after `yield` runs on shutdown.

    In Go terms, this is equivalent to having an init() function and a
    defer cleanup() at the process level.
    """
    # -------------------------------------------------------------------------
    # STARTUP
    # -------------------------------------------------------------------------
    logger.info(
        "Starting %s v%s [env=%s, debug=%s]",
        settings.app_name,
        settings.app_version,
        settings.environment,
        settings.debug,
    )

    # Phase 2+: initialise DB connection pool and create tables
    if settings.database_url:
        from app.db.database import init_db
        try:
            import asyncio
            await asyncio.wait_for(init_db(), timeout=10.0)
            logger.info("Database initialised")
        except Exception as err:
            logger.warning("Database startup init warning (will retry on query): %s", err)
    else:
        logger.warning("DATABASE_URL not set — running without database (tests only)")

    # Phase 4+: load embedding model here

    yield

    # -------------------------------------------------------------------------
    # SHUTDOWN
    # -------------------------------------------------------------------------
    logger.info("Shutting down %s", settings.app_name)
    # Phase 2+: close DB connection pool
    if settings.database_url:
        from app.db.database import close_db
        await close_db()


def create_application() -> FastAPI:
    """
    FastAPI application factory.

    Returns a fully configured FastAPI instance.
    Called at module level (app = create_application()) so that
    `uvicorn app.main:app` can find the app object.
    """
    _app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Production-style AI Document Intelligence & RAG Platform. "
            "Upload documents, ask questions, receive grounded answers with citations."
        ),
        # OpenAPI docs are available at /docs (Swagger UI) and /redoc
        docs_url="/docs",
        redoc_url="/redoc",
        # The lifespan parameter replaces the deprecated on_event decorators
        lifespan=lifespan,
    )

    @_app.middleware("http")
    async def log_requests(request, call_next):
        logger.info("--> %s %s", request.method, request.url.path)
        try:
            response = await call_next(request)
            logger.info("<-- %s %s [status=%d]", request.method, request.url.path, response.status_code)
            return response
        except Exception as e:
            logger.error("!!! %s %s [error=%s]", request.method, request.url.path, e)
            raise

    # -------------------------------------------------------------------------
    # CORS Middleware
    # -------------------------------------------------------------------------
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins if "*" not in settings.allowed_origins else ["*"],
        allow_origin_regex=r"https://.*" if "*" in settings.allowed_origins else None,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # -------------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------------
    register_exception_handlers(_app)

    # -------------------------------------------------------------------------
    # Routes
    # -------------------------------------------------------------------------
    # Health check at root level (no /api/v1 prefix) — standard convention
    _app.include_router(health_router)

    # All versioned API routes under /api/v1
    _app.include_router(api_router, prefix=settings.api_v1_prefix)

    logger.info(
        "Routes registered: prefix=%s",
        settings.api_v1_prefix,
    )

    return _app


# Create the application instance
# Uvicorn will import this module and look for `app`
app = create_application()
