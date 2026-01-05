import { Router } from 'express';
import { ok } from '../utils/response.js';

const router = Router();

router.get('/', (_req, res) => ok(res, { status: 'ok' }));

export default router;
