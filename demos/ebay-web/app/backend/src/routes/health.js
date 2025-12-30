import express from 'express';
import { dbAvailable } from '../services/dataService.js';

const router = express.Router();

router.get('/health', async (req, res) => {
  const db = await dbAvailable();
  res.status(200).json({
    status: 'ok',
    uptime: Math.floor(process.uptime()),
    version: process.env.npm_package_version || '1.0.0',
    env: process.env.NODE_ENV || 'development',
    db: db ? 'connected' : 'demo'
  });
});

// Convenience endpoints for common reverse-proxy setups.
// Some clients probe /api or /api/health to validate wiring.
router.get('/api', (_req, res) => {
  res.status(200).json({ status: 'ok' });
});

router.get('/api/health', async (_req, res) => {
  const db = await dbAvailable();
  res.status(200).json({
    status: 'ok',
    uptime: Math.floor(process.uptime()),
    version: process.env.npm_package_version || '1.0.0',
    env: process.env.NODE_ENV || 'development',
    db: db ? 'connected' : 'demo'
  });
});

export default router;
