import os
from functools import wraps
from datetime import datetime
from types import SimpleNamespace

import requests
from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from config import Config
from logger import logger

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
app.config.update(
    SESSION_TYPE            = "filesystem",
    SESSION_FILE_DIR        = os.path.join(os.getcwd(), "flask_session"),
    SESSION_PERMANENT       = False,
    SESSION_USE_SIGNER      = False,
    SESSION_COOKIE_SAMESITE = "Lax",
    SESSION_COOKIE_SECURE   = False,
    SESSION_COOKIE_HTTPONLY = True,
    WTF_CSRF_ENABLED        = True,
)
Session(app)
CSRFProtect(app)

API_BASE = "http://127.0.0.1:8000"


# ── Helpers ────────────────────────────────────────────────────────────────

def api(method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.request(method, f"{API_BASE}{path}", headers=headers, timeout=10, **kwargs)
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
    if isinstance(d, dict):
        ns = SimpleNamespace(**{k: to_obj(v) for k, v in d.items()})
        for field in ("dob", "created_at"):
            if hasattr(ns, field) and isinstance(getattr(ns, field), str):
                try:
                    val = getattr(ns, field)
                    setattr(ns, field,
                        datetime.strptime(val, "%Y-%m-%d").date() if field == "dob"
                        else datetime.fromisoformat(val.replace(" ", "T")))
                except Exception:
                    pass
        return ns
    if isinstance(d, list):
        return [to_obj(i) for i in d]
    return d


def flash_msgs():
    return session.pop("success_msg", None), session.pop("error_msg", None)


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


# ── Auth ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if "token" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            return render_template("login.html", error="Email and password are required")
        data, err = api("POST", "/api/auth/login", json={"email": email, "password": password})
        if err:
            logger.warning(f"Login failed for {email} — {err}")
            return render_template("login.html", error=err)
        session.update(token=data["token"], user=data["email"],
                       user_name=data["full_name"], role=data["role"])
        logger.info(f"Login success: {email}")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    api("POST", "/api/auth/logout", token=session.get("token"))
    logger.info(f"Logout: {session.get('user')}")
    session.clear()
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
@admin_required
def register():
    if request.method == "POST":
        payload = {k: request.form.get(k, "").strip() for k in ("full_name", "email", "password")}
        data, err = api("POST", "/api/auth/register", token=session["token"], json=payload)
        if err:
            return render_template("register.html", error=err)
        session["success_msg"] = f"Staff user '{data['full_name']}' created successfully!"
        return redirect(url_for("manage_users"))
    return render_template("register.html")


# ── Dashboard ──────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    stats = {}
    if session.get("role") == "admin":
        data, _ = api("GET", "/api/dashboard/stats", token=session["token"])
        stats = data or {}
    success, error = flash_msgs()
    return render_template("dashboard.html",
                           user_name=session.get("user_name"),
                           role=session.get("role"),
                           success=success, error=error, **stats)


# ── Users ──────────────────────────────────────────────────────────────────

@app.route("/admin/users")
@admin_required
def manage_users():
    users_data, _ = api("GET", "/api/users", token=session["token"])
    success, error = flash_msgs()
    return render_template("manage_users.html",
                           users=[to_obj(u) for u in (users_data or [])],
                           success=success, error=error)


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    data, err = api("DELETE", f"/api/users/{user_id}", token=session["token"])
    session["error_msg" if err else "success_msg"] = err or data.get("message", "User deleted.")
    return redirect(url_for("manage_users"))


# ── Customers ──────────────────────────────────────────────────────────────

def _nominee_list(form):
    nominees = []
    for i in range(1, 4):
        name     = form.get(f"nominee_name_{i}", "").strip()
        relation = form.get(f"nominee_relation_{i}", "").strip()
        aadhaar  = form.get(f"nominee_aadhaar_{i}", "").strip()
        if not any((name, relation, aadhaar)):
            continue
        nominees.append({
            "nominee_name":   name,
            "relation":       relation,
            "aadhaar_number": aadhaar,
            "phone_number":   form.get(f"nominee_phone_{i}", "").strip() or None,
            "email":          form.get(f"nominee_email_{i}", "").strip() or None,
        })
    return nominees


def _address(form):
    return {k: form.get(k, "").strip() or None
            for k in ("flat_no", "block_number", "street", "city", "state", "pincode")}


def _parent(form):
    return {k: form.get(k, "").strip() or None
            for k in ("father_name", "father_occupation", "mother_name", "mother_type")}


@app.route("/add_customer", methods=["GET", "POST"])
@login_required
def add_customer():
    if request.method == "POST":
        form = request.form
        payload = {
            "full_name":    form.get("full_name", "").strip(),
            "dob":          form.get("dob", "").strip(),
            "gender":       form.get("gender", "") or "",
            "email":        form.get("email", "").strip(),
            "phone":        form.get("phone", "").strip(),
            "account_type": form.get("account_type", "").strip(),
            "aadhaar":      form.get("aadhaar", "").strip(),
            "pan":          form.get("pan", "").strip().upper(),
            "address":        _address(form),
            "parent_details": _parent(form),
            "nominees": _nominee_list(form) if form.get("add_nominees") == "yes" else [],
        }
        data, err = api("POST", "/api/customers", token=session["token"], json=payload)
        if err:
            return render_template("add_customer.html", error=err)
        session["success_msg"] = (
            f"Customer '{data['full_name']}' registered! Account: {data['account_number']}"
        )
        return redirect(url_for("view_customers" if session.get("role") == "admin" else "dashboard"))
    return render_template("add_customer.html")


@app.route("/customers")
@admin_required
def view_customers():
    page         = request.args.get("page", 1, type=int)
    search_query = request.args.get("search", "").strip()
    per_page     = 10

    if search_query:
        raw, _ = api("GET", "/api/customers/search",
                     token=session["token"], params={"q": search_query})
        items       = [to_obj(c) for c in (raw or [])]
        total       = len(items)
        total_pages = 1
    else:
        raw, _ = api("GET", "/api/customers", token=session["token"],
                     params={"page": page, "per_page": per_page})
        raw         = raw or {}
        items       = [to_obj(c) for c in raw.get("items", [])]
        total       = raw.get("total", 0)
        total_pages = raw.get("pages", 1)

    pagination = SimpleNamespace(
        items=items, page=page, per_page=per_page,
        pages=total_pages, total=total,
        has_prev=page > 1, has_next=page < total_pages,
        prev_num=page - 1, next_num=page + 1,
        iter_pages=lambda **kw: range(1, total_pages + 1),
    )
    success, error = flash_msgs()
    return render_template("view_customers.html",
                           customers=pagination, search_query=search_query,
                           success=success, error=error)


@app.route("/customer/<int:customer_id>")
@admin_required
def customer_detail(customer_id):
    data, err = api("GET", f"/api/customers/{customer_id}", token=session["token"])
    if err or not data:
        session["error_msg"] = err or "Customer not found"
        return redirect(url_for("view_customers"))
    success, _ = flash_msgs()
    return render_template("customer_detail.html", customer=to_obj(data), success=success)


@app.route("/customer/delete/<int:customer_id>", methods=["POST"])
@admin_required
def delete_customer(customer_id):
    data, err = api("DELETE", f"/api/customers/{customer_id}", token=session["token"])
    session["error_msg" if err else "success_msg"] = err or data.get("message", "Customer deleted.")
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
        payload = {
            "full_name":      form.get("full_name", "").strip(),
            "gender":         form.get("gender", "") or None,
            "email":          form.get("email", "").strip(),
            "phone":          form.get("phone", "").strip(),
            "account_type":   form.get("account_type", "").strip(),
            "address":        _address(form),
            "parent_details": _parent(form),
        }
        updated, err = api("PUT", f"/api/customers/{customer_id}",
                           token=session["token"], json=payload)
        if err:
            return render_template("edit_customer.html", customer=customer, error=err)
        _, kyc_err = api("PATCH", f"/api/customers/{customer_id}/kyc",
                         token=session["token"],
                         json={"document_verified": form.get("document_verified") == "1",
                               "risk_category": form.get("risk_category", "Low")})
        if kyc_err:
            return render_template("edit_customer.html", customer=to_obj(updated), error=kyc_err)
        session["success_msg"] = f"Customer '{updated['full_name']}' updated!"
        return redirect(url_for("customer_detail", customer_id=customer_id))
    return render_template("edit_customer.html", customer=customer)


# ── Error handlers & misc ──────────────────────────────────────────────────

@app.route("/unauthorized")
def unauthorized():
    return render_template("unauthorized.html"), 403

@app.errorhandler(403)
def forbidden(e):
    return render_template("unauthorized.html"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500: {e}")
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1800, debug=False)