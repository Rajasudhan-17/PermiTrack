from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, Response
from flask_login import current_user, login_required

from ..extensions import db
from ..services.reports import generate_leave_letter_pdf

from ..models import ClassGroup, Leave, OD, RequestStatus, Role, User, utcnow
from ..services.uploads import (
    build_file_response,
    save_uploaded_file,
    uploaded_file_exists,
    validate_uploaded_document,
)
from ..services.workflows import (
    apply_leave_review,
    build_leave_conflicts,
    can_review_leave,
    leave_proof_access_allowed,
    submit_leave_request,
    student_history_access_allowed,
)


bp = Blueprint("leaves", __name__)


@bp.route("/apply", methods=["GET", "POST"])
@login_required
def apply_leave():
    if current_user.role not in (Role.STUDENT.value, Role.FACULTY.value):
        flash("Only students and faculty can apply for leave.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        start = request.form.get("start_date")
        end = request.form.get("end_date")
        reason = request.form.get("reason", "").strip()
        is_emergency = request.form.get("is_emergency") == "on"

        if not start or not end or not reason:
            flash("Start date, end date, and reason are required.", "danger")
            return redirect(url_for("leaves.apply_leave"))

        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter valid dates in YYYY-MM-DD format.", "danger")
            return redirect(url_for("leaves.apply_leave"))

        if end_date < start_date:
            flash("End date cannot be earlier than start date.", "danger")
            return redirect(url_for("leaves.apply_leave"))

        success, _leave, response = submit_leave_request(current_user, start_date, end_date, reason, is_emergency)
        if not success:
            flash(*response)
            return redirect(url_for("leaves.apply_leave"))

        if is_emergency:
            flash(
                "Emergency leave submitted in fast-track mode. Please upload supporting proof as soon as possible.",
                "warning",
            )
        else:
            flash("Leave request submitted successfully.", "success")
        return redirect(url_for("leaves.my_leaves"))

    return render_template("apply.html")


@bp.route("/my_leaves")
@login_required
def my_leaves():
    leaves = Leave.query.filter_by(requested_by=current_user.id).order_by(Leave.applied_on.desc()).all()
    return render_template("my_leaves.html", leaves=leaves)


@bp.route("/pending")
@login_required
def pending():
    leave_conflicts = {}
    if current_user.role == Role.FACULTY.value:
        leaves = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .join(ClassGroup, ClassGroup.id == User.class_group_id)
            .filter(ClassGroup.faculty_id == current_user.id, Leave.status == RequestStatus.PENDING.value)
            .order_by(Leave.is_emergency.desc(), Leave.applied_on.asc())
            .all()
        )
        leave_conflicts = build_leave_conflicts(leaves)
    elif current_user.role == Role.HOD.value:
        leaves = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .filter(User.department_id == current_user.department_id, Leave.status == RequestStatus.FACULTY_APPROVED.value)
            .order_by(Leave.is_emergency.desc(), Leave.applied_on.asc())
            .all()
        )
    else:
        flash("You are not allowed to view pending leave reviews.", "danger")
        return redirect(url_for("main.index"))

    return render_template("pending.html", leaves=leaves, leave_conflicts=leave_conflicts)


@bp.route("/review/<int:leave_id>", methods=["GET", "POST"])
@login_required
def review(leave_id):
    leave = db.session.get(Leave, leave_id)
    if not leave:
        flash("Leave request not found.", "danger")
        return redirect(url_for("leaves.pending"))

    if not can_review_leave(current_user, leave):
        flash("You are not authorized to review this leave request.", "danger")
        return redirect(url_for("leaves.pending"))

    if request.method == "POST":
        action = request.form.get("action")
        comment = request.form.get("comment", "").strip()

        if action not in ("APPROVE", "REJECT"):
            flash("Invalid review action.", "danger")
            return redirect(url_for("leaves.review", leave_id=leave_id))

        success, response = apply_leave_review(leave_id, current_user.id, action, comment)
        flash(*response)
        if not success:
            return redirect(url_for("leaves.review", leave_id=leave_id))
        return redirect(url_for("leaves.pending"))

    return render_template("review.html", leave=leave)


@bp.route("/leave/<int:leave_id>/upload_proof", methods=["GET", "POST"])
@login_required
def upload_leave_proof(leave_id):
    leave = db.session.get(Leave, leave_id)
    if not leave or leave.requested_by != current_user.id:
        flash("Leave request not found.", "danger")
        return redirect(url_for("leaves.my_leaves"))

    if not leave.is_emergency:
        flash("Supporting proof can only be uploaded for emergency leave requests.", "warning")
        return redirect(url_for("leaves.my_leaves"))

    if request.method == "POST":
        proof = request.files.get("proof")
        proof_filename, proof_mimetype, proof_error = validate_uploaded_document(proof)
        if proof_error:
            flash(proof_error, "danger")
            return redirect(url_for("leaves.upload_leave_proof", leave_id=leave_id))

        try:
            save_uploaded_file(proof, current_app.config["LEAVE_UPLOAD_PREFIX"], proof_filename, proof_mimetype)
        except Exception:
            current_app.logger.exception("Failed to save leave proof for leave %s", leave_id)
            flash("Unable to store the proof document right now. Please try again.", "danger")
            return redirect(url_for("leaves.upload_leave_proof", leave_id=leave_id))

        leave.proof_filename = proof_filename
        leave.proof_mimetype = proof_mimetype
        leave.proof_uploaded_on = utcnow()
        db.session.commit()
        flash("Emergency leave proof uploaded successfully.", "success")
        return redirect(url_for("leaves.my_leaves"))

    return render_template("upload_leave_proof.html", leave=leave)


@bp.route("/leave_proof/<int:leave_id>")
@login_required
def send_leave_proof(leave_id):
    leave = db.session.get(Leave, leave_id)
    if not leave:
        flash("Leave request not found.", "danger")
        return redirect(url_for("main.index"))

    if not leave.proof_filename:
        flash("No proof has been uploaded for this leave request yet.", "warning")
        return redirect(url_for("leaves.my_leaves"))

    if not leave_proof_access_allowed(current_user, leave):
        flash("You are not authorized to access this proof file.", "danger")
        return redirect(url_for("main.index"))

    if not uploaded_file_exists(current_app.config["LEAVE_UPLOAD_PREFIX"], leave.proof_filename):
        flash("The proof file could not be found on the server.", "danger")
        return redirect(url_for("leaves.my_leaves"))

    return build_file_response(current_app.config["LEAVE_UPLOAD_PREFIX"], leave.proof_filename, leave.proof_mimetype)


@bp.route("/leave/<int:leave_id>/download_letter")
@login_required
def download_leave_letter(leave_id):
    leave = db.session.get(Leave, leave_id)
    if not leave:
        flash("Leave request not found.", "danger")
        return redirect(url_for("leaves.my_leaves"))

    if leave.status != RequestStatus.APPROVED.value:
        flash("Approval letter is only available for fully approved requests.", "warning")
        return redirect(url_for("leaves.my_leaves"))

    if not leave_proof_access_allowed(current_user, leave):
        flash("You are not authorized to access this approval letter.", "danger")
        return redirect(url_for("main.index"))

    pdf_data = generate_leave_letter_pdf(leave)
    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=leave_approval_letter_{leave.id}.pdf"},
    )


@bp.route("/student/<int:user_id>/history")
@login_required
def student_history(user_id):
    student = db.session.get(User, user_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("main.index"))

    if not student_history_access_allowed(current_user, student):
        flash("You are not authorized to view this student's history.", "danger")
        return redirect(url_for("main.index"))

    leaves = Leave.query.filter_by(requested_by=student.id).order_by(Leave.applied_on.desc()).all()
    ods = OD.query.filter_by(requested_by=student.id).order_by(OD.applied_on.desc()).all()

    return render_template(
        "student_history.html",
        student=student,
        leaves=leaves,
        ods=ods,
    )


