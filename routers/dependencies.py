"""
routers/dependencies.py

Fixes applied:
  [4] token_blacklist set — logout adds token here, verify_token checks it
  [5] generate_account_number removed — now imported from database.py (single source)
"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from config import Config
from database import Customer                                   # [FIX 5] single source
import jwt

engine       = create_engine(Config.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

JWT_SECRET       = Config.SECRET_KEY
JWT_ALGORITHM    = "HS256"
JWT_EXPIRE_HOURS = 24
security         = HTTPBearer()

# ── Token blacklist (in-memory) ───────────────────────────────────────────────
# For multi-process/multi-server deployments, replace with Redis:
#   import redis; r = redis.Redis(); r.setex(token, 86400, "blacklisted")
token_blacklist: set = set()                                    # [FIX 4]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_token(user_id: int, email: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "email":   email,
        "role":    role,
        "exp":     datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    raw = credentials.credentials

    # [FIX 4] Reject blacklisted tokens (logged-out users)
    if raw in token_blacklist:
        raise HTTPException(status_code=401, detail="Token has been revoked. Please login again.")

    try:
        return jwt.decode(raw, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


def require_admin(token: dict = Depends(verify_token)) -> dict:
    if token.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return token


# ── [FIX 5] Delegate to Customer model — no more duplicate logic ──────────────
def generate_account_number(db: Session) -> str:
    return Customer.generate_account_number()


def build_customer_response(c: Customer) -> dict:
    return {
        "customer_id":    c.customer_id,
        "full_name":      c.full_name,
        "age":            c.age,
        "dob":            str(c.dob) if c.dob else None,
        "gender":         c.gender,
        "phone_number":   c.phone_number,
        "email":          c.email,
        "aadhaar_number": c.aadhaar_number,
        "pan_number":     c.pan_number,
        "account_type":   c.account_type,
        "account_number": c.account_number,
        "ifsc_code":      c.ifsc_code,
        "created_at":     str(c.created_at),
        "address": {
            "flat_no":      c.address.flat_no,
            "block_number": c.address.block_number,
            "street":       c.address.street,
            "city":         c.address.city,
            "state":        c.address.state,
            "pincode":      c.address.pincode,
        } if c.address else None,
        "parent_details": {
            "father_name":       c.parent_details.father_name,
            "father_occupation": c.parent_details.father_occupation,
            "mother_name":       c.parent_details.mother_name,
            "mother_type":       c.parent_details.mother_type,
        } if c.parent_details else None,
        "nominees": [{
            "nominee_name":   n.nominee_name,
            "relation":       n.relation,
            "phone_number":   n.phone_number,
            "email":          n.email,
            "aadhaar_number": n.aadhaar_number,
            "city":           n.city,
            "state":          n.state,
            "pincode":        n.pincode,
        } for n in c.nominees],
        "kyc": {
            "document_verified": c.kyc.document_verified,
            "risk_category":     c.kyc.risk_category,
        } if c.kyc else None,
    }