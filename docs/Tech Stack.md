# AI Massage Booking — Tech Stack

## Frontend
- **Framework:** Next.js 16 (React 19, TypeScript, App Router)
- **Styling:** Tailwind CSS 4
- **HTTP:** Axios (lib/api.ts)
- **State/Real-time:** React hooks; socket.io-client installed (not yet wired)
- **UI Components:** hand-rolled (no component library) + `components/TherapistGantt.tsx`

## Backend
- **API:** Flask 3 (blueprint-based request-response, not Flask-RESTx)
- **Real-time:** Flask-SocketIO (scaffolded; not yet wired to UI)
- **ORM:** SQLAlchemy + Alembic (migrations)
- **Auth:** Flask-JWT-Extended (JWT) — admin/therapist login
- **Telephony:** Twilio (inbound/outbound calls, Media Streams) — planned
- **Voice Module:** Flask blueprint `voice_booking/` (webhooks + WebSocket) — scaffolded, not active

## Database
- **Primary:** SQLite (default, no setup needed)
- **Cache/Session:** Redis (optional — falls back gracefully)

## AI Layer
- **Orchestration:** LangChain
- **LLM:** OpenAI GPT-4o (chat, recommendations, scheduling logic)
- **Memory:** Redis + PostgreSQL (session + long-term client history)
- **Async AI tasks:** Celery + Redis broker

## Voice AI (Phone Booking)
- **STT:** Deepgram (preferred for low latency) or OpenAI Whisper API
- **Conversation:** GPT-4o + function calling (extracts booking params → calls API)
- **TTS:** ElevenLabs or OpenAI TTS
- **Streaming:** Twilio Media Streams ↔ Flask WebSocket endpoint
- **Session State:** Redis (tracks caller's position in booking flow)
- **Agent Prompt:** Vietnamese-capable, follows BA flow (shop → date → guests → services → time → therapist → phone)
- **Alternative (managed):** Vapi or Retell — ship faster, ~$0.10–0.30/min

## Infrastructure
- **Async tasks:** Celery (email/SMS reminders, follow-ups)
- **Payments:** Stripe
- **Deployment:** Docker + Docker Compose
- **Hosting:** Vercel (frontend) / Railway or Fly.io (backend)

## Flow
1. Client chats via Next.js UI → Flask API → LangChain → GPT-4o
2. Booking logic hits SQLite, real-time pushed via SocketIO
3. Celery handles reminders + async AI (e.g., post-session follow-up)
4. Caller dials → Twilio → Flask WebSocket → Deepgram (STT) → GPT-4o (function call) → checks slot via API → TTS response → Twilio plays to caller
