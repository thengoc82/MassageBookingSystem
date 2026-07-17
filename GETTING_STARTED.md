# AI Massage Booking System - Getting Started

## Overview

This is a complete full-stack AI-powered massage booking system with:
- **Backend**: Flask REST API with SQLite
- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Features**: Real-time booking, therapist scheduling, customer management, voice AI integration (planned)

## Project Status

✅ **Completed**:
- Complete Flask backend with 40+ API endpoints
- All database models (12 tables)
- Service layer with business logic
- Next.js frontend with booking flow
- Customer booking management
- Shop listings and course browsing
- Docker setup

⏳ **Pending**:
- Voice booking module (Twilio integration)
- Database migrations
- Admin dashboard UI
- Payment integration (Stripe)

## Quick Start

### 1. Start Backend (Terminal 1)

```bash
cd "spa-booking-api"

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Initialize database (creates SQLite file automatically)
python3 -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database created')"

# Run server
python run.py
```

Backend will run at: http://localhost:5000

### 2. Start Frontend (Terminal 2)

```bash
cd "spa-booking-frontend"

# Install dependencies
npm install

# Already configured with .env.local

# Run development server
npm run dev
```

Frontend will run at: http://localhost:3000

### 3. Test the Application

Visit http://localhost:3000 and:
1. Click "Book Now"
2. Select a shop
3. Choose date and services
4. Complete booking flow

## Database

SQLite is used by default. No database server needed — the file is created automatically at `spa-booking-api/instance/spa_booking.db` on first run.

## Architecture

### Backend Structure
```
spa-booking-api/
├── app/
│   ├── models/              # 12 SQLAlchemy models
│   ├── blueprints/          # 6 API route blueprints
│   ├── services/            # Business logic layer
│   └── utils/               # Helpers, decorators, errors
├── migrations/              # Alembic migrations
└── tests/                   # Unit tests
```

### Frontend Structure
```
spa-booking-frontend/
├── app/
│   ├── page.tsx            # Home page
│   ├── booking/            # Multi-step booking wizard
│   ├── my-bookings/        # Booking management
│   └── shops/              # Shop listings
├── lib/api.ts              # API client
└── types/index.ts          # TypeScript types
```

## API Endpoints

### Public Endpoints
- `GET /api/shops` - List all shops
- `GET /api/shops/{id}/courses` - Get courses for a shop
- `GET /api/shops/{id}/available-slots` - Find available time slots
- `POST /api/bookings` - Create a booking
- `POST /api/booking-eligibility-checks` - Check customer eligibility

### Admin Endpoints (require JWT)
- `POST /api/admin/shops` - Create shop
- `POST /api/admin/shops/{id}/courses` - Create course
- `POST /api/admin/shops/{id}/therapists` - Create therapist
- `GET /api/admin/bookings` - List all bookings

### Auth
- `POST /api/auth/login` - Admin/therapist login

## Key Features

### Customer Booking Flow
1. Select shop location
2. Choose date
3. Specify number of guests
4. Select massage services
5. Pick available time slot
6. Enter phone number (auto-creates customer)
7. Eligibility check (NG List validation)
8. Confirm booking → Receive booking code

### Business Rules
- Group bookings (2+ people) cannot request specific therapist
- Blocked customers (NG List) cannot book
- Availability is optimistic — no reservation holds, slot confirmed at booking time
- Booking status: Booked → CheckedIn → CheckedOut (or Cancelled)

## Next Steps

### To add initial data:

Create a seed script or use the admin endpoints to add:
1. Shops (locations)
2. Courses (massage services)
3. Therapists
4. Admin users

### To deploy:

**Backend**: Railway, Fly.io, or Heroku
**Frontend**: Vercel (recommended for Next.js)

## Documentation

Full specifications available in project root:
- `REST_API_Specification.md` - Complete API docs
- `Database_Schema.md` - Database design
- `Business_Analysis_Domain_Model.md` - Business rules
- `User_Stories_Process_Flow.md` - User flows

## Troubleshooting

### Backend won't start
- Check `.env` file exists
- Run `python3 -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"` to initialize the DB

### Frontend API errors
- Ensure backend is running at http://localhost:5000
- Check NEXT_PUBLIC_API_URL in .env.local
- Check CORS is enabled in Flask

### Database issues
- Delete `instance/spa_booking.db` to reset the database, then re-run the init command above

## Support

For issues or questions, refer to the documentation files in the project root or check the inline code comments.
