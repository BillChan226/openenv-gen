-- 01_schema.sql
-- Expedia-style travel booking schema (PostgreSQL)
-- Conventions: snake_case, money stored as INTEGER cents with *_cents suffix.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Updated-at trigger helper
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================
-- Core identity
-- =====================
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  phone TEXT,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS users_email_uq ON users (email);

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS payment_methods (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand TEXT NOT NULL,
  last4 TEXT NOT NULL,
  exp_month INTEGER NOT NULL,
  exp_year INTEGER NOT NULL,
  billing_zip TEXT,
  token TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS payment_methods_user_id_idx ON payment_methods (user_id);

-- =====================
-- Search entities
-- =====================
CREATE TABLE IF NOT EXISTS locations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL,
  label TEXT NOT NULL,
  type TEXT NOT NULL,
  country_code TEXT,
  region TEXT,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  CONSTRAINT locations_type_chk CHECK (type IN ('city','airport','region'))
);

CREATE UNIQUE INDEX IF NOT EXISTS locations_code_uq ON locations (code);
-- Spec mentions trigram index as optional; implement btree for portability.
CREATE INDEX IF NOT EXISTS locations_label_idx ON locations (label);

CREATE TABLE IF NOT EXISTS airlines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL,
  name TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS airlines_code_uq ON airlines (code);

CREATE TABLE IF NOT EXISTS flights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  airline_id UUID NOT NULL REFERENCES airlines(id) ON DELETE RESTRICT,
  flight_number TEXT NOT NULL,
  origin_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  destination_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  depart_at TIMESTAMPTZ NOT NULL,
  arrive_at TIMESTAMPTZ NOT NULL,
  duration_minutes INTEGER NOT NULL,
  stops INTEGER NOT NULL DEFAULT 0,
  seat_class TEXT NOT NULL DEFAULT 'economy',
  price_cents INTEGER NOT NULL,
  refundable BOOLEAN NOT NULL DEFAULT FALSE,
  baggage_included BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT flights_seat_class_chk CHECK (seat_class IN ('economy','business','first')),
  CONSTRAINT flights_stops_nonneg_chk CHECK (stops >= 0),
  CONSTRAINT flights_duration_positive_chk CHECK (duration_minutes > 0),
  CONSTRAINT flights_depart_before_arrive_chk CHECK (depart_at < arrive_at),
  CONSTRAINT flights_origin_ne_destination_chk CHECK (origin_location_id <> destination_location_id)
);

CREATE INDEX IF NOT EXISTS flights_origin_dest_depart_idx
  ON flights (origin_location_id, destination_location_id, depart_at);
CREATE INDEX IF NOT EXISTS flights_price_idx ON flights (price_cents);
CREATE INDEX IF NOT EXISTS flights_airline_idx ON flights (airline_id);

-- =====================
-- Hotels
-- =====================
CREATE TABLE IF NOT EXISTS hotels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  description TEXT,
  address TEXT,
  star_rating NUMERIC(2,1),
  review_rating NUMERIC(2,1),
  review_count INTEGER NOT NULL DEFAULT 0,
  nightly_base_price_cents INTEGER NOT NULL,
  is_vip_access BOOLEAN NOT NULL DEFAULT FALSE,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT hotels_review_count_nonneg_chk CHECK (review_count >= 0)
);

CREATE INDEX IF NOT EXISTS hotels_location_idx ON hotels (location_id);
CREATE INDEX IF NOT EXISTS hotels_price_idx ON hotels (nightly_base_price_cents);

CREATE TABLE IF NOT EXISTS hotel_photos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id UUID NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS hotel_photos_hotel_id_idx ON hotel_photos (hotel_id);

CREATE TABLE IF NOT EXISTS hotel_amenities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL,
  label TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS hotel_amenities_code_uq ON hotel_amenities (code);

CREATE TABLE IF NOT EXISTS hotel_hotel_amenities (
  hotel_id UUID NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
  amenity_id UUID NOT NULL REFERENCES hotel_amenities(id) ON DELETE CASCADE,
  PRIMARY KEY (hotel_id, amenity_id)
);

CREATE INDEX IF NOT EXISTS hotel_hotel_amenities_amenity_idx ON hotel_hotel_amenities (amenity_id);

CREATE TABLE IF NOT EXISTS hotel_rooms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id UUID NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  bed_configuration TEXT,
  max_guests INTEGER NOT NULL DEFAULT 2,
  price_per_night_cents INTEGER NOT NULL,
  inventory INTEGER NOT NULL DEFAULT 10,
  CONSTRAINT hotel_rooms_max_guests_positive_chk CHECK (max_guests > 0),
  CONSTRAINT hotel_rooms_inventory_nonneg_chk CHECK (inventory >= 0)
);

CREATE INDEX IF NOT EXISTS hotel_rooms_hotel_id_idx ON hotel_rooms (hotel_id);

-- =====================
-- Cars
-- =====================
CREATE TABLE IF NOT EXISTS car_companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cars (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES car_companies(id) ON DELETE RESTRICT,
  pickup_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  dropoff_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  model TEXT NOT NULL,
  car_type TEXT NOT NULL,
  seats INTEGER NOT NULL DEFAULT 5,
  transmission TEXT NOT NULL DEFAULT 'automatic',
  fuel_type TEXT NOT NULL DEFAULT 'gas',
  base_price_per_day_cents INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT cars_seats_positive_chk CHECK (seats > 0)
);

CREATE INDEX IF NOT EXISTS cars_pickup_dropoff_idx ON cars (pickup_location_id, dropoff_location_id);
CREATE INDEX IF NOT EXISTS cars_price_idx ON cars (base_price_per_day_cents);

-- =====================
-- Packages
-- =====================
CREATE TABLE IF NOT EXISTS packages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_type TEXT NOT NULL,
  flight_id UUID NOT NULL REFERENCES flights(id) ON DELETE RESTRICT,
  hotel_id UUID NOT NULL REFERENCES hotels(id) ON DELETE RESTRICT,
  car_id UUID REFERENCES cars(id) ON DELETE RESTRICT,
  discount_cents INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT packages_bundle_type_chk CHECK (bundle_type IN ('flight_hotel','flight_hotel_car'))
);

CREATE INDEX IF NOT EXISTS packages_bundle_type_idx ON packages (bundle_type);

-- =====================
-- Favorites
-- =====================
CREATE TABLE IF NOT EXISTS favorites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  item_type TEXT NOT NULL DEFAULT 'hotel',
  hotel_id UUID REFERENCES hotels(id) ON DELETE CASCADE,
  flight_id UUID REFERENCES flights(id) ON DELETE CASCADE,
  car_id UUID REFERENCES cars(id) ON DELETE CASCADE,
  package_id UUID REFERENCES packages(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT favorites_item_type_chk CHECK (item_type IN ('hotel','flight','car','package'))
);

CREATE INDEX IF NOT EXISTS favorites_user_id_idx ON favorites (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS favorites_user_item_uq
  ON favorites (user_id, item_type, hotel_id, flight_id, car_id, package_id);

-- =====================
-- Promo codes
-- =====================
CREATE TABLE IF NOT EXISTS promo_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL,
  discount_type TEXT NOT NULL DEFAULT 'amount',
  discount_value INTEGER NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  expires_at TIMESTAMPTZ,
  CONSTRAINT promo_codes_discount_type_chk CHECK (discount_type IN ('amount','percent'))
);

CREATE UNIQUE INDEX IF NOT EXISTS promo_codes_code_uq ON promo_codes (code);

-- =====================
-- Cart
-- =====================
CREATE TABLE IF NOT EXISTS carts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  session_id TEXT,
  promo_code_id UUID REFERENCES promo_codes(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS carts_user_id_idx ON carts (user_id);
CREATE INDEX IF NOT EXISTS carts_session_id_idx ON carts (session_id);

CREATE TRIGGER carts_set_updated_at
BEFORE UPDATE ON carts
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS cart_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cart_id UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  item_type TEXT NOT NULL,
  flight_id UUID REFERENCES flights(id) ON DELETE RESTRICT,
  hotel_id UUID REFERENCES hotels(id) ON DELETE RESTRICT,
  hotel_room_id UUID REFERENCES hotel_rooms(id) ON DELETE RESTRICT,
  car_id UUID REFERENCES cars(id) ON DELETE RESTRICT,
  package_id UUID REFERENCES packages(id) ON DELETE RESTRICT,
  start_date DATE,
  end_date DATE,
  passengers INTEGER,
  guests INTEGER,
  rooms INTEGER,
  extras JSONB,
  subtotal_cents INTEGER NOT NULL,
  taxes_cents INTEGER NOT NULL DEFAULT 0,
  fees_cents INTEGER NOT NULL DEFAULT 0,
  total_cents INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT cart_items_item_type_chk CHECK (item_type IN ('flight','hotel','car','package'))
);

CREATE INDEX IF NOT EXISTS cart_items_cart_id_idx ON cart_items (cart_id);
CREATE INDEX IF NOT EXISTS cart_items_type_idx ON cart_items (item_type);

-- =====================
-- Orders / Trips
-- =====================
CREATE TABLE IF NOT EXISTS orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'confirmed',
  promo_code_id UUID REFERENCES promo_codes(id) ON DELETE SET NULL,
  subtotal_cents INTEGER NOT NULL,
  taxes_cents INTEGER NOT NULL DEFAULT 0,
  fees_cents INTEGER NOT NULL DEFAULT 0,
  discounts_cents INTEGER NOT NULL DEFAULT 0,
  total_cents INTEGER NOT NULL,
  payment_status TEXT NOT NULL DEFAULT 'paid',
  refund_total_cents INTEGER NOT NULL DEFAULT 0,
  cancelled_at TIMESTAMPTZ,
  confirmation_code TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT orders_status_chk CHECK (status IN ('pending','confirmed','cancelled')),
  CONSTRAINT orders_payment_status_chk CHECK (payment_status IN ('unpaid','paid','failed'))
);

CREATE INDEX IF NOT EXISTS orders_user_id_idx ON orders (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS orders_confirmation_uq ON orders (confirmation_code);

CREATE TABLE IF NOT EXISTS order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  item_type TEXT NOT NULL,
  flight_id UUID REFERENCES flights(id) ON DELETE RESTRICT,
  hotel_id UUID REFERENCES hotels(id) ON DELETE RESTRICT,
  hotel_room_id UUID REFERENCES hotel_rooms(id) ON DELETE RESTRICT,
  car_id UUID REFERENCES cars(id) ON DELETE RESTRICT,
  package_id UUID REFERENCES packages(id) ON DELETE RESTRICT,
  start_date DATE,
  end_date DATE,
  passengers INTEGER,
  guests INTEGER,
  rooms INTEGER,
  extras JSONB,
  subtotal_cents INTEGER NOT NULL,
  taxes_cents INTEGER NOT NULL DEFAULT 0,
  fees_cents INTEGER NOT NULL DEFAULT 0,
  total_cents INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'confirmed',
  cancelled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT order_items_item_type_chk CHECK (item_type IN ('flight','hotel','car','package')),
  CONSTRAINT order_items_status_chk CHECK (status IN ('confirmed','cancelled','modified'))
);

CREATE INDEX IF NOT EXISTS order_items_order_id_idx ON order_items (order_id);
CREATE INDEX IF NOT EXISTS order_items_type_idx ON order_items (item_type);

COMMIT;
