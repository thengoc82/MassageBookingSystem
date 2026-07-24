"""add username and password to therapists

Revision ID: a2b3c4d5e6f7
Revises: 9f3b2a1c4d5e
Create Date: 2026-07-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a2b3c4d5e6f7'
down_revision = '9f3b2a1c4d5e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('therapists', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('password', sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint('uq_therapists_username', ['username'])


def downgrade():
    with op.batch_alter_table('therapists', schema=None) as batch_op:
        batch_op.drop_constraint('uq_therapists_username', type_='unique')
        batch_op.drop_column('password')
        batch_op.drop_column('username')
