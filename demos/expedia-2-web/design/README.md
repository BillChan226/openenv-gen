# Expedia-Style Travel Booking Platform — Design Overview

## 1. Goal
Build an Expedia-inspired travel booking web app that supports searching and booking **flights, hotels, cars, and packages**, with **cart/checkout**, **trips management**, **favorites**, and **JWT-based authentication**.

This folder contains the canonical design specs for downstream agents:
- `design/spec.database.json` — PostgreSQL schema
- `design/spec.api.json` — REST API contract (Express)
- `design/spec.ui.json` — React UI structure and components

## 2. Tech Stack
- Frontend: React + Vite + TailwindCSS
- Backend: Node.js + Express
- Database: PostgreSQL
- Auth: JWT (Bearer token) + bcrypt password hashing

## 3. Key Product Flows
### 3.1 Auth
- Register (email, password, full_name)
- Login → returns `{ token, user }`
- Profile management (full_name, phone)
- Saved payment methods (tokenized/placeholder only)

### 3.2 Search & Details
- Flights: search → results (filters/sort) → details → add to cart
- Hotels: search → results (filters/sort) → details (gallery, rooms) → add to cart
- Cars: search → results → details → add to cart
- Packages: search → results → details → add to cart

### 3.3 Cart & Checkout
- Cart supports multi-item: flight/hotel/car/package
- Promo code support
- Checkout simulates payment processing
- Creates an order and order items

### 3.4 Trips
- View upcoming / past trips (based on order start/end dates)
- Download confirmation (simple PDF/HTML render is acceptable)
- Cancel & limited modify (dates/guest counts) depending on item type

### 3.5 Favorites
- Favorite hotels (and optionally flights/cars/packages later)

## 4. Global Conventions (Integration-Critical)
### 4.1 Naming
- Database columns: **snake_case**
- API JSON fields: **snake_case** (match DB where possible)

### 4.2 Money
- Store money as **integer cents** with `_cents` suffix (e.g., `price_cents`).
- Currency: USD.

### 4.3 Time
- Date fields: `YYYY-MM-DD`
- Datetime fields: ISO-8601 strings
- DB datetime columns use `*_at` suffix (e.g., `depart_at`, `created_at`).

### 4.4 API Response Wrappers
- All list endpoints return **`{ "items": [...] }`** (and may include `total`, `limit`, `offset`).

### 4.5 Auth
- Protected endpoints require header: `Authorization: Bearer <token>`

## 5. Pages (UI)
- Home (tabbed search)
- Flights Results, Flight Details
- Hotels Results, Hotel Details
- Cars Results, Car Details
- Packages Search/Results
- Favorites
- Cart
- Checkout
- Trips (Upcoming/Past)
- Profile
- Login, Register

## 6. Seed Data
- Minimum: 50 flights, 30 hotels, 20 cars
- Test user:
  - email: `admin@expedia.com`
  - password: `admin123`
  - full_name: `Admin User`

## 7. Visual Guidance
Use screenshots in `/screenshots` as reference for layout and styling:
- `Expedia-Main-Page.png` (home + tabbed search)
- `Search-Flight.png` (flight results)
- `Search-Hotel.png` (hotel results)
- `Flight-Detail.png` (flight detail)
- `Hotel-Detail-Page.png` (hotel detail)
