import { seed } from './data.js';

function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

// Extremely small SQL "adapter" that supports the specific query patterns used
// by our routes. This enables running the backend without Postgres.
export function createMemoryDb() {
  const state = deepClone(seed);

  function selectById(table, id) {
    return state[table].find((r) => String(r.id) === String(id));
  }

  function filterBy(table, predicate) {
    return state[table].filter(predicate);
  }

  function insert(table, row) {
    state[table].push(row);
    return row;
  }

  function update(table, id, patch) {
    const idx = state[table].findIndex((r) => String(r.id) === String(id));
    if (idx === -1) return null;
    state[table][idx] = { ...state[table][idx], ...patch };
    return state[table][idx];
  }

  function remove(table, predicate) {
    const before = state[table].length;
    state[table] = state[table].filter((r) => !predicate(r));
    return before - state[table].length;
  }

  async function query(text, params = []) {
    const sql = String(text).trim().replace(/\s+/g, ' ');

    // USERS
    if (sql.startsWith('SELECT id, email, full_name, password_hash, phone FROM users WHERE email =')) {
      const email = params[0];
      const rows = filterBy('users', (u) => u.email === email).map((u) => ({
        id: u.id,
        email: u.email,
        full_name: u.full_name,
        password_hash: u.password_hash,
        phone: u.phone
      }));
      return { rows };
    }

    if (sql.startsWith('SELECT id, email, full_name, phone FROM users WHERE id =')) {
      const id = params[0];
      const u = selectById('users', id);
      return {
        rows: u
          ? [{ id: u.id, email: u.email, full_name: u.full_name, phone: u.phone }]
          : []
      };
    }

    if (sql.startsWith('INSERT INTO users')) {
      // Two supported shapes:
      // 1) From auth/register route:
      //    INSERT INTO users (email, password_hash, full_name) VALUES ($1,$2,$3)
      //    params = [email, password_hash, full_name]
      // 2) Internal/seed style:
      //    params = [id, email, full_name, password_hash, phone]
      let id;
      let email;
      let full_name;
      let password_hash;
      let phone;

      if (params.length === 3) {
        [email, password_hash, full_name] = params;
        id = String(Date.now()) + Math.random().toString(16).slice(2);
        phone = null;
      } else {
        [id, email, full_name, password_hash, phone] = params;
      }

      const now = new Date().toISOString();
      const row = {
        id,
        email,
        full_name,
        password_hash,
        phone: phone ?? null,
        is_admin: false,
        created_at: now,
        updated_at: now
      };
      insert('users', row);
      return { rows: [{ id: row.id, email: row.email, full_name: row.full_name, phone: row.phone, is_admin: row.is_admin, created_at: row.created_at }] };
    }

    // LOCATIONS
    if (sql.startsWith('SELECT id, type, name, country_code, airport_code FROM locations')) {
      const q = params[0] ? String(params[0]).toLowerCase().replace(/%/g, '') : '';
      const rows = state.locations
        .filter((l) => {
          if (!q) return true;
          return (
            String(l.name).toLowerCase().includes(q) ||
            String(l.airport_code || '').toLowerCase().includes(q) ||
            String(l.id).toLowerCase().includes(q)
          );
        })
        .slice(0, 20);
      return { rows };
    }

    // FLIGHTS
    if (sql.startsWith('SELECT COUNT(*)::int AS count FROM flights')) {
      return { rows: [{ count: state.flights.length }] };
    }

    if (sql.includes('FROM flights f') && sql.includes('LIMIT') && sql.includes('OFFSET')) {
      // naive pagination only
      const limit = params[params.length - 2];
      const offset = params[params.length - 1];
      const rows = state.flights.slice(offset, offset + limit).map((f) => ({ ...f }));
      return { rows };
    }

    if (sql.includes('FROM flights f') && sql.includes('WHERE f.id =')) {
      const id = params[0];
      const f = selectById('flights', id);
      return { rows: f ? [{ ...f }] : [] };
    }

    if (sql.startsWith('SELECT price_cents FROM flights WHERE id =')) {
      const id = params[0];
      const f = selectById('flights', id);
      return { rows: f ? [{ price_cents: f.price_cents }] : [] };
    }

    // HOTELS
    if (sql.startsWith('SELECT COUNT(*)::int AS count FROM hotels')) {
      return { rows: [{ count: state.hotels.length }] };
    }

    if (sql.includes('FROM hotels h') && sql.includes('LIMIT') && sql.includes('OFFSET')) {
      const limit = params[params.length - 2];
      const offset = params[params.length - 1];
      const rows = state.hotels.slice(offset, offset + limit).map((h) => ({ ...h }));
      return { rows };
    }

    if (sql.includes('FROM hotels h') && sql.includes('WHERE h.id =')) {
      const id = params[0];
      const h = selectById('hotels', id);
      return { rows: h ? [{ ...h }] : [] };
    }

    if (sql.startsWith('SELECT id, hotel_id, name, capacity, refundable, price_per_night_cents, currency FROM hotel_rooms WHERE hotel_id =')) {
      const hotel_id = params[0];
      const rows = filterBy('hotel_rooms', (r) => String(r.hotel_id) === String(hotel_id));
      return { rows };
    }

    if (sql.startsWith('SELECT price_per_night_cents FROM hotel_rooms WHERE id =')) {
      const [id, hotel_id] = params;
      const room = state.hotel_rooms.find((r) => String(r.id) === String(id) && String(r.hotel_id) === String(hotel_id));
      return { rows: room ? [{ price_per_night_cents: room.price_per_night_cents }] : [] };
    }

    // hotel details rooms query (routes/hotels.js)
    if (sql.startsWith('SELECT id, hotel_id, name, bed_configuration, max_guests, price_per_night_cents, inventory')) {
      const hotel_id = params[0];
      const rows = filterBy('hotel_rooms', (r) => String(r.hotel_id) === String(hotel_id))
        .slice()
        .sort((a, b) => (a.price_per_night_cents ?? 0) - (b.price_per_night_cents ?? 0))
        .map((r) => ({
          id: r.id,
          hotel_id: r.hotel_id,
          name: r.name,
          bed_configuration: r.bed_configuration ?? null,
          max_guests: r.max_guests ?? r.capacity ?? null,
          price_per_night_cents: r.price_per_night_cents,
          inventory: r.inventory ?? null
        }));
      return { rows };
    }


    // CARS
    if (sql.startsWith('SELECT COUNT(*)::int AS count FROM cars')) {
      return { rows: [{ count: state.cars.length }] };
    }

    if (sql.includes('FROM cars c') && sql.includes('LIMIT') && sql.includes('OFFSET')) {
      const limit = params[params.length - 2];
      const offset = params[params.length - 1];
      const rows = state.cars.slice(offset, offset + limit).map((c) => ({ ...c }));
      return { rows };
    }

    if (sql.includes('FROM cars c') && sql.includes('WHERE c.id =')) {
      const id = params[0];
      const c = selectById('cars', id);
      return { rows: c ? [{ ...c }] : [] };
    }

    if (sql.startsWith('SELECT base_price_per_day_cents FROM cars WHERE id =')) {
      const id = params[0];
      const c = selectById('cars', id);
      return { rows: c ? [{ base_price_per_day_cents: c.base_price_per_day_cents }] : [] };
    }

    // PACKAGES
    if (sql.startsWith('SELECT COUNT(*)::int AS count FROM packages')) {
      return { rows: [{ count: state.packages.length }] };
    }

    if (sql.includes('FROM packages p') && sql.includes('LIMIT') && sql.includes('OFFSET')) {
      const limit = params[params.length - 2];
      const offset = params[params.length - 1];
      const rows = state.packages.slice(offset, offset + limit).map((p) => ({ ...p }));
      return { rows };
    }

    if (sql.includes('FROM packages p') && sql.includes('WHERE p.id =')) {
      const id = params[0];
      const p = selectById('packages', id);
      return { rows: p ? [{ ...p }] : [] };
    }

    // FAVORITES
    if (sql.startsWith('SELECT id, user_id, item_type, item_id, created_at FROM favorites WHERE user_id =')) {
      const user_id = params[0];
      const rows = filterBy('favorites', (f) => String(f.user_id) === String(user_id));
      return { rows };
    }

    if (sql.startsWith('INSERT INTO favorites')) {
      // Route: INSERT INTO favorites (user_id, item_type, item_id) VALUES ($1, $2, $3)
      // Some legacy callers might pass (id, user_id, item_type, item_id).
      // IMPORTANT: Do not try to "guess" param order beyond these two supported shapes;
      // guessing caused malformed favorites in memory mode.
      let id;
      let user_id;
      let item_type;
      let item_id;

      if (params.length === 3) {
        [user_id, item_type, item_id] = params;
        id = `FAV_${state.favorites.length + 1}`;
      } else if (params.length === 4) {
        [id, user_id, item_type, item_id] = params;
      } else {
        throw new Error(`Unsupported favorites insert param length: ${params.length}`);
      }

      const now = new Date().toISOString();

      // Enforce required fields to avoid returning malformed objects.
      if (user_id == null || item_type == null || item_id == null) {
        throw new Error('Invalid favorites insert params');
      }

      // Mimic POSTGRES: ON CONFLICT DO NOTHING (user_id,item_type,item_id)
      const existing = state.favorites.find(
        (f) => String(f.user_id) === String(user_id) && f.item_type === item_type && String(f.item_id) === String(item_id)
      );
      if (existing) return { rows: [] };

      const row = { id, user_id, item_type, item_id, created_at: now };
      insert('favorites', row);
      return { rows: [row] };
    }

    if (sql.startsWith('SELECT id FROM favorites WHERE user_id =')) {
      const [user_id, item_type, item_id] = params;
      const existing = state.favorites.find(
        (f) => String(f.user_id) === String(user_id) && f.item_type === item_type && String(f.item_id) === String(item_id)
      );
      return { rows: existing ? [{ id: existing.id }] : [] };
    }

    if (sql.startsWith('DELETE FROM favorites WHERE id =')) {
      const [id, user_id] = params;
      remove('favorites', (f) => String(f.id) === String(id) && String(f.user_id) === String(user_id));
      return { rows: [] };
    }

    // PAYMENT METHODS
    if (sql.startsWith('SELECT id, brand, last4, exp_month, exp_year, created_at FROM payment_methods WHERE user_id =')) {
      const user_id = params[0];
      const rows = filterBy('payment_methods', (pm) => String(pm.user_id) === String(user_id));
      return { rows };
    }

    if (sql.startsWith('INSERT INTO payment_methods')) {
      const [id, user_id, brand, last4, exp_month, exp_year] = params;
      const now = new Date().toISOString();
      const row = { id, user_id, brand, last4, exp_month, exp_year, created_at: now };
      insert('payment_methods', row);
      return { rows: [row] };
    }

    if (sql.startsWith('DELETE FROM payment_methods WHERE id =')) {
      const [id, user_id] = params;
      remove('payment_methods', (pm) => String(pm.id) === String(id) && String(pm.user_id) === String(user_id));
      return { rows: [] };
    }

    // CART
    if (sql.startsWith('SELECT id, user_id, promo_code_id, created_at, updated_at FROM carts WHERE user_id =')) {
      const user_id = params[0];
      const cart = state.carts.find((c) => String(c.user_id) === String(user_id));
      return { rows: cart ? [cart] : [] };
    }

    if (sql.startsWith('INSERT INTO carts')) {
      // Supports both Postgres-style insert (user_id only) and older memory signature (id, user_id).
      // Postgres query in routes/cart.js: INSERT INTO carts (user_id) VALUES ($1)
      // Some callers may pass (id, user_id).
      let id;
      let user_id;
      if (params.length === 1) {
        user_id = params[0];
        id = `C_${state.carts.length + 1}`;
      } else {
        [id, user_id] = params;
        if (user_id == null) {
          user_id = id;
          id = `C_${state.carts.length + 1}`;
        }
      }
      const now = new Date().toISOString();
      const row = { id, user_id, promo_code_id: null, created_at: now, updated_at: now };
      insert('carts', row);
      return { rows: [row] };
    }

    if (sql.startsWith('UPDATE carts SET updated_at =')) {
      // Postgres query: UPDATE carts SET updated_at = now() WHERE id = $1
      // Params: [cartId]
      const id = params[0];
      update('carts', id, { updated_at: new Date().toISOString() });
      return { rows: [] };
    }

    // Date diff helpers used by computeItemPricing()
    if (sql.startsWith('SELECT GREATEST(($2::date - $1::date), 1)::int AS nights')) {
      const [start, end] = params;
      const startDate = new Date(start);
      const endDate = new Date(end);
      const ms = endDate.getTime() - startDate.getTime();
      const nights = Number.isFinite(ms) ? Math.max(1, Math.round(ms / 86400000)) : 1;
      return { rows: [{ nights }] };
    }

    if (sql.startsWith('SELECT GREATEST(($2::date - $1::date), 1)::int AS days')) {
      const [start, end] = params;
      const startDate = new Date(start);
      const endDate = new Date(end);
      const ms = endDate.getTime() - startDate.getTime();
      const days = Number.isFinite(ms) ? Math.max(1, Math.round(ms / 86400000)) : 1;
      return { rows: [{ days }] };
    }

    // cartWithItems() cart header query (routes/cart.js)
    if (sql.startsWith('SELECT c.id, c.user_id, c.session_id, c.promo_code_id, c.created_at, c.updated_at')) {
      const cart_id = params[0];
      const cart = selectById('carts', cart_id);
      if (!cart) return { rows: [] };

      // promo_codes not modeled in memory seed; return null promo_code.
      return {
        rows: [
          {
            id: cart.id,
            user_id: cart.user_id,
            session_id: cart.session_id ?? null,
            promo_code_id: cart.promo_code_id ?? null,
            created_at: cart.created_at,
            updated_at: cart.updated_at,
            promo_code: null
          }
        ]
      };
    }

    // cartWithItems() items query (routes/cart.js)
    if (sql.startsWith('SELECT id, cart_id, item_type, flight_id, hotel_id, hotel_room_id, car_id, package_id')) {
      const cart_id = params[0];
      const rows = filterBy('cart_items', (ci) => String(ci.cart_id) === String(cart_id))
        .slice()
        .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
      return { rows };
    }

    if (sql.startsWith('SELECT c.id AS cart_id')) {
      // cart details join
      const cart_id = params[0];
      const cart = selectById('carts', cart_id);
      if (!cart) return { rows: [] };
      return {
        rows: [
          {
            cart_id: cart.id,
            user_id: cart.user_id,
            promo_code_id: cart.promo_code_id,
            created_at: cart.created_at,
            updated_at: cart.updated_at
          }
        ]
      };
    }

    if (sql.startsWith('SELECT ci.id')) {
      const cart_id = params[0];
      const rows = filterBy('cart_items', (ci) => String(ci.cart_id) === String(cart_id));
      return { rows };
    }

    if (sql.startsWith('INSERT INTO cart_items')) {
      // Matches routes/cart.js insert order:
      // cart_id, item_type, flight_id, hotel_id, hotel_room_id, car_id, package_id,
      // start_date, end_date, passengers, guests, rooms, extras,
      // subtotal_cents, taxes_cents, fees_cents, total_cents
      const [
        cart_id,
        item_type,
        flight_id,
        hotel_id,
        hotel_room_id,
        car_id,
        package_id,
        start_date,
        end_date,
        passengers,
        guests,
        rooms,
        extras,
        subtotal_cents,
        taxes_cents,
        fees_cents,
        total_cents
      ] = params;

      const id = `CI_${state.cart_items.length + 1}`;
      const row = {
        id,
        cart_id,
        item_type,
        flight_id: flight_id ?? null,
        hotel_id: hotel_id ?? null,
        hotel_room_id: hotel_room_id ?? null,
        car_id: car_id ?? null,
        package_id: package_id ?? null,
        start_date: start_date ?? null,
        end_date: end_date ?? null,
        passengers: passengers ?? null,
        guests: guests ?? null,
        rooms: rooms ?? null,
        extras: extras ?? null,
        subtotal_cents,
        taxes_cents,
        fees_cents,
        total_cents,
        created_at: new Date().toISOString()
      };
      insert('cart_items', row);
      return { rows: [row] };
    }

    if (sql.startsWith('SELECT * FROM cart_items WHERE id =')) {
      const [id, cart_id] = params;
      const row = state.cart_items.find((ci) => String(ci.id) === String(id) && String(ci.cart_id) === String(cart_id));
      return { rows: row ? [row] : [] };
    }

    if (sql.startsWith('UPDATE cart_items SET')) {
      // Matches routes/cart.js update order:
      // start_date, end_date, passengers, guests, rooms, extras,
      // subtotal_cents, taxes_cents, fees_cents, total_cents,
      // id, cart_id
      const [
        start_date,
        end_date,
        passengers,
        guests,
        rooms,
        extras,
        subtotal_cents,
        taxes_cents,
        fees_cents,
        total_cents,
        id,
        cart_id
      ] = params;

      const row = state.cart_items.find((ci) => String(ci.id) === String(id) && String(ci.cart_id) === String(cart_id));
      if (!row) return { rows: [] };

      Object.assign(row, {
        start_date: start_date ?? null,
        end_date: end_date ?? null,
        passengers: passengers ?? null,
        guests: guests ?? null,
        rooms: rooms ?? null,
        extras: extras ?? null,
        subtotal_cents,
        taxes_cents,
        fees_cents,
        total_cents
      });

      return { rows: [row] };
    }

    if (sql.startsWith('DELETE FROM cart_items WHERE id =')) {
      const [id, cart_id] = params;
      remove('cart_items', (ci) => String(ci.id) === String(id) && String(ci.cart_id) === String(cart_id));
      return { rows: [] };
    }

    if (sql.startsWith('SELECT id, code, discount_type')) {
      const id = params[0];
      const promo = selectById('promo_codes', id);
      return { rows: promo ? [promo] : [] };
    }

    if (sql.startsWith('SELECT id, code, discount_type, discount_value, is_active, expires_at FROM promo_codes WHERE code =')) {
      const code = params[0];
      const promo = state.promo_codes.find((p) => p.code === code);
      return { rows: promo ? [promo] : [] };
    }

    if (sql.startsWith('UPDATE carts SET promo_code_id =')) {
      // Supports both:
      // 1) UPDATE carts SET promo_code_id = $1, updated_at = now() WHERE id = $2
      // 2) UPDATE carts SET promo_code_id = NULL, updated_at = now() WHERE id = $1
      let promo_code_id;
      let id;
      if (params.length === 2) {
        [promo_code_id, id] = params;
      } else {
        promo_code_id = null;
        [id] = params;
      }
      update('carts', id, { promo_code_id, updated_at: new Date().toISOString() });
      return { rows: [] };
    }

    // DATE DIFF helpers
    if (sql.startsWith('SELECT GREATEST((') && sql.includes(')::int AS nights')) {
      return { rows: [{ nights: 1 }] };
    }

    if (sql.startsWith('SELECT GREATEST((') && sql.includes(')::int AS days')) {
      return { rows: [{ days: 1 }] };
    }

    // CHECKOUT / ORDERS (minimal)
    if (sql.startsWith('SELECT id FROM payment_methods WHERE id =')) {
      const [id, user_id] = params;
      const pm = state.payment_methods.find((p) => String(p.id) === String(id) && String(p.user_id) === String(user_id));
      return { rows: pm ? [{ id: pm.id }] : [] };
    }

    if (sql.startsWith('SELECT id, promo_code_id FROM carts WHERE user_id =')) {
      const user_id = params[0];
      const cart = state.carts.find((c) => String(c.user_id) === String(user_id));
      return { rows: cart ? [{ id: cart.id, promo_code_id: cart.promo_code_id }] : [] };
    }

    // cart items by cart_id (used by checkout.js and cart.js)
    // Supports both alias and non-alias query variants.
    if (
      sql.startsWith('SELECT') &&
      ((sql.includes('FROM cart_items ci') && sql.includes('WHERE ci.cart_id =')) ||
        (sql.includes('FROM cart_items') && !sql.includes('FROM cart_items ci') && sql.includes('WHERE cart_id =')))
    ) {
      const cart_id = params[0];
      let rows = filterBy('cart_items', (ci) => String(ci.cart_id) === String(cart_id));

      // Respect ORDER BY created_at direction if present.
      if (sql.includes('ORDER BY created_at ASC')) {
        rows = rows.slice().sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)));
      } else if (sql.includes('ORDER BY created_at DESC')) {
        rows = rows.slice().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
      }

      return { rows };
    }


    // ORDERS / CHECKOUT

    // Trips list count
    if (sql.startsWith('SELECT COUNT(*)::int AS count FROM orders WHERE user_id =')) {
      const user_id = params[0];
      const count = state.orders.filter((o) => String(o.user_id) === String(user_id)).length;
      return { rows: [{ count }] };
    }

    // Trips list
    // Be tolerant to minor SQL formatting differences (e.g. whitespace/newlines)
    // as long as the selected columns and filters match.
    if (
      sql.startsWith('SELECT id, user_id, status, subtotal_cents, taxes_cents, fees_cents, discounts_cents, total_cents,') &&
      sql.includes('FROM orders') &&
      sql.includes('WHERE user_id = $1') &&
      sql.includes('ORDER BY created_at DESC') &&
      sql.includes('LIMIT $2 OFFSET $3')
    ) {
      const [user_id, limit, offset] = params;
      const rows = state.orders
        .filter((o) => String(o.user_id) === String(user_id))
        .slice()
        .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
        .slice(offset, offset + limit)
        .map((o) => ({
          id: o.id,
          user_id: o.user_id,
          status: o.status,
          subtotal_cents: o.subtotal_cents,
          taxes_cents: o.taxes_cents,
          fees_cents: o.fees_cents,
          discounts_cents: o.discounts_cents,
          total_cents: o.total_cents,
          payment_status: o.payment_status,
          refund_total_cents: o.refund_total_cents,
          cancelled_at: o.cancelled_at,
          confirmation_code: o.confirmation_code,
          created_at: o.created_at
        }));
      return { rows };
    }

    // Trip details: order by id + user_id
    if (
      sql.startsWith('SELECT id, user_id, status, subtotal_cents, taxes_cents, fees_cents, discounts_cents, total_cents,') &&
      sql.includes('FROM orders') &&
      sql.includes('WHERE id = $1 AND user_id = $2')
    ) {
      const [id, user_id] = params;
      const o = state.orders.find((ord) => String(ord.id) === String(id) && String(ord.user_id) === String(user_id));
      if (!o) return { rows: [] };
      return {
        rows: [
          {
            id: o.id,
            user_id: o.user_id,
            status: o.status,
            subtotal_cents: o.subtotal_cents,
            taxes_cents: o.taxes_cents,
            fees_cents: o.fees_cents,
            discounts_cents: o.discounts_cents,
            total_cents: o.total_cents,
            payment_status: o.payment_status,
            refund_total_cents: o.refund_total_cents,
            cancelled_at: o.cancelled_at,
            confirmation_code: o.confirmation_code,
            created_at: o.created_at
          }
        ]
      };
    }

    // Trip details: items by order_id
    if (
      sql.startsWith('SELECT id, order_id, item_type, flight_id, hotel_id, hotel_room_id, car_id, package_id,') &&
      sql.includes('FROM order_items') &&
      sql.includes('WHERE order_id = $1')
    ) {
      const order_id = params[0];
      let rows = state.order_items.filter((oi) => String(oi.order_id) === String(order_id));
      if (sql.includes('ORDER BY created_at ASC')) {
        rows = rows.slice().sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)));
      } else if (sql.includes('ORDER BY created_at DESC')) {
        rows = rows.slice().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
      }
      return { rows: rows.map((oi) => ({ ...oi })) };
    }

    // Trip patch pre-check
    if (sql.startsWith('SELECT id FROM orders WHERE id = $1 AND user_id = $2')) {
      const [id, user_id] = params;
      const o = state.orders.find((ord) => String(ord.id) === String(id) && String(ord.user_id) === String(user_id));
      return { rows: o ? [{ id: o.id }] : [] };
    }

    // Trip cancel: lock select
    if (sql.startsWith('SELECT id, status, total_cents FROM orders WHERE id = $1 AND user_id = $2')) {
      const [id, user_id] = params;
      const o = state.orders.find((ord) => String(ord.id) === String(id) && String(ord.user_id) === String(user_id));
      return { rows: o ? [{ id: o.id, status: o.status, total_cents: o.total_cents }] : [] };
    }

    // Trip cancel: update order
    if (sql.startsWith("UPDATE orders SET status = 'cancelled'")) {
      const [id] = params;
      const now = new Date().toISOString();
      const o = update('orders', id, {
        status: 'cancelled',
        cancelled_at: now,
        refund_total_cents: selectById('orders', id)?.total_cents ?? 0,
        updated_at: now
      });
      return { rows: o ? [{ ...o }] : [] };
    }

    // Trip cancel: update order items
    if (sql.startsWith("UPDATE order_items SET status = 'cancelled'")) {
      const [order_id] = params;
      const now = new Date().toISOString();
      state.order_items = state.order_items.map((oi) =>
        String(oi.order_id) === String(order_id) ? { ...oi, status: 'cancelled', cancelled_at: now } : oi
      );
      return { rows: [] };
    }

    // Trip cancel: select updated order
    if (
      sql.startsWith('SELECT id, user_id, status, subtotal_cents, taxes_cents, fees_cents, discounts_cents, total_cents,') &&
      sql.includes('FROM orders') &&
      sql.includes('WHERE id = $1') &&
      !sql.includes('AND user_id =')
    ) {
      const [id] = params;
      const o = selectById('orders', id);
      if (!o) return { rows: [] };
      return {
        rows: [
          {
            id: o.id,
            user_id: o.user_id,
            status: o.status,
            subtotal_cents: o.subtotal_cents,
            taxes_cents: o.taxes_cents,
            fees_cents: o.fees_cents,
            discounts_cents: o.discounts_cents,
            total_cents: o.total_cents,
            payment_status: o.payment_status,
            refund_total_cents: o.refund_total_cents,
            cancelled_at: o.cancelled_at,
            confirmation_code: o.confirmation_code,
            created_at: o.created_at
          }
        ]
      };
    }

    // Trip item patch: select existing
    if (sql.startsWith('SELECT * FROM order_items WHERE id = $1 AND order_id = $2')) {
      const [id, order_id] = params;
      const oi = state.order_items.find((r) => String(r.id) === String(id) && String(r.order_id) === String(order_id));
      return { rows: oi ? [{ ...oi }] : [] };
    }

    // Trip item patch: update
    if (sql.startsWith('UPDATE order_items SET start_date = COALESCE(')) {
      const [start_date, end_date, passengers, guests, rooms, extras, id, order_id] = params;
      const oi = state.order_items.find((r) => String(r.id) === String(id) && String(r.order_id) === String(order_id));
      if (!oi) return { rows: [] };
      const patched = {
        ...oi,
        start_date: start_date ?? oi.start_date,
        end_date: end_date ?? oi.end_date,
        passengers: passengers ?? oi.passengers,
        guests: guests ?? oi.guests,
        rooms: rooms ?? oi.rooms,
        extras: extras ?? oi.extras,
        status: 'modified'
      };
      state.order_items = state.order_items.map((r) => (String(r.id) === String(id) ? patched : r));
      return { rows: [{ ...patched }] };
    }

    if (sql.startsWith('INSERT INTO orders (')) {
      // Matches routes/checkout.js insert order:
      // user_id, promo_code_id, subtotal_cents, taxes_cents, fees_cents, discounts_cents, total_cents, confirmation_code
      const [
        user_id,
        promo_code_id,
        subtotal_cents,
        taxes_cents,
        fees_cents,
        discounts_cents,
        total_cents,
        confirmation_code
      ] = params;

      const id = `ORD_${state.orders.length + 1}`;
      const now = new Date().toISOString();
      const row = {
        id,
        user_id,
        status: 'confirmed',
        promo_code_id: promo_code_id ?? null,
        subtotal_cents,
        taxes_cents,
        fees_cents,
        discounts_cents,
        total_cents,
        payment_status: 'paid',
        refund_total_cents: 0,
        cancelled_at: null,
        confirmation_code,
        created_at: now,
        updated_at: now
      };
      insert('orders', row);
      return { rows: [row] };
    }

    if (sql.startsWith('INSERT INTO order_items (')) {
      // Matches routes/checkout.js insert order:
      // order_id, item_type, flight_id, hotel_id, hotel_room_id, car_id, package_id,
      // start_date, end_date, passengers, guests, rooms, extras,
      // subtotal_cents, taxes_cents, fees_cents, total_cents
      const [
        order_id,
        item_type,
        flight_id,
        hotel_id,
        hotel_room_id,
        car_id,
        package_id,
        start_date,
        end_date,
        passengers,
        guests,
        rooms,
        extras,
        subtotal_cents,
        taxes_cents,
        fees_cents,
        total_cents
      ] = params;

      const id = `OI_${state.order_items.length + 1}`;
      const now = new Date().toISOString();
      const row = {
        id,
        order_id,
        item_type,
        flight_id: flight_id ?? null,
        hotel_id: hotel_id ?? null,
        hotel_room_id: hotel_room_id ?? null,
        car_id: car_id ?? null,
        package_id: package_id ?? null,
        start_date: start_date ?? null,
        end_date: end_date ?? null,
        passengers: passengers ?? null,
        guests: guests ?? null,
        rooms: rooms ?? null,
        extras: extras ?? null,
        subtotal_cents,
        taxes_cents,
        fees_cents,
        total_cents,
        status: 'confirmed',
        cancelled_at: null,
        created_at: now
      };
      insert('order_items', row);
      return { rows: [row] };
    }

    if (sql.startsWith('DELETE FROM cart_items WHERE cart_id =')) {
      const cart_id = params[0];
      remove('cart_items', (ci) => String(ci.cart_id) === String(cart_id));
      return { rows: [] };
    }

    // Fallback: return empty
    return { rows: [] };
  }

  async function withTransaction(fn) {
    // no real transactions in memory
    const client = { query };
    return fn(client);
  }

  return { query, withTransaction, state };
}
