-- app/database/init/02_seed.sql
-- Seed data (demo)
-- NOTE: Password hashes are bcrypt ($2a$10$...).
-- admin@expedia.com / admin123
-- user@example.com / password123

-- NOTE: Do not wrap seed in an explicit transaction.
-- When executed by the postgres Docker entrypoint, scripts are already run
-- with ON_ERROR_STOP=1. Avoiding BEGIN/COMMIT makes failures easier to debug
-- and prevents transaction-state issues.


-- USERS
-- admin@expedia.com / admin123 (or admin@example.com / admin123)
INSERT INTO users (id, email, password_hash, name, phone, created_at, updated_at)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'admin@expedia.com', '$2a$10$CwTycUXWue0Thq9StjUM0uJ8l0j5GQqvG8nJQm3CqWqfZ8nR3bQ8K', 'Admin User', '+1-555-0100', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'),
  ('33333333-3333-3333-3333-333333333333', 'admin@example.com', '$2a$10$7EqJtq98hPqEX7fNZaFWoOHi1o2y9mJc8l8RkY7xvKqvZ3p0nZf3G', 'Example Admin', '+1-555-0101', '2025-01-02T00:00:00Z', '2025-01-02T00:00:00Z'),
  ('44444444-4444-4444-4444-444444444444', 'user@example.com', '$2a$10$KIXl0C7pX2C5m8mQ8jG7Uu9Z2m1f0qVQv7oXQ2m7oJbWkq0V0o3o2', 'Example User', '+1-555-0102', '2025-01-03T00:00:00Z', '2025-01-03T00:00:00Z'),
  ('55555555-5555-5555-5555-555555555555', 'jamie@demo.com', '$2a$10$wH8kQqgqgqgqgqgqgqgqgO4x6j7m8n9p0q1r2s3t4u5v6w7x8y9z0', 'Jamie Demo', '+1-555-0103', '2025-01-04T00:00:00Z', '2025-01-04T00:00:00Z'),
  ('66666666-6666-6666-6666-666666666666', 'taylor@demo.com', '$2a$10$z9y8x7w6v5u4t3s2r1q0p9n8m7j6h5g4f3e2d1c0b9a8Z7Y6X5W4', 'Taylor Demo', '+1-555-0104', '2025-01-05T00:00:00Z', '2025-01-05T00:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- PAYMENT METHODS
INSERT INTO payment_methods (id, user_id, brand, last4, exp_month, exp_year, token, billing_name, created_at)
VALUES
  ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'visa', '4242', 12, 2030, 'pm_demo_visa_4242', 'Admin User', '2025-01-01T00:00:00Z'),
  ('23232323-2323-2323-2323-232323232323', '33333333-3333-3333-3333-333333333333', 'mastercard', '4444', 11, 2031, 'pm_demo_mc_4444', 'Example Admin', '2025-01-02T00:00:00Z'),
  ('24242424-2424-2424-2424-242424242424', '44444444-4444-4444-4444-444444444444', 'amex', '0005', 10, 2032, 'pm_demo_amex_0005', 'Example User', '2025-01-03T00:00:00Z'),
  ('25252525-2525-2525-2525-252525252525', '55555555-5555-5555-5555-555555555555', 'visa', '1111', 9, 2030, 'pm_demo_visa_1111', 'Jamie Demo', '2025-01-04T00:00:00Z'),
  ('26262626-2626-2626-2626-262626262626', '66666666-6666-6666-6666-666666666666', 'visa', '2222', 8, 2030, 'pm_demo_visa_2222', 'Taylor Demo', '2025-01-05T00:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- LOCATIONS
INSERT INTO locations (id, type, code, name, country, region, lat, lng)
VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'airport', 'SFO', 'San Francisco International Airport', 'United States', 'CA', 37.621313, -122.378955),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 'airport', 'LAX', 'Los Angeles International Airport', 'United States', 'CA', 33.941589, -118.408530),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'city', 'NYC', 'New York', 'United States', 'NY', 40.712776, -74.005974),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 'city', 'LAS', 'Las Vegas', 'United States', 'NV', 36.169941, -115.139832),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', 'city', 'SEA', 'Seattle', 'United States', 'WA', 47.606209, -122.332069),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa6', 'city', 'MIA', 'Miami', 'United States', 'FL', 25.761681, -80.191788),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa7', 'city', 'CHI', 'Chicago', 'United States', 'IL', 41.878113, -87.629799),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa8', 'city', 'BOS', 'Boston', 'United States', 'MA', 42.360081, -71.058884),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa9', 'region', NULL, 'Bay Area', 'United States', 'CA', 37.774929, -122.419418),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa10', 'place', NULL, 'Disneyland Resort', 'United States', 'CA', 33.812092, -117.918976)
ON CONFLICT (id) DO NOTHING;

-- FLIGHTS
INSERT INTO flights (id, airline, flight_number, origin_location_id, destination_location_id, depart_at, arrive_at, duration_minutes, stops_count, base_price_cents, currency)
VALUES
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001', 'United', 'UA101', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', '2026-02-10T15:00:00Z', '2026-02-10T16:35:00Z', 95, 0, 12900, 'USD'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb002', 'Delta', 'DL220', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '2026-02-17T18:00:00Z', '2026-02-17T19:40:00Z', 100, 0, 13500, 'USD'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb003', 'American', 'AA330', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '2026-03-05T13:00:00Z', '2026-03-05T18:10:00Z', 310, 1, 18900, 'USD'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb004', 'Southwest', 'WN455', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa6', '2026-03-12T16:00:00Z', '2026-03-12T22:20:00Z', 380, 1, 21000, 'USD'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb005', 'JetBlue', 'B6123', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa8', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa6', '2026-04-01T12:30:00Z', '2026-04-01T16:10:00Z', 220, 0, 17500, 'USD'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb006', 'Alaska', 'AS778', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', '2026-02-11T17:00:00Z', '2026-02-11T19:10:00Z', 130, 0, 9900, 'USD'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb007', 'United', 'UA305', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', '2026-03-01T14:00:00Z', '2026-03-01T22:10:00Z', 490, 1, 25900, 'USD')
ON CONFLICT (id) DO NOTHING;

-- FLIGHT SEGMENTS
INSERT INTO flight_segments (id, flight_id, segment_index, origin_location_id, destination_location_id, depart_at, arrive_at, carrier, flight_number, layover_minutes_after)
VALUES
  ('cccccccc-cccc-cccc-cccc-cccccccc0001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb003', 0, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa7', '2026-03-05T13:00:00Z', '2026-03-05T15:10:00Z', 'American', 'AA120', 55),
  ('cccccccc-cccc-cccc-cccc-cccccccc0002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb003', 1, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa7', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '2026-03-05T16:05:00Z', '2026-03-05T18:10:00Z', 'American', 'AA121', NULL),
  ('cccccccc-cccc-cccc-cccc-cccccccc0003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb004', 0, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa7', '2026-03-12T16:00:00Z', '2026-03-12T18:40:00Z', 'Southwest', 'WN200', 70),
  ('cccccccc-cccc-cccc-cccc-cccccccc0004', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb004', 1, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa7', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa6', '2026-03-12T19:50:00Z', '2026-03-12T22:20:00Z', 'Southwest', 'WN201', NULL),
  ('cccccccc-cccc-cccc-cccc-cccccccc0005', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb007', 0, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa7', '2026-03-01T14:00:00Z', '2026-03-01T18:10:00Z', 'United', 'UA900', 65),
  ('cccccccc-cccc-cccc-cccc-cccccccc0006', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb007', 1, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa7', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', '2026-03-01T19:15:00Z', '2026-03-01T22:10:00Z', 'United', 'UA901', NULL)
ON CONFLICT (id) DO NOTHING;

-- HOTELS
INSERT INTO hotels (id, name, location_id, address, lat, lng, star_rating, vip_access, description, amenities, created_at)
VALUES
  ('dddddddd-dddd-dddd-dddd-ddddddddd001', 'Harbor View Hotel', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '123 Embarcadero, San Francisco, CA', 37.795200, -122.393700, 4.5, true, 'Modern waterfront hotel near downtown attractions.', '["Free WiFi","Breakfast available","Fitness center","Pool"]'::jsonb, '2025-01-01T00:00:00Z'),
  ('dddddddd-dddd-dddd-dddd-ddddddddd002', 'Sunset Boulevard Suites', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', '456 Sunset Blvd, Los Angeles, CA', 34.098300, -118.326700, 4.0, false, 'Comfortable suites with easy access to Hollywood.', '["Free WiFi","Parking","Pet friendly"]'::jsonb, '2025-01-01T00:00:00Z'),
  ('dddddddd-dddd-dddd-dddd-ddddddddd003', 'Central Park Boutique', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', '789 5th Ave, New York, NY', 40.764400, -73.974200, 5.0, true, 'Luxury boutique hotel steps from Central Park.', '["Free WiFi","Spa","Gym","Concierge"]'::jsonb, '2025-01-01T00:00:00Z'),
  ('dddddddd-dddd-dddd-dddd-ddddddddd004', 'Desert Lights Resort', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '101 Strip Ave, Las Vegas, NV', 36.114700, -115.172800, 4.2, false, 'Resort-style stay near entertainment and dining.', '["Pool","Casino","Free parking","Gym"]'::jsonb, '2025-01-05T00:00:00Z'),
  ('dddddddd-dddd-dddd-dddd-ddddddddd005', 'Pike Place Inn', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', '85 Pike St, Seattle, WA', 47.609700, -122.342500, 3.9, false, 'Cozy hotel steps from Pike Place Market.', '["Free WiFi","Coffee shop","Pet friendly"]'::jsonb, '2025-01-06T00:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- HOTEL PHOTOS
INSERT INTO hotel_photos (id, hotel_id, url, alt, sort_order)
VALUES
  ('eeeeeeee-eeee-eeee-eeee-eeeeeeee0001', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 'https://images.unsplash.com/photo-1501117716987-c8e1ecb2101f?auto=format&fit=crop&w=1200&q=60', 'Harbor View Hotel exterior', 0),
  ('eeeeeeee-eeee-eeee-eeee-eeeeeeee0002', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1200&q=60', 'Harbor View Hotel room', 1),
  ('eeeeeeee-eeee-eeee-eeee-eeeeeeee0003', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 'https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&w=1200&q=60', 'Harbor View Hotel lobby', 2),
  ('eeeeeeee-eeee-eeee-eeee-eeeeeeee0004', 'dddddddd-dddd-dddd-dddd-ddddddddd002', 'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=1200&q=60', 'Sunset Boulevard Suites exterior', 0),
  ('eeeeeeee-eeee-eeee-eeee-eeeeeeee0005', 'dddddddd-dddd-dddd-dddd-ddddddddd003', 'https://images.unsplash.com/photo-1551887373-6d7bb0ce4f6c?auto=format&fit=crop&w=1200&q=60', 'Central Park Boutique lobby', 0)
ON CONFLICT (id) DO NOTHING;

-- ROOM TYPES
INSERT INTO room_types (id, hotel_id, name, bed_configuration, max_guests, refundable, price_per_night_cents, currency, inventory)
VALUES
  ('ffffffff-ffff-ffff-ffff-ffffffff0001', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 'Standard King', '1 King Bed', 2, true, 18900, 'USD', 10),
  ('ffffffff-ffff-ffff-ffff-ffffffff0002', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 'Deluxe Double', '2 Double Beds', 4, false, 21900, 'USD', 6),
  ('ffffffff-ffff-ffff-ffff-ffffffff0003', 'dddddddd-dddd-dddd-dddd-ddddddddd002', 'Studio Suite', '1 Queen Bed', 2, true, 15900, 'USD', 12),
  ('ffffffff-ffff-ffff-ffff-ffffffff0004', 'dddddddd-dddd-dddd-dddd-ddddddddd003', 'Park View King', '1 King Bed', 2, true, 32900, 'USD', 5),
  ('ffffffff-ffff-ffff-ffff-ffffffff0005', 'dddddddd-dddd-dddd-dddd-ddddddddd004', 'Resort Queen', '2 Queen Beds', 4, true, 20900, 'USD', 20),
  ('ffffffff-ffff-ffff-ffff-ffffffff0006', 'dddddddd-dddd-dddd-dddd-ddddddddd005', 'Cozy King', '1 King Bed', 2, true, 14900, 'USD', 8)
ON CONFLICT (id) DO NOTHING;

-- REVIEWS
INSERT INTO reviews (id, hotel_id, author_name, rating, title, comment, created_at)
VALUES
  ('99999999-9999-9999-9999-999999990001', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 'Jamie', 9, 'Great location', 'Loved the views and walkability.', '2025-02-01T00:00:00Z'),
  ('99999999-9999-9999-9999-999999990002', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 'Taylor', 8, 'Nice stay', 'Clean rooms and friendly staff.', '2025-02-10T00:00:00Z'),
  ('99999999-9999-9999-9999-999999990003', 'dddddddd-dddd-dddd-dddd-ddddddddd002', 'Morgan', 7, 'Good value', 'Convenient to Hollywood, rooms were spacious.', '2025-02-12T00:00:00Z'),
  ('99999999-9999-9999-9999-999999990004', 'dddddddd-dddd-dddd-dddd-ddddddddd003', 'Avery', 10, 'Exceptional', 'Top service and perfect location.', '2025-02-20T00:00:00Z'),
  ('99999999-9999-9999-9999-999999990005', 'dddddddd-dddd-dddd-dddd-ddddddddd005', 'Riley', 8, 'Charming', 'Loved the nearby market and coffee.', '2025-02-22T00:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- CARS
INSERT INTO cars (id, company, model, car_type, seats, transmission, fuel_type, price_per_day_cents, currency, pickup_location_id, dropoff_location_id, inventory)
VALUES
  ('12121212-1212-1212-1212-121212120001', 'Hertz', 'Toyota Corolla', 'compact', 5, 'automatic', 'gas', 4500, 'USD', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 10),
  ('12121212-1212-1212-1212-121212120002', 'Avis', 'Ford Explorer', 'suv', 7, 'automatic', 'gas', 8900, 'USD', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 6),
  ('12121212-1212-1212-1212-121212120003', 'Enterprise', 'Honda Civic', 'compact', 5, 'automatic', 'gas', 4700, 'USD', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', 12),
  ('12121212-1212-1212-1212-121212120004', 'Budget', 'Nissan Rogue', 'suv', 5, 'automatic', 'gas', 7600, 'USD', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 8),
  ('12121212-1212-1212-1212-121212120005', 'Sixt', 'BMW 3 Series', 'luxury', 5, 'automatic', 'gas', 15900, 'USD', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 3)
ON CONFLICT (id) DO NOTHING;

-- CAR EXTRAS
INSERT INTO car_extras (id, code, name, pricing_model, price_cents, currency)
VALUES
  ('13131313-1313-1313-1313-131313130001', 'gps', 'GPS Navigation', 'per_day', 799, 'USD'),
  ('13131313-1313-1313-1313-131313130002', 'child_seat', 'Child Seat', 'per_rental', 2500, 'USD'),
  ('13131313-1313-1313-1313-131313130003', 'insurance', 'Damage Waiver', 'per_day', 1999, 'USD'),
  ('13131313-1313-1313-1313-131313130004', 'wifi', 'In-car WiFi', 'per_day', 999, 'USD'),
  ('13131313-1313-1313-1313-131313130005', 'additional_driver', 'Additional Driver', 'per_rental', 1500, 'USD')
ON CONFLICT (id) DO NOTHING;

-- PROMO CODES
INSERT INTO promo_codes (id, code, type, value, min_subtotal_cents, starts_at, ends_at, max_redemptions, redemptions_count, active)
VALUES
  ('14141414-1414-1414-1414-141414140001', 'WELCOME10', 'percent', 10, 10000, '2025-01-01T00:00:00Z', '2027-01-01T00:00:00Z', 1000, 0, true),
  ('14141414-1414-1414-1414-141414140002', 'SAVE25', 'fixed', 2500, 15000, '2025-01-01T00:00:00Z', '2026-12-31T00:00:00Z', 500, 0, true),
  ('14141414-1414-1414-1414-141414140003', 'FLASH15', 'percent', 15, 20000, '2025-06-01T00:00:00Z', '2026-06-01T00:00:00Z', 250, 3, true),
  ('14141414-1414-1414-1414-141414140004', 'VIP50', 'fixed', 5000, 40000, '2025-01-01T00:00:00Z', '2027-01-01T00:00:00Z', 100, 1, true),
  ('14141414-1414-1414-1414-141414140005', 'EXPIRED5', 'percent', 5, 5000, '2024-01-01T00:00:00Z', '2024-12-31T00:00:00Z', 100, 100, false)
ON CONFLICT (id) DO NOTHING;

-- CARTS
INSERT INTO carts (id, user_id, promo_code_id, created_at, updated_at)
VALUES
  ('15151515-1515-1515-1515-151515150001', '11111111-1111-1111-1111-111111111111', NULL, '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'),
  ('15151515-1515-1515-1515-151515150002', '33333333-3333-3333-3333-333333333333', '14141414-1414-1414-1414-141414140001', '2025-01-02T00:00:00Z', '2025-01-02T00:00:00Z'),
  ('15151515-1515-1515-1515-151515150003', '44444444-4444-4444-4444-444444444444', NULL, '2025-01-03T00:00:00Z', '2025-01-03T00:00:00Z'),
  ('15151515-1515-1515-1515-151515150004', '55555555-5555-5555-5555-555555555555', NULL, '2025-01-04T00:00:00Z', '2025-01-04T00:00:00Z'),
  ('15151515-1515-1515-1515-151515150005', '66666666-6666-6666-6666-666666666666', '14141414-1414-1414-1414-141414140002', '2025-01-05T00:00:00Z', '2025-01-05T00:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- CART ITEMS
INSERT INTO cart_items (id, cart_id, type, reference_id, quantity, start_date, end_date, metadata, price_cents, currency, created_at)
VALUES
  ('16161616-1616-1616-1616-161616160001', '15151515-1515-1515-1515-151515150002', 'flight', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001', 1, NULL, NULL, '{"fare_class":"economy","passengers":1}'::jsonb, 12900, 'USD', '2025-02-01T10:00:00Z'),
  ('16161616-1616-1616-1616-161616160002', '15151515-1515-1515-1515-151515150002', 'hotel', 'dddddddd-dddd-dddd-dddd-ddddddddd001', 1, '2026-02-10', '2026-02-12', '{"guests":2,"rooms":1}'::jsonb, 37800, 'USD', '2025-02-01T10:05:00Z'),
  ('16161616-1616-1616-1616-161616160003', '15151515-1515-1515-1515-151515150003', 'car', '12121212-1212-1212-1212-121212120001', 1, '2026-02-10', '2026-02-12', '{"extras":["gps"]}'::jsonb, 9000, 'USD', '2025-02-02T09:00:00Z'),
  ('16161616-1616-1616-1616-161616160004', '15151515-1515-1515-1515-151515150004', 'flight', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb005', 2, NULL, NULL, '{"fare_class":"economy","passengers":2}'::jsonb, 35000, 'USD', '2025-02-03T11:00:00Z'),
  ('16161616-1616-1616-1616-161616160005', '15151515-1515-1515-1515-151515150005', 'hotel', 'dddddddd-dddd-dddd-dddd-ddddddddd002', 1, '2026-03-12', '2026-03-14', '{"guests":2,"rooms":1}'::jsonb, 31800, 'USD', '2025-02-04T12:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- PACKAGE BUNDLES
INSERT INTO package_bundles (id, flight_id, hotel_id, car_id, discount_percent, created_at)
VALUES
  ('17171717-1717-1717-1717-171717170001', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001', 'dddddddd-dddd-dddd-dddd-ddddddddd001', '12121212-1212-1212-1212-121212120002', 12, '2025-02-10T00:00:00Z'),
  ('17171717-1717-1717-1717-171717170002', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb003', 'dddddddd-dddd-dddd-dddd-ddddddddd004', NULL, 10, '2025-02-11T00:00:00Z'),
  ('17171717-1717-1717-1717-171717170003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb006', 'dddddddd-dddd-dddd-dddd-ddddddddd005', '12121212-1212-1212-1212-121212120003', 15, '2025-02-12T00:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- BOOKINGS
INSERT INTO bookings (id, user_id, type, status, total_cents, currency, details, created_at, updated_at)
VALUES
  ('18181818-1818-1818-1818-181818180001', '44444444-4444-4444-4444-444444444444', 'flight', 'confirmed', 13500, 'USD', '{"fare_class":"economy","passengers":1}'::jsonb, '2025-03-01T12:00:00Z', '2025-03-01T12:00:00Z'),
  ('18181818-1818-1818-1818-181818180002', '33333333-3333-3333-3333-333333333333', 'hotel', 'confirmed', 37800, 'USD', '{"hotel_id":"dddddddd-dddd-dddd-dddd-ddddddddd001","nights":2}'::jsonb, '2025-03-02T12:00:00Z', '2025-03-02T12:00:00Z'),
  ('18181818-1818-1818-1818-181818180003', '11111111-1111-1111-1111-111111111111', 'car', 'cancelled', 9000, 'USD', '{"car_id":"12121212-1212-1212-1212-121212120001","days":2}'::jsonb, '2025-03-03T12:00:00Z', '2025-03-04T12:00:00Z'),
  ('18181818-1818-1818-1818-181818180004', '55555555-5555-5555-5555-555555555555', 'package', 'confirmed', 52000, 'USD', '{"bundle_id":"17171717-1717-1717-1717-171717170001"}'::jsonb, '2025-03-05T12:00:00Z', '2025-03-05T12:00:00Z'),
  ('18181818-1818-1818-1818-181818180005', '66666666-6666-6666-6666-666666666666', 'hotel', 'modified', 31800, 'USD', '{"hotel_id":"dddddddd-dddd-dddd-dddd-ddddddddd002","nights":2,"modified":true}'::jsonb, '2025-03-06T12:00:00Z', '2025-03-07T12:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- BOOKING ITEMS
INSERT INTO booking_items (id, booking_id, type, reference_id, start_date, end_date, metadata, line_total_cents, currency)
VALUES
  ('19191919-1919-1919-1919-191919190001', '18181818-1818-1818-1818-181818180001', 'flight', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb002', NULL, NULL, '{"fare_class":"economy"}'::jsonb, 13500, 'USD'),
  ('19191919-1919-1919-1919-191919190002', '18181818-1818-1818-1818-181818180002', 'hotel', 'dddddddd-dddd-dddd-dddd-ddddddddd001', '2026-02-10', '2026-02-12', '{"guests":2,"rooms":1}'::jsonb, 37800, 'USD'),
  ('19191919-1919-1919-1919-191919190003', '18181818-1818-1818-1818-181818180003', 'car', '12121212-1212-1212-1212-121212120001', '2026-02-10', '2026-02-12', '{"extras":["gps","insurance"]}'::jsonb, 9000, 'USD'),
  ('19191919-1919-1919-1919-191919190004', '18181818-1818-1818-1818-181818180004', 'flight', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbb001', NULL, NULL, '{"fare_class":"economy"}'::jsonb, 12900, 'USD'),
  ('19191919-1919-1919-1919-191919190005', '18181818-1818-1818-1818-181818180004', 'hotel', 'dddddddd-dddd-dddd-dddd-ddddddddd001', '2026-02-10', '2026-02-12', '{"guests":4,"rooms":1}'::jsonb, 43800, 'USD')
ON CONFLICT (id) DO NOTHING;

-- PAYMENT TRANSACTIONS
INSERT INTO payment_transactions (id, booking_id, user_id, amount_cents, currency, status, payment_method_id, provider, provider_reference, created_at)
VALUES
  ('20202020-2020-2020-2020-202020200001', '18181818-1818-1818-1818-181818180001', '44444444-4444-4444-4444-444444444444', 13500, 'USD', 'succeeded', '24242424-2424-2424-2424-242424242424', 'demo', 'ch_demo_0001', '2025-03-01T12:01:00Z'),
  ('20202020-2020-2020-2020-202020200002', '18181818-1818-1818-1818-181818180002', '33333333-3333-3333-3333-333333333333', 37800, 'USD', 'succeeded', '23232323-2323-2323-2323-232323232323', 'demo', 'ch_demo_0002', '2025-03-02T12:01:00Z'),
  ('20202020-2020-2020-2020-202020200003', '18181818-1818-1818-1818-181818180003', '11111111-1111-1111-1111-111111111111', 9000, 'USD', 'failed', '22222222-2222-2222-2222-222222222222', 'demo', 'ch_demo_0003', '2025-03-03T12:01:00Z'),
  ('20202020-2020-2020-2020-202020200004', '18181818-1818-1818-1818-181818180004', '55555555-5555-5555-5555-555555555555', 52000, 'USD', 'succeeded', '25252525-2525-2525-2525-252525252525', 'demo', 'ch_demo_0004', '2025-03-05T12:01:00Z'),
  ('20202020-2020-2020-2020-202020200005', '18181818-1818-1818-1818-181818180005', '66666666-6666-6666-6666-666666666666', 31800, 'USD', 'succeeded', '26262626-2626-2626-2626-262626262626', 'demo', 'ch_demo_0005', '2025-03-06T12:01:00Z')
ON CONFLICT (id) DO NOTHING;

-- FAVORITES
INSERT INTO favorites (id, user_id, type, reference_id, created_at)
VALUES
  ('21212121-2121-2121-2121-212121210001', '44444444-4444-4444-4444-444444444444', 'hotel', 'dddddddd-dddd-dddd-dddd-ddddddddd001', '2025-02-15T00:00:00Z'),
  ('21212121-2121-2121-2121-212121210002', '33333333-3333-3333-3333-333333333333', 'hotel', 'dddddddd-dddd-dddd-dddd-ddddddddd003', '2025-02-16T00:00:00Z'),
  ('21212121-2121-2121-2121-212121210003', '11111111-1111-1111-1111-111111111111', 'hotel', 'dddddddd-dddd-dddd-dddd-ddddddddd002', '2025-02-17T00:00:00Z'),
  ('21212121-2121-2121-2121-212121210004', '55555555-5555-5555-5555-555555555555', 'hotel', 'dddddddd-dddd-dddd-dddd-ddddddddd005', '2025-02-18T00:00:00Z'),
  ('21212121-2121-2121-2121-212121210005', '66666666-6666-6666-6666-666666666666', 'hotel', 'dddddddd-dddd-dddd-dddd-ddddddddd004', '2025-02-19T00:00:00Z')
ON CONFLICT (id) DO NOTHING;

-- end seed
