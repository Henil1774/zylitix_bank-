"""
routers/auth.py
Auth endpoints: register, login, me

Changes vs original:
  • Rate limiting on /login  → 5 attempts / minute per IP  (slowapi)
  • Structured logging on every auth event                  (logger)
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash, check_password_hash

from database import User
from validation import validate_api_register, validate_api_login
from routers.dependencies import get_db, create_token, verify_token, token_blacklist
from logger import logger

# ── rate limiter (add to api.py: app.state.limiter = limiter) ────────────────
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ── Register ──────────────────────────────────────────────────────────────────
@router.post("/register", status_code=201)
async def register(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    ok, result = validate_api_register(data)
    if not ok:
        logger.warning("Register validation failed | errors=%s", result)
        raise HTTPException(status_code=422, detail=result)

    if db.query(User).filter(User.email == result["email"]).first():
        logger.warning("Register duplicate email | email=%s", result["email"])
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        full_name=result["full_name"],
        email=result["email"],
        password=generate_password_hash(result["password"]),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("New user registered | id=%s email=%s", user.id, user.email)
    return {
        "message":   "Registered successfully. Please login.",
        "user_id":   user.id,
        "full_name": user.full_name,
        "email":     user.email,
        "role":      user.role,
    }


# ── Login  (rate-limited: 5 req/min per IP) ───────────────────────────────────
@router.post("/login")
@limiter.limit("5/minute")                     # ← rate limit: core 1-liner
async def login(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    ok, result = validate_api_login(data)
    if not ok:
        logger.warning("Login validation failed | ip=%s errors=%s",
                       request.client.host, result)
        raise HTTPException(status_code=422, detail=result)

    user = db.query(User).filter(User.email == result["email"]).first()
    if not user or not check_password_hash(user.password, result["password"]):
        logger.warning("Failed login attempt | ip=%s email=%s",
                       request.client.host, result["email"])
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user.id, user.email, user.role)
    logger.info("Login success | id=%s email=%s role=%s ip=%s",
                user.id, user.email, user.role, request.client.host)
    return {
        "message":    "Login successful!",
        "token":      token,
        "user_id":    user.id,
        "full_name":  user.full_name,
        "email":      user.email,
        "role":       user.role,
        "expires_in": "24 hours",
    }


# ── Me ────────────────────────────────────────────────────────────────────────
@router.get("/me")
def get_me(token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == token["user_id"]).first()
    if not user:
        logger.warning("GET /me — user not found | user_id=%s", token["user_id"])
        raise HTTPException(status_code=404, detail="User not found")

    logger.debug("GET /me | user_id=%s email=%s", user.id, user.email)
    return {
        "user_id":    user.id,
        "full_name":  user.full_name,
        "email":      user.email,
        "role":       user.role,
        "created_at": str(user.created_at),
    }


# ── Logout — blacklists the token so it cannot be reused ─────────────────────
@router.post("/logout")
def logout(
    request: Request,
    token:   dict = Depends(verify_token),
):
    raw_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    token_blacklist.add(raw_token)                          # [FIX 4] invalidate token
    logger.info("Logout | user_id=%s email=%s ip=%s",
                token.get("user_id"), token.get("email"), request.client.host)
    return {"message": "Logged out successfully."}