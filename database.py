from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy import text

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    full_name  = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(100), unique=True, nullable=False)
    password   = db.Column(db.String(256), nullable=False)
    role       = db.Column(db.String(10), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Customer(db.Model):
    __tablename__ = 'customers'

    customer_id    = db.Column(db.Integer, primary_key=True)
    full_name      = db.Column(db.String(100), nullable=False)
    dob            = db.Column(db.Date, nullable=True)

    gender         = db.Column(db.String(20))
    phone_number   = db.Column(db.String(15), unique=True, nullable=False)
    email          = db.Column(db.String(100), unique=True)
    aadhaar_number = db.Column(db.String(12), unique=True, nullable=False)
    pan_number     = db.Column(db.String(10), unique=True, nullable=False)
    account_type   = db.Column(db.String(50), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    ifsc_code      = db.Column(db.String(15), default='ZYLI000001')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    address        = db.relationship('CustomerAddress', backref='customer', cascade='all, delete-orphan', uselist=False)
    parent_details = db.relationship('ParentDetails',   backref='customer', cascade='all, delete-orphan', uselist=False)
    nominees       = db.relationship('Nominee',         backref='customer', cascade='all, delete-orphan')
    kyc            = db.relationship('KYCDetails',      backref='customer', cascade='all, delete-orphan', uselist=False)

    @property
    def age(self):
        """
        Computed from dob at runtime — always accurate, never stale.
        MySQL disallows CURDATE() in generated columns, so this
        @property is the correct approach for Python/Flask usage.
        For raw SQL queries, use the 'customers_with_age' view instead.
        """
        if not self.dob:
            return None
        today = date.today()
        return today.year - self.dob.year - (
            (today.month, today.day) < (self.dob.month, self.dob.day)
        )

    @staticmethod
    def generate_account_number():
        """
        Race-condition-safe account number generation using a MySQL advisory
        lock (GET_LOCK). Prevents two concurrent requests from reading the same
        last record before either commits.
        Falls back gracefully in non-MySQL environments (e.g. tests).
        """
        from config import Config

        try:
            db.session.execute(text("SELECT GET_LOCK('account_number_gen', 5)"))
        except Exception:
            pass 

        try:
            last   = Customer.query.order_by(Customer.customer_id.desc()).first()
            prefix = Config.ACCOUNT_PREFIX
            start  = Config.ACCOUNT_START_NUMBER

            if last and last.account_number:
                try:
                    new_num = int(last.account_number.replace(prefix, '')) + 1
                except ValueError:
                    new_num = start
            else:
                new_num = start

            return f'{prefix}{new_num}'
        finally:
            try:
                db.session.execute(text("SELECT RELEASE_LOCK('account_number_gen')"))
            except Exception:
                pass

    def __repr__(self):
        return f'<Customer {self.full_name} - {self.account_number}>'


class CustomerAddress(db.Model):
    __tablename__ = 'customer_address'
    address_id   = db.Column(db.Integer, primary_key=True)
    customer_id  = db.Column(db.Integer, db.ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    flat_no      = db.Column(db.String(20))
    block_number = db.Column(db.String(20))
    society_name = db.Column(db.String(100))
    street       = db.Column(db.String(100))
    city         = db.Column(db.String(50))
    state        = db.Column(db.String(50))
    pincode      = db.Column(db.String(6))


class ParentDetails(db.Model):
    __tablename__     = 'parent_details'
    parent_id         = db.Column(db.Integer, primary_key=True)
    customer_id       = db.Column(db.Integer, db.ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    father_name       = db.Column(db.String(100))
    father_occupation = db.Column(db.String(50))
    mother_name       = db.Column(db.String(100))
    mother_type       = db.Column(db.String(20))


class Nominee(db.Model):
    __tablename__  = 'nominees'
    nominee_id     = db.Column(db.Integer, primary_key=True)
    customer_id    = db.Column(db.Integer, db.ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    nominee_name   = db.Column(db.String(100), nullable=False)
    relation       = db.Column(db.String(50), nullable=False)
    phone_number   = db.Column(db.String(15))
    email          = db.Column(db.String(100))
    aadhaar_number = db.Column(db.String(12))
    flat_no        = db.Column(db.String(20))
    block_number   = db.Column(db.String(20))
    city           = db.Column(db.String(50))
    state          = db.Column(db.String(50))
    pincode        = db.Column(db.String(6))

class KYCDetails(db.Model):
    __tablename__     = 'kyc_details'
    kyc_id            = db.Column(db.Integer, primary_key=True)
    customer_id       = db.Column(db.Integer, db.ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False)
    document_verified = db.Column(db.Boolean, default=False)
    risk_category     = db.Column(db.String(20), default='Low')