-- app/database/init/01_schema.sql
-- PostgreSQL schema for ebay-web (mock e-commerce domain)

BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Generic updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================
-- Users & addresses
-- =========================

CREATE TABLE IF NOT EXISTS app_user (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  newsletter_subscribed BOOLEAN NOT NULL DEFAULT FALSE,
  role VARCHAR(50) NOT NULL DEFAULT 'customer',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_user_email ON app_user (email);

CREATE TABLE IF NOT EXISTS address (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  full_name VARCHAR(200) NOT NULL,
  company VARCHAR(200),
  line1 VARCHAR(255) NOT NULL,
  line2 VARCHAR(255),
  city VARCHAR(100) NOT NULL,
  state VARCHAR(100) NOT NULL,
  postal_code VARCHAR(20) NOT NULL,
  country VARCHAR(2) NOT NULL DEFAULT 'US',
  phone VARCHAR(50),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_address_user_id ON address (user_id);

ALTER TABLE app_user
  ADD COLUMN IF NOT EXISTS default_billing_address_id UUID,
  ADD COLUMN IF NOT EXISTS default_shipping_address_id UUID;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_user_default_billing'
  ) THEN
    ALTER TABLE app_user
      ADD CONSTRAINT fk_user_default_billing
        FOREIGN KEY (default_billing_address_id) REFERENCES address(id) ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_user_default_shipping'
  ) THEN
    ALTER TABLE app_user
      ADD CONSTRAINT fk_user_default_shipping
        FOREIGN KEY (default_shipping_address_id) REFERENCES address(id) ON DELETE SET NULL;
  END IF;
END $$;

-- =========================
-- Categories (3-level tree)
-- =========================

CREATE TABLE IF NOT EXISTS category (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug VARCHAR(120) UNIQUE NOT NULL,
  name VARCHAR(200) NOT NULL,
  level SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 3),
  parent_id UUID REFERENCES category(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_category_parent_level
    CHECK (
      (level = 1 AND parent_id IS NULL)
      OR (level IN (2,3) AND parent_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_category_parent_id ON category (parent_id);
CREATE INDEX IF NOT EXISTS idx_category_slug ON category (slug);

-- =========================
-- Products
-- =========================

CREATE TABLE IF NOT EXISTS product (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sku VARCHAR(64) UNIQUE NOT NULL,
  name VARCHAR(400) NOT NULL,
  price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  rating NUMERIC(2,1) NOT NULL DEFAULT 0 CHECK (rating >= 0 AND rating <= 5),
  review_count INTEGER NOT NULL DEFAULT 0 CHECK (review_count >= 0),
  primary_image_url TEXT NOT NULL,
  short_description TEXT NOT NULL,
  description TEXT NOT NULL,
  attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
  inventory_status VARCHAR(20) NOT NULL DEFAULT 'in_stock' CHECK (inventory_status IN ('in_stock','low_stock','out_of_stock')),
  -- Denormalized category path for API consumption (e.g., electronics/audio/soundbars)
  category_path TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Relationship: product belongs to a leaf category (level 3)
CREATE TABLE IF NOT EXISTS product_category (
  product_id UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
  category_id UUID NOT NULL REFERENCES category(id) ON DELETE RESTRICT,
  PRIMARY KEY (product_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_product_category_category_id ON product_category (category_id);

-- Search indexes
CREATE INDEX IF NOT EXISTS idx_product_sku ON product (sku);
CREATE INDEX IF NOT EXISTS idx_product_name ON product (name);
CREATE INDEX IF NOT EXISTS idx_product_rating ON product (rating);

-- Trigram indexes for ILIKE search
CREATE INDEX IF NOT EXISTS idx_product_name_trgm ON product USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_product_sku_trgm ON product USING GIN (sku gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_product_desc_trgm ON product USING GIN (description gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_product_short_desc_trgm ON product USING GIN (short_description gin_trgm_ops);

-- =========================
-- Wishlist
-- =========================

CREATE TABLE IF NOT EXISTS wishlist_item (
  user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_wishlist_item_user_id ON wishlist_item (user_id);

-- =========================
-- Orders
-- =========================

CREATE TABLE IF NOT EXISTS "order" (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  order_number VARCHAR(40) UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ship_to_name VARCHAR(200) NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN ('processing','shipped','delivered','cancelled')),
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_user_id ON "order" (user_id);
CREATE INDEX IF NOT EXISTS idx_order_created_at ON "order" (created_at);

CREATE TABLE IF NOT EXISTS order_item (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id UUID NOT NULL REFERENCES "order"(id) ON DELETE CASCADE,
  product_id UUID REFERENCES product(id) ON DELETE SET NULL,
  sku VARCHAR(64) NOT NULL,
  name VARCHAR(400) NOT NULL,
  unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
  quantity INTEGER NOT NULL CHECK (quantity >= 1),
  line_total_cents INTEGER NOT NULL CHECK (line_total_cents >= 0)
);

CREATE INDEX IF NOT EXISTS idx_order_item_order_id ON order_item (order_id);
CREATE INDEX IF NOT EXISTS idx_order_item_product_id ON order_item (product_id);

-- =========================
-- Cart (optional, supports guest + signed-in)
-- =========================

CREATE TABLE IF NOT EXISTS cart (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES app_user(id) ON DELETE CASCADE,
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_cart_user UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_cart_user_id ON cart (user_id);

CREATE TABLE IF NOT EXISTS cart_item (
  cart_id UUID NOT NULL REFERENCES cart(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
  quantity INTEGER NOT NULL CHECK (quantity >= 1),
  added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (cart_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_cart_item_product_id ON cart_item (product_id);

-- =========================
-- updated_at triggers
-- =========================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'update_app_user_updated_at'
  ) THEN
    CREATE TRIGGER update_app_user_updated_at
    BEFORE UPDATE ON app_user
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'update_address_updated_at'
  ) THEN
    CREATE TRIGGER update_address_updated_at
    BEFORE UPDATE ON address
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'update_category_updated_at'
  ) THEN
    CREATE TRIGGER update_category_updated_at
    BEFORE UPDATE ON category
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'update_product_updated_at'
  ) THEN
    CREATE TRIGGER update_product_updated_at
    BEFORE UPDATE ON product
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'update_order_updated_at'
  ) THEN
    CREATE TRIGGER update_order_updated_at
    BEFORE UPDATE ON "order"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'update_cart_updated_at'
  ) THEN
    CREATE TRIGGER update_cart_updated_at
    BEFORE UPDATE ON cart
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
  END IF;
END $$;

COMMIT;
