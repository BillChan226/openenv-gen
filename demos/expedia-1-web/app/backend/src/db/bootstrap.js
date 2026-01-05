const db = require('../db');

// Minimal schema/bootstrap for local QA/dev.
// This is intentionally lightweight and idempotent (CREATE TABLE IF NOT EXISTS).
//
// NOTE: This project is not using a full migration framework; instead we provide
// a bootstrap that can be invoked on startup (optional) or via an npm script.

async function ensureExtensions() {
  // gen_random_uuid() lives in pgcrypto.
  await db.query('CREATE EXTENSION IF NOT EXISTS pgcrypto');
}

async function ensureTables() {
  // Users
  await db.query(`
    CREATE TABLE IF NOT EXISTS users (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      name TEXT NOT NULL,
      phone TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);

  // Payment methods
  await db.query(`
    CREATE TABLE IF NOT EXISTS payment_methods (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      brand TEXT NOT NULL,
      last4 TEXT NOT NULL,
      exp_month INT NOT NULL,
      exp_year INT NOT NULL,
      token TEXT NOT NULL,
      billing_name TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);

  // Locations
  await db.query(`
    CREATE TABLE IF NOT EXISTS locations (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name TEXT NOT NULL,
      country TEXT,
      region TEXT,
      lat DOUBLE PRECISION,
      lng DOUBLE PRECISION
    );
  `);

  // Flights
  await db.query(`
    CREATE TABLE IF NOT EXISTS flights (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      from_location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
      to_location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
      airline TEXT NOT NULL,
      flight_number TEXT,
      depart_at TIMESTAMPTZ,
      arrive_at TIMESTAMPTZ,
      duration_minutes INT,
      price NUMERIC(10,2) NOT NULL,
      currency TEXT NOT NULL DEFAULT 'USD',
      stops INT NOT NULL DEFAULT 0
    );
  `);

  // Hotels
  await db.query(`
    CREATE TABLE IF NOT EXISTS hotels (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
      name TEXT NOT NULL,
      description TEXT,
      star_rating INT,
      nightly_price NUMERIC(10,2) NOT NULL,
      amenities JSONB NOT NULL DEFAULT '[]'::jsonb,
      address TEXT,
      lat DOUBLE PRECISION,
      lng DOUBLE PRECISION,
      photos JSONB NOT NULL DEFAULT '[]'::jsonb,
      vip_access BOOLEAN NOT NULL DEFAULT false
    );
  `);

  // Cars
  await db.query(`
    CREATE TABLE IF NOT EXISTS cars (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
      company TEXT NOT NULL,
      model TEXT NOT NULL,
      car_type TEXT,
      seats INT,
      price_per_day NUMERIC(10,2) NOT NULL,
      currency TEXT NOT NULL DEFAULT 'USD',
      image_url TEXT
    );
  `);

  // Cart items
  await db.query(`
    CREATE TABLE IF NOT EXISTS cart_items (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      item_type TEXT NOT NULL,
      ref_id TEXT NOT NULL,
      start_date DATE,
      end_date DATE,
      quantity INT NOT NULL DEFAULT 1,
      meta JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);

  // Bookings
  await db.query(`
    CREATE TABLE IF NOT EXISTS bookings (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      booking_type TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'confirmed',
      total_amount NUMERIC(10,2) NOT NULL,
      currency TEXT NOT NULL DEFAULT 'USD',
      details JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);

  // Favorites (also used by src/models/favorites.js)
  await db.query(`
    CREATE TABLE IF NOT EXISTS favorites (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      type TEXT NOT NULL,
      item_id TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE (user_id, type, item_id)
    );
  `);
}

async function seed() {
  // Seed a few locations if empty.
  const { rows } = await db.query('SELECT COUNT(*)::int AS count FROM locations');
  if (rows[0]?.count > 0) return;

  await db.query(
    `INSERT INTO locations (name, country, region, lat, lng) VALUES
      ('New York', 'US', 'NY', 40.7128, -74.0060),
      ('San Francisco', 'US', 'CA', 37.7749, -122.4194),
      ('London', 'GB', 'England', 51.5072, -0.1276)
    `
  );
}

async function bootstrap({ withSeed = true } = {}) {
  await ensureExtensions();
  await ensureTables();
  if (withSeed) await seed();
}

module.exports = {
  bootstrap,
};
