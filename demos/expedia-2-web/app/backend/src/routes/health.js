import { Router } from 'express';
import { dbStatus } from '../db.js';

const router = Router();

router.get('/health', (_req, res) => {
  res.json({ status: 'ok', db: dbStatus() });
});

export default router;
