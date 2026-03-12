from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from config import Config
from database import Customer
import jwt

engine       = create_engine(Config.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

JWT_SECRET    = Config.SECRET_KEY
JWT_ALGORITHM = "HS256"
security      = HTTPBearer()
token_blacklist: set = set()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_token(user_id: int, email: str, role: str) -> str:
    payload = {"user_id": user_id, "email": email, "role": role,
               "exp": datetime.utcnow() + timedelta(hours=24)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    raw = credentials.credentials
    if raw in token_blacklist:
        raise HTTPException(status_code=401, detail="Token has been invalidated. Please login again.")
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


def generate_account_number(db: Session) -> str:
    prefix = Config.ACCOUNT_PREFIX
    start  = Config.ACCOUNT_START_NUMBER
    try:
        db.execute(text("SELECT GET_LOCK('account_number_gen', 5)"))
    except Exception:
        pass
    try:
        last = db.query(Customer).order_by(Customer.customer_id.desc()).first()
        if last and last.account_number:
            try:
                new_num = int(last.account_number.replace(prefix, "")) + 1
            except ValueError:
                new_num = start
        else:
            new_num = start
        return f"{prefix}{new_num}"
    finally:
        try:
            db.execute(text("SELECT RELEASE_LOCK('account_number_gen')"))
        except Exception:
            pass


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
        "address": {k: getattr(c.address, k) for k in
                    ("flat_no", "block_number", "street", "city", "state", "pincode")
                    } if c.address else None,
        "parent_details": {k: getattr(c.parent_details, k) for k in
                           ("father_name", "father_occupation", "mother_name", "mother_type")
                           } if c.parent_details else None,
        "nominees": [{"nominee_name": n.nominee_name, "relation": n.relation,
                      "phone_number": n.phone_number, "email": n.email,
                      "aadhaar_number": n.aadhaar_number, "city": n.city,
                      "state": n.state, "pincode": n.pincode}
                     for n in c.nominees],
        "kyc": {"document_verified": c.kyc.document_verified,
                "risk_category": c.kyc.risk_category} if c.kyc else None,
    }