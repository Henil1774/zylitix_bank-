"""
routers/users.py
User management endpoints: list, delete (admin only)
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import User
from config import Config
from routers.dependencies import get_db, require_admin

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("")
def get_users(token: dict = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id":         u.id,
            "full_name":  u.full_name,
            "email":      u.email,
            "role":       u.role,
            "created_at": str(u.created_at),
        }
        for u in users
    ]

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    token: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email == Config.ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Cannot delete the main admin account!")
    name = user.full_name
    try:
        db.delete(user)
        db.commit()
        return {"message": f"User '{name}' deleted successfully.", "user_id": user_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))