import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    # First, let's check what tables exist
    from sqlalchemy import text
    try:
        result = db.session.execute(text('SELECT name FROM sqlite_master WHERE type="table"'))
        existing_tables = [row[0] for row in result]
        print(f'Existing tables: {existing_tables}')
    except Exception as e:
        print(f'Error checking existing tables: {e}')
        existing_tables = []

    # Clear all tables if they exist
    print('Dropping all tables...')
    db.drop_all()

    # Create all tables
    print('Creating all tables...')
    db.create_all()

    # Check all tables again
    try:
        result = db.session.execute(text('SELECT name FROM sqlite_master WHERE type="table"'))
        tables = [row[0] for row in result]
        print(f'Tables created: {tables}')

        # Check if booking_therapists specifically exists
        if 'booking_therapists' in tables:
            print('✓ booking_therapists table created successfully!')
        else:
            print('✗ booking_therapists table not created')

        # Check if shops exists (it should)
        if 'shops' in tables:
            print('✓ shops table created successfully!')
        else:
            print('✗ shops table not created')

    except Exception as e:
        print(f'✗ Error listing tables: {e}')
        import traceback
        traceback.print_exc()
