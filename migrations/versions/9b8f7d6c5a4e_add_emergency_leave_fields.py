"""add emergency leave fields

Revision ID: 9b8f7d6c5a4e
Revises: ffab3e36b707
Create Date: 2026-04-01 19:20:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b8f7d6c5a4e"
down_revision = "ffab3e36b707"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("leave", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_emergency", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("proof_filename", sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column("proof_mimetype", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("proof_uploaded_on", sa.DateTime(), nullable=True))

    with op.batch_alter_table("leave", schema=None) as batch_op:
        batch_op.alter_column("is_emergency", server_default=None)


def downgrade():
    with op.batch_alter_table("leave", schema=None) as batch_op:
        batch_op.drop_column("proof_uploaded_on")
        batch_op.drop_column("proof_mimetype")
        batch_op.drop_column("proof_filename")
        batch_op.drop_column("is_emergency")
