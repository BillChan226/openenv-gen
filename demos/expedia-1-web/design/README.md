# Voyager Booking Platform (Expedia-style)

A full-featured travel booking web application (Expedia-style) that enables users to search and book **flights**, **hotels**, **car rentals**, and **discounted packages**, manage trips, and complete secure checkout with a **multi-item cart**. The platform includes authentication, user profiles, favorites, rich listing details (photos, maps, reviews), and post-booking actions like downloadable confirmations and cancellation/modification within defined rules.

## Key Features

### App Shell & Navigation
- Responsive top navigation with tabs: **Stays / Flights / Cars / Packages**
- Account menu (login/register or profile/trips)
- Cart icon with badge showing total items
- Consistent footer

### Authentication & Account
- Email/password registration + login
- JWT-based auth (access token)
- Logout + expired-session handling
- Profile management (name, email, phone)
- Saved payment methods (tokenized placeholders)

### Search & Booking
- **Flights**: one-way/round-trip search, filters (price/airline/stops/time), sorting (price/duration/departure), flight details & fare class selection
- **Hotels**: search by location + date range + guests/rooms, filters (stars/price/amenities/distance), list + optional map view, hotel details with gallery, rooms, reviews, VIP badge
- **Cars**: search by pickup/dropoff + dates, filters (type/price/company), car details with extras
- **Packages**: bundle flight+hotel+optional car with discount and comparison vs individual totals

### Cart, Promo Codes & Checkout
- Multi-item cart for flights/hotels/cars/packages
- Transparent totals: subtotal, taxes, fees, discounts
- Promo codes (percent or fixed) with constraints (min spend, expiry)
- Checkout with traveler/guest/driver details and simulated payment
- Successful checkout creates bookings and clears cart

### Trips & Post-booking
- Trips page grouped into Upcoming / Past
- Booking detail view
- Download confirmation (PDF-like download or print-to-PDF)
- Cancel/modify actions based on policy windows

### Favorites
- Heart (favorite) hotels (persisted per user)

## Tech Stack
- **Frontend:** React + Vite + TailwindCSS
- **Backend:** Node.js + Express (REST)
- **Database:** PostgreSQL
- **Auth:** JWT + bcrypt
- **Validation:** Zod or Joi
- **Maps:** Leaflet + OpenStreetMap (no paid keys)
- **PDF:** server-side generation (e.g., pdfkit) or print-to-PDF fallback

## Getting Started (Docker)

> This repository is structured to run as a multi-service stack: frontend, backend, and Postgres.

### Prerequisites
- Docker + Docker Compose

### Run
```bash
# from repo root
docker compose -f docker/docker-compose.yml up --build
```

### Expected Services
- Frontend (React/Vite): http://localhost:5173
- Backend (Express API): http://localhost:3000
- API base URL: http://localhost:3000/api
- PostgreSQL: localhost:5432

### Seeded Test User
- Email: **admin@expedia.com**
- Password: **admin123**

### Common Environment Variables
- `DATABASE_URL` (or `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)
- `JWT_SECRET`
- `CORS_ORIGIN` (e.g., `http://localhost:5173`)
- `VITE_API_BASE` (e.g., `http://localhost:3000/api`)
