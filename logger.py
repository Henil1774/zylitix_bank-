"""
logger.py — Centralised logging for Zylitix Bank
Sits in the project root. Creates logs/app.log and logs/error.log.

Usage (anywhere in the project):
    from logger import logger
    logger.info("User logged in: %s", email)
    logger.warning("Failed login attempt: %s", email)
    logger.error("DB error: %s", str(e))
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_fmt = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── logs/app.log — INFO and above (general activity) ─────────────────────────
_app_fh = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"),
    maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
)
_app_fh.setLevel(logging.INFO)
_app_fh.setFormatter(_fmt)

# ── logs/error.log — WARNING and above only ───────────────────────────────────
_err_fh = RotatingFileHandler(
    os.path.join(LOG_DIR, "error.log"),
    maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
)
_err_fh.setLevel(logging.WARNING)
_err_fh.setFormatter(_fmt)

# ── console — INFO and above ──────────────────────────────────────────────────
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(_fmt)

# ── named logger ──────────────────────────────────────────────────────────────
logger = logging.getLogger("zylitix")
logger.setLevel(logging.DEBUG)
logger.addHandler(_app_fh)
logger.addHandler(_err_fh)
logger.addHandler(_ch)
logger.propagate = False


def setup_uvicorn_logging():
    """Forward uvicorn access logs into app.log as well."""
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv = logging.getLogger(name)
        uv.addHandler(_app_fh)