from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, Response
from flask_login import current_user, login_required

from ..extensions import db
from ..models import OD, RequestStatus, Role, User
from ..services.emailing import send_email
from ..services.uploads import build_file_response, save_uploaded_file, uploaded_file_exists, validate_uploaded_proof
from ..services.workflows import apply_od_review, can_review_od, get_assigned_faculty_for_user, is_hod_for_user
from ..services.reports import generate_od_letter_pdf
from ..services.audit import log_audit_event


bp = Blueprint("ods", __name__)


@bp.route("/apply_od", methods=["GET", "POST"])
@login_required
def apply_od():
    if current_user.role != Role.STUDENT.value:
        flash("Only students can apply for OD through this workflow.", "danger")
        return redirect(url_for("main.index"))

    if getattr(current_user, "is_blocked", False):
        flash("You have been blocked from applying for Leave and OD. Please contact your Faculty / Mentor / HOD.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        event_date_raw = request.form.get("event_date")
        reason = request.form.get("reason", "").strip()
        proof = request.files.get("proof")
        event_coordinator_id = request.form.get("event_coordinator_id", type=int)

        if not event_date_raw or not reason or not event_coordinator_id:
            flash("Event date, reason, and Event Coordinator are required.", "danger")
            return redirect(url_for("ods.apply_od"))

        try:
            event_date = datetime.strptime(event_date_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Please select a valid event date.", "danger")
            return redirect(url_for("ods.apply_od"))

        assigned_faculty_id = get_assigned_faculty_for_user(current_user)
        if not assigned_faculty_id:
            flash("No faculty is assigned to your class yet. Please contact the admin.", "danger")
            return redirect(url_for("ods.apply_od"))

        proof_filename = None
        proof_mimetype = None
        if proof and proof.filename:
            proof_filename, proof_mimetype, proof_error = validate_uploaded_proof(proof)
            if proof_error:
                flash(proof_error, "danger")
                return redirect(url_for("ods.apply_od"))
            try:
                save_uploaded_file(proof, current_app.config["OD_UPLOAD_PREFIX"], proof_filename, proof_mimetype)
            except Exception:
                current_app.logger.exception("Failed to save OD proof for user %s", current_user.id)
                flash("Unable to store the proof document right now. Please try again.", "danger")
                return redirect(url_for("ods.apply_od"))

        od = OD(
            requested_by=current_user.id,
            faculty_id=assigned_faculty_id,
            event_coordinator_id=event_coordinator_id,
            event_date=event_date,
            reason=reason,
            proof_filename=proof_filename,
            proof_mimetype=proof_mimetype,
            status=RequestStatus.PENDING.value,
        )
        db.session.add(od)
        db.session.commit()
        log_audit_event("OD_REQUESTED", od)

        event_coordinator = db.session.get(User, event_coordinator_id)
        if event_coordinator and event_coordinator.email:
            try:
                send_email(
                    "New OD Request Submitted",
                    [event_coordinator.email],
                    (
                        f"Hello {event_coordinator.full_name or event_coordinator.username},\n\n"
                        f"{current_user.full_name or current_user.username} submitted an OD request for {event_date}.\n\n"
                        f"Reason: {reason}\n"
                    ),
                )
            except Exception:
                current_app.logger.exception("Failed to queue OD submission email for OD %s", od.id)

        flash("OD request submitted successfully.", "success")
        return redirect(url_for("ods.my_ods"))

    event_coordinators = User.query.filter_by(role=Role.EVENT_COORDINATOR.value).all()
    return render_template("apply_od.html", event_coordinators=event_coordinators)


@bp.route("/my_ods")
@login_required
def my_ods():
    ods = OD.query.filter_by(requested_by=current_user.id).order_by(OD.applied_on.desc()).all()
    return render_template("my_ods.html", ods=ods)


@bp.route("/pending_od")
@login_required
def pending_od():
    if current_user.role == Role.EVENT_COORDINATOR.value:
        ods = OD.query.filter_by(
            event_coordinator_id=current_user.id,
            status=RequestStatus.PENDING.value,
        ).order_by(OD.applied_on.asc()).all()
    elif current_user.role == Role.MENTOR.value:
        ods = (
            OD.query.join(User, User.id == OD.requested_by)
            .filter(User.mentor_id == current_user.id, OD.status == RequestStatus.EVENT_COORDINATOR_APPROVED.value)
            .order_by(OD.applied_on.asc())
            .all()
        )
    elif current_user.role == Role.FACULTY.value:
        ods = OD.query.filter_by(
            faculty_id=current_user.id,
            status=RequestStatus.MENTOR_APPROVED.value,
        ).order_by(OD.applied_on.asc()).all()
    elif current_user.role == Role.HOD.value:
        ods = (
            OD.query.join(User, User.id == OD.requested_by)
            .filter(User.department_id == current_user.department_id, OD.status == RequestStatus.FACULTY_APPROVED.value)
            .order_by(OD.applied_on.asc())
            .all()
        )
    else:
        flash("You are not allowed to view pending OD reviews.", "danger")
        return redirect(url_for("main.index"))

    return render_template("pending_od.html", ods=ods)


@bp.route("/review_od/<int:od_id>", methods=["GET", "POST"])
@login_required
def review_od(od_id):
    od = db.session.get(OD, od_id)
    if not od:
        flash("OD request not found.", "danger")
        return redirect(url_for("ods.pending_od"))

    if not can_review_od(current_user, od):
        flash("You are not authorized to review this OD request.", "danger")
        return redirect(url_for("ods.pending_od"))

    if request.method == "POST":
        action = request.form.get("action")
        comment = request.form.get("comment", "").strip()

        if action not in ("APPROVE", "REJECT"):
            flash("Invalid review action.", "danger")
            return redirect(url_for("ods.review_od", od_id=od_id))

        success, response = apply_od_review(od_id, current_user.id, action, comment)
        flash(*response)
        if not success:
            return redirect(url_for("ods.review_od", od_id=od_id))
        return redirect(url_for("ods.pending_od"))

    return render_template("review_od.html", od=od)


@bp.route("/od_proof/<int:od_id>")
@login_required
def send_od_proof(od_id):
    od = db.session.get(OD, od_id)
    if not od:
        flash("OD request not found.", "danger")
        return redirect(url_for("main.index"))

    if not od.proof_filename:
        flash("No proof was uploaded for this OD request.", "warning")
        return redirect(url_for("ods.my_ods"))

    requester = od.requester
    allowed = (
        current_user.role == Role.ADMIN.value
        or current_user.id == od.requested_by
        or (current_user.role == Role.EVENT_COORDINATOR.value and od.event_coordinator_id == current_user.id)
        or (current_user.role == Role.MENTOR.value and requester and requester.mentor_id == current_user.id)
        or (current_user.role == Role.FACULTY.value and od.faculty_id == current_user.id)
        or (requester and current_user.role == Role.HOD.value and is_hod_for_user(current_user, requester))
    )

    if not allowed:
        flash("You are not authorized to access this proof file.", "danger")
        return redirect(url_for("main.index"))

    if not uploaded_file_exists(current_app.config["OD_UPLOAD_PREFIX"], od.proof_filename):
        flash("The proof file could not be found on the server.", "danger")
        target = "ods.my_ods" if current_user.role == Role.STUDENT.value else "ods.pending_od"
        return redirect(url_for(target))

    log_audit_event("OD_PROOF_DOWNLOADED", od)
    return build_file_response(current_app.config["OD_UPLOAD_PREFIX"], od.proof_filename, od.proof_mimetype)


@bp.route("/od/<int:od_id>/download_letter")
@login_required
def download_od_letter(od_id):
    od = db.session.get(OD, od_id)
    if not od:
        flash("OD request not found.", "danger")
        return redirect(url_for("ods.my_ods"))

    if od.status != RequestStatus.APPROVED.value:
        flash("Approval letter is only available for fully approved requests.", "warning")
        return redirect(url_for("ods.my_ods"))

    requester = od.requester
    allowed = (
        current_user.role == Role.ADMIN.value
        or current_user.id == od.requested_by
        or (current_user.role == Role.EVENT_COORDINATOR.value and od.event_coordinator_id == current_user.id)
        or (current_user.role == Role.MENTOR.value and requester and requester.mentor_id == current_user.id)
        or (current_user.role == Role.FACULTY.value and od.faculty_id == current_user.id)
        or (requester and current_user.role == Role.HOD.value and is_hod_for_user(current_user, requester))
    )

    if not allowed:
        flash("You are not authorized to access this approval letter.", "danger")
        return redirect(url_for("main.index"))

    pdf_data = generate_od_letter_pdf(od)
    log_audit_event("OD_LETTER_DOWNLOADED", od)
    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=od_approval_letter_{od.id}.pdf"},
    )

