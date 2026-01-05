# FoodHub — Design Overview

FoodHub is a DoorDash/UberEats-inspired food delivery web app.

- **Frontend**: React + Vite at **http://localhost:8000**
- **Backend API**: Express at **http://localhost:3000**
- **Database**: PostgreSQL

This folder contains the authoritative design specs used by DatabaseAgent, BackendAgent, and FrontendAgent.

## Goals / Core User Flows

1. **Browse restaurants** on Home with category pills, promo banners, and store cards.
2. **Search** restaurants and dishes (menu items) with suggestions and recent searches.
3. **View restaurant page** (cover image, meta, category icons, menu grid) and open **item detail modal**.
4. **Single-restaurant cart**: add items from exactly one restaurant at a time.
5. **Checkout**: choose address + payment method, place order, view confirmation.
6. **Orders**: order tracking (status/ETA), order history, reorder.
7. **Favorites**: favorite restaurants.

## Key Constraints (Must-Implement)

### Money & Fees
- **All money is stored in integer cents** (`*_cents`) in DB and API.
- **Service fee** is **5% of subtotal**.
  - `service_fee_cents = round(subtotal_cents * 0.05)` (round half up; implement with integer math: `(subtotal_cents * 5 + 50) / 100` floor)
- `total_cents = subtotal_cents + delivery_fee_cents + service_fee_cents - discount_cents`

### Cart: Single Restaurant
- A cart belongs to one user and is either **empty** or associated to exactly **one restaurant**.
- If user attempts to add an item from a different restaurant:
  - API returns `409 CART_RESTAURANT_MISMATCH` with current cart summary.
  - UI prompts user to clear cart or cancel.

### Promo Codes
Promo codes are defined in `design/spec.requirements.json` and must be seeded in DB.
- Promo codes can be **percent** or **fixed**.
- Validation rules: active window, min subtotal, usage limits.

## Naming Conventions

- **Database**: `snake_case` columns and tables.
- **API**: `camelCase` JSON.
- Backend must transform DB → API and API → DB.

Common transforms:
- `created_at` → `createdAt`
- `delivery_fee_cents` → `deliveryFeeCents`
- `minimum_order_cents` → `minimumOrderCents`
- `price_cents` → `priceCents`

## API Response Conventions (Critical)

All endpoints use a consistent wrapper:

- **Success (single)**: `{ "success": true, "data": { ... } }`
- **Success (list)**: `{ "success": true, "data": { "items": [...], "pagination": { ... } } }`
- **Error**: `{ "success": false, "error": { "code": "STRING", "message": "Human readable", "details": {} } }`

**All list endpoints MUST return `data.items`**.

## Authentication

- JWT Bearer token.
- `Authorization: Bearer <token>`
- Passwords stored as bcrypt hashes.

## High-Level Architecture

- Frontend calls backend via `VITE_API_BASE_URL` defaulting to `http://localhost:3000`.
- Backend talks to PostgreSQL.
- Cart pricing is computed server-side (authoritative) and returned in cart/order summary.

## Seed Expectations

Seed data must support demo browsing:
- Restaurant categories (with emojis)
- ~10-20 restaurants across categories
- Each restaurant has menu categories and 8-20 menu items with images
- Promo codes from requirements
- A demo user (email/password) plus saved address and payment method

## UI Style Requirements

UI must closely match the provided DoorDash-style screenshots in `screenshots/`:
- App shell: **left sidebar** + **top header**
- Rounded pill chips, large rounded search bar
- Store cards with images, rating, fees
- Primary brand color: **#FF3008** (use for CTAs and active states)

See `design/spec.ui.json` for exact page/component breakdown.
