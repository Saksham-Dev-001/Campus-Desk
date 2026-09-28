from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint("auth", __name__)

def is_safe_url(target):
    if not target or not isinstance(target, str):
        return False
    # Prevent protocol-relative URLs like '//evil.com'
    if target.startswith("//") or target.startswith("\\\\"):
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if not user or not user.check_password(password):
            flash("Invalid credentials. Please check and try again.", "error")
        elif not user.active:
            flash("Account is disabled. Contact the administrator.", "error")
        else:
            login_user(user, remember=True)
            next_url = request.args.get("next")
            if not is_safe_url(next_url):
                next_url = url_for("dashboard")
            return redirect(next_url)

    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
