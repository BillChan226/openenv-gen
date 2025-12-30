import express from 'express';
import { body } from 'express-validator';

import { authRequired } from '../middleware/auth.js';
import { validate } from '../middleware/validators.js';
import { getCart, addToCart, updateCartItem, removeCartItem, clearCart } from '../services/cartService.js';

const router = express.Router();

router.use(authRequired);

router.get('/', async (req, res, next) => {
  try {
    const cart = await getCart(req.user.id);
    return res.json(cart);
  } catch (e) {
    return next(e);
  }
});

router.post(
  '/items',
  validate([
    body('productId').trim().notEmpty().withMessage('productId is required'),
    body('quantity').optional().isInt({ min: 1, max: 999 }).toInt()
  ]),
  async (req, res, next) => {
    try {
      const cart = await addToCart(req.user.id, req.body.productId, req.body.quantity ?? 1);
      return res.status(201).json(cart);
    } catch (e) {
      return next(e);
    }
  }
);

router.patch(
  '/items',
  validate([
    body('productId').trim().notEmpty().withMessage('productId is required'),
    body('quantity').isInt({ min: 0, max: 999 }).toInt()
  ]),
  async (req, res, next) => {
    try {
      const cart = await updateCartItem(req.user.id, req.body.productId, req.body.quantity);
      return res.json(cart);
    } catch (e) {
      return next(e);
    }
  }
);

// RESTful variant: PATCH /api/cart/items/:productId
router.patch(
  '/items/:productId',
  validate([body('quantity').isInt({ min: 0, max: 999 }).toInt()]),
  async (req, res, next) => {
    try {
      const cart = await updateCartItem(req.user.id, req.params.productId, req.body.quantity);
      return res.json(cart);
    } catch (e) {
      return next(e);
    }
  }
);

router.delete(
  '/items',
  validate([body('productId').trim().notEmpty().withMessage('productId is required')]),
  async (req, res, next) => {
    try {
      const cart = await removeCartItem(req.user.id, req.body.productId);
      return res.json(cart);
    } catch (e) {
      return next(e);
    }
  }
);

// RESTful variant: DELETE /api/cart/items/:productId
router.delete('/items/:productId', async (req, res, next) => {
  try {
    const cart = await removeCartItem(req.user.id, req.params.productId);
    return res.json(cart);
  } catch (e) {
    return next(e);
  }
});

router.delete('/', async (req, res, next) => {
  try {
    const cart = await clearCart(req.user.id);
    return res.json(cart);
  } catch (e) {
    return next(e);
  }
});

export default router;
