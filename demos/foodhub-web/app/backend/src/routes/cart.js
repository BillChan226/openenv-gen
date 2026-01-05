import { Router } from 'express';
import { z } from 'zod';

import { query } from '../db.js';
import { ApiError, ok } from '../utils/response.js';
import { rowToCamel, rowsToCamel } from '../utils/case.js';
import { requireAuth } from '../middleware/auth.js';
import { computeCartPricing } from '../utils/pricing.js';

const router = Router();

const getOrCreateCartId = async (userId) => {
  const { rows } = await query('SELECT id FROM carts WHERE user_id = $1', [userId]);
  if (rows.length) return rows[0].id;

  const created = await query(
    'INSERT INTO carts (user_id, restaurant_id, fulfillment_type, promo_code_id) VALUES ($1, NULL, $2, NULL) RETURNING id',
    [userId, 'DELIVERY']
  );
  return created.rows[0].id;
};

const computeCart = async (userId) => {
  const cartId = await getOrCreateCartId(userId);

  const cartRes = await query(
    `SELECT c.id, c.user_id, c.restaurant_id, c.fulfillment_type, c.promo_code_id, c.special_instructions,
            r.name AS restaurant_name, r.delivery_fee_cents, r.minimum_order_cents,
            pc.code AS promo_code
     FROM carts c
     LEFT JOIN restaurants r ON r.id = c.restaurant_id
     LEFT JOIN promo_codes pc ON pc.id = c.promo_code_id
     WHERE c.id = $1`,
    [cartId]
  );

  const cartRow = cartRes.rows[0];
  const cart = rowToCamel(cartRow);

  const itemsRes = await query(
    `SELECT ci.id, ci.cart_id, ci.menu_item_id, ci.quantity, ci.unit_price_cents, ci.modifier_total_cents,
            ci.notes,
            mi.restaurant_id, mi.name AS menu_item_name, mi.description AS menu_item_description,
            mi.price_cents AS menu_item_price_cents, mi.image_url AS menu_item_image_url, mi.unit_info AS menu_item_unit_info,
            mi.is_available
     FROM cart_items ci
     JOIN menu_items mi ON mi.id = ci.menu_item_id
     WHERE ci.cart_id = $1
     ORDER BY ci.created_at ASC`,
    [cartId]
  );

  const items = rowsToCamel(itemsRes.rows).map((r) => {
    const lineTotalCents = r.quantity * (r.unitPriceCents + r.modifierTotalCents);
    return {
      id: r.id,
      menuItemId: r.menuItemId,
      menuItem: {
        id: r.menuItemId,
        restaurantId: r.restaurantId,
        menuCategoryId: null,
        name: r.menuItemName,
        description: r.menuItemDescription ?? null,
        priceCents: r.menuItemPriceCents,
        imageUrl: r.menuItemImageUrl ?? null,
        unitInfo: r.menuItemUnitInfo ?? null,
        isAvailable: r.isAvailable,
        modifierGroups: []
      },
      quantity: r.quantity,
      unitPriceCents: r.unitPriceCents,
      modifierTotalCents: r.modifierTotalCents,
      notes: r.notes ?? null,
      // Schema currently doesn't store selected modifier options in cart_items.
      selectedModifierOptionIds: [],
      lineTotalCents
    };
  });

  const subtotalCents = items.reduce((sum, i) => sum + i.lineTotalCents, 0);
  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);

  const deliveryFeeCents = cart.restaurantId ? Number(cart.deliveryFeeCents || 0) : 0;

  let discountCents = 0;
  if (cart.promoCode) {
    const promoRes = await query(
      `SELECT code, discount_type, discount_value, min_subtotal_cents, max_discount_cents, is_active
       FROM promo_codes WHERE code = $1`,
      [cart.promoCode]
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

  const pricing = computeCartPricing({ subtotalCents, deliveryFeeCents, discountCents });

  return {
    id: cart.id,
    restaurantId: cart.restaurantId ?? null,
    restaurant: cart.restaurantId
      ? {
          id: cart.restaurantId,
          name: cart.restaurantName,
          deliveryFeeCents,
          minimumOrderCents: cart.minimumOrderCents
        }
      : null,
    fulfillmentType: cart.fulfillmentType,
    promoCode: cart.promoCode ?? null,
    specialInstructions: cart.specialInstructions ?? null,
    items,
    pricing: { ...pricing, itemCount }
  };
};

router.get('/', requireAuth, async (req, res, next) => {
  try {
    const cart = await computeCart(req.user.id);
    return ok(res, { cart });
  } catch (err) {
    return next(err);
  }
});

router.post('/items', requireAuth, async (req, res, next) => {
  try {
    const body = z
      .object({
        menuItemId: z.string().uuid(),
        quantity: z.number().int().min(1).max(99),
        notes: z.string().max(500).optional(),
        // Not persisted in schema; accepted but ignored for forward compatibility.
        selectedModifierOptionIds: z.array(z.string().uuid()).optional()
      })
      .parse(req.body);

    const cartId = await getOrCreateCartId(req.user.id);

    const miRes = await query('SELECT id, restaurant_id, price_cents FROM menu_items WHERE id = $1', [
      body.menuItemId
    ]);
    if (!miRes.rows.length) throw new ApiError('NOT_FOUND', 'Menu item not found', 404);
    const mi = rowToCamel(miRes.rows[0]);

    const cartRes = await query('SELECT restaurant_id FROM carts WHERE id = $1', [cartId]);
    const cartRestaurantId = cartRes.rows[0]?.restaurant_id;

    if (cartRestaurantId && cartRestaurantId !== mi.restaurantId) {
      const cart = await computeCart(req.user.id);
      throw new ApiError('CART_RESTAURANT_MISMATCH', 'Cart contains items from another restaurant', 409, {
        cart
      });
    }

    if (!cartRestaurantId) {
      await query('UPDATE carts SET restaurant_id = $1 WHERE id = $2', [mi.restaurantId, cartId]);
    }

    // Schema supports modifier_total_cents but no modifier option selections.
    const modifierTotalCents = 0;

    await query(
      `INSERT INTO cart_items (cart_id, menu_item_id, quantity, unit_price_cents, modifier_total_cents, notes)
       VALUES ($1,$2,$3,$4,$5,$6)`,
      [cartId, body.menuItemId, body.quantity, mi.priceCents, modifierTotalCents, body.notes ?? null]
    );

    const cart = await computeCart(req.user.id);
    return ok(res, { cart });
  } catch (err) {
    return next(err);
  }
});

router.patch('/items/:cartItemId', requireAuth, async (req, res, next) => {
  try {
    const cartItemId = z.string().uuid().parse(req.params.cartItemId);
    const body = z.object({ quantity: z.number().int().min(1).max(99) }).parse(req.body);

    const cartId = await getOrCreateCartId(req.user.id);

    const upd = await query('UPDATE cart_items SET quantity = $1 WHERE id = $2 AND cart_id = $3', [
      body.quantity,
      cartItemId,
      cartId
    ]);
    if (!upd.rowCount) throw new ApiError('NOT_FOUND', 'Cart item not found', 404);

    const cart = await computeCart(req.user.id);
    return ok(res, { cart });
  } catch (err) {
    return next(err);
  }
});

router.delete('/items/:cartItemId', requireAuth, async (req, res, next) => {
  try {
    const cartItemId = z.string().uuid().parse(req.params.cartItemId);
    const cartId = await getOrCreateCartId(req.user.id);

    const del = await query('DELETE FROM cart_items WHERE id = $1 AND cart_id = $2', [cartItemId, cartId]);
    if (!del.rowCount) throw new ApiError('NOT_FOUND', 'Cart item not found', 404);

    // if empty, clear restaurant and promo
    const countRes = await query('SELECT COUNT(*)::int AS count FROM cart_items WHERE cart_id = $1', [cartId]);
    if (countRes.rows[0].count === 0) {
      await query('UPDATE carts SET restaurant_id = NULL, promo_code_id = NULL WHERE id = $1', [cartId]);
    }

    const cart = await computeCart(req.user.id);
    return ok(res, { cart });
  } catch (err) {
    return next(err);
  }
});

router.post('/apply-promo', requireAuth, async (req, res, next) => {
  try {
    const body = z.object({ code: z.string().min(1).max(50) }).parse(req.body);

    const promoRes = await query('SELECT id, code, is_active FROM promo_codes WHERE code = $1', [body.code]);
    if (!promoRes.rows.length) throw new ApiError('NOT_FOUND', 'Promo code not found', 404);
    const promo = rowToCamel(promoRes.rows[0]);
    if (!promo.isActive) throw new ApiError('PROMO_INACTIVE', 'Promo code is inactive', 400);

    const cartId = await getOrCreateCartId(req.user.id);
    await query('UPDATE carts SET promo_code_id = $1 WHERE id = $2', [promo.id, cartId]);

    const cart = await computeCart(req.user.id);
    return ok(res, { cart });
  } catch (err) {
    return next(err);
  }
});

router.delete('/promo', requireAuth, async (req, res, next) => {
  try {
    const cartId = await getOrCreateCartId(req.user.id);
    await query('UPDATE carts SET promo_code_id = NULL WHERE id = $1', [cartId]);

    const cart = await computeCart(req.user.id);
    return ok(res, { cart });
  } catch (err) {
    return next(err);
  }
});

router.patch('/', requireAuth, async (req, res, next) => {
  try {
    const body = z
      .object({
        fulfillmentType: z.enum(['DELIVERY', 'PICKUP']).optional(),
        specialInstructions: z.string().max(500).nullable().optional()
      })
      .parse(req.body);

    const cartId = await getOrCreateCartId(req.user.id);

    const updates = [];
    const values = [];
    let idx = 1;

    if (body.fulfillmentType) {
      updates.push(`fulfillment_type = $${idx++}`);
      values.push(body.fulfillmentType);
    }

    if (body.specialInstructions !== undefined) {
      updates.push(`special_instructions = $${idx++}`);
      values.push(body.specialInstructions);
    }

    if (!updates.length) throw new ApiError('VALIDATION_ERROR', 'No updates provided', 400);

    values.push(cartId);
    await query(`UPDATE carts SET ${updates.join(', ')}, updated_at = now() WHERE id = $${idx}`, values);

    const cart = await computeCart(req.user.id);
    return ok(res, { cart });
  } catch (err) {
    return next(err);
  }
});

router.delete('/', requireAuth, async (req, res, next) => {
  try {
    const cartId = await getOrCreateCartId(req.user.id);

    await query('DELETE FROM cart_items WHERE cart_id = $1', [cartId]);
    await query('UPDATE carts SET restaurant_id = NULL, promo_code_id = NULL, special_instructions = NULL WHERE id = $1', [
      cartId
    ]);

    const cart = await computeCart(req.user.id);
    return ok(res, { cart });
  } catch (err) {
    return next(err);
  }
});

export default router;
