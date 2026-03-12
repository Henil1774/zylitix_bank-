"""
tests/test_validation.py — Unit tests for Zylitix Bank validation layer

Run with:
    pytest tests/test_validation.py -v

These tests import validation.py directly — no Flask/FastAPI server needed.
"""

import pytest
import sys
import os

# Allow import from project root (file sits in root, same level as validation.py)
sys.path.insert(0, os.path.dirname(__file__))

from validation import (
    validate_api_register,
    validate_api_login,
    validate_api_customer_create,
    _validate_phone_str,
    _validate_pan_str,
    _validate_aadhaar_str,
    _validate_dob_str,
    _validate_pincode_str,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _valid_customer_payload(**overrides):
    """Return a minimal valid customer dict, with any field overrideable."""
    base = {
        "full_name":    "Raj Sharma",
        "dob":          "1995-06-15",
        "gender":       "Male",
        "email":        "raj@example.com",
        "phone":        "9876543210",
        "account_type": "Savings",
        "aadhaar":      "123456789012",
        "pan":          "ABCDE1234F",
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
#  Test 1 — Phone number validation
# ─────────────────────────────────────────────────────────────────────────────

class TestPhoneValidation:
    def test_valid_phone(self):
        assert _validate_phone_str("9876543210") == "9876543210"

    def test_phone_must_be_10_digits(self):
        with pytest.raises(ValueError, match="10 digits"):
            _validate_phone_str("98765")

    def test_phone_must_start_with_6789(self):
        with pytest.raises(ValueError, match="start with"):
            _validate_phone_str("1234567890")

    def test_phone_no_letters(self):
        with pytest.raises(ValueError, match="digits only"):
            _validate_phone_str("98765abcde")

    def test_phone_strips_whitespace(self):
        assert _validate_phone_str("  9876543210  ") == "9876543210"


# ─────────────────────────────────────────────────────────────────────────────
#  Test 2 — PAN number validation
# ─────────────────────────────────────────────────────────────────────────────

class TestPanValidation:
    def test_valid_pan(self):
        assert _validate_pan_str("ABCDE1234F") == "ABCDE1234F"

    def test_pan_lowercase_accepted(self):
        assert _validate_pan_str("abcde1234f") == "ABCDE1234F"

    def test_pan_wrong_format(self):
        with pytest.raises(ValueError, match="invalid"):
            _validate_pan_str("12345ABCDE")

    def test_pan_too_short(self):
        with pytest.raises(ValueError, match="10 characters"):
            _validate_pan_str("ABCDE123")

    def test_pan_special_chars_rejected(self):
        with pytest.raises(ValueError):
            _validate_pan_str("ABC#E1234F")


# ─────────────────────────────────────────────────────────────────────────────
#  Test 3 — Aadhaar validation
# ─────────────────────────────────────────────────────────────────────────────

class TestAadhaarValidation:
    def test_valid_aadhaar(self):
        assert _validate_aadhaar_str("123456789012") == "123456789012"

    def test_aadhaar_must_be_12_digits(self):
        with pytest.raises(ValueError, match="12 digits"):
            _validate_aadhaar_str("12345")

    def test_aadhaar_no_letters(self):
        with pytest.raises(ValueError, match="digits only"):
            _validate_aadhaar_str("AABBCC789012")

    def test_aadhaar_exactly_12(self):
        with pytest.raises(ValueError):
            _validate_aadhaar_str("1234567890123")   # 13 digits


# ─────────────────────────────────────────────────────────────────────────────
#  Test 4 — Date of birth / age validation
# ─────────────────────────────────────────────────────────────────────────────

class TestDobValidation:
    def test_valid_dob(self):
        dob = _validate_dob_str("1995-06-15")
        assert dob.year == 1995

    def test_under_18_rejected(self):
        with pytest.raises(ValueError, match="18"):
            _validate_dob_str("2015-01-01")

    def test_future_date_rejected(self):
        with pytest.raises(ValueError, match="past"):
            _validate_dob_str("2099-01-01")

    def test_invalid_format_rejected(self):
        with pytest.raises(ValueError, match="format"):
            _validate_dob_str("15/06/1995")

    def test_empty_dob_rejected(self):
        with pytest.raises(ValueError, match="required"):
            _validate_dob_str("")


# ─────────────────────────────────────────────────────────────────────────────
#  Test 5 — Full API registration flow
# ─────────────────────────────────────────────────────────────────────────────

class TestApiRegister:
    def test_valid_registration(self):
        ok, result = validate_api_register({
            "full_name": "Priya Mehta",
            "email":     "priya@example.com",
            "password":  "secure123",
        })
        assert ok is True
        assert result["email"] == "priya@example.com"
        assert result["full_name"] == "Priya Mehta"

    def test_short_password_rejected(self):
        ok, result = validate_api_register({
            "full_name": "Test User",
            "email":     "test@example.com",
            "password":  "abc",           # < 6 chars
        })
        assert ok is False

    def test_invalid_email_rejected(self):
        ok, result = validate_api_register({
            "full_name": "Test User",
            "email":     "not-an-email",
            "password":  "secure123",
        })
        assert ok is False

    def test_email_normalised_to_lowercase(self):
        ok, result = validate_api_register({
            "full_name": "Test User",
            "email":     "TEST@EXAMPLE.COM",
            "password":  "secure123",
        })
        assert ok is True
        assert result["email"] == "test@example.com"

    def test_name_with_special_chars_rejected(self):
        ok, result = validate_api_register({
            "full_name": "Raj@123",
            "email":     "raj@example.com",
            "password":  "secure123",
        })
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
#  Bonus — Customer create (end-to-end validation)
# ─────────────────────────────────────────────────────────────────────────────

class TestCustomerCreate:
    def test_valid_customer(self):
        ok, result = validate_api_customer_create(_valid_customer_payload())
        assert ok is True
        assert result["full_name"] == "Raj Sharma"
        assert result["pan"] == "ABCDE1234F"

    def test_invalid_account_type(self):
        ok, _ = validate_api_customer_create(
            _valid_customer_payload(account_type="InvalidType")
        )
        assert ok is False

    def test_missing_required_field(self):
        payload = _valid_customer_payload()
        del payload["aadhaar"]
        ok, _ = validate_api_customer_create(payload)
        assert ok is False

    def test_pincode_must_be_6_digits(self):
        ok, _ = validate_api_customer_create(
            _valid_customer_payload(pincode="12345")   # 5 digits
        )
        assert ok is False

    def test_nominees_capped_at_3(self):
        """Even if 5 nominees are sent, only 3 should be kept."""
        nominees = [
            {"nominee_name": f"N{i}", "relation": "Father",
             "aadhaar_number": "1" * 12}
            for i in range(5)
        ]
        ok, result = validate_api_customer_create(
            _valid_customer_payload(nominees=nominees)
        )
        assert ok is True
        assert len(result["nominees"]) == 3