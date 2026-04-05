from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..services.auth_security import clear_failed_logins, login_allowed, register_failed_login
from ..models import User


bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        client_ip = request.remote_addr or "unknown"

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("auth.login"))

        allowed, locked_until = login_allowed(username, client_ip)
        if not allowed:
            locked_until_display = locked_until.strftime("%Y-%m-%d %H:%M:%S") if locked_until else "later"
            flash(f"Too many failed sign-in attempts. Try again after {locked_until_display}.", "danger")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            clear_failed_logins(username, client_ip)
            login_user(user)
            flash(f"Welcome back, {user.full_name or user.username}.", "success")
            return redirect(url_for("main.index"))

        register_failed_login(username, client_ip)
        flash("Invalid username or password.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("index.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
