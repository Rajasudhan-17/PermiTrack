from flask import Blueprint, Response, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..auth import admin_required
from ..extensions import db
from ..models import ClassGroup, Department, Leave, OD, RequestStatus, Role, User
from ..services.reports import csv_response_content, pdf_response_content, report_context
from ..services.seed import ensure_seed_data
from ..services.uploads import delete_uploaded_file
from ..services.workflows import get_form_value


bp = Blueprint("admin", __name__, url_prefix="/admin")


def _resolve_class_group(department_id, year, section):
    if not department_id or not year or not section:
        return None

    return ClassGroup.query.filter_by(
        department_id=department_id,
        year=year,
        section=section.strip().upper(),
    ).first()


def _resolve_user_assignment(form, role):
    if role == Role.STUDENT.value:
        department_id = get_form_value(form, "student_department_id", int)
        year = get_form_value(form, "student_year", int)
        section = get_form_value(form, "student_section", str)
        class_group = _resolve_class_group(department_id, year, section)
        return department_id, class_group.id if class_group else None

    if role == Role.FACULTY.value:
        department_id = get_form_value(form, "faculty_department_id", int)
        year = get_form_value(form, "faculty_year", int)
        section = get_form_value(form, "faculty_section", str)
        class_group = _resolve_class_group(department_id, year, section)
        return department_id, class_group.id if class_group else None

    if role == Role.HOD.value:
        return get_form_value(form, "hod_department_id", int), None

    return None, None


def _remove_proof_file(prefix, filename):
    if not filename:
        return

    try:
        delete_uploaded_file(prefix, filename)
    except Exception:
        current_app.logger.exception("Failed to delete uploaded proof '%s' for prefix '%s'.", filename, prefix)


def _delete_leave_records(leaves, restore_balance=False):
    deleted_count = 0

    for leave in leaves:
        if restore_balance and leave.status == RequestStatus.APPROVED.value and leave.requester:
            requested_days = (leave.end_date - leave.start_date).days + 1
            leave.requester.leave_balance += requested_days

        _remove_proof_file(current_app.config["LEAVE_UPLOAD_PREFIX"], leave.proof_filename)
        db.session.delete(leave)
        deleted_count += 1

    return deleted_count


def _delete_od_records(ods):
    deleted_count = 0

    for od in ods:
        _remove_proof_file(current_app.config["OD_UPLOAD_PREFIX"], od.proof_filename)
        db.session.delete(od)
        deleted_count += 1

    return deleted_count


def _delete_user_related_records(user):
    leave_rows = (
        Leave.query.filter((Leave.requested_by == user.id) | (Leave.approved_by == user.id))
        .order_by(Leave.id.asc())
        .all()
    )
    unique_leaves = list({leave.id: leave for leave in leave_rows}.values())

    od_rows = (
        OD.query.filter((OD.requested_by == user.id) | (OD.approved_by == user.id) | (OD.faculty_id == user.id))
        .order_by(OD.id.asc())
        .all()
    )
    unique_ods = list({od.id: od for od in od_rows}.values())

    leave_count = _delete_leave_records(unique_leaves, restore_balance=True)
    od_count = _delete_od_records(unique_ods)
    return leave_count, od_count


@bp.route("/create_department", methods=["GET", "POST"])
@login_required
@admin_required
def create_department():
    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("Department name is required.", "danger")
            return redirect(url_for("admin.create_department"))

        if Department.query.filter(db.func.lower(Department.name) == name.lower()).first():
            flash("That department already exists.", "warning")
            return redirect(url_for("admin.create_department"))

        db.session.add(Department(name=name))
        db.session.commit()
        flash("Department created successfully.", "success")
        return redirect(url_for("admin.create_department"))

    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template("admin_create_department.html", departments=departments)


@bp.route("/create_class", methods=["GET", "POST"])
@login_required
@admin_required
def create_class():
    if request.method == "POST":
        department_id = request.form.get("department_id", type=int)
        year = request.form.get("year", type=int)
        section = request.form.get("section", "").strip().upper()

        if not department_id or not year or not section:
            flash("Department, year, and section are required.", "danger")
            return redirect(url_for("admin.create_class"))

        existing_class = ClassGroup.query.filter_by(
            department_id=department_id,
            year=year,
            section=section,
        ).first()
        if existing_class:
            flash("That class already exists.", "warning")
            return redirect(url_for("admin.create_class"))

        db.session.add(ClassGroup(department_id=department_id, year=year, section=section))
        db.session.commit()
        flash("Class created successfully.", "success")
        return redirect(url_for("admin.create_class"))

    departments = Department.query.order_by(Department.name.asc()).all()
    classes = ClassGroup.query.order_by(ClassGroup.department_id, ClassGroup.year, ClassGroup.section).all()
    return render_template("admin_create_class.html", departments=departments, classes=classes)


@bp.route("/create_user", methods=["GET", "POST"])
@login_required
@admin_required
def admin_create_user():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", Role.STUDENT.value)
        valid_roles = {role_item.value for role_item in Role}

        if not full_name or not username or not email or not password:
            flash("Full name, username, email, and password are required.", "danger")
            return redirect(url_for("admin.admin_create_user"))

        if role not in valid_roles:
            flash("Please choose a valid role.", "danger")
            return redirect(url_for("admin.admin_create_user"))

        department_id, class_group_id = _resolve_user_assignment(request.form, role)

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("A user with that username or email already exists.", "warning")
            return redirect(url_for("admin.admin_create_user"))

        selected_department = None
        if department_id is not None:
            selected_department = db.session.get(Department, department_id)
            if not selected_department:
                flash("Selected department was not found.", "danger")
                return redirect(url_for("admin.admin_create_user"))

        selected_class = None
        if class_group_id:
            selected_class = db.session.get(ClassGroup, class_group_id)
            if not selected_class:
                flash("Selected class was not found.", "danger")
                return redirect(url_for("admin.admin_create_user"))

        if selected_department and selected_class and selected_class.department_id != selected_department.id:
            flash("Selected class does not belong to the chosen department.", "danger")
            return redirect(url_for("admin.admin_create_user"))

        if role == Role.STUDENT.value and not selected_class:
            flash("Students must be assigned to a department, year, and section.", "danger")
            return redirect(url_for("admin.admin_create_user"))

        if role == Role.FACULTY.value and not selected_class:
            flash("Faculty users must be assigned to a department, year, and section.", "danger")
            return redirect(url_for("admin.admin_create_user"))

        if role == Role.HOD.value and not department_id:
            flash("HOD users must be assigned to a department.", "danger")
            return redirect(url_for("admin.admin_create_user"))

        if role == Role.HOD.value and selected_department and selected_department.hod_id:
            flash("That department already has an assigned HOD.", "warning")
            return redirect(url_for("admin.admin_create_user"))

        if role == Role.FACULTY.value and selected_class and selected_class.faculty_id:
            flash("That class already has an assigned faculty member.", "warning")
            return redirect(url_for("admin.admin_create_user"))

        new_user = User(
            full_name=full_name,
            username=username,
            email=email,
            role=role,
            leave_balance=999 if role == Role.ADMIN.value else 20,
        )
        new_user.set_password(password)

        if role == Role.STUDENT.value:
            new_user.class_group_id = selected_class.id
            new_user.department_id = selected_class.department_id
        elif selected_department:
            new_user.department_id = selected_department.id

        db.session.add(new_user)
        db.session.flush()

        if role == Role.HOD.value and selected_department:
            selected_department.hod_id = new_user.id

        if role == Role.FACULTY.value and selected_class:
            selected_class.faculty_id = new_user.id

        db.session.commit()
        flash(f"{role.capitalize()} user created successfully.", "success")
        return redirect(url_for("admin.admin_create_user"))

    departments = Department.query.order_by(Department.name.asc()).all()
    classes = ClassGroup.query.order_by(ClassGroup.department_id, ClassGroup.year, ClassGroup.section).all()
    users = User.query.order_by(User.role.asc(), User.full_name.asc(), User.username.asc()).all()
    return render_template("admin_create_user.html", departments=departments, classes=classes, users=users)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("admin.admin_create_user"))

    if user.id == current_user.id:
        flash("You cannot delete the admin account you are currently logged in with.", "danger")
        return redirect(url_for("admin.admin_create_user"))

    if user.role == Role.ADMIN.value:
        remaining_admins = User.query.filter_by(role=Role.ADMIN.value).count()
        if remaining_admins <= 1:
            flash("At least one admin account must remain in the system.", "danger")
            return redirect(url_for("admin.admin_create_user"))

    leave_count, od_count = _delete_user_related_records(user)

    Department.query.filter_by(hod_id=user.id).update({"hod_id": None}, synchronize_session=False)
    ClassGroup.query.filter_by(faculty_id=user.id).update({"faculty_id": None}, synchronize_session=False)
    User.query.filter_by(faculty_id=user.id).update({"faculty_id": None}, synchronize_session=False)

    db.session.delete(user)
    db.session.commit()
    flash(
        f"Deleted user '{user.full_name or user.username}' and removed {leave_count} leave record(s) and {od_count} OD record(s).",
        "success",
    )
    return redirect(url_for("admin.admin_create_user"))


@bp.route("/assign_hod", methods=["GET", "POST"])
@login_required
@admin_required
def assign_hod():
    departments = Department.query.order_by(Department.name.asc()).all()
    hod_users = User.query.filter_by(role=Role.HOD.value).order_by(User.full_name.asc(), User.username.asc()).all()

    if request.method == "POST":
        department_id = request.form.get("department_id", type=int)
        hod_user_id = request.form.get("hod_user_id", type=int)

        department = db.session.get(Department, department_id)
        hod_user = db.session.get(User, hod_user_id)

        if not department:
            flash("Department not found.", "danger")
            return redirect(url_for("admin.assign_hod"))
        if not hod_user or hod_user.role != Role.HOD.value:
            flash("Please select a valid HOD user.", "danger")
            return redirect(url_for("admin.assign_hod"))
        if department.hod_id and department.hod_id != hod_user.id:
            flash("This department already has a different HOD assigned.", "warning")
            return redirect(url_for("admin.assign_hod"))

        department.hod_id = hod_user.id
        hod_user.department_id = department.id
        db.session.commit()
        flash("HOD assigned successfully.", "success")
        return redirect(url_for("admin.assign_hod"))

    return render_template("admin_assign_hod.html", departments=departments, faculty_users=hod_users)


@bp.route("/assign_faculty", methods=["GET", "POST"])
@login_required
@admin_required
def assign_faculty():
    classes = ClassGroup.query.order_by(ClassGroup.department_id, ClassGroup.year, ClassGroup.section).all()
    faculty_users = User.query.filter_by(role=Role.FACULTY.value).order_by(User.full_name.asc(), User.username.asc()).all()

    if request.method == "POST":
        class_group_id = request.form.get("class_group_id", type=int)
        faculty_id = request.form.get("faculty_id", type=int)

        class_group = db.session.get(ClassGroup, class_group_id)
        faculty_user = db.session.get(User, faculty_id)

        if not class_group:
            flash("Class not found.", "danger")
            return redirect(url_for("admin.assign_faculty"))
        if not faculty_user or faculty_user.role != Role.FACULTY.value:
            flash("Please select a valid faculty user.", "danger")
            return redirect(url_for("admin.assign_faculty"))
        if class_group.faculty_id and class_group.faculty_id != faculty_user.id:
            flash("This class already has a different faculty member assigned.", "warning")
            return redirect(url_for("admin.assign_faculty"))

        class_group.faculty_id = faculty_user.id
        faculty_user.department_id = class_group.department_id
        db.session.commit()
        flash("Faculty assigned to class successfully.", "success")
        return redirect(url_for("admin.assign_faculty"))

    return render_template("admin_assign_faculty.html", classes=classes, faculty_users=faculty_users)


@bp.route("/all_leaves")
@login_required
@admin_required
def admin_all_leaves():
    leaves = Leave.query.order_by(Leave.applied_on.desc()).all()
    return render_template("admin_all_leaves.html", leaves=leaves)


@bp.route("/all_leaves/clear", methods=["POST"])
@login_required
@admin_required
def clear_all_leaves():
    leaves = Leave.query.order_by(Leave.id.asc()).all()
    deleted_count = _delete_leave_records(leaves, restore_balance=True)
    db.session.commit()
    flash(
        f"Cleared {deleted_count} leave record(s) and restored balances for approved leave entries.",
        "success",
    )
    return redirect(url_for("admin.admin_all_leaves"))


@bp.route("/all_ods")
@login_required
@admin_required
def admin_all_ods():
    ods = OD.query.order_by(OD.applied_on.desc()).all()
    return render_template("admin_all_ods.html", ods=ods)


@bp.route("/all_ods/clear", methods=["POST"])
@login_required
@admin_required
def clear_all_ods():
    ods = OD.query.order_by(OD.id.asc()).all()
    deleted_count = _delete_od_records(ods)
    db.session.commit()
    flash(f"Cleared {deleted_count} OD record(s).", "success")
    return redirect(url_for("admin.admin_all_ods"))


@bp.route("/reports")
@login_required
@admin_required
def reports():
    filters, rows, departments, classes = report_context(request.args)
    export_format = request.args.get("format")

    if export_format == "csv":
        request_type = filters["request_type"]
        filename = f"{request_type}_report.csv"
        return Response(
            csv_response_content(rows, filters),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    if export_format == "pdf":
        request_type = filters["request_type"]
        filename = f"{request_type}_report.pdf"
        return Response(
            pdf_response_content(rows, filters),
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return render_template(
        "admin_reports.html",
        rows=rows,
        filters=filters,
        departments=departments,
        classes=classes,
        statuses=[status.value for status in RequestStatus],
    )


@bp.route("/initdb", methods=["POST"])
def initdb():
    if not current_app.config["ENABLE_INITDB_ROUTE"]:
        abort(404)

    configured_token = current_app.config.get("INITDB_TOKEN")
    supplied_token = request.form.get("token") or request.headers.get("X-Initdb-Token") or request.args.get("token")
    if configured_token and supplied_token != configured_token:
        abort(403)

    message, status_code = ensure_seed_data()
    return message, status_code
