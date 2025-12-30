import express from 'express';

import pool from '../db/pool.js';
import { ApiError } from '../middleware/apiError.js';
import { authRequired } from '../middleware/auth.js';

const router = express.Router();

const DEFAULT_SETTINGS = {
  theme: 'light',
  notifications: {
    email: true,
    inApp: true,
  },
};

function normalizeSettingsPayload(body) {
  // Accept either {settings:{...}} or direct {theme,...}
  const candidate = body?.settings && typeof body.settings === 'object' ? body.settings : body;
  if (!candidate || typeof candidate !== 'object') return null;

  const out = {};

  if (candidate.theme !== undefined) {
    if (typeof candidate.theme !== 'string' || !candidate.theme.trim()) return { error: 'theme' };
    out.theme = candidate.theme.trim();
  }

  if (candidate.notifications !== undefined) {
    if (typeof candidate.notifications !== 'object' || candidate.notifications === null || Array.isArray(candidate.notifications)) {
      return { error: 'notifications' };
    }
    const n = candidate.notifications;
    if (n.email !== undefined && typeof n.email !== 'boolean') return { error: 'notifications.email' };
    if (n.inApp !== undefined && typeof n.inApp !== 'boolean') return { error: 'notifications.inApp' };

    out.notifications = {
      ...(n.email !== undefined ? { email: n.email } : {}),
      ...(n.inApp !== undefined ? { inApp: n.inApp } : {}),
    };
  }

  if (candidate.name !== undefined) {
    if (typeof candidate.name !== 'string') return { error: 'name' };
    out.name = candidate.name;
  }

  if (candidate.avatarUrl !== undefined) {
    if (candidate.avatarUrl !== null && typeof candidate.avatarUrl !== 'string') return { error: 'avatarUrl' };
    out.avatarUrl = candidate.avatarUrl;
  }

  return out;
}

async function ensureUserSettingsRow(userId) {
  await pool.query(
    `INSERT INTO user_settings (user_id, theme, notifications_email, notifications_in_app)
     VALUES ($1, $2, $3, $4)
     ON CONFLICT (user_id) DO NOTHING`,
    [
      userId,
      DEFAULT_SETTINGS.theme,
      DEFAULT_SETTINGS.notifications.email,
      DEFAULT_SETTINGS.notifications.inApp,
    ]
  );
}

async function getSettingsResponse(userId) {
  await ensureUserSettingsRow(userId);

  const { rows } = await pool.query(
    `SELECT u.id, u.email, u.name, u.role, u.avatar_url,
            s.theme, s.notifications_email, s.notifications_in_app
     FROM app_user u
     JOIN user_settings s ON s.user_id = u.id
     WHERE u.id = $1
     LIMIT 1`,
    [userId]
  );

  const row = rows[0];
  if (!row) throw ApiError.unauthorized('User not found');

  return {
    user: {
      id: row.id,
      email: row.email,
      name: row.name,
      role: row.role,
      avatarUrl: row.avatar_url,
    },
    settings: {
      theme: row.theme,
      notifications: {
        email: row.notifications_email,
        inApp: row.notifications_in_app,
      },
    },
  };
}

// GET /api/settings (auth required)
router.get('/', authRequired, async (req, res, next) => {
  try {
    const userId = req.user?.id;
    if (!userId) return next(ApiError.unauthorized('Invalid token'));

    const payload = await getSettingsResponse(userId);
    return res.status(200).json(payload);
  } catch (err) {
    return next(err);
  }
});

// PATCH /api/settings (partial update)
router.patch('/', authRequired, async (req, res, next) => {
  try {
    const userId = req.user?.id;
    if (!userId) return next(ApiError.unauthorized('Invalid token'));

    const patch = normalizeSettingsPayload(req.body);
    if (!patch) {
      return next(ApiError.badRequest('settings object is required', { fields: ['settings'] }));
    }
    if (patch.error) {
      return next(ApiError.badRequest('Invalid settings payload', { field: patch.error }));
    }

    await ensureUserSettingsRow(userId);

    // Update profile fields if provided
    if (patch.name !== undefined || patch.avatarUrl !== undefined) {
      await pool.query(
        `UPDATE app_user
         SET name = COALESCE($2, name),
             avatar_url = COALESCE($3, avatar_url)
         WHERE id = $1`,
        [userId, patch.name ?? null, patch.avatarUrl ?? null]
      );
    }

    // Update settings fields if provided
    if (patch.theme !== undefined) {
      await pool.query('UPDATE user_settings SET theme = $2 WHERE user_id = $1', [userId, patch.theme]);
    }

    if (patch.notifications !== undefined) {
      if (patch.notifications.email !== undefined) {
        await pool.query('UPDATE user_settings SET notifications_email = $2 WHERE user_id = $1', [
          userId,
          patch.notifications.email,
        ]);
      }
      if (patch.notifications.inApp !== undefined) {
        await pool.query('UPDATE user_settings SET notifications_in_app = $2 WHERE user_id = $1', [
          userId,
          patch.notifications.inApp,
        ]);
      }
    }

    const payload = await getSettingsResponse(userId);
    return res.status(200).json(payload);
  } catch (err) {
    return next(err);
  }
});

// PUT /api/settings (full replace of settings, partial profile allowed)
router.put('/', authRequired, async (req, res, next) => {
  try {
    const userId = req.user?.id;
    if (!userId) return next(ApiError.unauthorized('Invalid token'));

    const nextSettings = normalizeSettingsPayload(req.body);
    if (!nextSettings) {
      return next(ApiError.badRequest('settings object is required', { fields: ['settings'] }));
    }
    if (nextSettings.error) {
      return next(ApiError.badRequest('Invalid settings payload', { field: nextSettings.error }));
    }

    await ensureUserSettingsRow(userId);

    // Profile
    if (nextSettings.name !== undefined || nextSettings.avatarUrl !== undefined) {
      await pool.query(
        `UPDATE app_user
         SET name = COALESCE($2, name),
             avatar_url = COALESCE($3, avatar_url)
         WHERE id = $1`,
        [userId, nextSettings.name ?? null, nextSettings.avatarUrl ?? null]
      );
    }

    // Settings full replace (use defaults for missing)
    const theme = nextSettings.theme ?? DEFAULT_SETTINGS.theme;
    const notifications = nextSettings.notifications ?? DEFAULT_SETTINGS.notifications;

    await pool.query(
      `UPDATE user_settings
       SET theme = $2,
           notifications_email = $3,
           notifications_in_app = $4
       WHERE user_id = $1`,
      [userId, theme, notifications.email, notifications.inApp]
    );

    const payload = await getSettingsResponse(userId);
    return res.status(200).json(payload);
  } catch (err) {
    return next(err);
  }
});

export default router;
