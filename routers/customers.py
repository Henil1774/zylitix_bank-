"""
routers/customers.py

Fixes applied:
  [3] GET /api/customers now has real DB-level pagination (page + per_page)
  [6] Search changed from path param /search/{q} to query param /search?q=
      — fixes crash on special chars like O'Brien, Raj & Sons
  [7] str(e) no longer returned to client in 500 responses — logged server-side only
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import Customer, CustomerAddress, ParentDetails, Nominee, KYCDetails
from validation import validate_api_customer_create, validate_api_customer_update, _clean
from config import Config
from logger import logger
from routers.dependencies import (
    get_db, verify_token, require_admin,
    generate_account_number, build_customer_response,
)

router = APIRouter(prefix="/api/customers", tags=["Customers"])


# ── List with DB pagination ───────────────────────────────────────────────────
@router.get("")
def get_all(
    page:         int = Query(default=1,  ge=1),
    per_page:     int = Query(default=10, ge=1, le=100),
    account_type: str = None,
    city:         str = None,
    token: dict = Depends(require_admin),
    db:    Session = Depends(get_db),
):
    query = db.query(Customer)

    if account_type:
        query = query.filter(Customer.account_type == account_type)
    if city:
        query = query.join(CustomerAddress).filter(
            CustomerAddress.city.ilike(f"%{city}%")
        )

    total       = query.count()                                    # DB count
    total_pages = max(1, (total + per_page - 1) // per_page)
    items       = (
        query.order_by(Customer.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
             .all()
    )

    return {
        "items":    [build_customer_response(c) for c in items],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    total_pages,
    }


# ── Search via query param (safe for special chars) ───────────────────────────
@router.get("/search")
def search(
    q:     str = Query(..., min_length=1, description="Search term"),
    token: dict = Depends(verify_token),
    db:    Session = Depends(get_db),
):
    s  = f"%{q}%"
    cs = db.query(Customer).filter(
        or_(
            Customer.full_name.ilike(s),
            Customer.phone_number.ilike(s),
            Customer.email.ilike(s),
            Customer.account_number.ilike(s),
            Customer.pan_number.ilike(s),
        )
    ).all()
    if not cs:
        raise HTTPException(status_code=404, detail="No customers found")
    return [build_customer_response(c) for c in cs]


# ── Get single customer ───────────────────────────────────────────────────────
@router.get("/{customer_id}")
def get_one(
    customer_id: int,
    token: dict = Depends(verify_token),
    db:    Session = Depends(get_db),
):
    c = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return build_customer_response(c)


# ── Create customer ───────────────────────────────────────────────────────────
@router.post("", status_code=201)
async def create_customer(
    request: Request,
    token:   dict    = Depends(verify_token),
    db:      Session = Depends(get_db),
):
    data = await request.json()
    ok, result = validate_api_customer_create(data)
    if not ok:
        raise HTTPException(status_code=422, detail=result)

    if db.query(Customer).filter(Customer.phone_number == result["phone"]).first():
        raise HTTPException(status_code=409, detail="Phone number already exists")
    if db.query(Customer).filter(Customer.email == result["email"]).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    if db.query(Customer).filter(Customer.aadhaar_number == result["aadhaar"]).first():
        raise HTTPException(status_code=409, detail="Aadhaar number already exists")
    if db.query(Customer).filter(Customer.pan_number == result["pan"]).first():
        raise HTTPException(status_code=409, detail="PAN number already exists")

    try:
        customer = Customer(
            full_name      = result["full_name"],
            dob            = result["dob"],
            gender         = result["gender"],
            phone_number   = result["phone"],
            email          = result["email"],
            aadhaar_number = result["aadhaar"],
            pan_number     = result["pan"],
            account_type   = result["account_type"],
            account_number = generate_account_number(db),
            ifsc_code      = Config.BANK_IFSC,
        )
        db.add(customer)
        db.flush()

        addr = result.get("address") or {}
        db.add(CustomerAddress(
            customer_id  = customer.customer_id,
            flat_no      = addr.get("flat_no"),
            block_number = addr.get("block_number"),
            street       = addr.get("street"),
            city         = addr.get("city"),
            state        = addr.get("state"),
            pincode      = addr.get("pincode"),
        ))

        par = result.get("parent_details") or {}
        db.add(ParentDetails(
            customer_id       = customer.customer_id,
            father_name       = par.get("father_name"),
            father_occupation = par.get("father_occupation"),
            mother_name       = par.get("mother_name"),
            mother_type       = par.get("mother_type"),
        ))

        db.add(KYCDetails(
            customer_id       = customer.customer_id,
            document_verified = False,
            risk_category     = "Low",
        ))

        for n in result.get("nominees", []):
            db.add(Nominee(
                customer_id    = customer.customer_id,
                nominee_name   = n.get("nominee_name"),
                relation       = n.get("relation"),
                phone_number   = n.get("phone_number"),
                email          = n.get("email"),
                aadhaar_number = n.get("aadhaar_number"),
            ))

        db.commit()
        db.refresh(customer)
        logger.info("Customer created | id=%s account=%s by=%s",
                    customer.customer_id, customer.account_number, token.get("email"))
        return build_customer_response(customer)

    except Exception as e:
        db.rollback()
        logger.error("Customer create failed | error=%s", str(e))   # [FIX 7] log, don't expose
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


# ── Update customer ───────────────────────────────────────────────────────────
@router.put("/{customer_id}")
async def update_customer(
    customer_id: int,
    request:     Request,
    token:       dict    = Depends(require_admin),
    db:          Session = Depends(get_db),
):
    data = await request.json()
    ok, result = validate_api_customer_update(data)
    if not ok:
        raise HTTPException(status_code=422, detail=result)

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    if result.get("phone"):
        if db.query(Customer).filter(
            Customer.phone_number == result["phone"],
            Customer.customer_id  != customer_id
        ).first():
            raise HTTPException(status_code=409, detail="Phone already used by another customer")
    if result.get("email"):
        if db.query(Customer).filter(
            Customer.email       == result["email"],
            Customer.customer_id != customer_id
        ).first():
            raise HTTPException(status_code=409, detail="Email already used by another customer")

    try:
        for field in ("full_name", "gender", "email", "account_type"):
            if result.get(field) is not None:
                setattr(customer, field, result[field])
        if result.get("phone"):
            customer.phone_number = result["phone"]

        if result.get("address") and customer.address:
            for k, v in result["address"].items():
                setattr(customer.address, k, v)
        if result.get("parent_details") and customer.parent_details:
            for k, v in result["parent_details"].items():
                setattr(customer.parent_details, k, v)

        db.commit()
        db.refresh(customer)
        logger.info("Customer updated | id=%s by=%s", customer_id, token.get("email"))
        return build_customer_response(customer)

    except Exception as e:
        db.rollback()
        logger.error("Customer update failed | id=%s error=%s", customer_id, str(e))  # [FIX 7]
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


# ── Delete customer ───────────────────────────────────────────────────────────
@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    token: dict    = Depends(require_admin),
    db:    Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    name = customer.full_name
    try:
        db.delete(customer)
        db.commit()
        logger.info("Customer deleted | id=%s name=%s by=%s",
                    customer_id, name, token.get("email"))
        return {"message": "Deleted successfully", "customer_id": customer_id, "customer_name": name}
    except Exception as e:
        db.rollback()
        logger.error("Customer delete failed | id=%s error=%s", customer_id, str(e))  # [FIX 7]
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


# ── KYC update ────────────────────────────────────────────────────────────────
@router.patch("/{customer_id}/kyc")
async def update_kyc(
    customer_id: int,
    request: Request,
    token:   dict    = Depends(require_admin),
    db:      Session = Depends(get_db),
):
    data              = await request.json()
    document_verified = data.get("document_verified")
    risk_category     = _clean(data.get("risk_category", ""))

    if document_verified is None:
        raise HTTPException(status_code=422, detail="document_verified (boolean) is required")
    if not isinstance(document_verified, bool):
        raise HTTPException(status_code=422, detail="document_verified must be true or false")
    if risk_category and risk_category not in ["Low", "Medium", "High"]:
        raise HTTPException(status_code=422, detail="risk_category must be Low, Medium, or High")

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not customer.kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")

    customer.kyc.document_verified = document_verified
    if risk_category:
        customer.kyc.risk_category = risk_category
    db.commit()

    logger.info("KYC updated | customer_id=%s verified=%s risk=%s by=%s",
                customer_id, document_verified, risk_category, token.get("email"))
    return {
        "message":           "KYC updated",
        "customer_id":       customer_id,
        "document_verified": customer.kyc.document_verified,
        "risk_category":     customer.kyc.risk_category,
    }