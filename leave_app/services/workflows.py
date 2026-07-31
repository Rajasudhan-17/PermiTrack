from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import select
from sqlalchemy.orm.exc import StaleDataError

from ..extensions import db
from ..models import ClassGroup, Leave, OD, RequestStatus, Role, User
from .emailing import send_email
from .audit import log_audit_event


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_form_value(form, key, cast=str):
    values = [value for value in form.getlist(key) if value not in (None, "")]
    if not values:
        return None

    raw_value = values[-1]
    if cast is int:
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None
    if cast is str:
        return raw_value
    return cast(raw_value)


def get_assigned_faculty_for_user(user):
    if user.class_group and user.class_group.faculty_id:
        return user.class_group.faculty_id
    if user.faculty_id:
        return user.faculty_id
    return None


def is_hod_for_user(hod_user, target_user):
    return bool(
        hod_user.role == Role.HOD.value
        and hod_user.id
        and target_user.department
        and target_user.department.hod_id == hod_user.id
    )


def can_review_leave(user, leave):
    applicant = leave.requester
    if not applicant:
        return False
    if user.role == Role.MENTOR.value:
        return (
            leave.status == RequestStatus.PENDING.value
            and applicant.mentor_id == user.id
        )
    if user.role == Role.FACULTY.value:
        return (
            leave.status == RequestStatus.MENTOR_APPROVED.value
            and applicant.class_group
            and applicant.class_group.faculty_id == user.id
        )
    if user.role == Role.HOD.value:
        return leave.status == RequestStatus.FACULTY_APPROVED.value and is_hod_for_user(user, applicant)
    return False


def can_review_od(user, od):
    applicant = od.requester
    if not applicant:
        return False
    if user.role == Role.EVENT_COORDINATOR.value:
        return od.status == RequestStatus.PENDING.value and od.event_coordinator_id == user.id
    if user.role == Role.MENTOR.value:
        return od.status == RequestStatus.EVENT_COORDINATOR_APPROVED.value and applicant.mentor_id == user.id
    if user.role == Role.FACULTY.value:
        return od.status == RequestStatus.MENTOR_APPROVED.value and od.faculty_id == user.id
    if user.role == Role.HOD.value:
        return od.status == RequestStatus.FACULTY_APPROVED.value and is_hod_for_user(user, applicant)
    return False


def status_badge(status):
    mapping = {
        RequestStatus.PENDING.value: "warning",
        RequestStatus.EVENT_COORDINATOR_APPROVED.value: "info",
        RequestStatus.MENTOR_APPROVED.value: "info",
        RequestStatus.FACULTY_APPROVED.value: "info",
        RequestStatus.APPROVED.value: "success",
        RequestStatus.REJECTED.value: "danger",
    }
    return mapping.get(status, "secondary")


def pending_counts_for_user(user):
    pending_leave_count = 0
    pending_od_count = 0

    if not user.is_authenticated:
        return pending_leave_count, pending_od_count

    if user.role == Role.EVENT_COORDINATOR.value:
        pending_leave_count = 0
        pending_od_count = OD.query.filter_by(status=RequestStatus.PENDING.value, event_coordinator_id=user.id).count()
    elif user.role == Role.MENTOR.value:
        pending_leave_count = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .filter(User.mentor_id == user.id, Leave.status == RequestStatus.PENDING.value)
            .count()
        )
        pending_od_count = (
            OD.query.join(User, User.id == OD.requested_by)
            .filter(User.mentor_id == user.id, OD.status == RequestStatus.EVENT_COORDINATOR_APPROVED.value)
            .count()
        )
    elif user.role == Role.FACULTY.value:
        pending_leave_count = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .join(ClassGroup, ClassGroup.id == User.class_group_id)
            .filter(ClassGroup.faculty_id == user.id, Leave.status == RequestStatus.MENTOR_APPROVED.value)
            .count()
        )
        pending_od_count = OD.query.filter_by(status=RequestStatus.MENTOR_APPROVED.value, faculty_id=user.id).count()
    elif user.role == Role.HOD.value:
        pending_leave_count = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .filter(User.department_id == user.department_id, Leave.status == RequestStatus.FACULTY_APPROVED.value)
            .count()
        )
        pending_od_count = (
            OD.query.join(User, User.id == OD.requested_by)
            .filter(User.department_id == user.department_id, OD.status == RequestStatus.FACULTY_APPROVED.value)
            .count()
        )

    return pending_leave_count, pending_od_count


def leave_proof_access_allowed(user, leave):
    requester = leave.requester
    if not requester:
        return False

    return bool(
        user.role == Role.ADMIN.value
        or user.id == leave.requested_by
        or (user.role == Role.MENTOR.value and requester.mentor_id == user.id)
        or (
            user.role == Role.FACULTY.value
            and requester.class_group
            and requester.class_group.faculty_id == user.id
        )
        or is_hod_for_user(user, requester)
    )


def student_history_access_allowed(user, student):
    if not student:
        return False
    if user.id == student.id:
        return True
    if user.role == Role.ADMIN.value:
        return True
    if user.role == Role.HOD.value:
        return student.department_id == user.department_id
    if user.role == Role.MENTOR.value:
        return student.mentor_id == user.id
    if user.role == Role.FACULTY.value:
        if student.class_group and student.class_group.faculty_id == user.id:
            return True
        if student.faculty_id == user.id:
            return True
    if user.role == Role.EVENT_COORDINATOR.value:
        return OD.query.filter_by(requested_by=student.id, event_coordinator_id=user.id).first() is not None
    return False



def build_leave_conflict_snapshot(leave):
    requester = leave.requester
    class_group_id = requester.class_group_id if requester else None
    if not class_group_id:
        return {
            "count": 0,
            "level": "low",
            "message": "No class assignment available for conflict analysis.",
        }

    leave_count = (
        Leave.query.join(User, User.id == Leave.requested_by)
        .filter(
            User.class_group_id == class_group_id,
            Leave.id != leave.id,
            Leave.status.in_(
                [
                    RequestStatus.PENDING.value,
                    RequestStatus.FACULTY_APPROVED.value,
                    RequestStatus.APPROVED.value,
                ]
            ),
            Leave.start_date <= leave.end_date,
            Leave.end_date >= leave.start_date,
        )
        .count()
    )
    od_count = (
        OD.query.join(User, User.id == OD.requested_by)
        .filter(
            User.class_group_id == class_group_id,
            OD.status.in_(
                [
                    RequestStatus.PENDING.value,
                    RequestStatus.FACULTY_APPROVED.value,
                    RequestStatus.APPROVED.value,
                ]
            ),
            OD.event_date >= leave.start_date,
            OD.event_date <= leave.end_date,
        )
        .count()
    )

    total_conflicts = leave_count + od_count
    threshold = current_app.config.get("FACULTY_CONFLICT_THRESHOLD", 3)
    if total_conflicts >= threshold:
        message = f"High conflict: {total_conflicts} other absence(s) overlap this period."
        level = "high"
    elif total_conflicts > 0:
        message = f"Watchlist: {total_conflicts} other absence(s) overlap this period."
        level = "medium"
    else:
        message = "No overlapping absences detected for this class."
        level = "low"

    return {"count": total_conflicts, "level": level, "message": message}


def build_leave_conflicts(leaves):
    return {leave.id: build_leave_conflict_snapshot(leave) for leave in leaves}


def supports_row_locking():
    engine = db.session.get_bind()
    return engine is not None and engine.dialect.name != "sqlite"


def locked_scalar(statement):
    if supports_row_locking():
        statement = statement.with_for_update()
    return db.session.execute(statement).scalar_one_or_none()


def lock_user(user_id):
    return locked_scalar(select(User).where(User.id == user_id))


def lock_leave(leave_id):
    return locked_scalar(select(Leave).where(Leave.id == leave_id))


def lock_od(od_id):
    return locked_scalar(select(OD).where(OD.id == od_id))


def notify_leave_submission(leave, applicant):
    reviewer = db.session.get(User, leave.approved_by) if leave.approved_by else None
    if not reviewer or not reviewer.email:
        return

    send_email(
        "New Leave Request Submitted",
        [reviewer.email],
        (
            f"Hello {reviewer.full_name or reviewer.username},\n\n"
            f"{applicant.full_name or applicant.username} submitted a leave request from "
            f"{leave.start_date} to {leave.end_date}.\n\n"
            f"Reason: {leave.reason}\n"
            f"Emergency: {'Yes' if leave.is_emergency else 'No'}\n"
        ),
    )


def submit_leave_request(user, start_date, end_date, reason, is_emergency):
    try:
        locked_user = lock_user(user.id)
        if not locked_user:
            return False, None, ("Unable to load your account details. Please try again.", "danger")

        if getattr(locked_user, "is_blocked", False):
            db.session.rollback()
            return False, None, ("You have been blocked from applying for Leave and OD.", "danger")

        overlapping_leave = Leave.query.filter(
            Leave.requested_by == locked_user.id,
            Leave.status.in_(
                [
                    RequestStatus.PENDING.value,
                    RequestStatus.FACULTY_APPROVED.value,
                    RequestStatus.APPROVED.value,
                ]
            ),
            Leave.start_date <= end_date,
            Leave.end_date >= start_date,
        ).first()
        if overlapping_leave:
            db.session.rollback()
            return False, None, ("You already have a leave request overlapping this period.", "warning")

        if locked_user.role == Role.STUDENT.value and not locked_user.mentor_id:
            db.session.rollback()
            return False, None, ("No mentor is assigned to your account yet. Please contact the HOD/Admin.", "danger")

        requested_days = (end_date - start_date).days + 1
        if (
            locked_user.role == Role.STUDENT.value
            and not is_emergency
            and locked_user.leave_balance < requested_days
        ):
            db.session.rollback()
            return (
                False,
                None,
                (
                    f"Not enough leave balance. You currently have {locked_user.leave_balance} day(s) left.",
                    "danger",
                ),
            )

        leave = Leave(
            requested_by=locked_user.id,
            approved_by=locked_user.mentor_id if locked_user.role == Role.STUDENT.value else get_assigned_faculty_for_user(locked_user),
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            is_emergency=is_emergency,
            status=RequestStatus.PENDING.value,
        )
        db.session.add(leave)
        db.session.commit()
        log_audit_event("LEAVE_REQUESTED", leave)
        notify_leave_submission(leave, locked_user)
        return True, leave, None
    except StaleDataError:
        db.session.rollback()
        return False, None, ("Your account was updated by another request. Please try again.", "warning")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to submit leave request.")
        return False, None, ("Unable to submit the leave request right now. Please try again.", "danger")


def apply_leave_review(leave_id, reviewer_id, action, comment):
    try:
        reviewer = db.session.get(User, reviewer_id)
        leave = lock_leave(leave_id)
        if not reviewer or not leave:
            db.session.rollback()
            return False, ("Leave request not found.", "danger")

        applicant = lock_user(leave.requested_by)
        if not applicant:
            db.session.rollback()
            return False, ("Leave request applicant could not be loaded.", "danger")

        leave.requester = applicant
        if not can_review_leave(reviewer, leave):
            db.session.rollback()
            return False, ("This leave request is no longer available for your review.", "warning")

        email_subject = None
        email_recipients = []
        email_body = None

        if action == "APPROVE":
            if reviewer.role == Role.MENTOR.value:
                leave.status = RequestStatus.MENTOR_APPROVED.value
                leave.approved_by = reviewer.id
                email_subject = "Leave Forwarded to Faculty"
                email_recipients = [applicant.email]
                email_body = (
                    f"Dear {applicant.full_name or applicant.username},\n\n"
                    f"Your leave request from {leave.start_date} to {leave.end_date} was approved by mentor "
                    f"{reviewer.full_name or reviewer.username} and forwarded to the Faculty advisor.\n\n"
                    f"Comment: {comment or 'No comment'}\n"
                )
                flash_message = "Leave approved by mentor and forwarded to the Faculty."
                flash_category = "success"
            elif reviewer.role == Role.FACULTY.value:
                leave.status = RequestStatus.FACULTY_APPROVED.value
                leave.approved_by = reviewer.id
                email_subject = "Leave Forwarded to HOD"
                email_recipients = [applicant.email]
                email_body = (
                    f"Dear {applicant.full_name or applicant.username},\n\n"
                    f"Your leave request from {leave.start_date} to {leave.end_date} was approved by faculty "
                    f"{reviewer.full_name or reviewer.username} and forwarded to the HOD.\n\n"
                    f"Comment: {comment or 'No comment'}\n"
                )
                flash_message = "Leave approved by faculty and forwarded to the HOD."
                flash_category = "success"
            elif reviewer.role == Role.HOD.value:
                requested_days = (leave.end_date - leave.start_date).days + 1
                if applicant.leave_balance < requested_days:
                    db.session.rollback()
                    return False, (
                        f"The student does not have enough leave balance ({applicant.leave_balance} day(s) left).",
                        "danger",
                    )

                applicant.leave_balance -= requested_days
                leave.status = RequestStatus.APPROVED.value
                leave.approved_by = reviewer.id
                email_subject = "Leave Approved"
                email_recipients = [applicant.email]
                email_body = (
                    f"Dear {applicant.full_name or applicant.username},\n\n"
                    f"Your leave request from {leave.start_date} to {leave.end_date} has been approved by the HOD.\n\n"
                    f"Comment: {comment or 'No comment'}\n"
                )
                flash_message = "Leave fully approved and leave balance updated."
                flash_category = "success"
            else:
                db.session.rollback()
                return False, ("Your role is not authorized to approve leaves.", "danger")
        else:
            leave.status = RequestStatus.REJECTED.value
            leave.approved_by = reviewer.id
            email_subject = "Leave Rejected"
            email_recipients = [applicant.email]
            email_body = (
                f"Dear {applicant.full_name or applicant.username},\n\n"
                f"Your leave request from {leave.start_date} to {leave.end_date} has been rejected.\n\n"
                f"Comment: {comment or 'No comment'}\n"
            )
            flash_message = "Leave request rejected."
            flash_category = "warning"

        leave.review_comment = comment
        leave.reviewed_on = utcnow()
        db.session.commit()
        log_audit_event(
            f"LEAVE_REVIEW_{action}",
            leave,
            details=f"Reviewer: {reviewer.username} (Role: {reviewer.role}), Comment: {comment or ''}"
        )

        if email_subject and email_recipients and email_body is not None:
            try:
                send_email(email_subject, email_recipients, email_body)
            except Exception as exc:
                current_app.logger.exception(
                    "Failed to send leave review email for leave %s: %s", leave_id, exc
                )

        return True, (flash_message, flash_category)
    except StaleDataError:
        db.session.rollback()
        return False, ("This leave request was updated by another reviewer. Please refresh and try again.", "warning")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to review leave request %s", leave_id)
        return False, ("Unable to save this leave review right now. Please try again.", "danger")


def apply_od_review(od_id, reviewer_id, action, comment):
    try:
        reviewer = db.session.get(User, reviewer_id)
        od = lock_od(od_id)
        if not reviewer or not od:
            db.session.rollback()
            return False, ("OD request not found.", "danger")

        applicant = lock_user(od.requested_by)
        if not applicant:
            db.session.rollback()
            return False, ("OD request applicant could not be loaded.", "danger")

        od.requester = applicant
        if not can_review_od(reviewer, od):
            db.session.rollback()
            return False, ("This OD request is no longer available for your review.", "warning")

        email_subject = None
        email_recipients = []
        email_body = None

        if action == "APPROVE":
            if reviewer.role == Role.EVENT_COORDINATOR.value:
                od.status = RequestStatus.EVENT_COORDINATOR_APPROVED.value
                od.approved_by = reviewer.id
                email_subject = "OD Forwarded to Mentor"
                email_recipients = [applicant.email]
                email_body = (
                    f"Dear {applicant.full_name or applicant.username},\n\n"
                    f"Your OD request for {od.event_date} was approved by event coordinator "
                    f"{reviewer.full_name or reviewer.username} and forwarded to your Mentor.\n\n"
                    f"Comment: {comment or 'No comment'}\n"
                )
                flash_message = "OD approved by event coordinator and forwarded to the Mentor."
                flash_category = "success"
            elif reviewer.role == Role.MENTOR.value:
                od.status = RequestStatus.MENTOR_APPROVED.value
                od.approved_by = reviewer.id
                email_subject = "OD Forwarded to Faculty"
                email_recipients = [applicant.email]
                email_body = (
                    f"Dear {applicant.full_name or applicant.username},\n\n"
                    f"Your OD request for {od.event_date} was approved by mentor "
                    f"{reviewer.full_name or reviewer.username} and forwarded to the Faculty advisor.\n\n"
                    f"Comment: {comment or 'No comment'}\n"
                )
                flash_message = "OD approved by mentor and forwarded to the Faculty."
                flash_category = "success"
            elif reviewer.role == Role.FACULTY.value:
                od.status = RequestStatus.FACULTY_APPROVED.value
                od.approved_by = reviewer.id
                email_subject = "OD Forwarded to HOD"
                email_recipients = [applicant.email]
                email_body = (
                    f"Dear {applicant.full_name or applicant.username},\n\n"
                    f"Your OD request for {od.event_date} was approved by faculty "
                    f"{reviewer.full_name or reviewer.username} and forwarded to the HOD.\n\n"
                    f"Comment: {comment or 'No comment'}\n"
                )
                flash_message = "OD approved by faculty and forwarded to the HOD."
                flash_category = "success"
            elif reviewer.role == Role.HOD.value:
                od.status = RequestStatus.APPROVED.value
                od.approved_by = reviewer.id
                email_subject = "OD Approved"
                email_recipients = [applicant.email]
                email_body = (
                    f"Dear {applicant.full_name or applicant.username},\n\n"
                    f"Your OD request for {od.event_date} has been approved by the HOD.\n\n"
                    f"Comment: {comment or 'No comment'}\n"
                )
                flash_message = "OD fully approved."
                flash_category = "success"
            else:
                db.session.rollback()
                return False, ("Your role is not authorized to approve ODs.", "danger")
        else:
            od.status = RequestStatus.REJECTED.value
            od.approved_by = reviewer.id
            email_subject = "OD Rejected"
            email_recipients = [applicant.email]
            email_body = (
                f"Dear {applicant.full_name or applicant.username},\n\n"
                f"Your OD request for {od.event_date} has been rejected.\n\n"
                f"Comment: {comment or 'No comment'}\n"
            )
            flash_message = "OD request rejected."
            flash_category = "warning"

        od.review_comment = comment
        od.reviewed_on = utcnow()
        db.session.commit()
        log_audit_event(
            f"OD_REVIEW_{action}",
            od,
            details=f"Reviewer: {reviewer.username} (Role: {reviewer.role}), Comment: {comment or ''}"
        )

        if email_subject and email_recipients and email_body is not None:
            try:
                send_email(email_subject, email_recipients, email_body)
            except Exception as exc:
                current_app.logger.exception(
                    "Failed to send OD review email for OD %s: %s", od_id, exc
                )

        return True, (flash_message, flash_category)
    except StaleDataError:
        db.session.rollback()
        return False, ("This OD request was updated by another reviewer. Please refresh and try again.", "warning")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to review OD request %s", od_id)
        return False, ("Unable to save this OD review right now. Please try again.", "danger")
