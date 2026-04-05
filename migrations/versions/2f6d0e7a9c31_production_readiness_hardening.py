"""production readiness hardening

Revision ID: 2f6d0e7a9c31
Revises: 9b8f7d6c5a4e
Create Date: 2026-04-04 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2f6d0e7a9c31"
down_revision = "9b8f7d6c5a4e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_index("ix_user_role", ["role"], unique=False)
        batch_op.create_index("ix_user_department_role", ["department_id", "role"], unique=False)
        batch_op.create_index("ix_user_class_group_id", ["class_group_id"], unique=False)
        batch_op.create_index("ix_user_faculty_id", ["faculty_id"], unique=False)
        batch_op.alter_column("version_id", server_default=None)

    with op.batch_alter_table("leave", schema=None) as batch_op:
        batch_op.add_column(sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_index("ix_leave_requested_by_status", ["requested_by", "status"], unique=False)
        batch_op.create_index("ix_leave_status_applied_on", ["status", "applied_on"], unique=False)
        batch_op.create_index("ix_leave_start_end", ["start_date", "end_date"], unique=False)
        batch_op.create_index("ix_leave_approved_by", ["approved_by"], unique=False)
        batch_op.alter_column("version_id", server_default=None)

    with op.batch_alter_table("od", schema=None) as batch_op:
        batch_op.add_column(sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_index("ix_od_requested_by_status", ["requested_by", "status"], unique=False)
        batch_op.create_index("ix_od_faculty_id_status", ["faculty_id", "status"], unique=False)
        batch_op.create_index("ix_od_status_applied_on", ["status", "applied_on"], unique=False)
        batch_op.create_index("ix_od_event_date", ["event_date"], unique=False)
        batch_op.alter_column("version_id", server_default=None)

    with op.batch_alter_table("class_group", schema=None) as batch_op:
        batch_op.create_index("ix_class_group_faculty_id", ["faculty_id"], unique=False)

    op.create_table(
        "email_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("recipients", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status in ('QUEUED', 'SENDING', 'SENT', 'FAILED')", name="ck_email_queue_status_valid"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_queue_status_available_at", "email_queue", ["status", "available_at"], unique=False)
    op.create_index("ix_email_queue_created_at", "email_queue", ["created_at"], unique=False)

    op.create_table(
        "login_attempt",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("ix_login_attempt_locked_until", "login_attempt", ["locked_until"], unique=False)
    op.create_index("ix_login_attempt_last_attempt_at", "login_attempt", ["last_attempt_at"], unique=False)


def downgrade():
    op.drop_index("ix_login_attempt_last_attempt_at", table_name="login_attempt")
    op.drop_index("ix_login_attempt_locked_until", table_name="login_attempt")
    op.drop_table("login_attempt")

    op.drop_index("ix_email_queue_created_at", table_name="email_queue")
    op.drop_index("ix_email_queue_status_available_at", table_name="email_queue")
    op.drop_table("email_queue")

    with op.batch_alter_table("class_group", schema=None) as batch_op:
        batch_op.drop_index("ix_class_group_faculty_id")

    with op.batch_alter_table("od", schema=None) as batch_op:
        batch_op.drop_index("ix_od_event_date")
        batch_op.drop_index("ix_od_status_applied_on")
        batch_op.drop_index("ix_od_faculty_id_status")
        batch_op.drop_index("ix_od_requested_by_status")
        batch_op.drop_column("version_id")

    with op.batch_alter_table("leave", schema=None) as batch_op:
        batch_op.drop_index("ix_leave_approved_by")
        batch_op.drop_index("ix_leave_start_end")
        batch_op.drop_index("ix_leave_status_applied_on")
        batch_op.drop_index("ix_leave_requested_by_status")
        batch_op.drop_column("version_id")

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_index("ix_user_faculty_id")
        batch_op.drop_index("ix_user_class_group_id")
        batch_op.drop_index("ix_user_department_role")
        batch_op.drop_index("ix_user_role")
        batch_op.drop_column("version_id")
