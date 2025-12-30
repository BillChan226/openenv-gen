import express from 'express';

import pool from '../db/pool.js';
import { ApiError } from '../middleware/apiError.js';
import { authRequired } from '../middleware/auth.js';

const router = express.Router();

function mapProjectRow(row) {
  return {
    id: row.id,
    key: row.key,
    name: row.name,
    description: row.description,
    leadUserId: row.lead_user_id,
    isArchived: row.is_archived,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    issueCount: Number(row.issue_count ?? 0),
  };
}

// GET /api/projects
router.get('/', authRequired, async (_req, res, next) => {
  try {
    const { rows } = await pool.query(
      `SELECT
        p.id,
        p.key,
        p.name,
        p.description,
        p.lead_user_id,
        p.is_archived,
        p.created_at,
        p.updated_at,
        COUNT(i.id) AS issue_count
      FROM project p
      LEFT JOIN issue i ON i.project_id = p.id
      WHERE p.is_archived = FALSE
      GROUP BY p.id
      ORDER BY p.created_at DESC`
    );

    return res.status(200).json({ items: rows.map(mapProjectRow) });
  } catch (err) {
    return next(err);
  }
});

// POST /api/projects
router.post('/', authRequired, async (req, res, next) => {
  try {
    const { key, name, description } = req.body ?? {};
    const projectKey = String(key || '').trim().toUpperCase();
    const projectName = String(name || '').trim();

    if (!projectKey || !projectName) {
      return next(ApiError.badRequest('key and name are required', { fields: ['key', 'name'] }));
    }

    if (!/^[A-Z][A-Z0-9]{1,9}$/.test(projectKey)) {
      return next(ApiError.badRequest('key must be 2-10 chars, uppercase letters/numbers, starting with a letter', { key: projectKey }));
    }

    const leadUserId = req.user?.id ?? null;

    const { rows } = await pool.query(
      `INSERT INTO project (key, name, description, lead_user_id)
       VALUES ($1, $2, $3, $4)
       RETURNING id, key, name, description, lead_user_id, is_archived, created_at, updated_at`,
      [projectKey, projectName, description ?? null, leadUserId]
    );

    const projectRow = rows[0];

    // Activity
    await pool.query(
      `INSERT INTO activity_event (project_id, issue_id, actor_user_id, type, summary, metadata)
       VALUES ($1, NULL, $2, 'PROJECT_CREATED', $3, $4)`,
      [projectRow.id, leadUserId, `Project ${projectKey} created`, { projectKey }]
    );

    return res.status(201).json({ project: mapProjectRow({ ...projectRow, issue_count: 0 }) });
  } catch (err) {
    // Unique violation for project key
    if (err?.code === '23505') {
      return next(ApiError.badRequest('Project key already exists', { key: req.body?.key }));
    }
    return next(err);
  }
});

// GET /api/projects/:key (get-by-key)
router.get('/:key', authRequired, async (req, res, next) => {
  try {
    const key = String(req.params.key || '').toUpperCase();
    if (!key) return next(ApiError.badRequest('Project key is required'));

    const { rows } = await pool.query(
      `SELECT
        p.id,
        p.key,
        p.name,
        p.description,
        p.lead_user_id,
        p.is_archived,
        p.created_at,
        p.updated_at,
        COUNT(i.id) AS issue_count
      FROM project p
      LEFT JOIN issue i ON i.project_id = p.id
      WHERE p.key = $1
      GROUP BY p.id
      LIMIT 1`,
      [key]
    );

    const row = rows[0];
    if (!row) return next(ApiError.notFound('Project not found', { key }));

    return res.status(200).json({ project: mapProjectRow(row) });
  } catch (err) {
    return next(err);
  }
});

export default router;
