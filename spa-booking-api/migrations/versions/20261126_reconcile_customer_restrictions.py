"""Preserve legacy customer blocks as restriction records.

Revision ID: 20261126_customer_restrictions
Revises: 20260721_add_booking_therapists_table
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op


revision = '20261126_customer_restrictions'
down_revision = '20260721_add_booking_therapists_table'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    customers = sa.table('customers',
                         sa.column('id', sa.Integer),
                         sa.column('phone_number', sa.String),
                         sa.column('is_blocked', sa.Boolean))
    restrictions = sa.table('customer_restrictions',
                            sa.column('customer_id', sa.Integer),
                            sa.column('phone_number', sa.String),
                            sa.column('reason', sa.Text),
                            sa.column('blocked_by', sa.String),
                            sa.column('blocked_at', sa.DateTime),
                            sa.column('updated_at', sa.DateTime),
                            sa.column('is_active', sa.Boolean))
    rows = connection.execute(sa.select(customers.c.id, customers.c.phone_number,
                                        customers.c.is_blocked)).all()
    for customer_id, phone, was_blocked in rows:
        active = connection.execute(sa.select(restrictions.c.customer_id).where(
            restrictions.c.customer_id == customer_id,
            restrictions.c.is_active.is_(True),
        ).limit(1)).first()
        if was_blocked and active is None:
            now = datetime.utcnow()
            connection.execute(restrictions.insert().values(
                customer_id=customer_id,
                phone_number=phone,
                reason='Legacy block; original reason unavailable',
                blocked_by='legacy migration',
                blocked_at=now,
                updated_at=now,
                is_active=True,
            ))
        connection.execute(customers.update().where(customers.c.id == customer_id).values(
            is_blocked=bool(was_blocked or active is not None)))


def downgrade():
    # Preserve block history; this data reconciliation has no safe inverse.
    pass
