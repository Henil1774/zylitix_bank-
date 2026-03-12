from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, date
from config import Config

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True)
    full_name  = Column(String(100), nullable=False)
    email      = Column(String(100), unique=True, nullable=False)
    password   = Column(String(256), nullable=False)
    role       = Column(String(10), nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)

    def is_admin(self):
        return self.role == "admin"


class Customer(Base):
    __tablename__ = "customers"

    customer_id    = Column(Integer, primary_key=True)
    full_name      = Column(String(100), nullable=False)
    dob            = Column(Date)
    gender         = Column(String(20))
    phone_number   = Column(String(15), unique=True, nullable=False)
    email          = Column(String(100), unique=True)
    aadhaar_number = Column(String(12), unique=True, nullable=False)
    pan_number     = Column(String(10), unique=True, nullable=False)
    account_type   = Column(String(50), nullable=False)
    account_number = Column(String(20), unique=True, nullable=False)
    ifsc_code      = Column(String(15), default="ZYLI000001")
    created_at     = Column(DateTime, default=datetime.utcnow)

    address        = relationship("CustomerAddress", backref="customer", cascade="all, delete-orphan", uselist=False)
    parent_details = relationship("ParentDetails",   backref="customer", cascade="all, delete-orphan", uselist=False)
    nominees       = relationship("Nominee",         backref="customer", cascade="all, delete-orphan")
    kyc            = relationship("KYCDetails",      backref="customer", cascade="all, delete-orphan", uselist=False)

    @property
    def age(self):
        if not self.dob:
            return None
        today = date.today()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))


class CustomerAddress(Base):
    __tablename__ = "customer_address"

    address_id   = Column(Integer, primary_key=True)
    customer_id  = Column(Integer, ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    flat_no      = Column(String(20))
    block_number = Column(String(20))
    society_name = Column(String(100))
    street       = Column(String(100))
    city         = Column(String(50))
    state        = Column(String(50))
    pincode      = Column(String(6))


class ParentDetails(Base):
    __tablename__ = "parent_details"

    parent_id         = Column(Integer, primary_key=True)
    customer_id       = Column(Integer, ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    father_name       = Column(String(100))
    father_occupation = Column(String(50))
    mother_name       = Column(String(100))
    mother_type       = Column(String(20))


class Nominee(Base):
    __tablename__ = "nominees"

    nominee_id     = Column(Integer, primary_key=True)
    customer_id    = Column(Integer, ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    nominee_name   = Column(String(100), nullable=False)
    relation       = Column(String(50), nullable=False)
    phone_number   = Column(String(15))
    email          = Column(String(100))
    aadhaar_number = Column(String(12))
    flat_no        = Column(String(20))
    block_number   = Column(String(20))
    city           = Column(String(50))
    state          = Column(String(50))
    pincode        = Column(String(6))


class KYCDetails(Base):
    __tablename__ = "kyc_details"

    kyc_id            = Column(Integer, primary_key=True)
    customer_id       = Column(Integer, ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    document_verified = Column(Boolean, default=False)
    risk_category     = Column(String(20), default="Low")