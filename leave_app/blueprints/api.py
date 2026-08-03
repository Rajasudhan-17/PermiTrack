import hashlib
import secrets
from datetime import timedelta
from functools import wraps

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Leave, OD, RequestStatus, Role, User, utcnow
from ..services.auth_security import clear_failed_logins, login_allowed, register_failed_login
from ..services.workflows import pending_counts_for_user
from ..services.risk_scoring import calculate_leave_risk, calculate_od_risk

bp = Blueprint("api", __name__, url_prefix="/api/v1")


def hash_token(token_str):
    if not token_str:
        return ""
    return hashlib.sha256(token_str.encode("utf-8")).hexdigest()


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-API-Token")
        if not token:
            return jsonify({"message": "Token is missing"}), 401

        hashed = hash_token(token)
        user = User.query.filter_by(api_token=hashed).first()
        if not user or not user.token_expires_at or user.token_expires_at < utcnow():
            return jsonify({"message": "Token is invalid or expired"}), 401

        return f(user, *args, **kwargs)

    return decorated


@bp.route("/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    client_ip = request.remote_addr or "unknown"
    allowed, locked_until = login_allowed(username, client_ip)
    if not allowed:
        locked_until_display = locked_until.strftime("%Y-%m-%d %H:%M:%S") if locked_until else "later"
        return jsonify({"message": f"Too many failed sign-in attempts. Try again after {locked_until_display}."}), 429

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        # Clear rate limiting attempts on successful login
        clear_failed_logins(username, client_ip)

        # Generate secure API token
        raw_token = secrets.token_hex(32)
        hashed_token = hash_token(raw_token)

        # Update user with hashed token and expiry
        user.api_token = hashed_token
        user.token_expires_at = utcnow() + timedelta(hours=24)
        db.session.commit()

        return jsonify(
            {
                "message": "Login successful",
                "token": raw_token,  # only return raw token to client once
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": user.role,
                },
            }
        )

    # Register failed attempt on failure
    register_failed_login(username, client_ip)
    return jsonify({"message": "Invalid username or password"}), 401


@bp.route("/auth/logout", methods=["POST"])
@token_required
def api_logout(current_user):
    # Clear the token and expiry date to invalidate it
    current_user.api_token = None
    current_user.token_expires_at = None
    db.session.commit()
    return jsonify({"message": "Logout successful"})


@bp.route("/dashboard", methods=["GET"])
@token_required
def api_dashboard(current_user):
    if current_user.role == Role.ADMIN.value:
        metrics = {
            "role": current_user.role,
            "admin_user_count": User.query.count(),
            "admin_leave_count": Leave.query.count(),
            "admin_od_count": OD.query.count(),
        }
    else:
        pending_leave, pending_od = pending_counts_for_user(current_user)
        metrics = {
            "role": current_user.role,
            "leave_balance": current_user.leave_balance,
            "pending_leave_reviews": pending_leave,
            "pending_od_reviews": pending_od,
            "applied_leaves_count": Leave.query.filter_by(requested_by=current_user.id).count(),
            "applied_ods_count": OD.query.filter_by(requested_by=current_user.id).count(),
        }
    return jsonify(metrics)


@bp.route("/leaves", methods=["GET"])
@token_required
def api_leaves(current_user):
    leaves = Leave.query.filter_by(requested_by=current_user.id).order_by(Leave.applied_on.desc()).all()
    result = []
    for l in leaves:
        result.append(
            {
                "id": l.id,
                "start_date": l.start_date.strftime("%Y-%m-%d"),
                "end_date": l.end_date.strftime("%Y-%m-%d"),
                "is_emergency": l.is_emergency,
                "status": l.status,
                "reason": l.reason,
                "applied_on": l.applied_on.strftime("%Y-%m-%d %H:%M"),
                "review_comment": l.review_comment,
            }
        )
    return jsonify(result)


@bp.route("/ods", methods=["GET"])
@token_required
def api_ods(current_user):
    ods = OD.query.filter_by(requested_by=current_user.id).order_by(OD.applied_on.desc()).all()
    result = []
    for o in ods:
        result.append(
            {
                "id": o.id,
                "event_date": o.event_date.strftime("%Y-%m-%d"),
                "status": o.status,
                "reason": o.reason,
                "applied_on": o.applied_on.strftime("%Y-%m-%d %H:%M"),
                "review_comment": o.review_comment,
            }
        )
    return jsonify(result)


@bp.route("/pending", methods=["GET"])
@token_required
def api_pending(current_user):
    leaves = []
    ods = []

    if current_user.role == Role.EVENT_COORDINATOR.value:
        leaves = []
        ods = OD.query.filter_by(event_coordinator_id=current_user.id, status=RequestStatus.PENDING.value).all()
    elif current_user.role == Role.MENTOR.value:
        leaves = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .filter(User.mentor_id == current_user.id, Leave.status == RequestStatus.PENDING.value)
            .all()
        )
        ods = (
            OD.query.join(User, User.id == OD.requested_by)
            .filter(User.mentor_id == current_user.id, OD.status == RequestStatus.EVENT_COORDINATOR_APPROVED.value)
            .all()
        )
    elif current_user.role == Role.FACULTY.value:
        from ..models import ClassGroup
        class_groups = ClassGroup.query.filter_by(faculty_id=current_user.id).all()
        class_group_ids = [cg.id for cg in class_groups]
        leaves = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .filter(
                (User.faculty_id == current_user.id) | (User.class_group_id.in_(class_group_ids)),
                Leave.status == RequestStatus.MENTOR_APPROVED.value
            )
            .all()
        )
        ods = OD.query.filter_by(faculty_id=current_user.id, status=RequestStatus.MENTOR_APPROVED.value).all()
    elif current_user.role == Role.HOD.value:
        from ..models import Department
        depts = Department.query.filter_by(hod_id=current_user.id).all()
        dept_ids = [d.id for d in depts]
        leaves = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .filter(User.department_id.in_(dept_ids), Leave.status == RequestStatus.FACULTY_APPROVED.value)
            .all()
        )
        ods = (
            OD.query.join(User, User.id == OD.requested_by)
            .filter(User.department_id.in_(dept_ids), OD.status == RequestStatus.FACULTY_APPROVED.value)
            .all()
        )

    leave_data = []
    for l in leaves:
        score, level, reasons = calculate_leave_risk(l)
        leave_data.append({
            "id": l.id,
            "applicant": l.applicant.username,
            "start_date": l.start_date.strftime("%Y-%m-%d"),
            "end_date": l.end_date.strftime("%Y-%m-%d"),
            "reason": l.reason,
            "is_emergency": l.is_emergency,
            "risk": {
                "score": score,
                "level": level,
                "reasons": reasons
            }
        })

    od_data = []
    for o in ods:
        score, level, reasons = calculate_od_risk(o)
        od_data.append({
            "id": o.id,
            "applicant": o.applicant.username,
            "event_date": o.event_date.strftime("%Y-%m-%d"),
            "reason": o.reason,
            "risk": {
                "score": score,
                "level": level,
                "reasons": reasons
            }
        })

    return jsonify({"pending_leaves": leave_data, "pending_ods": od_data})
