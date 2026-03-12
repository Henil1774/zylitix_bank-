"""
routers/dashboard.py
Dashboard endpoints: stats
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import Customer
from routers.dependencies import get_db, require_admin

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
def stats(token: dict = Depends(require_admin), db: Session = Depends(get_db)):
    return {
        "total_customers": db.query(Customer).count(),
        "savings_count":   db.query(Customer).filter(Customer.account_type == "Savings").count(),
        "current_count":   db.query(Customer).filter(Customer.account_type == "Current").count(),
        "business_count":  db.query(Customer).filter(Customer.account_type == "Business").count(),
        "fd_count":        db.query(Customer).filter(Customer.account_type == "Fixed Deposit").count(),
    }