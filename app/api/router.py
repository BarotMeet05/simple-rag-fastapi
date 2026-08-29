# app/api/router.py
"""
API Router — Central Route Registration
=========================================
This module assembles all route modules into a single APIRouter
that main.py mounts at the API prefix.

WHY a central router?
---------------------
Rather than registering every route directly on the FastAPI app in main.py,
we aggregate routes here. This keeps main.py focused on application-level
concerns (middleware, lifespan, exception handlers) rather than routing details.

It also makes it easy to add new route groups in future phases —
just import and include the new router here.
"""

from fastapi import APIRouter

from app.api.routes import chat, documents, health, search

api_router = APIRouter()

# Health check lives at the root (/health), not under /api/v1
# We include it separately in main.py.
# Here we register all versioned API routes.

api_router.include_router(documents.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)
