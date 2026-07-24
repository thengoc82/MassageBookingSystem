"""add booking_therapists association table

Revision ID: 20260721_add_booking_therapists_table
Revises: b3c4d5e6f7a0
Create Date: 2026-07-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260721_add_booking_therapists_table'
down_revision = 'b3c4d5e6f7a0'
branch_labels = None
depends_on = None


def upgrade():
    # Create booking_therapists association table
    op.create_table(
        'booking_therapists',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False, index=True),
        sa.Column('person_index', sa.Integer(), nullable=False),
        sa.Column('therapist_id', sa.Integer(), nullable=False, index=True),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['therapist_id'], ['therapists.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('booking_id', 'person_index', name='uq_booking_person')
    )


def downgrade():
    op.drop_table('booking_therapists')