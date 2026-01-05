import { Router } from 'express';

import { query } from '../db.js';
import { requireAuth } from '../middleware/auth.js';
import { assert } from '../utils/validation.js';
import { okItem, errorResponse } from '../utils/response.js';

const router = Router();

async function getOrCreateCart(userId) {
  const existing = await query('SELECT id, user_id, promo_code_id, created_at, updated_at FROM carts WHERE user_id = $1', [userId]);
  if (existing.rows[0]) return existing.rows[0];

  const created = await query(
    `INSERT INTO carts (user_id)
     VALUES ($1)
     RETURNING id, user_id, promo_code_id, created_at, updated_at`,
    [userId]
  );
  return created.rows[0];
}

async function cartWithItems(cartId) {
  const cartRes = await query(
    `SELECT c.id, c.user_id, c.session_id, c.promo_code_id, c.created_at, c.updated_at,
            pc.code AS promo_code
     FROM carts c
     LEFT JOIN promo_codes pc ON pc.id = c.promo_code_id
     WHERE c.id = $1`,
    [cartId]
  );
  const cart = cartRes.rows[0];

  const itemsRes = await query(
    `SELECT id, cart_id, item_type, flight_id, hotel_id, hotel_room_id, car_id, package_id,
            start_date, end_date, passengers, guests, rooms, extras,
            subtotal_cents, taxes_cents, fees_cents, total_cents, created_at
     FROM cart_items
     WHERE cart_id = $1
     ORDER BY created_at DESC`,
    [cartId]
  );

  const totals = itemsRes.rows.reduce(
    (acc, it) => {
      acc.subtotal_cents += it.subtotal_cents;
      acc.taxes_cents += it.taxes_cents;
      acc.fees_cents += it.fees_cents;
      acc.total_cents += it.total_cents;
      return acc;
    },
    { subtotal_cents: 0, taxes_cents: 0, fees_cents: 0, total_cents: 0 }
  );

  return { cart, items: itemsRes.rows, totals };
}

async function computeItemPricing(body) {
  const item_type = body.item_type;
  const start_date = body.start_date ?? null;
  const end_date = body.end_date ?? null;

  // Simplified pricing rules: taxes=10%, fees=2%.
  const taxRate = 0.1;
  const feeRate = 0.02;

  let subtotal = 0;

  if (item_type === 'flight') {
    assert(typeof body.flight_id === 'string', 'Invalid input', { field: 'flight_id' });
    const passengers = Number(body.passengers || 1);
    assert(Number.isInteger(passengers) && passengers >= 1 && passengers <= 9, 'Invalid input', { field: 'passengers' });

    const fRes = await query('SELECT price_cents FROM flights WHERE id = $1', [body.flight_id]);
    const f = fRes.rows[0];
    assert(!!f, 'Invalid input', { field: 'flight_id' });

    subtotal = f.price_cents * passengers;
    return {
      item_type,
      flight_id: body.flight_id,
      passengers,
      start_date,
      end_date,
      subtotal_cents: subtotal,
      taxes_cents: Math.round(subtotal * taxRate),
      fees_cents: Math.round(subtotal * feeRate)
    };
  }

  if (item_type === 'hotel') {
    assert(typeof body.hotel_id === 'string', 'Invalid input', { field: 'hotel_id' });
    assert(typeof body.hotel_room_id === 'string', 'Invalid input', { field: 'hotel_room_id' });
    assert(typeof start_date === 'string' && typeof end_date === 'string', 'Invalid input', { field: 'start_date/end_date' });

    const rooms = Number(body.rooms || 1);
    const guests = Number(body.guests || 1);
    assert(Number.isInteger(rooms) && rooms >= 1 && rooms <= 9, 'Invalid input', { field: 'rooms' });
    assert(Number.isInteger(guests) && guests >= 1 && guests <= 20, 'Invalid input', { field: 'guests' });

    const rRes = await query('SELECT price_per_night_cents FROM hotel_rooms WHERE id = $1 AND hotel_id = $2', [body.hotel_room_id, body.hotel_id]);
    const room = rRes.rows[0];
    assert(!!room, 'Invalid input', { field: 'hotel_room_id' });

    const nightsRes = await query('SELECT GREATEST(($2::date - $1::date), 1)::int AS nights', [start_date, end_date]);
    const nights = nightsRes.rows[0].nights;

    subtotal = room.price_per_night_cents * nights * rooms;

    return {
      item_type,
      hotel_id: body.hotel_id,
      hotel_room_id: body.hotel_room_id,
      start_date,
      end_date,
      rooms,
      guests,
      subtotal_cents: subtotal,
      taxes_cents: Math.round(subtotal * taxRate),
      fees_cents: Math.round(subtotal * feeRate)
    };
  }

  if (item_type === 'car') {
    assert(typeof body.car_id === 'string', 'Invalid input', { field: 'car_id' });
    assert(typeof start_date === 'string' && typeof end_date === 'string', 'Invalid input', { field: 'start_date/end_date' });

    const cRes = await query('SELECT base_price_per_day_cents FROM cars WHERE id = $1', [body.car_id]);
    const car = cRes.rows[0];
    assert(!!car, 'Invalid input', { field: 'car_id' });

    const daysRes = await query('SELECT GREATEST(($2::date - $1::date), 1)::int AS days', [start_date, end_date]);
    const days = daysRes.rows[0].days;

    subtotal = car.base_price_per_day_cents * days;

    return {
      item_type,
      car_id: body.car_id,
      start_date,
      end_date,
      extras: body.extras ?? null,
      subtotal_cents: subtotal,
      taxes_cents: Math.round(subtotal * taxRate),
      fees_cents: Math.round(subtotal * feeRate)
    };
  }

  if (item_type === 'package') {
    assert(typeof body.package_id === 'string', 'Invalid input', { field: 'package_id' });

    const pRes = await query(
      `SELECT p.discount_cents, f.price_cents AS flight_price_cents, h.nightly_base_price_cents AS hotel_price_cents
       FROM packages p
       JOIN flights f ON f.id = p.flight_id
       JOIN hotels h ON h.id = p.hotel_id
       WHERE p.id = $1`,
      [body.package_id]
    );
    const p = pRes.rows[0];
    assert(!!p, 'Invalid input', { field: 'package_id' });

    subtotal = Math.max(0, p.flight_price_cents + p.hotel_price_cents - p.discount_cents);

    return {
      item_type,
      package_id: body.package_id,
      subtotal_cents: subtotal,
      taxes_cents: Math.round(subtotal * taxRate),
      fees_cents: Math.round(subtotal * feeRate)
    };
  }

  throw Object.assign(new Error('Invalid input'), { status: 400, code: 'VALIDATION_ERROR', details: { field: 'item_type' } });
}

router.get('/cart', requireAuth, async (req, res, next) => {
  try {
    const cart = await getOrCreateCart(req.user.id);
    const payload = await cartWithItems(cart.id);
    return okItem(res, 'cart', payload);
  } catch (err) {
    return next(err);
  }
});

router.post('/cart/items', requireAuth, async (req, res, next) => {
  try {
    const cart = await getOrCreateCart(req.user.id);
    const pricing = await computeItemPricing(req.body || {});

    const total_cents = pricing.subtotal_cents + pricing.taxes_cents + pricing.fees_cents;

    const cols = [
      'cart_id',
      'item_type',
      'flight_id',
      'hotel_id',
      'hotel_room_id',
      'car_id',
      'package_id',
      'start_date',
      'end_date',
      'passengers',
      'guests',
      'rooms',
      'extras',
      'subtotal_cents',
      'taxes_cents',
      'fees_cents',
      'total_cents'
    ];

    const vals = [
      cart.id,
      pricing.item_type,
      pricing.flight_id ?? null,
      pricing.hotel_id ?? null,
      pricing.hotel_room_id ?? null,
      pricing.car_id ?? null,
      pricing.package_id ?? null,
      pricing.start_date ?? null,
      pricing.end_date ?? null,
      pricing.passengers ?? null,
      pricing.guests ?? null,
      pricing.rooms ?? null,
      pricing.extras ?? null,
      pricing.subtotal_cents,
      pricing.taxes_cents,
      pricing.fees_cents,
      total_cents
    ];

    const placeholders = vals.map((_, idx) => `$${idx + 1}`).join(', ');

    await query(
      `INSERT INTO cart_items (${cols.join(', ')})
       VALUES (${placeholders})
       RETURNING id, cart_id, item_type, flight_id, hotel_id, hotel_room_id, car_id, package_id,
                 start_date, end_date, passengers, guests, rooms, extras,
                 subtotal_cents, taxes_cents, fees_cents, total_cents, created_at`,
      vals
    );

    await query('UPDATE carts SET updated_at = now() WHERE id = $1', [cart.id]);

    const payload = await cartWithItems(cart.id);
    return res.status(201).json({ cart: payload });
  } catch (err) {
    return next(err);
  }
});

router.patch('/cart/items/:cart_item_id', requireAuth, async (req, res, next) => {
  try {
    const { cart_item_id } = req.params;

    const cart = await getOrCreateCart(req.user.id);

    const existing = await query('SELECT * FROM cart_items WHERE id = $1 AND cart_id = $2', [cart_item_id, cart.id]);
    const item = existing.rows[0];
    if (!item) return errorResponse(res, 404, 'NOT_FOUND', 'Cart item not found', null);

    const merged = { ...item, ...(req.body || {}) };
    const pricing = await computeItemPricing(merged);
    const total_cents = pricing.subtotal_cents + pricing.taxes_cents + pricing.fees_cents;

    await query(
      `UPDATE cart_items
       SET start_date = $1,
           end_date = $2,
           passengers = $3,
           guests = $4,
           rooms = $5,
           extras = $6,
           subtotal_cents = $7,
           taxes_cents = $8,
           fees_cents = $9,
           total_cents = $10
       WHERE id = $11 AND cart_id = $12
       RETURNING id`,
      [


        pricing.start_date ?? null,
        pricing.end_date ?? null,
        pricing.passengers ?? null,
        pricing.guests ?? null,
        pricing.rooms ?? null,
        pricing.extras ?? null,
        pricing.subtotal_cents,
        pricing.taxes_cents,
        pricing.fees_cents,
        total_cents,
        cart_item_id,
        cart.id
      ]
    );

    await query('UPDATE carts SET updated_at = now() WHERE id = $1', [cart.id]);

    const payload = await cartWithItems(cart.id);
    return res.json({ cart: payload });
  } catch (err) {
    return next(err);
  }
});

router.delete('/cart/items/:cart_item_id', requireAuth, async (req, res, next) => {
  try {
    const { cart_item_id } = req.params;
    const cart = await getOrCreateCart(req.user.id);

    await query('DELETE FROM cart_items WHERE id = $1 AND cart_id = $2', [cart_item_id, cart.id]);
    await query('UPDATE carts SET updated_at = now() WHERE id = $1', [cart.id]);

    return res.status(204).send();
  } catch (err) {
    return next(err);
  }
});

router.post('/cart/apply-promo', requireAuth, async (req, res, next) => {
  try {
    const { code } = req.body || {};
    assert(typeof code === 'string' && code.trim().length > 0, 'Invalid input', { field: 'code' });

    const cart = await getOrCreateCart(req.user.id);

    const promoRes = await query(
      `SELECT id, code, discount_type, discount_value, is_active, expires_at
       FROM promo_codes
       WHERE code = $1`,
      [code.trim().toUpperCase()]
    );

    const promo = promoRes.rows[0];
    if (!promo || !promo.is_active) return errorResponse(res, 400, 'VALIDATION_ERROR', 'Invalid promo code', null);
    if (promo.expires_at && new Date(promo.expires_at).getTime() < Date.now()) {
      return errorResponse(res, 400, 'VALIDATION_ERROR', 'Promo code expired', null);
    }

    await query('UPDATE carts SET promo_code_id = $1, updated_at = now() WHERE id = $2', [promo.id, cart.id]);

    const payload = await cartWithItems(cart.id);
    return res.json({ cart: payload, promo });
  } catch (err) {
    return next(err);
  }
});

export default router;
