"""Update reservation schema for capacity-based flow

Revision ID: 09a2b6ba1cef
Revises: 23ef72500a61
Create Date: 2026-07-16 21:45:30.136636

"""
from alembic import op
import sqlalchemy as sa


revision = '09a2b6ba1cef'
down_revision = '23ef72500a61'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    conn.exec_driver_sql("""
        CREATE TABLE reservations_new (
            id INTEGER PRIMARY KEY,
            session_id VARCHAR(100) NOT NULL,
            shop_id INTEGER NOT NULL,
            date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            number_of_people INTEGER NOT NULL,
            customer_phone VARCHAR(20),
            duration INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            reserved_until DATETIME NOT NULL,
            created_at DATETIME,
            FOREIGN KEY (shop_id) REFERENCES shops (id),
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    """)

    conn.exec_driver_sql("""
        INSERT INTO reservations_new (id, session_id, shop_id, date, start_time, end_time,
                                        number_of_people, customer_phone, duration, course_id,
                                        reserved_until, created_at)
        SELECT id, 'migrated', 0, '2026-01-01', '09:00', '10:00',
               1, NULL, 60, 1,
               reserved_until, created_at
        FROM reservations
    """)

    conn.exec_driver_sql("DROP TABLE reservations")
    conn.exec_driver_sql("ALTER TABLE reservations_new RENAME TO reservations")

    conn.exec_driver_sql("CREATE INDEX ix_reservations_customer_phone ON reservations (customer_phone)")
    conn.exec_driver_sql("CREATE INDEX ix_reservations_session ON reservations (session_id)")
    conn.exec_driver_sql("CREATE INDEX ix_reservations_shop_date ON reservations (shop_id, date)")

    try:
        conn.exec_driver_sql("DROP TABLE time_slots")
    except Exception:
        pass


def downgrade():
    raise Exception("Downgrade not supported for this migration")
