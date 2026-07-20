"""add preferences_json to bookings

Revision ID: 9f3b2a1c4d5e
Revises: 09a2b6ba1cef
Create Date: 2026-07-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '9f3b2a1c4d5e'
down_revision = '09a2b6ba1cef'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('preferences_json', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.drop_column('preferences_json')
