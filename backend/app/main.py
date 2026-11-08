"""Main FastAPI application entry point."""

import os
import sys
# Reconfigure stdout and stderr for UTF-8 with fallback to avoid charmap UnicodeEncodeErrors on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base

# Import API routers (Phase 1-7)
from app.api import jobs, technicians, skills, service_zones

# Import Phase 1-7 routers
from app.routers import scheduling
from app.routers.disruptions import router as disruptions_router
from app.routers.dashboard import router as dashboard_router
from app.routers.assignments import router as assignments_router

# Import Phase 8+ routers
from app.routers.auth import router as auth_router
from app.routers.customer import router as customer_router
from app.routers.technician_portal import router as technician_portal_router
from app.routers.admin import router as admin_router
from app.routers.websocket import router as ws_router

# Import models to register them with SQLAlchemy
from app import models

# Create database tables
Base.metadata.create_all(bind=engine)

# ── Auto-migrate: add new columns if they don't exist (SQLite safe) ──────────
try:
    import sqlite3 as _sqlite3
    import re as _re

    _db_url = settings.database_url
    _db_path = _re.sub(r"^sqlite:///", "", _db_url)
    if _db_path.startswith("./"):
        import os as _os
        _db_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), _db_path[2:])

    _conn = _sqlite3.connect(_db_path)
    _cur = _conn.cursor()
    _cur.execute("PRAGMA table_info(technicians)")
    _existing_cols = [row[1] for row in _cur.fetchall()]
    if "email" not in _existing_cols:
        _cur.execute("ALTER TABLE technicians ADD COLUMN email TEXT")
    if "phone" not in _existing_cols:
        _cur.execute("ALTER TABLE technicians ADD COLUMN phone TEXT")
    _conn.commit()
    _conn.close()
except Exception as _e:
    print(f"[WARN] Auto-migration skipped: {_e}")

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DispatchGrid v2 — Intelligent Workforce Scheduling & On-Demand Field Service Platform",
    debug=settings.debug,
)

# ── CORS Middleware Configuration ─────────────────────────────────────────────
# Allowed origins for frontend clients (production Vercel & local development)
allowed_origins = [
    "https://dispatchgrid1.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Merge any additional origins specified in the CORS_ORIGINS environment variable
env_cors = os.getenv("CORS_ORIGINS", "")
if env_cors:
    for origin in env_cors.split(","):
        cleaned = origin.strip().rstrip("/")
        if cleaned and cleaned not in allowed_origins:
            allowed_origins.append(cleaned)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With", "*"],
    expose_headers=["*"],
    max_age=86400,
)


@app.on_event("startup")
def on_startup():
    """Seed initial V2 data and start the APScheduler background jobs on server startup."""
    try:
        from app.seed.v2_seed import seed
        seed()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("V2 seeding on startup failed: %s", exc)

    try:
        from app.background.scheduler import start_scheduler
        start_scheduler()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Scheduler failed to start: %s", exc)


@app.on_event("shutdown")
def on_shutdown():
    """Stop the background scheduler on shutdown."""
    try:
        from app.background.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "version": settings.app_version,
    }


# ── Core CRUD routers ──────────────────────────────────────────────────────────
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(technicians.router, prefix="/api/technicians", tags=["Technicians"])
app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])
app.include_router(service_zones.router, prefix="/api/service-zones", tags=["Service Zones"])

# ── Scheduling engine router ───────────────────────────────────────────────────
app.include_router(scheduling.router, prefix="/api", tags=["Scheduling"])

# ── Assignment management router ───────────────────────────────────────────────
app.include_router(assignments_router, prefix="/api/assignments", tags=["Assignments"])

# ── Disruption handling router ─────────────────────────────────────────────────
app.include_router(disruptions_router, prefix="/api/disruptions", tags=["Disruptions"])

# ── Dashboard analytics router ─────────────────────────────────────────────────
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

# ── Phase 8+: Auth ────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

# ── Phase 8+: Customer portal ─────────────────────────────────────────────────
app.include_router(customer_router, prefix="/api/customer", tags=["Customer"])

# ── Phase 8+: Technician portal ───────────────────────────────────────────────
app.include_router(technician_portal_router, prefix="/api/technician", tags=["Technician"])

# ── Phase 8+: Admin dashboard ─────────────────────────────────────────────────
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

# ── Phase 8+: WebSocket / SSE real-time ───────────────────────────────────────
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
