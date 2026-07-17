# AI Massage Booking System

A full-stack AI-powered massage booking platform with Flask backend and Next.js frontend.

## Project Structure

```
AI Massage Booking Project/
├── spa-booking-api/          # Flask Backend
│   ├── app/
│   │   ├── models/           # SQLAlchemy models (time_slot.py is deprecated)
│   │   ├── blueprints/       # API routes (auth, public, bookings, admin, therapist, voice_booking)
│   │   ├── services/         # Business logic layer
│   │   └── utils/            # Helpers, errors, response wrappers
│   ├── migrations/           # Alembic migrations
│   ├── tests/                # pytest suite
│   ├── requirements.txt
│   ├── run.py
│   └── docker-compose.yml
│
└── spa-booking-frontend/     # Next.js Frontend (App Router)
    ├── app/                  # Pages: /, /shops, /dashboard, /reservation, /booking, /my-bookings
    ├── components/           # Shared UI (e.g. TherapistGantt)
    ├── lib/                  # API client (axios)
    ├── types/                # TypeScript types
    └── package.json
```

## Backend (Flask API)

### Prerequisites
- Python 3.9+
- Redis 7+ (optional — app falls back gracefully)

### Setup

1. Navigate to backend directory:
```bash
cd spa-booking-api
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment file:
```bash
cp .env.example .env
```

5. Update `.env` with your configuration:
- Redis URL (optional)
- JWT secret keys
- API keys (Twilio, OpenAI, etc.)

6. Initialize database:
```bash
python3 -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database created')"
```

7. Run the server:
```bash
python run.py
```

API will be available at `http://localhost:5000`

### Docker Setup (Alternative)

```bash
docker-compose up -d
```

### API Endpoints

**Public:**
- `GET /api/shops` - List shops
- `GET /api/shops/{id}/courses` - List courses
- `GET /api/shops/{id}/available-slots` - Get available slots
- `POST /api/bookings` - Create booking
- `GET /api/bookings` - List bookings by phone

**Admin:**
- `POST /api/admin/shops` - Create shop
- `POST /api/admin/shops/{id}/courses` - Create course
- `POST /api/admin/shops/{id}/therapists` - Create therapist

**Auth:**
- `POST /api/auth/login` - Login

## Frontend (Next.js)

### Prerequisites
- Node.js 18+
- npm or yarn

### Setup

1. Navigate to frontend directory:
```bash
cd spa-booking-frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.local.example .env.local
```

4. Update `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:5000/api
```

5. Run development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
npm start
```

## Features

### Customer Features
- Browse shops and services
- View available time slots
- Book appointments (single or group)
- Select specific therapist or gender preference
- View and manage bookings
- Cancel bookings
- Eligibility checks (NG List blocking)

### Admin Features
- Manage shops, courses, therapists
- View all bookings
- Check-in/check-out customers
- Manage customer restrictions (NG List)
- Schedule therapist shifts

### Technical Features
- JWT authentication
- Real-time updates with Socket.IO
- Reservation holds (5-minute time locks)
- RESTful API design
- SQLite (zero-config database)
- Redis caching and sessions (optional)
- Responsive UI with Tailwind CSS

## Tech Stack

**Backend:**
- Flask 3.0
- SQLAlchemy + Alembic
- SQLite
- Redis (optional)
- Flask-JWT-Extended
- Flask-SocketIO

**Frontend:**
- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS 4
- Axios (API client), socket.io-client (installed, not yet wired)

**AI/Voice (Planned):**
- Twilio (telephony)
- OpenAI GPT-4o (conversation)
- Deepgram (STT)
- ElevenLabs (TTS)

## Development

### Backend Testing
```bash
pytest
```

### Frontend Testing
```bash
npm test
```

## Deployment

### Backend
- Railway / Fly.io recommended
- Requires PostgreSQL and Redis

### Frontend
- Vercel recommended (automatic Next.js optimization)

## License

MIT
