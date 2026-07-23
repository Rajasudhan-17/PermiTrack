from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from sqlalchemy import text

from ..extensions import db
from ..models import ClassGroup, Department, Leave, OD, Role, User


bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        dashboard_metrics = {}

        if current_user.role == Role.ADMIN.value:
            dashboard_metrics = {
                "admin_user_count": User.query.count(),
                "admin_department_count": Department.query.count(),
                "admin_class_count": ClassGroup.query.count(),
                "admin_leave_count": Leave.query.count(),
                "admin_od_count": OD.query.count(),
            }
        else:
            dashboard_metrics = {
                "applied_leave_count": Leave.query.filter_by(requested_by=current_user.id).count(),
                "applied_od_count": OD.query.filter_by(requested_by=current_user.id).count(),
            }

        return render_template("dashboard.html", **dashboard_metrics)

    return render_template("index.html")


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or not email:
            flash("Full name and email are required.", "danger")
            return redirect(url_for("main.profile"))

        if not current_password:
            flash("Current password is required to save changes.", "danger")
            return redirect(url_for("main.profile"))

        if not current_user.check_password(current_password):
            flash("Incorrect current password.", "danger")
            return redirect(url_for("main.profile"))

        if email != current_user.email:
            existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
            if existing_user:
                flash("That email is already in use by another account.", "danger")
                return redirect(url_for("main.profile"))

        if new_password:
            if new_password != confirm_password:
                flash("New password and confirmation do not match.", "danger")
                return redirect(url_for("main.profile"))
            current_user.set_password(new_password)

        current_user.full_name = full_name
        current_user.email = email
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("main.profile"))

    return render_template("profile.html")


@bp.route("/healthz")
def healthz():
    db.session.execute(text("SELECT 1"))
    return jsonify({"status": "ok"}), 200

