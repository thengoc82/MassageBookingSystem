"""add durations_json to courses, merge duplicate name rows

Revision ID: b3c4d5e6f7a0
Revises: a2b3c4d5e6f7
Create Date: 2026-07-20 14:00:00.000000

"""
import json

import sqlalchemy as sa
from alembic import op

revision = 'b3c4d5e6f7a0'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('durations_json', sa.Text(), nullable=True))
        batch_op.alter_column('duration', nullable=True)
        batch_op.alter_column('price', nullable=True)

    rows = conn.exec_driver_sql(
        "SELECT id, shop_id, name, course_type, duration, price FROM courses ORDER BY id"
    ).fetchall()

    groups = {}
    for row in rows:
        key = (row[1], row[2], row[3])
        if key not in groups:
            groups[key] = []
        groups[key].append({'id': row[0], 'duration': row[4], 'price': row[5]})

    for key, members in groups.items():
        if len(members) == 1:
            durations = [{'duration': members[0]['duration'], 'price': members[0]['price']}]
            conn.execute(
                sa.text("UPDATE courses SET durations_json = :d WHERE id = :id"),
                {"d": json.dumps(durations, ensure_ascii=False), "id": members[0]['id']}
            )
        else:
            keep_id = members[0]['id']
            durations = [{'duration': m['duration'], 'price': m['price']} for m in members]
            conn.execute(
                sa.text("UPDATE courses SET durations_json = :d WHERE id = :id"),
                {"d": json.dumps(durations, ensure_ascii=False), "id": keep_id}
            )

            delete_ids = [m['id'] for m in members[1:]]

            for old_id in delete_ids:
                conn.execute(
                    sa.text("UPDATE booking_services SET course_id = :new WHERE course_id = :old"),
                    {"new": keep_id, "old": old_id}
                )
                conn.execute(
                    sa.text("UPDATE booking_addons SET course_id = :new WHERE course_id = :old"),
                    {"new": keep_id, "old": old_id}
                )
                conn.execute(
                    sa.text("UPDATE reservations SET course_id = :new WHERE course_id = :old"),
                    {"new": keep_id, "old": old_id}
                )

            for old_id in delete_ids:
                conn.execute(sa.text("DELETE FROM courses WHERE id = :id"), {"id": old_id})


def downgrade():
    conn = op.get_bind()

    rows = conn.exec_driver_sql(
        "SELECT id, name, shop_id, course_type, durations_json FROM courses WHERE durations_json IS NOT NULL"
    ).fetchall()

    for row in rows:
        course_id = row[0]
        try:
            durations = json.loads(row[4])
        except (json.JSONDecodeError, TypeError):
            continue
        first = True
        for entry in durations:
            if first:
                conn.execute(
                    sa.text("UPDATE courses SET duration = :d, price = :p, durations_json = NULL WHERE id = :id"),
                    {"d": entry['duration'], "p": entry['price'], "id": course_id}
                )
                first = False
            else:
                conn.execute(
                    sa.text("INSERT INTO courses (shop_id, name, duration, price, course_type, status) VALUES (:s, :n, :d, :p, :t, 'active')"),
                    {"s": row[2], "n": row[1], "d": entry['duration'], "p": entry['price'], "t": row[3]}
                )
                new_id = conn.execute(sa.text("SELECT last_insert_rowid()")).scalar()
                conn.execute(
                    sa.text("UPDATE booking_services SET course_id = :new WHERE course_id = :old"),
                    {"new": new_id, "old": row[0]}
                )
                conn.execute(
                    sa.text("UPDATE booking_addons SET course_id = :new WHERE course_id = :old"),
                    {"new": new_id, "old": row[0]}
                )

    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_column('durations_json')
        batch_op.alter_column('duration', nullable=False)
        batch_op.alter_column('price', nullable=False)
