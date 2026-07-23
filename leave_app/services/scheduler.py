import os
import threading
import time
from ..models import ClassGroup, Leave, OD, RequestStatus, Role, User
from .emailing import send_email, process_email_queue


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


def start_email_worker(app):
    def worker():
        time.sleep(3)
        while True:
            try:
                with app.app_context():
                    process_email_queue()
            except Exception as exc:
                app.logger.error("Error in background email queue processor: %s", exc)
            time.sleep(10)

    thread = threading.Thread(target=worker, daemon=True, name="permitrack-email-worker")
    thread.start()


def register_scheduler(app):
    is_main_process = os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug
    if not app.config.get("TESTING") and is_main_process:
        start_email_worker(app)

