from ..models import ClassGroup, Leave, OD, RequestStatus, Role, User
from .emailing import send_email


def queue_daily_summary_emails():
    faculties = User.query.filter_by(role=Role.FACULTY.value).all()
    hods = User.query.filter_by(role=Role.HOD.value).all()

    for faculty in faculties:
        pending_ods = OD.query.filter_by(faculty_id=faculty.id, status=RequestStatus.PENDING.value).count()
        pending_leaves = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .join(ClassGroup, ClassGroup.id == User.class_group_id)
            .filter(ClassGroup.faculty_id == faculty.id, Leave.status == RequestStatus.PENDING.value)
            .count()
        )
        if pending_ods or pending_leaves:
            send_email(
                "Daily Pending Applications",
                [faculty.email],
                (
                    f"Hello {faculty.full_name or faculty.username},\n\n"
                    f"You have {pending_ods} OD request(s) and {pending_leaves} leave request(s) pending review."
                ),
            )

    for hod in hods:
        pending_ods = (
            OD.query.join(User, User.id == OD.requested_by)
            .filter(User.department_id == hod.department_id, OD.status == RequestStatus.FACULTY_APPROVED.value)
            .count()
        )
        pending_leaves = (
            Leave.query.join(User, User.id == Leave.requested_by)
            .filter(User.department_id == hod.department_id, Leave.status == RequestStatus.FACULTY_APPROVED.value)
            .count()
        )
        if pending_ods or pending_leaves:
            send_email(
                "Daily Pending Applications",
                [hod.email],
                (
                    f"Hello {hod.full_name or hod.username},\n\n"
                    f"You have {pending_ods} OD request(s) and {pending_leaves} leave request(s) waiting for your review."
                ),
            )


def register_scheduler(_app):
    # In production, summary generation should run from a dedicated scheduler
    # such as cron, ECS Scheduled Tasks, or EventBridge instead of the web app.
    return None
