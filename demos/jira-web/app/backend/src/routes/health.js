import express from 'express';
import pool from '../db/pool.js';
import { ApiError } from '../middleware/apiError.js';

const router = express.Router();

router.get('/health', async (_req, res, next) => {
  try {
    await pool.query('SELECT 1');
    return res.status(200).json({ status: 'ok', db: 'connected' });
  } catch (err) {
    // Allow explicitly opting out of DB requirement (e.g. unit tests).
    if (process.env.ALLOW_NO_DB === '1') {
      return res.status(200).json({ status: 'ok', db: 'disconnected' });
    }

    return next(
      ApiError.serviceUnavailable('Database unavailable', {
        db: 'disconnected',
        message: err?.message,
      })
    );
  }
});

export default router;
