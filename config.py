"""
Configuration file for Zylitix Bank Application
Loads all sensitive values from .env file
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_change_me")
    DEBUG      = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    DB_USER     = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = os.getenv("DB_PORT", "3306")
    DB_NAME     = os.getenv("DB_NAME", "zylitix_bank")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BANK_NAME   = os.getenv("BANK_NAME",   "Zylitix Bank")
    BANK_IFSC   = os.getenv("BANK_IFSC",   "ZYLI000001")
    BANK_BRANCH = os.getenv("BANK_BRANCH", "Main Branch, Ahmedabad")

    ACCOUNT_PREFIX       = os.getenv("ACCOUNT_PREFIX", "ZYL")
    ACCOUNT_START_NUMBER = int(os.getenv("ACCOUNT_START_NUMBER", 1000001))

    ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL",    "admin@zylitix.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMe@123")

    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE   = False  