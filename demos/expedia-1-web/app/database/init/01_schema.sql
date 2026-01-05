-- app/database/init/01_schema.sql
-- Schema version: 1.0.0
-- PostgreSQL

-- NOTE: Do not wrap schema in an explicit transaction.
-- The official postgres Docker image runs /docker-entrypoint-initdb.d/*.sql
-- with ON_ERROR_STOP=1 and may already be in a transaction depending on how
-- the script is executed. Keeping schema DDL outside an explicit BEGIN/COMMIT
-- avoids "cannot run inside a transaction block" issues for certain commands.


-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enums
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'location_type') THEN
    CREATE TYPE location_type AS ENUM ('airport','city','region','place');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'cart_item_type') THEN
    CREATE TYPE cart_item_type AS ENUM ('flight','hotel','car','package');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_type') THEN
    CREATE TYPE booking_type AS ENUM ('flight','hotel','car','package');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_status') THEN
    CREATE TYPE booking_status AS ENUM ('confirmed','cancelled','modified');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_item_type') THEN
    CREATE TYPE booking_item_type AS ENUM ('flight','hotel','car');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'car_type') THEN
    CREATE TYPE car_type AS ENUM ('economy','compact','midsize','suv','luxury','van');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transmission') THEN
    CREATE TYPE transmission AS ENUM ('automatic','manual');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'fuel_type') THEN
    CREATE TYPE fuel_type AS ENUM ('gas','diesel','hybrid','electric');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'promo_type') THEN
    CREATE TYPE promo_type AS ENUM ('percent','fixed');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
    CREATE TYPE payment_status AS ENUM ('succeeded','failed');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'favorite_type') THEN
    CREATE TYPE favorite_type AS ENUM ('hotel');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'car_extra_pricing_model') THEN
    CREATE TYPE car_extra_pricing_model AS ENUM ('per_day','per_rental');
  END IF;
END $$;

-- Trigger function to maintain updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Tables

-- users
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email varchar(255) NOT NULL UNIQUE,
  password_hash varchar(255) NOT NULL,
  name varchar(120) NOT NULL,
  phone varchar(30),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- payment_methods
CREATE TABLE IF NOT EXISTS payment_methods (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  brand varchar(30) NOT NULL,
  last4 char(4) NOT NULL,
  exp_month int NOT NULL,
  exp_year int NOT NULL,
  token varchar(255) NOT NULL,
  billing_name varchar(120),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_payment_methods_exp_month CHECK (exp_month BETWEEN 1 AND 12)
);

CREATE INDEX IF NOT EXISTS idx_payment_methods_user_id ON payment_methods(user_id);

-- locations
CREATE TABLE IF NOT EXISTS locations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  type location_type NOT NULL,
  code varchar(10),
  name varchar(120) NOT NULL,
  country varchar(80) NOT NULL,
  region varchar(80),
  lat numeric(9,6),
  lng numeric(9,6)
);

CREATE INDEX IF NOT EXISTS idx_locations_type ON locations(type);
CREATE INDEX IF NOT EXISTS idx_locations_code ON locations(code);
CREATE INDEX IF NOT EXISTS idx_locations_name_trgm ON locations USING gin (name gin_trgm_ops);

-- flights
CREATE TABLE IF NOT EXISTS flights (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  airline varchar(80) NOT NULL,
  flight_number varchar(20) NOT NULL,
  origin_location_id uuid NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  destination_location_id uuid NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  depart_at timestamptz NOT NULL,
  arrive_at timestamptz NOT NULL,
  duration_minutes int NOT NULL,
  stops_count int NOT NULL DEFAULT 0,
  base_price_cents int NOT NULL,
  currency char(3) NOT NULL DEFAULT 'USD',
  CONSTRAINT chk_flights_duration_positive CHECK (duration_minutes > 0),
  CONSTRAINT chk_flights_arrive_after_depart CHECK (arrive_at > depart_at),
  CONSTRAINT chk_flights_stops_nonnegative CHECK (stops_count >= 0),
  CONSTRAINT chk_flights_price_nonnegative CHECK (base_price_cents >= 0)
);

CREATE INDEX IF NOT EXISTS idx_flights_route_depart ON flights(origin_location_id, destination_location_id, depart_at);
CREATE INDEX IF NOT EXISTS idx_flights_airline ON flights(airline);

-- flight_segments
CREATE TABLE IF NOT EXISTS flight_segments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  flight_id uuid NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
  segment_index int NOT NULL,
  origin_location_id uuid NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  destination_location_id uuid NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  depart_at timestamptz NOT NULL,
  arrive_at timestamptz NOT NULL,
  carrier varchar(80) NOT NULL,
  flight_number varchar(20) NOT NULL,
  layover_minutes_after int,
  CONSTRAINT chk_flight_segments_arrive_after_depart CHECK (arrive_at > depart_at),
  CONSTRAINT chk_flight_segments_segment_index_nonnegative CHECK (segment_index >= 0),
  CONSTRAINT chk_flight_segments_layover_nonnegative CHECK (layover_minutes_after IS NULL OR layover_minutes_after >= 0)
);

CREATE INDEX IF NOT EXISTS idx_flight_segments_flight_id ON flight_segments(flight_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_flight_segments_flight_index ON flight_segments(flight_id, segment_index);

-- hotels
CREATE TABLE IF NOT EXISTS hotels (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(160) NOT NULL,
  location_id uuid NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  address varchar(255) NOT NULL,
  lat numeric(9,6) NOT NULL,
  lng numeric(9,6) NOT NULL,
  star_rating numeric(2,1) NOT NULL,
  vip_access boolean NOT NULL DEFAULT false,
  description text NOT NULL,
  amenities jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_hotels_star_rating_range CHECK (star_rating >= 0 AND star_rating <= 5)
);

CREATE INDEX IF NOT EXISTS idx_hotels_location_id ON hotels(location_id);
CREATE INDEX IF NOT EXISTS idx_hotels_star_rating ON hotels(star_rating);
CREATE INDEX IF NOT EXISTS idx_hotels_vip_access ON hotels(vip_access);

-- hotel_photos
CREATE TABLE IF NOT EXISTS hotel_photos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
  url text NOT NULL,
  alt varchar(160),
  sort_order int NOT NULL DEFAULT 0,
  CONSTRAINT chk_hotel_photos_sort_nonnegative CHECK (sort_order >= 0)
);

CREATE INDEX IF NOT EXISTS idx_hotel_photos_hotel_id ON hotel_photos(hotel_id);
CREATE INDEX IF NOT EXISTS idx_hotel_photos_sort ON hotel_photos(hotel_id, sort_order);

-- room_types
CREATE TABLE IF NOT EXISTS room_types (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
  name varchar(160) NOT NULL,
  bed_configuration varchar(160) NOT NULL,
  max_guests int NOT NULL,
  refundable boolean NOT NULL DEFAULT true,
  price_per_night_cents int NOT NULL,
  currency char(3) NOT NULL DEFAULT 'USD',
  inventory int NOT NULL DEFAULT 10,
  CONSTRAINT chk_room_types_max_guests_positive CHECK (max_guests > 0),
  CONSTRAINT chk_room_types_price_nonnegative CHECK (price_per_night_cents >= 0),
  CONSTRAINT chk_room_types_inventory_nonnegative CHECK (inventory >= 0)
);

CREATE INDEX IF NOT EXISTS idx_room_types_hotel_id ON room_types(hotel_id);

-- reviews
CREATE TABLE IF NOT EXISTS reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
  author_name varchar(120) NOT NULL,
  rating int NOT NULL,
  title varchar(160),
  comment text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_reviews_rating_range CHECK (rating BETWEEN 1 AND 10)
);

CREATE INDEX IF NOT EXISTS idx_reviews_hotel_id ON reviews(hotel_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);

-- cars
CREATE TABLE IF NOT EXISTS cars (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company varchar(120) NOT NULL,
  model varchar(120) NOT NULL,
  car_type car_type NOT NULL,
  seats int NOT NULL,
  transmission transmission NOT NULL,
  fuel_type fuel_type NOT NULL,
  price_per_day_cents int NOT NULL,
  currency char(3) NOT NULL DEFAULT 'USD',
  pickup_location_id uuid NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  dropoff_location_id uuid NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  inventory int NOT NULL DEFAULT 10,
  CONSTRAINT chk_cars_seats_positive CHECK (seats > 0),
  CONSTRAINT chk_cars_price_nonnegative CHECK (price_per_day_cents >= 0),
  CONSTRAINT chk_cars_inventory_nonnegative CHECK (inventory >= 0)
);

CREATE INDEX IF NOT EXISTS idx_cars_pickup_location_id ON cars(pickup_location_id);
CREATE INDEX IF NOT EXISTS idx_cars_company ON cars(company);
CREATE INDEX IF NOT EXISTS idx_cars_car_type ON cars(car_type);

-- car_extras
CREATE TABLE IF NOT EXISTS car_extras (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(40) NOT NULL UNIQUE,
  name varchar(120) NOT NULL,
  pricing_model car_extra_pricing_model NOT NULL,
  price_cents int NOT NULL,
  currency char(3) NOT NULL DEFAULT 'USD',
  CONSTRAINT chk_car_extras_price_nonnegative CHECK (price_cents >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_car_extras_code ON car_extras(code);

-- promo_codes
CREATE TABLE IF NOT EXISTS promo_codes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(40) NOT NULL UNIQUE,
  type promo_type NOT NULL,
  value int NOT NULL,
  min_subtotal_cents int NOT NULL DEFAULT 0,
  starts_at timestamptz,
  ends_at timestamptz,
  max_redemptions int,
  redemptions_count int NOT NULL DEFAULT 0,
  active boolean NOT NULL DEFAULT true,
  CONSTRAINT chk_promo_min_subtotal_nonnegative CHECK (min_subtotal_cents >= 0),
  CONSTRAINT chk_promo_redemptions_nonnegative CHECK (redemptions_count >= 0),
  CONSTRAINT chk_promo_max_redemptions_nonnegative CHECK (max_redemptions IS NULL OR max_redemptions >= 0),
  CONSTRAINT chk_promo_time_window CHECK (starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at),
  CONSTRAINT chk_promo_value_valid CHECK (
    (type = 'percent' AND value BETWEEN 1 AND 100) OR
    (type = 'fixed' AND value >= 0)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);
CREATE INDEX IF NOT EXISTS idx_promo_codes_active ON promo_codes(active);

-- carts
CREATE TABLE IF NOT EXISTS carts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  promo_code_id uuid REFERENCES promo_codes(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_carts_user_id ON carts(user_id);
CREATE INDEX IF NOT EXISTS idx_carts_promo_code_id ON carts(promo_code_id);

CREATE TRIGGER trg_carts_set_updated_at
BEFORE UPDATE ON carts
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- cart_items
CREATE TABLE IF NOT EXISTS cart_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cart_id uuid NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  type cart_item_type NOT NULL,
  reference_id uuid NOT NULL,
  quantity int NOT NULL DEFAULT 1,
  start_date date,
  end_date date,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  price_cents int NOT NULL,
  currency char(3) NOT NULL DEFAULT 'USD',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_cart_items_quantity_positive CHECK (quantity > 0),
  CONSTRAINT chk_cart_items_price_nonnegative CHECK (price_cents >= 0),
  CONSTRAINT chk_cart_items_date_range CHECK (start_date IS NULL OR end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_cart_items_cart_id ON cart_items(cart_id);
CREATE INDEX IF NOT EXISTS idx_cart_items_type ON cart_items(type);

-- package_bundles
CREATE TABLE IF NOT EXISTS package_bundles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  flight_id uuid NOT NULL REFERENCES flights(id) ON DELETE RESTRICT,
  hotel_id uuid NOT NULL REFERENCES hotels(id) ON DELETE RESTRICT,
  car_id uuid REFERENCES cars(id) ON DELETE RESTRICT,
  discount_percent int NOT NULL DEFAULT 10,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_package_bundles_discount_range CHECK (discount_percent BETWEEN 0 AND 100)
);

CREATE INDEX IF NOT EXISTS idx_package_bundles_flight_id ON package_bundles(flight_id);
CREATE INDEX IF NOT EXISTS idx_package_bundles_hotel_id ON package_bundles(hotel_id);

-- bookings
CREATE TABLE IF NOT EXISTS bookings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type booking_type NOT NULL,
  status booking_status NOT NULL DEFAULT 'confirmed',
  total_cents int NOT NULL,
  currency char(3) NOT NULL DEFAULT 'USD',
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_bookings_total_nonnegative CHECK (total_cents >= 0)
);

CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_created_at ON bookings(created_at);

CREATE TRIGGER trg_bookings_set_updated_at
BEFORE UPDATE ON bookings
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- booking_items
CREATE TABLE IF NOT EXISTS booking_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
  type booking_item_type NOT NULL,
  reference_id uuid NOT NULL,
  start_date date,
  end_date date,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  line_total_cents int NOT NULL,
  currency char(3) NOT NULL DEFAULT 'USD',
  CONSTRAINT chk_booking_items_line_total_nonnegative CHECK (line_total_cents >= 0),
  CONSTRAINT chk_booking_items_date_range CHECK (start_date IS NULL OR end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_booking_items_booking_id ON booking_items(booking_id);
CREATE INDEX IF NOT EXISTS idx_booking_items_type ON booking_items(type);

-- payment_transactions
CREATE TABLE IF NOT EXISTS payment_transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL UNIQUE REFERENCES bookings(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  amount_cents int NOT NULL,
  currency char(3) NOT NULL DEFAULT 'USD',
  status payment_status NOT NULL,
  payment_method_id uuid REFERENCES payment_methods(id) ON DELETE SET NULL,
  provider varchar(40) NOT NULL DEFAULT 'demo',
  provider_reference varchar(120),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_payment_transactions_amount_nonnegative CHECK (amount_cents >= 0)
);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_id ON payment_transactions(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_transactions_booking_id ON payment_transactions(booking_id);

-- favorites
CREATE TABLE IF NOT EXISTS favorites (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type favorite_type NOT NULL,
  reference_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_favorites_user_type_ref ON favorites(user_id, type, reference_id);
CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id);

-- end schema
