from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..models import AttendanceRecord, AttendanceStatus, ClassGroup, Department, Role, User, utcnow
from ..services.attendance import (
    get_attendance_sheet,
    get_student_attendance_summary,
    save_attendance_sheet,
)

bp = Blueprint("attendance", __name__, url_prefix="/attendance")


def attendance_access_allowed(user):
    return user and user.is_authenticated and user.role in (Role.FACULTY.value, Role.HOD.value)


@bp.route("/mark", methods=["GET", "POST"])
@login_required
def mark_attendance():
    if not attendance_access_allowed(current_user):
        flash("You are not authorized to access the attendance marking page.", "danger")
        return redirect(url_for("main.index"))

    # Determine accessible class groups
    if current_user.role == Role.ADMIN.value:
        class_groups = ClassGroup.query.order_by(ClassGroup.year.asc(), ClassGroup.section.asc()).all()
    elif current_user.role == Role.HOD.value:
        class_groups = ClassGroup.query.filter_by(department_id=current_user.department_id).order_by(ClassGroup.year.asc(), ClassGroup.section.asc()).all()
    else:  # Faculty
        class_groups = ClassGroup.query.filter_by(faculty_id=current_user.id).order_by(ClassGroup.year.asc(), ClassGroup.section.asc()).all()
        if not class_groups and current_user.class_group_id:
            cg = ClassGroup.query.get(current_user.class_group_id)
            if cg:
                class_groups = [cg]

    selected_class_id = request.args.get("class_id", type=int)
    if not selected_class_id and class_groups:
        selected_class_id = class_groups[0].id

    date_str = request.args.get("date", "").strip()
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = utcnow().date()
    else:
        target_date = utcnow().date()

    if request.method == "POST":
        class_id = request.form.get("class_id", type=int)
        post_date_str = request.form.get("date", "").strip()
        try:
            post_date = datetime.strptime(post_date_str, "%Y-%m-%d").date()
        except ValueError:
            post_date = utcnow().date()

        records_data = {}
        # Parse student responses from form
        for key, value in request.form.items():
            if key.startswith("status_"):
                try:
                    student_id = int(key.split("status_")[1])
                except ValueError:
                    continue
                reason = request.form.get(f"reason_{student_id}", "").strip()
                leave_id = request.form.get(f"leave_id_{student_id}", type=int)
                od_id = request.form.get(f"od_id_{student_id}", type=int)
                records_data[student_id] = {
                    "status": value,
                    "reason": reason,
                    "leave_id": leave_id,
                    "od_id": od_id,
                }

        if class_id and records_data:
            count = save_attendance_sheet(class_id, post_date, records_data, current_user)
            flash(f"Successfully saved attendance for {count} student(s) on {post_date}.", "success")
            return redirect(url_for("attendance.mark_attendance", class_id=class_id, date=post_date.strftime("%Y-%m-%d")))

    selected_class = ClassGroup.query.get(selected_class_id) if selected_class_id else None
    sheet = get_attendance_sheet(selected_class_id, target_date) if selected_class_id else []

    return render_template(
        "mark_attendance.html",
        class_groups=class_groups,
        selected_class_id=selected_class_id,
        selected_class=selected_class,
        target_date=target_date,
        sheet=sheet,
        status_options=[s.value for s in AttendanceStatus],
    )


@bp.route("/history", methods=["GET"])
@login_required
def history():
    if current_user.role == Role.STUDENT.value:
        summary = get_student_attendance_summary(current_user.id)
        records = (
            AttendanceRecord.query.filter_by(student_id=current_user.id)
            .order_by(AttendanceRecord.date.desc())
            .all()
        )
        return render_template(
            "attendance_history.html",
            is_student=True,
            summary=summary,
            records=records,
            student=current_user,
        )

    # Faculty / HOD / Admin View
    selected_student_id = request.args.get("student_id", type=int)
    student = User.query.get(selected_student_id) if selected_student_id else None

    if student:
        summary = get_student_attendance_summary(student.id)
        records = (
            AttendanceRecord.query.filter_by(student_id=student.id)
            .order_by(AttendanceRecord.date.desc())
            .all()
        )
    else:
        summary = None
        records = []

    return render_template(
        "attendance_history.html",
        is_student=False,
        summary=summary,
        records=records,
        student=student,
    )
