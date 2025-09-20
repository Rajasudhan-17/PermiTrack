"""Add faculty_id to user

Revision ID: c0bc29e75c6d
Revises: 
Create Date: 2025-09-18 10:18:53.603211

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'c0bc29e75c6d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('faculty_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_user_faculty', 'user', 'user', ['faculty_id'], ['id'])
def downgrade():
    op.drop_column('users', 'faculty_id')
    op.drop_constraint('fk_user_faculty', 'user', type_='foreignkey')
