import express from 'express';

import { authRequired } from '../middleware/auth.js';
import { ApiError } from '../middleware/errorHandler.js';
import { getDemoUser } from '../services/dataService.js';

const router = express.Router();

router.use(authRequired);

async function handleGetMe(req, res) {
  const demo = await getDemoUser();
  const user = {
    id: req.user.id,
    name: req.user.name,
    email: req.user.email,
    newsletterSubscribed: demo.newsletterSubscribed,
    addresses: demo.addresses
  };
  res.json({ user });
}

// Canonical account endpoint (alias of /me) for API contract compatibility.
router.get('/', handleGetMe);

router.get('/me', handleGetMe);

// QA-friendly: allow verifying account identity without requiring custom headers.
// Disabled in production.
router.post('/me', async (req, res, next) => {
  try {
    if (process.env.NODE_ENV === 'production') {
      return next(ApiError.notFound('Not found'));
    }

    const token = req.body?.token;
    if (!token) {
      return next(ApiError.badRequest('token is required'));
    }

    // Reuse the same auth middleware logic by temporarily setting query param.
    // authRequired already supports access_token query param in non-production.
    req.query = { ...(req.query || {}), access_token: String(token) };

    return authRequired(req, res, async (err) => {
      if (err) return next(err);
      const demo = await getDemoUser();
      const user = {
        id: req.user.id,
        name: req.user.name,
        email: req.user.email,
        newsletterSubscribed: demo.newsletterSubscribed,
        addresses: demo.addresses
      };
      return res.json({ user });
    });
  } catch (e) {
    return next(e);
  }
});


router.get('/orders', async (req, res) => {
  const demo = await getDemoUser();
  res.json({ items: demo.recentOrders || [] });
});

router.get('/addresses', async (req, res) => {
  const demo = await getDemoUser();
  res.json({ item: demo.addresses });
});

export default router;
