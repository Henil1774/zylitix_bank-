"""
api.py — Zylitix Bank FastAPI entry point (port 8000)

Changes vs original:
  • slowapi rate-limiter wired in (used by routers/auth.py /login)
  • logger.setup_uvicorn_logging() called so uvicorn logs → logs/zylitix.log
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler          # ← slowapi wiring
from slowapi.errors import RateLimitExceeded              # ← slowapi wiring

from routers import auth, dashboard, customers, users
from routers.auth import limiter                          # ← shared limiter
from logger import logger, setup_uvicorn_logging

setup_uvicorn_logging()

app = FastAPI(
    title="Zylitix Bank API",
    description="Banking REST API — auth, customers, dashboard, users.",
    version="3.0.0",
)

# ── Rate-limiter state + 429 handler ─────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1800", "http://127.0.0.1:1800"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(customers.router)
app.include_router(users.router)

logger.info("Zylitix Bank API v3.0.0 started")


@app.get("/", tags=["Root"])
def root():
    return {
        "bank":        "Zylitix Bank",
        "api_version": "3.0.0",
        "status":      "running",
        "docs":        "http://127.0.0.1:8000/docs",
    }