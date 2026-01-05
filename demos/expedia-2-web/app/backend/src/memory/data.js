// In-memory seed data for environments without Postgres/Docker.
// NOTE: This is NOT meant for production use.

export const seed = {
  users: [
    {
      id: '00000000-0000-0000-0000-000000000001',
      email: 'demo@example.com',
      full_name: 'Demo User',
      password_hash: '$2b$10$CwTycUXWue0Thq9StjUM0uJ8h1Hn0pV3q9Zp6mY0pQhKqK9xJ9x7m',
      phone: '+1 555-0100',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  ],
  locations: [
    { id: 'LOC_NYC', type: 'city', name: 'New York', country_code: 'US', airport_code: 'JFK' },
    { id: 'LOC_SFO', type: 'city', name: 'San Francisco', country_code: 'US', airport_code: 'SFO' },
    { id: 'LOC_LON', type: 'city', name: 'London', country_code: 'GB', airport_code: 'LHR' }
  ],
  flights: [
    {
      id: 'FL_001',
      origin_code: 'JFK',
      destination_code: 'SFO',
      depart_at: new Date(Date.now() + 86400000).toISOString(),
      arrive_at: new Date(Date.now() + 86400000 + 6 * 3600000).toISOString(),
      airline: 'Demo Air',
      flight_number: 'DA100',
      cabin_class: 'ECONOMY',
      stops: 0,
      duration_minutes: 360,
      price_cents: 25900,
      currency: 'USD'
    }
  ],
  hotels: [
    {
      id: 'HT_001',
      location_code: 'SFO',
      name: 'Demo Hotel',
      rating: 4.3,
      address: '1 Market St',
      city: 'San Francisco',
      country_code: 'US',
      description: 'A demo hotel for local testing.'
    }
  ],
  hotel_rooms: [
    {
      id: 'HR_001',
      hotel_id: 'HT_001',
      name: 'Standard Room',
      capacity: 2,
      refundable: true,
      price_per_night_cents: 15900,
      currency: 'USD'
    }
  ],
  cars: [
    {
      id: 'CR_001',
      location_code: 'SFO',
      vendor: 'Demo Rentals',
      model: 'Compact',
      seats: 5,
      transmission: 'automatic',
      base_price_per_day_cents: 4900,
      currency: 'USD'
    }
  ],
  packages: [
    {
      id: 'PK_001',
      title: 'Demo Package',
      origin_code: 'JFK',
      destination_code: 'SFO',
      nights: 3,
      price_cents: 69900,
      currency: 'USD'
    }
  ],
  favorites: [],
  payment_methods: [
    {
      id: 'PM_001',
      user_id: '00000000-0000-0000-0000-000000000001',
      brand: 'visa',
      last4: '4242',
      exp_month: 12,
      exp_year: 2030,
      created_at: new Date().toISOString()
    }
  ],
  carts: [
    {
      id: 'CART_001',
      user_id: '00000000-0000-0000-0000-000000000001',
      promo_code_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  ],
  cart_items: [],
  promo_codes: [
    {
      id: 'PR_001',
      code: 'DEMO10',
      discount_type: 'percent',
      discount_value: 10,
      is_active: true,
      expires_at: null
    }
  ],
  orders: [],
  order_items: []
};
