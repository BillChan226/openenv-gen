import express from 'express';
import { body, param } from 'express-validator';

import { authRequired } from '../middleware/auth.js';
import { validate } from '../middleware/validators.js';
import { getWishlist, toggleWishlist, removeFromWishlist } from '../services/wishlistService.js';

async function addToWishlist(userId, productId) {
  const wl = await getWishlist(userId);
  if (wl.productIds.includes(productId)) return wl;
  return toggleWishlist(userId, productId);
}

const router = express.Router();

router.use(authRequired);

router.get('/', async (req, res, next) => {
  try {
    const wl = await getWishlist(req.user.id);
    return res.json(wl);
  } catch (e) {
    return next(e);
  }
});

router.post(
  '/toggle',
  validate([body('productId').trim().notEmpty().withMessage('productId is required')]),
  async (req, res, next) => {
    try {
      const wl = await toggleWishlist(req.user.id, req.body.productId);
      return res.json(wl);
    } catch (e) {
      return next(e);
    }
  }
);

// Contract-compatible: add item (idempotent)
router.post(
  '/items',
  validate([body('productId').trim().notEmpty().withMessage('productId is required')]),
  async (req, res, next) => {
    try {
      const wl = await addToWishlist(req.user.id, req.body.productId);
      return res.status(201).json(wl);
    } catch (e) {
      return next(e);
    }
  }
);

// Contract-compatible: remove item by path param
router.delete(
  '/items/:productId',
  validate([param('productId').trim().notEmpty().withMessage('productId is required')]),
  async (req, res, next) => {
    try {
      const wl = await removeFromWishlist(req.user.id, req.params.productId);
      return res.json(wl);
    } catch (e) {
      return next(e);
    }
  }
);

// Backward-compatible: remove item by body
router.delete(
  '/items',
  validate([body('productId').trim().notEmpty().withMessage('productId is required')]),
  async (req, res, next) => {
    try {
      const wl = await removeFromWishlist(req.user.id, req.body.productId);
      return res.json(wl);
    } catch (e) {
      return next(e);
    }
  }
);

export default router;
