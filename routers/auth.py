from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash, check_password_hash
from database import User
from validation import validate_api_register, validate_api_login
from routers.dependencies import get_db, create_token, verify_token, token_blacklist

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", status_code=201)
async def register(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    ok, result = validate_api_register(data)
    if not ok:
        raise HTTPException(status_code=422, detail=result)
    if db.query(User).filter(User.email == result["email"]).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(full_name=result["full_name"], email=result["email"],
                password=generate_password_hash(result["password"]), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Registered successfully.", "user_id": user.id,
            "full_name": user.full_name, "email": user.email, "role": user.role}


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    ok, result = validate_api_login(data)
    if not ok:
        raise HTTPException(status_code=422, detail=result)
    user = db.query(User).filter(User.email == result["email"]).first()
    if not user or not check_password_hash(user.password, result["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"message": "Login successful!", "token": create_token(user.id, user.email, user.role),
            "user_id": user.id, "full_name": user.full_name, "email": user.email,
            "role": user.role, "expires_in": "24 hours"}


@router.post("/logout")
def logout(token: dict = Depends(verify_token), request: Request = None):
    raw = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if raw:
        token_blacklist.add(raw)
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == token["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.id, "full_name": user.full_name, "email": user.email,
            "role": user.role, "created_at": str(user.created_at)}