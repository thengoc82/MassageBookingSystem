# AI Massage Booking API

Flask-based REST API for the AI Massage Booking system.

## Quick Start

### Prerequisites
- Python 3.9+
- Redis 7+ (optional)

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
