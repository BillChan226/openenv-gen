import { Router } from 'express';
import { z } from 'zod';

import { query, pool } from '../db.js';
import { ApiError, listOk, ok } from '../utils/response.js';
import { rowToCamel, rowsToCamel } from '../utils/case.js';
import { requireAuth } from '../middleware/auth.js';
import { computeServiceFeeCents } from '../utils/pricing.js';

const router = Router();

const orderDto = (row) => {
  const o = rowToCamel(row);
  return {
    id: o.id,
    restaurantId: o.restaurantId,
    status: o.status,
    fulfillmentType: o.fulfillmentType,
    placedAt: o.placedAt,
    etaMinutes: o.etaMinutes ?? null,
    driverName: o.driverName ?? null,
    driverPhone: o.driverPhone ?? null,
    subtotalCents: o.subtotalCents,
    deliveryFeeCents: o.deliveryFeeCents,
    serviceFeeCents: o.serviceFeeCents,
    discountCents: o.discountCents,
    totalCents: o.totalCents
  };
};

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const limit = z.coerce.number().int().min(1).max(50).default(20).parse(req.query.limit ?? 20);
    const offset = z.coerce.number().int().min(0).default(0).parse(req.query.offset ?? 0);

    const countRes = await query('SELECT COUNT(*)::int AS count FROM orders WHERE user_id = $1', [req.user.id]);
    const total = countRes.rows[0]?.count ?? 0;

    const { rows } = await query(
      `SELECT id, restaurant_id, status, fulfillment_type, placed_at, eta_minutes, driver_name, driver_phone,
              subtotal_cents, delivery_fee_cents, service_fee_cents, discount_cents, total_cents
       FROM orders
       WHERE user_id = $1
       ORDER BY placed_at DESC
       LIMIT $2 OFFSET $3`,
      [req.user.id, limit, offset]
    );

    const items = rows.map(orderDto);
    return listOk(res, items, { limit, offset, total });
  } catch (err) {
    return next(err);
  }
});

router.post('/', requireAuth, async (req, res, next) => {
  const client = await pool.connect();
  try {
    const body = z
      .object({
        addressId: z.string().uuid(),
        paymentMethodId: z.string().uuid(),
        fulfillmentType: z.enum(['DELIVERY', 'PICKUP']).default('DELIVERY')
      })
      .parse(req.body);

    await client.query('BEGIN');

    const cartRes = await client.query(
      `SELECT c.id, c.restaurant_id, c.promo_code, r.delivery_fee_cents, r.minimum_order_cents
       FROM carts c
       LEFT JOIN restaurants r ON r.id = c.restaurant_id
       WHERE c.user_id = $1 FOR UPDATE`,
      [req.user.id]
    );
    if (!cartRes.rows.length) throw new ApiError('VALIDATION_ERROR', 'Cart is empty', 400);

    const cart = cartRes.rows[0];
    if (!cart.restaurant_id) throw new ApiError('VALIDATION_ERROR', 'Cart is empty', 400);

    const itemsRes = await client.query(
      `SELECT ci.id, ci.menu_item_id, ci.quantity, ci.unit_price_cents, ci.modifier_total_cents
       FROM cart_items ci
       WHERE ci.cart_id = $1`,
      [cart.id]
    );
    if (!itemsRes.rows.length) throw new ApiError('VALIDATION_ERROR', 'Cart is empty', 400);

    const subtotalCents = itemsRes.rows.reduce(
      (sum, r) => sum + r.quantity * (r.unit_price_cents + r.modifier_total_cents),
      0
    );

    if (subtotalCents < cart.minimum_order_cents) {
      throw new ApiError('MINIMUM_ORDER_NOT_MET', 'Minimum order not met', 409, {
        minimumOrderCents: cart.minimum_order_cents,
        subtotalCents
      });
    }

    let discountCents = 0;
    if (cart.promo_code) {
      const promoRes = await client.query(
        `SELECT code, discount_type, discount_value, min_subtotal_cents, max_discount_cents, is_active
         FROM promo_codes WHERE code = $1`,
        [cart.promo_code]
      );
      if (promoRes.rows.length) {
        const p = rowToCamel(promoRes.rows[0]);
        if (p.isActive && subtotalCents >= p.minSubtotalCents) {
          if (p.discountType === 'PERCENT') {
            discountCents = Math.floor((subtotalCents * Number(p.discountValue) + 50) / 100);
          } else {
            discountCents = Number(p.discountValue);
          }
          if (p.maxDiscountCents != null) discountCents = Math.min(discountCents, p.maxDiscountCents);
          discountCents = Math.min(discountCents, subtotalCents);
        }
      }
    }

    const deliveryFeeCents = body.fulfillmentType === 'DELIVERY' ? cart.delivery_fee_cents : 0;
    const serviceFeeCents = computeServiceFeeCents(subtotalCents);
    const totalCents = subtotalCents + deliveryFeeCents + serviceFeeCents - discountCents;

    // validate address + payment belong to user
    const addrRes = await client.query('SELECT id FROM addresses WHERE id = $1 AND user_id = $2', [
      body.addressId,
      req.user.id
    ]);
    if (!addrRes.rows.length) throw new ApiError('NOT_FOUND', 'Address not found', 404);

    const pmRes = await client.query(
      'SELECT id FROM payment_methods WHERE id = $1 AND user_id = $2',
      [body.paymentMethodId, req.user.id]
    );
    if (!pmRes.rows.length) throw new ApiError('NOT_FOUND', 'Payment method not found', 404);

    const orderRes = await client.query(
      `INSERT INTO orders (user_id, restaurant_id, status, fulfillment_type, placed_at, eta_minutes, driver_name, driver_phone,
                          subtotal_cents, delivery_fee_cents, service_fee_cents, discount_cents, total_cents,
                          address_id, payment_method_id)
       VALUES ($1,$2,'CONFIRMED',$3,now(),NULL,NULL,NULL,$4,$5,$6,$7,$8,$9,$10)
       RETURNING id, restaurant_id, status, fulfillment_type, placed_at, eta_minutes, driver_name, driver_phone,
                 subtotal_cents, delivery_fee_cents, service_fee_cents, discount_cents, total_cents`,
      [
        req.user.id,
        cart.restaurant_id,
        body.fulfillmentType,
        subtotalCents,
        deliveryFeeCents,
        serviceFeeCents,
        discountCents,
        totalCents,
        body.addressId,
        body.paymentMethodId
      ]
    );

    const orderId = orderRes.rows[0].id;

    for (const item of itemsRes.rows) {
      await client.query(
        `INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price_cents, modifier_total_cents)
         VALUES ($1,$2,$3,$4,$5)`,
        [orderId, item.menu_item_id, item.quantity, item.unit_price_cents, item.modifier_total_cents]
      );
    }

    // clear cart
    await client.query('DELETE FROM cart_items WHERE cart_id = $1', [cart.id]);
    await client.query('UPDATE carts SET restaurant_id = NULL, promo_code = NULL, special_instructions = NULL WHERE id = $1', [
      cart.id
    ]);

    await client.query('COMMIT');

    return ok(res, { order: orderDto(orderRes.rows[0]) });
  } catch (err) {
    await client.query('ROLLBACK');
    return next(err);
  } finally {
    client.release();
  }
});

router.get('/:orderId', requireAuth, async (req, res, next) => {
  try {
    const orderId = z.string().uuid().parse(req.params.orderId);

    const orderRes = await query(
      `SELECT id, restaurant_id, status, fulfillment_type, placed_at, eta_minutes, driver_name, driver_phone,
              subtotal_cents, delivery_fee_cents, service_fee_cents, discount_cents, total_cents
       FROM orders
       WHERE id = $1 AND user_id = $2`,
      [orderId, req.user.id]
    );

    if (!orderRes.rows.length) throw new ApiError('NOT_FOUND', 'Order not found', 404);

    const itemsRes = await query(
      `SELECT oi.id, oi.order_id, oi.menu_item_id, oi.quantity, oi.unit_price_cents, oi.modifier_total_cents,
              mi.name, mi.description, mi.image_url, mi.unit_info
       FROM order_items oi
       JOIN menu_items mi ON mi.id = oi.menu_item_id
       WHERE oi.order_id = $1`,
      [orderId]
    );

    const items = rowsToCamel(itemsRes.rows).map((r) => ({
      id: r.id,
      orderId: r.orderId,
      menuItemId: r.menuItemId,
      quantity: r.quantity,
      unitPriceCents: r.unitPriceCents,
      modifierTotalCents: r.modifierTotalCents,
      menuItem: {
        id: r.menuItemId,
        name: r.name,
        description: r.description ?? null,
        imageUrl: r.imageUrl ?? null,
        unitInfo: r.unitInfo ?? null
      }
    }));

    return ok(res, { order: orderDto(orderRes.rows[0]), items });
  } catch (err) {
    return next(err);
  }
});

router.post('/:orderId/reorder', requireAuth, async (req, res, next) => {
  try {
    const orderId = z.string().uuid().parse(req.params.orderId);

    const orderRes = await query('SELECT restaurant_id FROM orders WHERE id = $1 AND user_id = $2', [
      orderId,
      req.user.id
    ]);
    if (!orderRes.rows.length) throw new ApiError('NOT_FOUND', 'Order not found', 404);

    const restaurantId = orderRes.rows[0].restaurant_id;

    const cartRes = await query('SELECT id, restaurant_id FROM carts WHERE user_id = $1', [req.user.id]);
    const cartId = cartRes.rows.length
      ? cartRes.rows[0].id
      : (await query(
          'INSERT INTO carts (user_id, restaurant_id, fulfillment_type) VALUES ($1, NULL, $2) RETURNING id',
          [req.user.id, 'DELIVERY']
        )).rows[0].id;

    if (cartRes.rows[0]?.restaurant_id && cartRes.rows[0].restaurant_id !== restaurantId) {
      throw new ApiError('CART_RESTAURANT_MISMATCH', 'Cart contains items from another restaurant', 409);
    }

    await query('UPDATE carts SET restaurant_id = $1 WHERE id = $2', [restaurantId, cartId]);

    const itemsRes = await query(
      `SELECT menu_item_id, quantity, unit_price_cents, modifier_total_cents
       FROM order_items WHERE order_id = $1`,
      [orderId]
    );

    for (const it of itemsRes.rows) {
      await query(
        `INSERT INTO cart_items (cart_id, menu_item_id, quantity, unit_price_cents, modifier_total_cents)
         VALUES ($1,$2,$3,$4,$5)`,
        [cartId, it.menu_item_id, it.quantity, it.unit_price_cents, it.modifier_total_cents]
      );
    }

    return ok(res, { reordered: true });
  } catch (err) {
    return next(err);
  }
});

export default router;
