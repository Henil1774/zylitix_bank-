from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import Customer, CustomerAddress, ParentDetails, Nominee, KYCDetails
from validation import validate_api_customer_create, validate_api_customer_update, _clean
from config import Config
from routers.dependencies import get_db, verify_token, require_admin, generate_account_number, build_customer_response

router = APIRouter(prefix="/api/customers", tags=["Customers"])


@router.get("")
def get_all(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, le=100),
    account_type: str = None,
    city: str = None,
    token: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Customer)
    if account_type:
        query = query.filter(Customer.account_type == account_type)
    if city:
        query = query.join(CustomerAddress).filter(CustomerAddress.city.ilike(f"%{city}%"))
    total = query.count()
    items = query.order_by(Customer.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items":    [build_customer_response(c) for c in items],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    (total + per_page - 1) // per_page,
    }


@router.get("/search")
def search(
    q: str = Query(..., min_length=1),
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    s  = f"%{q}%"
    cs = db.query(Customer).filter(or_(
        Customer.full_name.ilike(s),
        Customer.phone_number.ilike(s),
        Customer.email.ilike(s),
        Customer.account_number.ilike(s),
        Customer.pan_number.ilike(s),
    )).all()
    if not cs:
        raise HTTPException(status_code=404, detail="No customers found")
    return [build_customer_response(c) for c in cs]


@router.get("/{customer_id}")
def get_one(customer_id: int, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return build_customer_response(c)


@router.post("", status_code=201)
async def create_customer(request: Request, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    data = await request.json()
    ok, result = validate_api_customer_create(data)
    if not ok:
        raise HTTPException(status_code=422, detail=result)

    for field, col in [("phone", Customer.phone_number), ("email", Customer.email),
                       ("aadhaar", Customer.aadhaar_number), ("pan", Customer.pan_number)]:
        if db.query(Customer).filter(col == result[field]).first():
            raise HTTPException(status_code=409, detail=f"{field.capitalize()} already exists")

    try:
        customer = Customer(
            full_name=result["full_name"], dob=result["dob"], gender=result["gender"],
            phone_number=result["phone"], email=result["email"],
            aadhaar_number=result["aadhaar"], pan_number=result["pan"],
            account_type=result["account_type"],
            account_number=generate_account_number(db),
            ifsc_code=Config.BANK_IFSC,
        )
        db.add(customer)
        db.flush()

        addr = result.get("address") or {}
        db.add(CustomerAddress(customer_id=customer.customer_id, **addr))

        par = result.get("parent_details") or {}
        db.add(ParentDetails(customer_id=customer.customer_id, **par))

        db.add(KYCDetails(customer_id=customer.customer_id, document_verified=False, risk_category="Low"))

        for n in result.get("nominees", []):
            db.add(Nominee(customer_id=customer.customer_id, **n))

        db.commit()
        db.refresh(customer)
        return build_customer_response(customer)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.put("/{customer_id}")
async def update_customer(customer_id: int, request: Request,
                          token: dict = Depends(require_admin), db: Session = Depends(get_db)):
    data = await request.json()
    ok, result = validate_api_customer_update(data)
    if not ok:
        raise HTTPException(status_code=422, detail=result)

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    for field, col in [("phone", Customer.phone_number), ("email", Customer.email)]:
        if result.get(field) and db.query(Customer).filter(
            col == result[field], Customer.customer_id != customer_id
        ).first():
            raise HTTPException(status_code=409, detail=f"{field.capitalize()} already used by another customer")

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
        return build_customer_response(customer)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, token: dict = Depends(require_admin), db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    name = customer.full_name
    try:
        db.delete(customer)
        db.commit()
        return {"message": "Deleted successfully", "customer_id": customer_id, "customer_name": name}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.patch("/{customer_id}/kyc")
async def update_kyc(customer_id: int, request: Request,
                     token: dict = Depends(require_admin), db: Session = Depends(get_db)):
    data              = await request.json()
    document_verified = data.get("document_verified")
    risk_category     = _clean(data.get("risk_category", ""))

    if document_verified is None or not isinstance(document_verified, bool):
        raise HTTPException(status_code=422, detail="document_verified must be true or false")
    if risk_category and risk_category not in ("Low", "Medium", "High"):
        raise HTTPException(status_code=422, detail="risk_category must be Low, Medium, or High")

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer or not customer.kyc:
        raise HTTPException(status_code=404, detail="Customer or KYC record not found")

    customer.kyc.document_verified = document_verified
    if risk_category:
        customer.kyc.risk_category = risk_category
    db.commit()
    return {"message": "KYC updated", "customer_id": customer_id,
            "document_verified": customer.kyc.document_verified,
            "risk_category": customer.kyc.risk_category}