import express from 'express';

const router = express.Router();

// Minimal demo users list for assignee pickers.
// GET /api/users
router.get('/', async (req, res) => {
  // If the request is unauthenticated, return an empty list instead of 401.
  // This prevents noisy failing requests during app bootstrap.
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return res.status(200).json({ users: [] });
  }

  return res.status(200).json({
    users: [
      {
        id: 'user_1',
        email: 'demo@example.com',
        username: 'demo',
        name: 'Demo User',
      },
    ],
  });
});

// GET /api/users/me
router.get('/me', async (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return res.status(401).json({
      error: 'unauthorized',
      message: 'Missing Authorization header',
      details: null,
    });
  }

  return res.status(200).json({
    user: {
      id: 'user_1',
      email: 'demo@example.com',
      username: 'demo',
      name: 'Demo User',
    },
  });
});

export default router;
