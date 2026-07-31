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


@bp.route("/students")
@login_required
def students_list():
    if current_user.role not in (Role.FACULTY.value, Role.MENTOR.value, Role.HOD.value):
        flash("You are not authorized to view the students list.", "danger")
        return redirect(url_for("main.index"))

    if current_user.role == Role.HOD.value:
        students = (
            User.query.filter_by(role=Role.STUDENT.value, department_id=current_user.department_id)
            .order_by(User.username.asc())
            .all()
        )
        list_title = f"Students in Department: {current_user.department.name if current_user.department else 'N/A'}"
    elif current_user.role == Role.FACULTY.value:
        classes = ClassGroup.query.filter_by(faculty_id=current_user.id).all()
        class_ids = [cg.id for cg in classes]
        students = (
            User.query.filter(
                User.role == Role.STUDENT.value,
                (User.faculty_id == current_user.id) | (User.class_group_id.in_(class_ids) if class_ids else False)
            )
            .order_by(User.username.asc())
            .all()
        )
        list_title = "Students of Assigned Classes"
    elif current_user.role == Role.MENTOR.value:
        students = (
            User.query.filter_by(role=Role.STUDENT.value, mentor_id=current_user.id)
            .order_by(User.username.asc())
            .all()
        )
        list_title = "Mentored Students"
    else:
        students = []
        list_title = "Students"

    return render_template("students_list.html", students=students, list_title=list_title)


@bp.route("/students/<int:student_id>/block", methods=["POST"])
@login_required
def block_student(student_id):
    if current_user.role not in (Role.FACULTY.value, Role.MENTOR.value, Role.HOD.value):
        flash("You are not authorized to perform this action.", "danger")
        return redirect(url_for("main.index"))

    student = db.session.get(User, student_id)
    if not student or student.role != Role.STUDENT.value:
        flash("Student not found.", "danger")
        return redirect(url_for("main.students_list"))

    # Verify authorization
    authorized = False
    if current_user.role == Role.HOD.value:
        authorized = (student.department_id == current_user.department_id)
    elif current_user.role == Role.FACULTY.value:
        classes = ClassGroup.query.filter_by(faculty_id=current_user.id).all()
        class_ids = [cg.id for cg in classes]
        authorized = (student.faculty_id == current_user.id) or (student.class_group_id in class_ids if class_ids else False)
    elif current_user.role == Role.MENTOR.value:
        authorized = (student.mentor_id == current_user.id)

    if not authorized:
        flash("You are not authorized to block this student.", "danger")
        return redirect(url_for("main.students_list"))

    student.is_blocked = True
    db.session.commit()
    flash(f"Student {student.full_name or student.username} has been blocked from applying for Leave and OD.", "success")
    return redirect(url_for("main.students_list"))


@bp.route("/students/<int:student_id>/unblock", methods=["POST"])
@login_required
def unblock_student(student_id):
    if current_user.role not in (Role.FACULTY.value, Role.MENTOR.value, Role.HOD.value):
        flash("You are not authorized to perform this action.", "danger")
        return redirect(url_for("main.index"))

    student = db.session.get(User, student_id)
    if not student or student.role != Role.STUDENT.value:
        flash("Student not found.", "danger")
        return redirect(url_for("main.students_list"))

    # Verify authorization
    authorized = False
    if current_user.role == Role.HOD.value:
        authorized = (student.department_id == current_user.department_id)
    elif current_user.role == Role.FACULTY.value:
        classes = ClassGroup.query.filter_by(faculty_id=current_user.id).all()
        class_ids = [cg.id for cg in classes]
        authorized = (student.faculty_id == current_user.id) or (student.class_group_id in class_ids if class_ids else False)
    elif current_user.role == Role.MENTOR.value:
        authorized = (student.mentor_id == current_user.id)

    if not authorized:
        flash("You are not authorized to unblock this student.", "danger")
        return redirect(url_for("main.students_list"))

    student.is_blocked = False
    db.session.commit()
    flash(f"Student {student.full_name or student.username} has been unblocked.", "success")
    return redirect(url_for("main.students_list"))

