-- 02_seed.sql
-- Seed data for local development/testing.

BEGIN;

-- Clear in dependency order
TRUNCATE TABLE
  order_items,
  orders,
  cart_items,
  carts,
  favorites,
  packages,
  cars,
  car_companies,
  hotel_rooms,
  hotel_hotel_amenities,
  hotel_amenities,
  hotel_photos,
  hotels,
  flights,
  airlines,
  locations,
  payment_methods,
  users
RESTART IDENTITY;

-- ============
-- Users
-- ============
INSERT INTO users (id, email, password_hash, full_name, phone, is_admin)
VALUES
  (
    '00000000-0000-0000-0000-000000000001',
    'admin@expedia.com',
    '$2b$10$9VxvSxlJ8MZcYQbKqjFQ2O6b3Gm2rQxgqG0eVQw8WjG0yqk4C1Nje',
    'Expedia Admin',
    '+1-555-0100',
    TRUE
  ),
  (
    '00000000-0000-0000-0000-000000000002',
    'jane@example.com',
    '$2b$10$Qm1oYc3m7d1sGv0H8m7KQeS8n9oPzSgq2m8dQfY8VgQ8mVfQj1T7K',
    'Jane Traveler',
    '+1-555-0101',
    FALSE
  ),
  (
    '00000000-0000-0000-0000-000000000003',
    'sam@example.com',
    '$2b$10$Qm1oYc3m7d1sGv0H8m7KQeS8n9oPzSgq2m8dQfY8VgQ8mVfQj1T7K',
    'Sam Explorer',
    NULL,
    FALSE
  );

INSERT INTO payment_methods (user_id, brand, last4, exp_month, exp_year, billing_zip, token)
VALUES
  ('00000000-0000-0000-0000-000000000002', 'VISA', '4242', 12, 2030, '94105', 'tok_visa_4242'),
  ('00000000-0000-0000-0000-000000000003', 'MASTERCARD', '4444', 11, 2029, '10001', 'tok_mc_4444');

-- ============
-- Locations (mix of cities/airports/regions)
-- ============
INSERT INTO locations (id, code, label, type, country_code, region, lat, lng)
VALUES
  ('10000000-0000-0000-0000-000000000001','NYC','New York, NY','city','US','NY',40.7128,-74.0060),
  ('10000000-0000-0000-0000-000000000002','JFK','John F. Kennedy International Airport (JFK)','airport','US','NY',40.6413,-73.7781),
  ('10000000-0000-0000-0000-000000000003','LGA','LaGuardia Airport (LGA)','airport','US','NY',40.7769,-73.8740),
  ('10000000-0000-0000-0000-000000000004','EWR','Newark Liberty International Airport (EWR)','airport','US','NJ',40.6895,-74.1745),

  ('10000000-0000-0000-0000-000000000005','BOS','Boston, MA','city','US','MA',42.3601,-71.0589),
  ('10000000-0000-0000-0000-000000000006','BOS-A','Boston Logan International Airport (BOS)','airport','US','MA',42.3656,-71.0096),

  ('10000000-0000-0000-0000-000000000007','SFO','San Francisco, CA','city','US','CA',37.7749,-122.4194),
  ('10000000-0000-0000-0000-000000000008','SFO-A','San Francisco International Airport (SFO)','airport','US','CA',37.6213,-122.3790),
  ('10000000-0000-0000-0000-000000000009','OAK','Oakland, CA','city','US','CA',37.8044,-122.2712),

  ('10000000-0000-0000-0000-000000000010','LAX','Los Angeles, CA','city','US','CA',34.0522,-118.2437),
  ('10000000-0000-0000-0000-000000000011','LAX-A','Los Angeles International Airport (LAX)','airport','US','CA',33.9416,-118.4085),

  ('10000000-0000-0000-0000-000000000012','SEA','Seattle, WA','city','US','WA',47.6062,-122.3321),
  ('10000000-0000-0000-0000-000000000013','SEA-A','Seattle-Tacoma International Airport (SEA)','airport','US','WA',47.4502,-122.3088),

  ('10000000-0000-0000-0000-000000000014','CHI','Chicago, IL','city','US','IL',41.8781,-87.6298),
  ('10000000-0000-0000-0000-000000000015','ORD','O\'Hare International Airport (ORD)','airport','US','IL',41.9742,-87.9073),

  ('10000000-0000-0000-0000-000000000016','MIA','Miami, FL','city','US','FL',25.7617,-80.1918),
  ('10000000-0000-0000-0000-000000000017','MIA-A','Miami International Airport (MIA)','airport','US','FL',25.7959,-80.2870),

  ('10000000-0000-0000-0000-000000000018','LAS','Las Vegas, NV','city','US','NV',36.1699,-115.1398),
  ('10000000-0000-0000-0000-000000000019','LAS-A','Harry Reid International Airport (LAS)','airport','US','NV',36.0840,-115.1537),

  ('10000000-0000-0000-0000-000000000020','AUS','Austin, TX','city','US','TX',30.2672,-97.7431),
  ('10000000-0000-0000-0000-000000000021','AUS-A','Austin-Bergstrom International Airport (AUS)','airport','US','TX',30.1975,-97.6664),

  ('10000000-0000-0000-0000-000000000022','DEN','Denver, CO','city','US','CO',39.7392,-104.9903),
  ('10000000-0000-0000-0000-000000000023','DEN-A','Denver International Airport (DEN)','airport','US','CO',39.8561,-104.6737),

  ('10000000-0000-0000-0000-000000000024','PHX','Phoenix, AZ','city','US','AZ',33.4484,-112.0740),
  ('10000000-0000-0000-0000-000000000025','PHX-A','Phoenix Sky Harbor International Airport (PHX)','airport','US','AZ',33.4342,-112.0116),

  ('10000000-0000-0000-0000-000000000026','DFW','Dallas, TX','city','US','TX',32.7767,-96.7970),
  ('10000000-0000-0000-0000-000000000027','DFW-A','Dallas/Fort Worth International Airport (DFW)','airport','US','TX',32.8998,-97.0403),

  ('10000000-0000-0000-0000-000000000028','ATL','Atlanta, GA','city','US','GA',33.7490,-84.3880),
  ('10000000-0000-0000-0000-000000000029','ATL-A','Hartsfield-Jackson Atlanta International Airport (ATL)','airport','US','GA',33.6407,-84.4277),

  ('10000000-0000-0000-0000-000000000030','WDC','Washington, DC','city','US','DC',38.9072,-77.0369),
  ('10000000-0000-0000-0000-000000000031','IAD','Washington Dulles International Airport (IAD)','airport','US','VA',38.9531,-77.4565),

  ('10000000-0000-0000-0000-000000000032','ORL','Orlando, FL','city','US','FL',28.5383,-81.3792),
  ('10000000-0000-0000-0000-000000000033','MCO','Orlando International Airport (MCO)','airport','US','FL',28.4312,-81.3081),

  ('10000000-0000-0000-0000-000000000034','SD','San Diego, CA','city','US','CA',32.7157,-117.1611),
  ('10000000-0000-0000-0000-000000000035','SAN','San Diego International Airport (SAN)','airport','US','CA',32.7338,-117.1933),

  ('10000000-0000-0000-0000-000000000036','REG-WEST','US West Coast','region','US','US West',NULL,NULL),
  ('10000000-0000-0000-0000-000000000037','REG-EAST','US East Coast','region','US','US East',NULL,NULL);

-- ============
-- Airlines
-- ============
INSERT INTO airlines (id, code, name)
VALUES
  ('20000000-0000-0000-0000-000000000001','AA','American Airlines'),
  ('20000000-0000-0000-0000-000000000002','DL','Delta Air Lines'),
  ('20000000-0000-0000-0000-000000000003','UA','United Airlines'),
  ('20000000-0000-0000-0000-000000000004','WN','Southwest Airlines'),
  ('20000000-0000-0000-0000-000000000005','B6','JetBlue');

-- ============
-- Flights (>= 50)
-- Generate 60 flights across common routes; depart_at spread across next 30 days.
-- ============
WITH routes AS (
  SELECT * FROM (VALUES
    ('SFO-A','LAX-A',  90),
    ('LAX-A','SFO-A',  95),
    ('JFK','LAX-A',   360),
    ('LAX-A','JFK',   345),
    ('SEA-A','SFO-A', 125),
    ('SFO-A','SEA-A', 120),
    ('ORD','MIA-A',   185),
    ('MIA-A','ORD',   190),
    ('DFW-A','DEN-A', 120),
    ('DEN-A','DFW-A', 125),
    ('BOS-A','ATL-A', 165),
    ('ATL-A','BOS-A', 160),
    ('LAS-A','PHX-A',  65),
    ('PHX-A','LAS-A',  70),
    ('IAD','MCO',     140),
    ('MCO','IAD',     145),
    ('SAN','SFO-A',    95),
    ('SFO-A','SAN',    90),
    ('AUS-A','DFW-A',  55),
    ('DFW-A','AUS-A',  55)
  ) AS t(origin_code, dest_code, duration_minutes)
),
airports AS (
  SELECT code, id FROM locations WHERE type='airport'
),
route_ids AS (
  SELECT a1.id AS origin_location_id, a2.id AS destination_location_id, r.duration_minutes,
         row_number() OVER (ORDER BY r.origin_code, r.dest_code) AS route_rn
  FROM routes r
  JOIN airports a1 ON a1.code = r.origin_code
  JOIN airports a2 ON a2.code = r.dest_code
),
airline_pool AS (
  SELECT id, code, row_number() OVER (ORDER BY code) AS airline_rn FROM airlines
)
INSERT INTO flights (
  airline_id, flight_number, origin_location_id, destination_location_id,
  depart_at, arrive_at, duration_minutes, stops, seat_class, price_cents, refundable, baggage_included
)
SELECT
  ap.id AS airline_id,
  ap.code || (100 + ((g-1) % 900))::text AS flight_number,
  r.origin_location_id,
  r.destination_location_id,
  now() + ((g-1) % 30) * interval '1 day' + (((g-1) % 12) + 6) * interval '1 hour' AS depart_at,
  (now() + ((g-1) % 30) * interval '1 day' + (((g-1) % 12) + 6) * interval '1 hour')
    + (r.duration_minutes * interval '1 minute') AS arrive_at,
  r.duration_minutes,
  CASE WHEN (g % 10)=0 THEN 1 ELSE 0 END AS stops,
  CASE (g-1) % 3 WHEN 0 THEN 'economy' WHEN 1 THEN 'business' ELSE 'first' END AS seat_class,
  (
    CASE (g-1) % 3
      WHEN 0 THEN 12900
      WHEN 1 THEN 28900
      ELSE 49900
    END
    + ((g % 20) * 500)
  ) AS price_cents,
  (g % 7)=0 AS refundable,
  TRUE
FROM generate_series(1,60) AS gs(g)
JOIN route_ids r ON r.route_rn = ((g-1) % 20) + 1
JOIN airline_pool ap ON ap.airline_rn = ((g-1) % 5) + 1;

-- ============
-- Hotels (>= 30)
-- ============
WITH city_locs AS (
  SELECT id, code, label, lat, lng FROM locations WHERE type='city'
),
hotels_seed AS (
  SELECT
    c.id AS location_id,
    c.code,
    c.label,
    (row_number() OVER (ORDER BY c.code)) AS rn
  FROM city_locs c
)
INSERT INTO hotels (location_id, name, description, address, star_rating, review_rating, review_count, nightly_base_price_cents, is_vip_access, lat, lng)
SELECT
  hs.location_id,
  hs.label || ' Grand Hotel ' || ((hs.rn-1) % 5 + 1)::text,
  'Modern hotel in ' || hs.label || ' with convenient access to top attractions.',
  (100 + hs.rn)::text || ' Main St, ' || hs.label,
  (3.0 + ((hs.rn % 3) * 0.5))::numeric(2,1),
  (4.0 + ((hs.rn % 6) * 0.1))::numeric(2,1),
  50 + (hs.rn * 7),
  13900 + ((hs.rn % 20) * 800),
  (hs.rn % 6)=0,
  hs.lat,
  hs.lng
FROM hotels_seed hs
CROSS JOIN generate_series(1,3) gs(n)
WHERE (hs.rn + gs.n) IS NOT NULL
LIMIT 30;

-- Photos: 3 per hotel
INSERT INTO hotel_photos (hotel_id, url, sort_order)
SELECT h.id,
       'https://picsum.photos/seed/hotel_' || substr(h.id::text,1,8) || '_' || p::text || '/1200/800' AS url,
       p-1 AS sort_order
FROM hotels h
CROSS JOIN generate_series(1,3) p;

-- Amenities master list
INSERT INTO hotel_amenities (code, label)
VALUES
  ('wifi','Free WiFi'),
  ('pool','Pool'),
  ('gym','Fitness Center'),
  ('parking','Parking Available'),
  ('breakfast','Breakfast Included'),
  ('spa','Spa'),
  ('pet_friendly','Pet Friendly'),
  ('airport_shuttle','Airport Shuttle'),
  ('restaurant','Restaurant'),
  ('bar','Bar/Lounge');

-- Associate 4 amenities per hotel deterministically
WITH a AS (
  SELECT id, row_number() OVER (ORDER BY code) AS rn FROM hotel_amenities
),
h AS (
  SELECT id, row_number() OVER (ORDER BY created_at, id) AS rn FROM hotels
)
INSERT INTO hotel_hotel_amenities (hotel_id, amenity_id)
SELECT
  h.id,
  a.id
FROM h
JOIN a
  ON a.rn IN (
    ((h.rn % 10) + 1),
    (((h.rn+2) % 10) + 1),
    (((h.rn+4) % 10) + 1),
    (((h.rn+6) % 10) + 1)
  );

-- Rooms: 2 per hotel
INSERT INTO hotel_rooms (hotel_id, name, bed_configuration, max_guests, price_per_night_cents, inventory)
SELECT
  h.id,
  'Standard Room',
  '1 Queen',
  2,
  GREATEST(9900, h.nightly_base_price_cents - 2000),
  12
FROM hotels h;

INSERT INTO hotel_rooms (hotel_id, name, bed_configuration, max_guests, price_per_night_cents, inventory)
SELECT
  h.id,
  'Suite',
  '1 King + Sofa bed',
  4,
  h.nightly_base_price_cents + 6000,
  6
FROM hotels h;

-- ============
-- Car companies + Cars (>= 20)
-- ============
INSERT INTO car_companies (id, name)
VALUES
  ('30000000-0000-0000-0000-000000000001','Hertz'),
  ('30000000-0000-0000-0000-000000000002','Avis'),
  ('30000000-0000-0000-0000-000000000003','Enterprise'),
  ('30000000-0000-0000-0000-000000000004','Budget');

WITH airports AS (
  SELECT id, row_number() OVER (ORDER BY code) AS rn FROM locations WHERE type='airport'
),
companies AS (
  SELECT id, row_number() OVER (ORDER BY name) AS rn FROM car_companies
),
models AS (
  SELECT model, car_type, seats, transmission, fuel_type, base_price_per_day_cents,
         row_number() OVER (ORDER BY model) AS rn
  FROM (VALUES
    ('Toyota Corolla','compact',5,'automatic','gas', 4200),
    ('Honda Civic','compact',5,'automatic','gas', 4500),
    ('Nissan Rogue','suv',5,'automatic','gas', 6500),
    ('Ford Explorer','suv',7,'automatic','gas', 8200),
    ('Tesla Model 3','electric',5,'automatic','electric', 9800),
    ('Jeep Wrangler','suv',5,'automatic','gas', 9000),
    ('Chevrolet Malibu','midsize',5,'automatic','gas', 5600),
    ('BMW 3 Series','luxury',5,'automatic','gas', 12000)
  ) AS m(model, car_type, seats, transmission, fuel_type, base_price_per_day_cents)
)
INSERT INTO cars (company_id, pickup_location_id, dropoff_location_id, model, car_type, seats, transmission, fuel_type, base_price_per_day_cents)
SELECT
  c.id,
  a1.id,
  a2.id,
  m.model,
  m.car_type,
  m.seats,
  m.transmission,
  m.fuel_type,
  m.base_price_per_day_cents + ((g % 10) * 200)
FROM generate_series(1,24) g
JOIN companies c ON c.rn = ((g-1) % 4) + 1
JOIN airports a1 ON a1.rn = ((g-1) % 10) + 1
JOIN airports a2 ON a2.rn = ((g+2) % 10) + 1
JOIN models m ON m.rn = ((g-1) % 8) + 1;

-- ============
-- Packages (some examples)
-- ============
INSERT INTO packages (bundle_type, flight_id, hotel_id, car_id, discount_cents)
SELECT
  'flight_hotel',
  f.id,
  h.id,
  NULL,
  2500
FROM flights f
JOIN hotels h ON TRUE
WHERE f.seat_class='economy'
LIMIT 10;

INSERT INTO packages (bundle_type, flight_id, hotel_id, car_id, discount_cents)
SELECT
  'flight_hotel_car',
  f.id,
  h.id,
  c.id,
  4500
FROM flights f
JOIN hotels h ON TRUE
JOIN cars c ON TRUE
WHERE f.seat_class='economy'
LIMIT 10;

-- ============
-- Promo codes
-- ============
INSERT INTO promo_codes (code, discount_type, discount_value, is_active, expires_at)
VALUES
  ('WELCOME10', 'percent', 10, TRUE, now() + interval '365 days'),
  ('SAVE25', 'amount', 2500, TRUE, now() + interval '180 days'),
  ('EXPIRED5', 'percent', 5, FALSE, now() - interval '1 day');

-- ============
-- Favorites (a few)
-- ============
INSERT INTO favorites (user_id, item_type, hotel_id)
SELECT '00000000-0000-0000-0000-000000000002', 'hotel', h.id
FROM hotels h
LIMIT 5;

-- ============
-- One sample cart with items
-- ============
INSERT INTO carts (id, user_id, promo_code_id)
VALUES (
  '40000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000002',
  (SELECT id FROM promo_codes WHERE code='WELCOME10')
);

-- Add flight item
INSERT INTO cart_items (cart_id, item_type, flight_id, passengers, subtotal_cents, taxes_cents, fees_cents, total_cents)
SELECT
  '40000000-0000-0000-0000-000000000001',
  'flight',
  f.id,
  1,
  f.price_cents,
  (f.price_cents * 0.08)::int,
  0,
  (f.price_cents + (f.price_cents * 0.08)::int)
FROM flights f
ORDER BY f.depart_at
LIMIT 1;

-- Add hotel item (2 nights)
INSERT INTO cart_items (cart_id, item_type, hotel_id, hotel_room_id, start_date, end_date, guests, rooms, subtotal_cents, taxes_cents, fees_cents, total_cents)
SELECT
  '40000000-0000-0000-0000-000000000001',
  'hotel',
  h.id,
  r.id,
  (current_date + 7),
  (current_date + 9),
  2,
  1,
  (r.price_per_night_cents * 2),
  ((r.price_per_night_cents * 2) * 0.12)::int,
  1500,
  (r.price_per_night_cents * 2) + (((r.price_per_night_cents * 2) * 0.12)::int) + 1500
FROM hotels h
JOIN hotel_rooms r ON r.hotel_id = h.id
ORDER BY h.created_at
LIMIT 1;

-- ============
-- One sample order + order items
-- ============
INSERT INTO orders (
  id, user_id, status, promo_code_id,
  subtotal_cents, taxes_cents, fees_cents, discounts_cents, total_cents,
  payment_status, refund_total_cents, confirmation_code
)
VALUES (
  '50000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000002',
  'confirmed',
  (SELECT id FROM promo_codes WHERE code='SAVE25'),
  60000,
  7200,
  1500,
  2500,
  66200,
  'paid',
  0,
  'CONF-TEST-0001'
);

INSERT INTO order_items (
  order_id, item_type, flight_id, start_date, end_date, passengers,
  subtotal_cents, taxes_cents, fees_cents, total_cents
)
SELECT
  '50000000-0000-0000-0000-000000000001',
  'flight',
  f.id,
  current_date + 21,
  NULL,
  1,
  f.price_cents,
  (f.price_cents * 0.08)::int,
  0,
  f.price_cents + (f.price_cents * 0.08)::int
FROM flights f
ORDER BY f.depart_at DESC
LIMIT 1;

INSERT INTO order_items (
  order_id, item_type, hotel_id, hotel_room_id, start_date, end_date, guests, rooms,
  subtotal_cents, taxes_cents, fees_cents, total_cents
)
SELECT
  '50000000-0000-0000-0000-000000000001',
  'hotel',
  h.id,
  r.id,
  current_date + 21,
  current_date + 24,
  2,
  1,
  (r.price_per_night_cents * 3),
  ((r.price_per_night_cents * 3) * 0.12)::int,
  1500,
  (r.price_per_night_cents * 3) + (((r.price_per_night_cents * 3) * 0.12)::int) + 1500
FROM hotels h
JOIN hotel_rooms r ON r.hotel_id = h.id
ORDER BY h.created_at DESC
LIMIT 1;

COMMIT;
