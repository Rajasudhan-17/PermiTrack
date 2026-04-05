from datetime import datetime, timezone
from enum import StrEnum

from flask_login import UserMixin

from .extensions import db


class Role(StrEnum):
    STUDENT = "student"
    FACULTY = "faculty"
    HOD = "hod"
    ADMIN = "admin"


class RequestStatus(StrEnum):
    PENDING = "PENDING"
    FACULTY_APPROVED = "FACULTY_APPROVED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class EmailStatus(StrEnum):
    QUEUED = "QUEUED"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"


ROLE_SQL = ", ".join(f"'{role.value}'" for role in Role)
REQUEST_STATUS_SQL = ", ".join(f"'{status.value}'" for status in RequestStatus)
EMAIL_STATUS_SQL = ", ".join(f"'{status.value}'" for status in EmailStatus)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Department(db.Model):
    __tablename__ = "department"
    __table_args__ = (
        db.CheckConstraint("length(trim(name)) > 0", name="ck_department_name_not_blank"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    hod_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    hod = db.relationship("User", foreign_keys=[hod_id], backref="hod_of_department", uselist=False)
    classes = db.relationship("ClassGroup", back_populates="department", lazy=True)


class ClassGroup(db.Model):
    __tablename__ = "class_group"
    __table_args__ = (
        db.UniqueConstraint("department_id", "year", "section", name="uq_class_group_department_year_section"),
        db.CheckConstraint("year >= 1", name="ck_class_group_year_positive"),
        db.CheckConstraint("length(trim(section)) > 0", name="ck_class_group_section_not_blank"),
        db.Index("ix_class_group_faculty_id", "faculty_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    department = db.relationship("Department", back_populates="classes")
    faculty = db.relationship("User", foreign_keys=[faculty_id], backref="assigned_classes", uselist=False)

    def __repr__(self):
        department_name = self.department.name if self.department else "Unknown"
        return f"<ClassGroup {department_name} Y{self.year}{self.section}>"


class User(UserMixin, db.Model):
    __tablename__ = "user"
    __table_args__ = (
        db.CheckConstraint(f"role in ({ROLE_SQL})", name="ck_user_role_valid"),
        db.CheckConstraint("leave_balance >= 0", name="ck_user_leave_balance_non_negative"),
        db.Index("ix_user_role", "role"),
        db.Index("ix_user_department_role", "department_id", "role"),
        db.Index("ix_user_class_group_id", "class_group_id"),
        db.Index("ix_user_faculty_id", "faculty_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150))
    role = db.Column(db.String(20), default=Role.STUDENT.value, nullable=False)
    leave_balance = db.Column(db.Integer, default=20, nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)
    class_group_id = db.Column(db.Integer, db.ForeignKey("class_group.id"), nullable=True)
    version_id = db.Column(db.Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version_id}

    faculty = db.relationship("User", remote_side=[id], backref="students")
    department = db.relationship("Department", foreign_keys=[department_id], backref="users", uselist=False)
    class_group = db.relationship("ClassGroup", foreign_keys=[class_group_id], backref="students", uselist=False)
    requested_leaves = db.relationship("Leave", foreign_keys="Leave.requested_by", backref="requester", lazy=True)
    approved_leaves = db.relationship("Leave", foreign_keys="Leave.approved_by", backref="approver", lazy=True)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash

        return check_password_hash(self.password_hash, password)


class Leave(db.Model):
    __tablename__ = "leave"
    __table_args__ = (
        db.CheckConstraint("end_date >= start_date", name="ck_leave_dates_valid"),
        db.CheckConstraint(f"status in ({REQUEST_STATUS_SQL})", name="ck_leave_status_valid"),
        db.Index("ix_leave_requested_by_status", "requested_by", "status"),
        db.Index("ix_leave_status_applied_on", "status", "applied_on"),
        db.Index("ix_leave_start_end", "start_date", "end_date"),
        db.Index("ix_leave_approved_by", "approved_by"),
    )

    id = db.Column(db.Integer, primary_key=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    is_emergency = db.Column(db.Boolean, default=False, nullable=False)
    proof_filename = db.Column(db.String(300), nullable=True)
    proof_mimetype = db.Column(db.String(120), nullable=True)
    proof_uploaded_on = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), default=RequestStatus.PENDING.value, nullable=False)
    applied_on = db.Column(db.DateTime, default=utcnow, nullable=False)
    review_comment = db.Column(db.Text, nullable=True)
    reviewed_on = db.Column(db.DateTime, nullable=True)
    version_id = db.Column(db.Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version_id}

    @property
    def applicant(self):
        return self.requester

    @property
    def requires_followup_proof(self):
        return self.is_emergency and not self.proof_filename


class OD(db.Model):
    __tablename__ = "od"
    __table_args__ = (
        db.CheckConstraint(f"status in ({REQUEST_STATUS_SQL})", name="ck_od_status_valid"),
        db.Index("ix_od_requested_by_status", "requested_by", "status"),
        db.Index("ix_od_faculty_id_status", "faculty_id", "status"),
        db.Index("ix_od_status_applied_on", "status", "applied_on"),
        db.Index("ix_od_event_date", "event_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    event_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    proof_filename = db.Column(db.String(300), nullable=True)
    proof_mimetype = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), default=RequestStatus.PENDING.value, nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    applied_on = db.Column(db.DateTime, default=utcnow, nullable=False)
    review_comment = db.Column(db.Text, nullable=True)
    reviewed_on = db.Column(db.DateTime, nullable=True)
    version_id = db.Column(db.Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version_id}

    faculty = db.relationship("User", foreign_keys=[faculty_id])
    requester = db.relationship("User", foreign_keys=[requested_by])
    approver = db.relationship("User", foreign_keys=[approved_by])

    @property
    def applicant(self):
        return self.requester


class EmailQueue(db.Model):
    __tablename__ = "email_queue"
    __table_args__ = (
        db.CheckConstraint(f"status in ({EMAIL_STATUS_SQL})", name="ck_email_queue_status_valid"),
        db.Index("ix_email_queue_status_available_at", "status", "available_at"),
        db.Index("ix_email_queue_created_at", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    recipients = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=EmailStatus.QUEUED.value)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.Text, nullable=True)
    available_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)


class LoginAttempt(db.Model):
    __tablename__ = "login_attempt"
    __table_args__ = (
        db.Index("ix_login_attempt_locked_until", "locked_until"),
        db.Index("ix_login_attempt_last_attempt_at", "last_attempt_at"),
    )

    key = db.Column(db.String(255), primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    ip_address = db.Column(db.String(64), nullable=False)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    window_started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_attempt_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    locked_until = db.Column(db.DateTime, nullable=True)
