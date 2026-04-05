from flask import Blueprint, jsonify, render_template
from flask_login import current_user
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


@bp.route("/healthz")
def healthz():
    db.session.execute(text("SELECT 1"))
    return jsonify({"status": "ok"}), 200
