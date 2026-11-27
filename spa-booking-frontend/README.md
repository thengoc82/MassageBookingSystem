# AI Massage Booking Frontend

Next.js frontend for the AI Massage Booking system.

## Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Set up environment:
```bash
cp .env.local.example .env.local
```

3. Configure `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:5000/api
NEXT_PUBLIC_CHATBOT_URL=http://localhost:8001
```

4. Run development server:
```bash
npm run dev
```

Frontend available at http://localhost:3000

## Project Structure

```
spa-booking-frontend/
├── app/                    # Next.js App Router
│   ├── page.tsx           # Home page
│   ├── layout.tsx         # Root layout
│   ├── booking/           # Booking flow
│   ├── my-bookings/       # Booking management
│   └── shops/             # Shop listings
├── lib/                   # Utilities
│   └── api.ts             # API client
├── types/                 # TypeScript definitions
│   └── index.ts
└── public/                # Static assets
```

## Features

- **Booking Flow**: Multi-step booking wizard
- **My Bookings**: Verify a short-lived phone code, then view, edit, or cancel eligible bookings
- **Shop Listings**: Browse locations and services
- **Admin and therapist pages**: JWT-protected shifts, restrictions, bookings, and role-authorized status actions
- **Chatbot**: Uses the FastAPI service on port 8001
- **Responsive Design**: Mobile-first with Tailwind CSS
- **TypeScript**: Full type safety

## Build for Production

```bash
npm run build
npm start
```

## Deployment

Recommended: Vercel (automatic Next.js optimization)

```bash
vercel deploy
```

## Environment Variables

- `NEXT_PUBLIC_API_URL` - Backend API base URL
- `NEXT_PUBLIC_CHATBOT_URL` - Chatbot service origin

See [RUNNING.md](../RUNNING.md) for the complete local configuration and test
commands. The phone code is printed only by the Flask development server;
knowing a phone number or booking code does not grant booking access.
