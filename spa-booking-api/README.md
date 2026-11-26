# AI Massage Booking API

Flask-based REST API for the AI Massage Booking system.

## Quick Start

### Prerequisites
- Python 3.9+
- Redis 7+ for customer booking access

### Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize database (creates SQLite file automatically):
```bash
python3 -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database created')"
```

5. Run server:
```bash
python run.py
```

API available at http://localhost:5000

Customer booking lookup, detail, modification, and cancellation require a six-digit access code. In Flask development mode, the code is printed with the phone number in the API terminal. Redis stores only a keyed hash, expires the code after five minutes, and enforces attempt and request limits. No Twilio account or paid service is needed for local testing.

For local testing, run `redis-cli ping` and expect `PONG`, then start the Flask API with `python run.py`. Enter a phone number on **My Bookings**, click **Get code**, and read the code in the Flask terminal. The code is not in the API response. The terminal provider is available only in Flask development mode. Docker Compose runs the API in production mode, where terminal delivery is blocked and customer access returns 503 until a real delivery provider is added. Production startup requires strong `SECRET_KEY` and `JWT_SECRET_KEY` values.

## Project Structure

```
spa-booking-api/
├── app/
│   ├── models/              # Database models
│   ├── blueprints/          # API routes
│   │   ├── auth/           # Authentication
│   │   ├── public/         # Public endpoints
│   │   ├── bookings/       # Booking management
│   │   ├── admin/          # Admin endpoints
│   │   ├── therapist/      # Therapist endpoints
│   │   └── voice_booking/  # Voice AI integration
│   ├── services/           # Business logic
│   ├── utils/              # Helpers
│   ├── config.py           # Configuration
│   └── extensions.py       # Flask extensions
├── migrations/             # Database migrations
├── tests/                  # Tests
├── requirements.txt
├── run.py                  # Entry point
└── docker-compose.yml
```

## API Documentation

See REST_API_Specification.md in the project root for full API documentation.

## Docker

Run with Docker:
```bash
docker-compose up -d
```

## Testing

```bash
pytest
```

## Environment Variables

Key variables in `.env`:
- `DATABASE_URL` - Database URI (default: `sqlite:///prod.db`)
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Flask secret key
- `JWT_SECRET_KEY` - JWT signing key
- API keys for Twilio, OpenAI, Deepgram, ElevenLabs (optional)
