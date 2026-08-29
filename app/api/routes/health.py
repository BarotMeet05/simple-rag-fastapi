# app/api/routes/health.py
"""
Health Check Endpoint
======================
GET /health

WHY a health check endpoint?
------------------------------
Every production service needs a /health (or /healthz) endpoint because:

1. Load balancers (ALB, Nginx) poll it to decide if a pod is ready for traffic
2. Docker / Kubernetes liveness and readiness probes call it
3. Monitoring systems (Datadog, PagerDuty) poll it for uptime tracking
4. You can check it manually to confirm the service started correctly

Health check design:
--------------------
The simplest health check returns HTTP 200. We go slightly further by
returning application metadata (version, environment) — useful when you have
multiple versions deployed and need to confirm which one is running.

In Phase 2+ we'll add "component health" (database reachability, embedding
model availability) so the endpoint reflects the health of the full system.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter()


@router.get(
    "/health",
    # Tags group endpoints in the Swagger UI
    tags=["Health"],
    summary="Service health check",
    description="Returns service status and metadata. Used by load balancers and monitoring.",
    # response_model tells FastAPI to validate and document the response shape
    # Using dict here — simple enough that a full Pydantic model would be overkill
    response_model=dict,
)
async def health_check(
    # Dependency injection — FastAPI calls get_settings() and passes the result
    # here automatically. This is how we avoid global variables.
    # You can think of it like Go's fx or wire, but built into the framework.
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Return service health status.

    async def — this is an async function.
    WHY async?
    ----------
    FastAPI runs on an ASGI server (uvicorn + anyio). Async functions are
    executed on the event loop without blocking it. Synchronous functions
    block the event loop for their duration, preventing other requests from
    being handled.

    For I/O-bound work (DB queries, HTTP calls to LLMs), async is always
    preferred. For CPU-bound work (e.g., heavy text processing), we'd use
    a thread pool. We'll cover this in Phase 2.

    This specific endpoint does no I/O, so async is a style choice here —
    but it's good practice to default to async in FastAPI.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
