"""
validation.py — Pydantic v2 models for Zylitix Bank
All form and API validation is handled via Pydantic schemas.
Flask views call the helper functions at the bottom which wrap
Pydantic's ValidationError into the (bool, result) tuple that
app.py already expects — so app.py requires zero changes.
"""

import re
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

# ─────────────────────────────────────────────
#  Shared helpers
# ─────────────────────────────────────────────

ACCOUNT_TYPES = Literal["Savings", "Current", "Business", "Fixed Deposit"]
GENDERS       = Literal["Male", "Female", "Other", ""]
RISK_CATS     = Literal["Low", "Medium", "High"]
MOTHER_TYPES  = Literal["Housewife", "Working", "Retired", ""]

NAME_RE = re.compile(r"^[A-Za-z\s.\-']+$")
PAN_RE  = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _clean(value):
    return str(value).strip() if value is not None else ""


def _validate_phone_str(v: str) -> str:
    v = _clean(v)
    if not v.isdigit():
        raise ValueError("Phone number must contain digits only")
    if len(v) != 10:
        raise ValueError("Phone number must be exactly 10 digits")
    if v[0] not in "6789":
        raise ValueError("Phone number must start with 6, 7, 8, or 9")
    return v


def _validate_aadhaar_str(v: str) -> str:
    v = _clean(v)
    if not v.isdigit():
        raise ValueError("Aadhaar number must contain digits only")
    if len(v) != 12:
        raise ValueError("Aadhaar number must be exactly 12 digits")
    return v


def _validate_pan_str(v: str) -> str:
    v = _clean(v).upper()
    if len(v) != 10:
        raise ValueError("PAN number must be exactly 10 characters")
    if not PAN_RE.match(v):
        raise ValueError("PAN format is invalid. Expected: ABCDE1234F")
    return v


def _validate_dob_str(v: str) -> date:
    v = _clean(v)
    if not v:
        raise ValueError("Date of birth is required")
    try:
        dob = datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid date format. Expected YYYY-MM-DD")
    today = date.today()
    if dob >= today:
        raise ValueError("Date of birth must be in the past")
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18:
        raise ValueError(f"Customer must be at least 18 years old (current age: {age})")
    if age > 120:
        raise ValueError("Please enter a valid date of birth")
    return dob


def _validate_pincode_str(v) -> Optional[str]:
    v = _clean(v) if v else ""
    if not v:
        return None
    if not v.isdigit():
        raise ValueError("Pincode must contain digits only")
    if len(v) != 6:
        raise ValueError("Pincode must be exactly 6 digits")
    return v


def _first_error(exc) -> str:
    errors = exc.errors()
    if errors:
        return errors[0]["msg"].removeprefix("Value error, ")
    return "Validation error"


# ─────────────────────────────────────────────
#  Pydantic Models
# ─────────────────────────────────────────────

class UserRegistrationSchema(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email:     EmailStr
    password:  str = Field(min_length=6, max_length=50)

    @field_validator("full_name")
    @classmethod
    def name_chars(cls, v):
        v = _clean(v)
        if not NAME_RE.match(v):
            raise ValueError("Full name can only contain letters, spaces, dots, hyphens and apostrophes")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):
        return _clean(str(v)).lower()


class NomineeSchema(BaseModel):
    nominee_name:   str = Field(min_length=1, max_length=100)
    relation:       str = Field(min_length=1, max_length=50)
    aadhaar_number: str
    phone_number:   Optional[str] = None
    email:          Optional[EmailStr] = None
    flat_no:        Optional[str] = None
    block_number:   Optional[str] = None
    city:           Optional[str] = None
    state:          Optional[str] = None
    pincode:        Optional[str] = None

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar(cls, v):
        return _validate_aadhaar_str(v)

    @field_validator("phone_number", mode="before")
    @classmethod
    def validate_phone(cls, v):
        v = _clean(v) if v else ""
        return _validate_phone_str(v) if v else None

    @field_validator("pincode", mode="before")
    @classmethod
    def validate_pincode(cls, v):
        return _validate_pincode_str(v)

    @field_validator("email", mode="before")
    @classmethod
    def optional_email(cls, v):
        v = _clean(v) if v else ""
        return v.lower() if v else None


class CustomerCreateSchema(BaseModel):
    full_name:    str = Field(min_length=2, max_length=100)
    dob:          str
    gender:       GENDERS = ""
    email:        EmailStr
    phone:        str
    account_type: ACCOUNT_TYPES
    aadhaar:      str
    pan:          str
    flat_no:      Optional[str] = None
    block_number: Optional[str] = None
    society_name: Optional[str] = None
    street:       Optional[str] = None
    city:         Optional[str] = None
    state:        Optional[str] = None
    pincode:      Optional[str] = None
    father_name:        Optional[str] = None
    father_occupation:  Optional[str] = None
    mother_name:        Optional[str] = None
    mother_type:        MOTHER_TYPES = ""
    nominees:     list[NomineeSchema] = Field(default_factory=list)
    dob_date:     Optional[date] = None
    age:          Optional[int]  = None

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("full_name")
    @classmethod
    def name_chars(cls, v):
        v = _clean(v)
        if not NAME_RE.match(v):
            raise ValueError("Full name can only contain letters, spaces, dots, hyphens and apostrophes")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):
        return _clean(str(v)).lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        return _validate_phone_str(v)

    @field_validator("aadhaar")
    @classmethod
    def validate_aadhaar(cls, v):
        return _validate_aadhaar_str(v)

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, v):
        return _validate_pan_str(v)

    @field_validator("pincode", mode="before")
    @classmethod
    def validate_pincode(cls, v):
        return _validate_pincode_str(v)

    @field_validator("nominees", mode="before")
    @classmethod
    def limit_nominees(cls, v):
        return (v or [])[:3]

    @model_validator(mode="after")
    def compute_dob_and_age(self):
        dob = _validate_dob_str(self.dob)
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        self.dob_date = dob
        self.age      = age
        return self


class CustomerEditSchema(BaseModel):
    full_name:    str = Field(min_length=2, max_length=100)
    gender:       GENDERS = ""
    email:        EmailStr
    phone:        str
    account_type: ACCOUNT_TYPES
    flat_no:      Optional[str] = None
    block_number: Optional[str] = None
    society_name: Optional[str] = None
    street:       Optional[str] = None
    city:         Optional[str] = None
    state:        Optional[str] = None
    pincode:      Optional[str] = None
    father_name:       Optional[str] = None
    father_occupation: Optional[str] = None
    mother_name:       Optional[str] = None
    mother_type:       MOTHER_TYPES = ""
    document_verified: bool = False
    risk_category:     RISK_CATS = "Low"

    @field_validator("full_name")
    @classmethod
    def name_chars(cls, v):
        v = _clean(v)
        if not NAME_RE.match(v):
            raise ValueError("Full name can only contain letters, spaces, dots, hyphens and apostrophes")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):
        return _clean(str(v)).lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        return _validate_phone_str(v)

    @field_validator("pincode", mode="before")
    @classmethod
    def validate_pincode(cls, v):
        return _validate_pincode_str(v)

    @field_validator("document_verified", mode="before")
    @classmethod
    def coerce_verified(cls, v):
        return v == "1" or v is True


class ApiLoginSchema(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):
        return _clean(str(v)).lower()


class ApiNomineeSchema(BaseModel):
    nominee_name:   str = Field(min_length=1, max_length=100)
    relation:       str = Field(min_length=1, max_length=50)
    aadhaar_number: Optional[str] = None
    phone_number:   Optional[str] = None
    email:          Optional[EmailStr] = None

    @field_validator("phone_number", mode="before")
    @classmethod
    def validate_phone(cls, v):
        v = _clean(v) if v else ""
        return _validate_phone_str(v) if v else None

    @field_validator("email", mode="before")
    @classmethod
    def optional_email(cls, v):
        v = _clean(v) if v else ""
        return v.lower() if v else None


class ApiCustomerCreateSchema(BaseModel):
    full_name:    str = Field(min_length=2, max_length=100)
    dob:          str
    gender:       GENDERS = ""
    email:        EmailStr
    phone:        str
    account_type: ACCOUNT_TYPES
    aadhaar:      str
    pan:          str
    address:      Optional[dict] = None
    parent_details: Optional[dict] = None
    nominees:     list[ApiNomineeSchema] = Field(default_factory=list)
    dob_date:     Optional[date] = None
    age:          Optional[int]  = None

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("full_name")
    @classmethod
    def name_chars(cls, v):
        v = _clean(v)
        if not NAME_RE.match(v):
            raise ValueError("Full name can only contain letters, spaces, dots, hyphens and apostrophes")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):
        return _clean(str(v)).lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        return _validate_phone_str(v)

    @field_validator("aadhaar")
    @classmethod
    def validate_aadhaar(cls, v):
        return _validate_aadhaar_str(v)

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, v):
        return _validate_pan_str(v)

    @field_validator("nominees", mode="before")
    @classmethod
    def limit_nominees(cls, v):
        return (v or [])[:3]

    @model_validator(mode="after")
    def compute_dob_and_age(self):
        dob = _validate_dob_str(self.dob)
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        self.dob_date = dob
        self.age      = age
        return self


class ApiCustomerUpdateSchema(BaseModel):
    full_name:    Optional[str] = None
    gender:       Optional[GENDERS] = None
    email:        Optional[EmailStr] = None
    phone:        Optional[str] = None
    account_type: Optional[ACCOUNT_TYPES] = None
    address:      Optional[dict] = None
    parent_details: Optional[dict] = None

    @field_validator("full_name")
    @classmethod
    def name_chars(cls, v):
        if v is None:
            return v
        v = _clean(v)
        if not NAME_RE.match(v):
            raise ValueError("Full name can only contain letters, spaces, dots, hyphens and apostrophes")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):
        return _clean(str(v)).lower() if v else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        return _validate_phone_str(v) if v else None


# ─────────────────────────────────────────────
#  Flask-compatible wrapper functions
#  app.py calls these — no changes needed there
# ─────────────────────────────────────────────

def validate_email(email: str):
    """Quick email check used by the login route."""
    email = _clean(email)
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Please enter a valid email address (e.g. name@example.com)"
    return True, None


def validate_user_registration(form):
    try:
        data = UserRegistrationSchema(
            full_name=form.get("full_name", ""),
            email=form.get("email", ""),
            password=form.get("password", ""),
        )
        return True, {"full_name": data.full_name, "email": data.email, "password": data.password}
    except Exception as exc:
        return False, _first_error(exc)


def validate_customer_form(form):
    add_nominees = _clean(form.get("add_nominees")) == "yes"
    nominees = []
    if add_nominees:
        for i in range(1, 4):
            name     = _clean(form.get(f"nominee_name_{i}", ""))
            relation = _clean(form.get(f"nominee_relation_{i}", ""))
            aadhaar  = _clean(form.get(f"nominee_aadhaar_{i}", ""))
            if not name and not relation and not aadhaar:
                continue
            nominees.append({
                "nominee_name":   name,
                "relation":       relation,
                "aadhaar_number": aadhaar,
                "phone_number":   _clean(form.get(f"nominee_phone_{i}", "")) or None,
                "email":          _clean(form.get(f"nominee_email_{i}", "")) or None,
                "flat_no":        _clean(form.get(f"nominee_flat_{i}", "")) or None,
                "block_number":   _clean(form.get(f"nominee_block_{i}", "")) or None,
                "city":           _clean(form.get(f"nominee_city_{i}", "")) or None,
                "state":          _clean(form.get(f"nominee_state_{i}", "")) or None,
                "pincode":        _clean(form.get(f"nominee_pincode_{i}", "")) or None,
            })
    try:
        data = CustomerCreateSchema(
            full_name    = form.get("full_name", ""),
            dob          = form.get("dob", ""),
            gender       = form.get("gender", "") or "",
            email        = form.get("email", ""),
            phone        = form.get("phone", ""),
            account_type = form.get("account_type", ""),
            aadhaar      = form.get("aadhaar", ""),
            pan          = form.get("pan", ""),
            flat_no      = form.get("flat_no") or None,
            block_number = form.get("block_number") or None,
            society_name = form.get("society_name") or None,
            street       = form.get("street") or None,
            city         = form.get("city") or None,
            state        = form.get("state") or None,
            pincode      = form.get("pincode") or None,
            father_name       = form.get("father_name") or None,
            father_occupation = form.get("father_occupation") or None,
            mother_name       = form.get("mother_name") or None,
            mother_type       = form.get("mother_type") or "",
            nominees     = nominees,
        )
        return True, {
            "full_name":         data.full_name,
            "dob":               data.dob_date,
            "age":               data.age,
            "gender":            data.gender or None,
            "email":             data.email,
            "phone":             data.phone,
            "account_type":      data.account_type,
            "aadhaar":           data.aadhaar,
            "pan":               data.pan,
            "flat_no":           data.flat_no,
            "block_number":      data.block_number,
            "society_name":      data.society_name,
            "street":            data.street,
            "city":              data.city,
            "state":             data.state,
            "pincode":           data.pincode,
            "father_name":       data.father_name,
            "father_occupation": data.father_occupation,
            "mother_name":       data.mother_name,
            "mother_type":       data.mother_type or None,
            "nominees": [
                {
                    "nominee_name":   n.nominee_name,
                    "relation":       n.relation,
                    "aadhaar_number": n.aadhaar_number,
                    "phone_number":   n.phone_number,
                    "email":          str(n.email) if n.email else None,
                    "flat_no":        n.flat_no,
                    "block_number":   n.block_number,
                    "city":           n.city,
                    "state":          n.state,
                    "pincode":        n.pincode,
                }
                for n in data.nominees
            ],
        }
    except Exception as exc:
        return False, _first_error(exc)


def validate_edit_customer_form(form):
    try:
        data = CustomerEditSchema(
            full_name    = form.get("full_name", ""),
            gender       = form.get("gender", "") or "",
            email        = form.get("email", ""),
            phone        = form.get("phone", ""),
            account_type = form.get("account_type", ""),
            flat_no      = form.get("flat_no") or None,
            block_number = form.get("block_number") or None,
            society_name = form.get("society_name") or None,
            street       = form.get("street") or None,
            city         = form.get("city") or None,
            state        = form.get("state") or None,
            pincode      = form.get("pincode") or None,
            father_name       = form.get("father_name") or None,
            father_occupation = form.get("father_occupation") or None,
            mother_name       = form.get("mother_name") or None,
            mother_type       = form.get("mother_type") or "",
            document_verified = form.get("document_verified"),
            risk_category     = form.get("risk_category") or "Low",
        )
        return True, {
            "full_name":         data.full_name,
            "gender":            data.gender or None,
            "email":             data.email,
            "phone":             data.phone,
            "account_type":      data.account_type,
            "flat_no":           data.flat_no,
            "block_number":      data.block_number,
            "society_name":      data.society_name,
            "street":            data.street,
            "city":              data.city,
            "state":             data.state,
            "pincode":           data.pincode,
            "father_name":       data.father_name,
            "father_occupation": data.father_occupation,
            "mother_name":       data.mother_name,
            "mother_type":       data.mother_type or None,
            "document_verified": data.document_verified,
            "risk_category":     data.risk_category,
        }
    except Exception as exc:
        return False, _first_error(exc)


# ── API wrappers ──────────────────────────────

def validate_api_register(data: dict):
    try:
        m = UserRegistrationSchema(**data)
        return True, {"full_name": m.full_name, "email": m.email, "password": m.password}
    except Exception as exc:
        return False, [e["msg"].removeprefix("Value error, ") for e in exc.errors()]


def validate_api_login(data: dict):
    try:
        m = ApiLoginSchema(**data)
        return True, {"email": m.email, "password": m.password}
    except Exception as exc:
        return False, [e["msg"].removeprefix("Value error, ") for e in exc.errors()]


def validate_api_customer_create(data: dict):
    try:
        m = ApiCustomerCreateSchema(**data)
        return True, {
            "full_name":      m.full_name,
            "dob":            m.dob_date,
            "age":            m.age,
            "gender":         m.gender or None,
            "email":          m.email,
            "phone":          m.phone,
            "account_type":   m.account_type,
            "aadhaar":        m.aadhaar,
            "pan":            m.pan,
            "address":        m.address,
            "parent_details": m.parent_details,
            "nominees":       [n.model_dump() for n in m.nominees],
        }
    except Exception as exc:
        return False, [e["msg"].removeprefix("Value error, ") for e in exc.errors()]


def validate_api_customer_update(data: dict):
    try:
        m = ApiCustomerUpdateSchema(**data)
        cleaned = {}
        if m.full_name      is not None: cleaned["full_name"]      = m.full_name
        if m.gender         is not None: cleaned["gender"]         = m.gender or None
        if m.email          is not None: cleaned["email"]          = m.email
        if m.phone          is not None: cleaned["phone"]          = m.phone
        if m.account_type   is not None: cleaned["account_type"]   = m.account_type
        if m.address        is not None: cleaned["address"]        = m.address
        if m.parent_details is not None: cleaned["parent_details"] = m.parent_details
        return True, cleaned
    except Exception as exc:
        return False, [e["msg"].removeprefix("Value error, ") for e in exc.errors()]