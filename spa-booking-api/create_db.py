import sys

sys.path.insert(0, '/Users/thengoc/Documents/Obsidian Vault/AI Massage Booking Project/spa-booking-api')

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Try to drop and recreate all tables
    print('Dropping all tables...')
    db.drop_all()

    print('Creating all tables...')
    db.create_all()

    # Verify booking_therapists table was created
    try:
        result = db.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='booking_therapists'"))
        tables = [row[0] for row in result]
        if 'booking_therapists' in tables:
            print('✓ booking_therapists table created successfully!')
        else:
            print('✗ booking_therapists table not created')
    except Exception as e:
        print(f'✗ Error checking tables: {e}')

    # List all tables
    try:
        result = db.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result]
        print(f'Tables created: {tables}')
    except Exception as e:
        print(f'✗ Error listing tables: {e}')
