"""
app.py — Flask frontend for Zylitix Bank

Fixes applied:
  [1] CSRF protection via Flask-WTF on all POST forms
  [2] Logger imported and used for login/logout/customer events
  [3] Custom 404 and 500 error pages
  [4] Logout now calls API to blacklist JWT token
  [5] Pagination passes page/per_page to API instead of Python slicing
"""

import requests
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from flask_wtf.csrf import CSRFProtect                          # [FIX 1]
from config import Config
from functools import wraps
from types import SimpleNamespace
from datetime import datetime
from logger import logger                                        # [FIX 2]
import os

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

app.config["SESSION_TYPE"]             = "filesystem"
app.config["SESSION_FILE_DIR"]         = os.path.join(os.getcwd(), "flask_session")
app.config["SESSION_PERMANENT"]        = False
app.config["SESSION_USE_SIGNER"]       = False                  # bytes/str conflict with flask-session + werkzeug
app.config["SESSION_COOKIE_SAMESITE"]  = "Lax"
app.config["SESSION_COOKIE_SECURE"]    = False                  # set True in prod
app.config["SESSION_COOKIE_HTTPONLY"]  = True                   # explicit
app.config["WTF_CSRF_TIME_LIMIT"]      = 3600                   # 1 hour CSRF token

Session(app)
csrf = CSRFProtect(app)                                         # [FIX 1]

API_BASE = "http://127.0.0.1:8000"


# ── Helpers ───────────────────────────────────────────────────────────────────

def api(method, path, token=None, **kwargs):
    """Make an API call. Returns (data_or_none, error_string_or_none)."""
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.request(
            method, f"{API_BASE}{path}",
            headers=headers, timeout=10, **kwargs
        )
        if resp.status_code in (200, 201):
            return resp.json(), None
        try:
            detail = resp.json().get("detail", "An error occurred")
            if isinstance(detail, list):
                detail = detail[0] if detail else "Validation error"
        except Exception:
            detail = f"Error {resp.status_code}"
        return None, detail
    except requests.ConnectionError:
        return None, "Cannot connect to API server. Make sure api.py is running on port 8000."
    except Exception as e:
        return None, str(e)


def to_obj(d):
    """Recursively convert dict to SimpleNamespace so templates use dot notation."""
    if isinstance(d, dict):
        ns = SimpleNamespace()
        for k, v in d.items():
            setattr(ns, k, to_obj(v))
        for date_field in ("dob", "created_at"):
            if hasattr(ns, date_field):
                val = getattr(ns, date_field)
                if val and isinstance(val, str):
                    try:
                        if date_field == "dob":
                            setattr(ns, date_field, datetime.strptime(val, "%Y-%m-%d").date())
                        else:
                            setattr(ns, date_field, datetime.fromisoformat(val.replace(" ", "T")))
                    except Exception:
                        pass
        return ns
    if isinstance(d, list):
        return [to_obj(i) for i in d]
    return d


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "token" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "token" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return render_template("unauthorized.html"), 403
        return f(*args, **kwargs)
    return decorated


# ── Custom Error Handlers ─────────────────────────────────────────────────────   [FIX 3]

@app.errorhandler(404)
def not_found(e):
    logger.warning("404 Not Found | path=%s", request.path)
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    logger.error("500 Server Error | path=%s error=%s", request.path, str(e))
    return render_template("500.html"), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template("unauthorized.html"), 403


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if "token" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            logger.warning("Login attempt with missing fields | ip=%s", request.remote_addr)
            return render_template("login.html", error="Email and password are required")

        data, err = api("POST", "/api/auth/login", json={"email": email, "password": password})
        if err:
            logger.warning("Failed login | email=%s ip=%s reason=%s",
                           email, request.remote_addr, err)           # [FIX 2]
            return render_template("login.html", error=err)

        session["token"]     = data["token"]
        session["user"]      = data["email"]
        session["user_name"] = data["full_name"]
        session["role"]      = data["role"]

        logger.info("Login success | email=%s role=%s ip=%s",
                    email, data["role"], request.remote_addr)          # [FIX 2]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
@admin_required
def register():
    if request.method == "POST":
        payload = {
            "full_name": request.form.get("full_name", "").strip(),
            "email":     request.form.get("email", "").strip(),
            "password":  request.form.get("password", ""),
        }
        data, err = api("POST", "/api/auth/register", token=session["token"], json=payload)
        if err:
            return render_template("register.html", error=err)

        logger.info("Staff user created | name=%s email=%s by=%s",
                    data["full_name"], data["email"], session.get("user"))   # [FIX 2]
        session["success_msg"] = f"Staff user '{data['full_name']}' created successfully!"
        return redirect(url_for("manage_users"))

    return render_template("register.html")


@app.route("/dashboard")
@login_required
def dashboard():
    total_customers = savings_count = current_count = business_count = fd_count = 0

    if session.get("role") == "admin":
        stats, err = api("GET", "/api/dashboard/stats", token=session["token"])
        if stats:
            total_customers = stats.get("total_customers", 0)
            savings_count   = stats.get("savings_count",   0)
            current_count   = stats.get("current_count",   0)
            business_count  = stats.get("business_count",  0)
            fd_count        = stats.get("fd_count",        0)

    success_msg = session.pop("success_msg", None)
    error_msg   = session.pop("error_msg",   None)

    return render_template("dashboard.html",
                           user_name=session.get("user_name"),
                           role=session.get("role"),
                           total_customers=total_customers,
                           savings_count=savings_count,
                           current_count=current_count,
                           business_count=business_count,
                           fd_count=fd_count,
                           success=success_msg,
                           error=error_msg)


@app.route("/admin/users")
@admin_required
def manage_users():
    users_data, err = api("GET", "/api/users", token=session["token"])
    users = [to_obj(u) for u in (users_data or [])]

    success_msg = session.pop("success_msg", None)
    error_msg   = session.pop("error_msg",   None)
    return render_template("manage_users.html",
                           users=users,
                           success=success_msg,
                           error=error_msg)


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    data, err = api("DELETE", f"/api/users/{user_id}", token=session["token"])
    if err:
        session["error_msg"] = err
    else:
        logger.info("User deleted | user_id=%s by=%s", user_id, session.get("user"))  # [FIX 2]
        session["success_msg"] = data.get("message", "User deleted successfully.")
    return redirect(url_for("manage_users"))


@app.route("/add_customer", methods=["GET", "POST"])
@login_required
def add_customer():
    if request.method == "POST":
        form = request.form

        nominees = []
        if form.get("add_nominees") == "yes":
            for i in range(1, 4):
                name     = form.get(f"nominee_name_{i}",     "").strip()
                relation = form.get(f"nominee_relation_{i}", "").strip()
                aadhaar  = form.get(f"nominee_aadhaar_{i}",  "").strip()
                if not name and not relation and not aadhaar:
                    continue
                nominees.append({
                    "nominee_name":   name,
                    "relation":       relation,
                    "aadhaar_number": aadhaar,
                    "phone_number":   form.get(f"nominee_phone_{i}", "").strip() or None,
                    "email":          form.get(f"nominee_email_{i}", "").strip() or None,
                })

        payload = {
            "full_name":    form.get("full_name", "").strip(),
            "dob":          form.get("dob", "").strip(),
            "gender":       form.get("gender", "") or "",
            "email":        form.get("email", "").strip(),
            "phone":        form.get("phone", "").strip(),
            "account_type": form.get("account_type", "").strip(),
            "aadhaar":      form.get("aadhaar", "").strip(),
            "pan":          form.get("pan", "").strip().upper(),
            "address": {
                "flat_no":      form.get("flat_no",      "").strip() or None,
                "block_number": form.get("block_number", "").strip() or None,
                "street":       form.get("street",       "").strip() or None,
                "city":         form.get("city",         "").strip() or None,
                "state":        form.get("state",        "").strip() or None,
                "pincode":      form.get("pincode",      "").strip() or None,
            },
            "parent_details": {
                "father_name":       form.get("father_name",       "").strip() or None,
                "father_occupation": form.get("father_occupation", "").strip() or None,
                "mother_name":       form.get("mother_name",       "").strip() or None,
                "mother_type":       form.get("mother_type",       "").strip() or None,
            },
            "nominees": nominees,
        }

        data, err = api("POST", "/api/customers", token=session["token"], json=payload)
        if err:
            return render_template("add_customer.html", error=err)

        logger.info("Customer created | name=%s account=%s by=%s",    # [FIX 2]
                    data["full_name"], data["account_number"], session.get("user"))
        session["success_msg"] = (
            f"Customer '{data['full_name']}' registered successfully! "
            f"Account Number: {data['account_number']}"
        )
        return redirect(
            url_for("view_customers") if session.get("role") == "admin"
            else url_for("dashboard")
        )

    return render_template("add_customer.html")


@app.route("/customers")
@admin_required
def view_customers():
    page     = request.args.get("page", 1, type=int)
    per_page = 10

    # [FIX 5] Pass pagination params to API — DB does the slicing, not Python
    raw, err = api(
        "GET", "/api/customers",
        token=session["token"],
        params={"page": page, "per_page": per_page}
    )

    if err or not raw:
        raw = {"items": [], "total": 0, "page": page,
               "per_page": per_page, "pages": 0}

    items       = [to_obj(c) for c in raw.get("items", [])]
    total       = raw.get("total", 0)
    total_pages = raw.get("pages", 1)

    pagination = SimpleNamespace(
        items      = items,
        page       = page,
        per_page   = per_page,
        pages      = total_pages,
        total      = total,
        has_prev   = page > 1,
        has_next   = page < total_pages,
        prev_num   = page - 1,
        next_num   = page + 1,
        iter_pages = lambda **kw: range(1, total_pages + 1),
    )

    success_msg = session.pop("success_msg", None)
    error_msg   = session.pop("error_msg",   None)
    return render_template("view_customers.html",
                           customers=pagination,
                           success=success_msg,
                           error=error_msg)


@app.route("/customer/<int:customer_id>")
@admin_required
def customer_detail(customer_id):
    data, err = api("GET", f"/api/customers/{customer_id}", token=session["token"])
    if err or not data:
        session["error_msg"] = err or "Customer not found"
        return redirect(url_for("view_customers"))

    customer    = to_obj(data)
    success_msg = session.pop("success_msg", None)
    return render_template("customer_detail.html", customer=customer, success=success_msg)


@app.route("/customer/delete/<int:customer_id>", methods=["POST"])
@admin_required
def delete_customer(customer_id):
    data, err = api("DELETE", f"/api/customers/{customer_id}", token=session["token"])
    if err:
        session["error_msg"] = err
    else:
        logger.info("Customer deleted | customer_id=%s by=%s",      # [FIX 2]
                    customer_id, session.get("user"))
        session["success_msg"] = data.get("message", "Customer deleted successfully.")
    return redirect(url_for("view_customers"))


@app.route("/customer/edit/<int:customer_id>", methods=["GET", "POST"])
@admin_required
def edit_customer(customer_id):
    data, err = api("GET", f"/api/customers/{customer_id}", token=session["token"])
    if err or not data:
        session["error_msg"] = err or "Customer not found"
        return redirect(url_for("view_customers"))

    customer = to_obj(data)

    if request.method == "POST":
        form = request.form

        update_payload = {
            "full_name":    form.get("full_name", "").strip(),
            "gender":       form.get("gender", "") or None,
            "email":        form.get("email", "").strip(),
            "phone":        form.get("phone", "").strip(),
            "account_type": form.get("account_type", "").strip(),
            "address": {
                "flat_no":      form.get("flat_no",      "").strip() or None,
                "block_number": form.get("block_number", "").strip() or None,
                "street":       form.get("street",       "").strip() or None,
                "city":         form.get("city",         "").strip() or None,
                "state":        form.get("state",        "").strip() or None,
                "pincode":      form.get("pincode",      "").strip() or None,
            },
            "parent_details": {
                "father_name":       form.get("father_name",       "").strip() or None,
                "father_occupation": form.get("father_occupation", "").strip() or None,
                "mother_name":       form.get("mother_name",       "").strip() or None,
                "mother_type":       form.get("mother_type",       "").strip() or None,
            },
        }

        updated, err = api("PUT", f"/api/customers/{customer_id}",
                           token=session["token"], json=update_payload)
        if err:
            return render_template("edit_customer.html", customer=customer, error=err)

        kyc_payload = {
            "document_verified": form.get("document_verified") == "1",
            "risk_category":     form.get("risk_category", "Low"),
        }
        _, kyc_err = api("PATCH", f"/api/customers/{customer_id}/kyc",
                         token=session["token"], json=kyc_payload)
        if kyc_err:
            return render_template("edit_customer.html", customer=to_obj(updated), error=kyc_err)

        logger.info("Customer updated | customer_id=%s by=%s",      # [FIX 2]
                    customer_id, session.get("user"))
        session["success_msg"] = f"Customer '{updated['full_name']}' updated successfully!"
        return redirect(url_for("customer_detail", customer_id=customer_id))

    return render_template("edit_customer.html", customer=customer)


@app.route("/logout")
def logout():
    # [FIX 4] Tell API to blacklist the token before clearing session
    if "token" in session:
        api("POST", "/api/auth/logout", token=session["token"])
        logger.info("Logout | email=%s ip=%s", session.get("user"), request.remote_addr)
    session.clear()
    return redirect(url_for("login"))


@app.route("/unauthorized")
def unauthorized():
    return render_template("unauthorized.html"), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1800, debug=False)