# Project Brief

## Overview
expedia - DesignAgent - Build a full-featured Expedia-style travel booking platform with the following capabilities:

## Core Features

### 1. User Authentication
- Email/password registration and login
- JWT-based authentication
- User profile management (name, email, phone, saved payment methods)
- Booking history view

### 2. Flight Search & Booking
- Search flights by origin, destination, dates, passengers
- Round-trip and one-way search options
- Filter by: price, airline, stops, departure time
- Sort results by price, duration, departure time
- Flight details: airline, flight number, departure/arrival times, duration, layovers
- Seat class selection (Economy, Business, First)
- Add to cart and checkout

### 3. Hotel Search & Booking  
- Search hotels by location, check-in/out dates, guests, rooms
- Filter by: star rating, price range, amenities, distance
- Hotel details: photos gallery, description, amenities, room types
- Room selection with different bed configurations
- Guest reviews and ratings display
- Map view with hotel locations

### 4. Car Rental
- Search by pickup/dropoff location and dates
- Filter by: car type, price, company
- Car details: model, seats, transmission, fuel type
- Add extras: GPS, child seat, insurance

### 5. Package Deals
- Bundle flight + hotel + car with discounts
- Compare package vs individual pricing

### 6. Shopping Cart & Checkout
- Multi-item cart (flights, hotels, cars)
- Price breakdown with taxes and fees
- Promo code application
- Secure payment form

### 7. Trip Management
- View upcoming and past trips
- Download booking confirmations
- Cancel or modify bookings

## UI Requirements
- Modern design inspired by Expedia reference screenshots
- Responsive layout
- Dark blue (#1668E3) and yellow/orange accent color scheme
- White background with clean cards
- Interactive date picker with calendar
- Autocomplete for locations with icons
- Image carousels for hotels
- Tab navigation for Stays/Flights/Cars/Packages
- Heart icons for favorites
- VIP Access badges

## Tech Stack
- Frontend: React, Vite, TailwindCSS
- Backend: Node.js/Express, PostgreSQL
- Auth: JWT with bcrypt

## Sample Data
- 50+ flights, 30+ hotels, 20+ cars
- Test user: admin@expedia.com / admin123

## Core Requirements
- Build a full-featured Expedia-style travel booking platform with the following capabilities:

## Core Features

### 1. User Authentication
- Email/password registration and login
- JWT-based authentication
- User profile management (name, email, phone, saved payment methods)
- Booking history view

### 2. Flight Search & Booking
- Search flights by origin, destination, dates, passengers
- Round-trip and one-way search options
- Filter by: price, airline, stops, departure time
- Sort results by price, duration, departure time
- Flight details: airline, flight number, departure/arrival times, duration, layovers
- Seat class selection (Economy, Business, First)
- Add to cart and checkout

### 3. Hotel Search & Booking  
- Search hotels by location, check-in/out dates, guests, rooms
- Filter by: star rating, price range, amenities, distance
- Hotel details: photos gallery, description, amenities, room types
- Room selection with different bed configurations
- Guest reviews and ratings display
- Map view with hotel locations

### 4. Car Rental
- Search by pickup/dropoff location and dates
- Filter by: car type, price, company
- Car details: model, seats, transmission, fuel type
- Add extras: GPS, child seat, insurance

### 5. Package Deals
- Bundle flight + hotel + car with discounts
- Compare package vs individual pricing

### 6. Shopping Cart & Checkout
- Multi-item cart (flights, hotels, cars)
- Price breakdown with taxes and fees
- Promo code application
- Secure payment form

### 7. Trip Management
- View upcoming and past trips
- Download booking confirmations
- Cancel or modify bookings

## UI Requirements
- Modern design inspired by Expedia reference screenshots
- Responsive layout
- Dark blue (#1668E3) and yellow/orange accent color scheme
- White background with clean cards
- Interactive date picker with calendar
- Autocomplete for locations with icons
- Image carousels for hotels
- Tab navigation for Stays/Flights/Cars/Packages
- Heart icons for favorites
- VIP Access badges

## Tech Stack
- Frontend: React, Vite, TailwindCSS
- Backend: Node.js/Express, PostgreSQL
- Auth: JWT with bcrypt

## Sample Data
- 50+ flights, 30+ hotels, 20+ cars
- Test user: admin@expedia.com / admin123

## Goals (project-specific)
- Deliver a working frontend + backend + database stack per specs.
- Ensure auth/login works with seeded users and core flows are testable.
- Provide smoke-testable APIs and UI based on design specs.

## Scope (adjust per project)
- In scope: stated features in requirements/specs.
- Out of scope: anything not in requirements/specs or marked optional.

## Success Criteria
- Services start (docker/local) and basic flows pass smoke tests.
- No critical 500s/404s on specified endpoints; UI aligns with design spec.
