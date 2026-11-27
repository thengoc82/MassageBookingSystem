# Getting started

See [RUNNING.md](RUNNING.md) for the current three-service setup, database
migration and seed commands, local environment variables, and test commands.

The customer journey starts at `/shops`, continues through the shop schedule
and booking form, and returns a booking code after Flask confirms capacity.
Existing bookings require a short-lived phone code printed by the Flask
development server. Admin and therapist pages require role JWTs from
`POST /api/auth/login`. The chatbot uses Flask for catalog, availability,
and writes; its FAQ retrieval uses a PostgreSQL pgvector index.

Availability is provisional until booking submission. Groups receive distinct
available therapists automatically and cannot name a therapist. Only
`Booked` bookings may be edited or cancelled. Admins or assigned therapists
perform check-in and check-out.

The public demo-data setup route was removed because it could create known
admin credentials without authentication. For an empty local development
database, use the command-line seed script described in [RUNNING.md](RUNNING.md).
