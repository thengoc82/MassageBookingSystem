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
- **My Bookings**: View and cancel bookings by phone
- **Shop Listings**: Browse locations and services
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
