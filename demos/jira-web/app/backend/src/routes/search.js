import express from 'express';

import pool from '../db/pool.js';
import { authRequired } from '../middleware/auth.js';
import { ApiError } from '../middleware/apiError.js';

const router = express.Router();

function normalizeEnum(value) {
  return String(value).trim().toUpperCase().replace(/\s+/g, '_');
}

async function handleSearch({ q, projectId, projectKey, status, assigneeId, limit, offset }) {
  const query = String(q ?? '').trim();
  if (!query) {
    throw ApiError.badRequest('q is required', { field: 'q' });
  }

  const projectIdNorm = projectId ? String(projectId).trim() : null;
  const projectKeyNorm = projectKey ? String(projectKey).trim().toUpperCase() : null;
  const statusNorm = status ? normalizeEnum(status) : null;
  const assigneeIdNorm = assigneeId != null && String(assigneeId).trim() !== '' ? String(assigneeId).trim() : null;

  const limitNorm = Math.min(50, Math.max(1, Number(limit ?? 20) || 20));
  const offsetNorm = Math.max(0, Number(offset ?? 0) || 0);

  // Build dynamic WHERE clauses safely
  const where = [];
  const params = [];

  // Search by full text (tsv) OR key/title/description substring
  params.push(query);
  params.push(`%${query}%`);
  where.push(
    `(i.search_tsv @@ plainto_tsquery('english', $1)
      OR i.key ILIKE $2
      OR i.title ILIKE $2
      OR i.description ILIKE $2)`
  );

  if (projectIdNorm) {
    params.push(projectIdNorm);
    where.push(`i.project_id = $${params.length}`);
  } else if (projectKeyNorm) {
    params.push(projectKeyNorm);
    where.push(`p.key = $${params.length}`);
  }

  if (statusNorm) {
    params.push(statusNorm);
    where.push(`i.status = $${params.length}`);
  }

  if (assigneeIdNorm) {
    params.push(assigneeIdNorm);
    where.push(`i.assignee_user_id = $${params.length}`);
  }

  params.push(limitNorm);
  const limitParam = `$${params.length}`;
  params.push(offsetNorm);
  const offsetParam = `$${params.length}`;

  const sql = `
      SELECT
        i.id,
        i.key,
        i.title,
        i.description,
        i.status,
        i.priority,
        i.assignee_user_id,
        i.reporter_user_id,
        i.project_id,
        i.created_at,
        i.updated_at,
        p.id AS project_id,
        p.key AS project_key,
        p.name AS project_name
      FROM issue i
      JOIN project p ON p.id = i.project_id
      WHERE ${where.join(' AND ')}
      ORDER BY i.updated_at DESC
      LIMIT ${limitParam}
      OFFSET ${offsetParam}
    `;

  const issuesRes = await pool.query(sql, params);

  const issues = issuesRes.rows.map((row) => ({
    id: row.id,
    key: row.key,
    title: row.title,
    description: row.description,
    status: row.status,
    priority: row.priority,
    assigneeId: row.assignee_user_id,
    reporterId: row.reporter_user_id,
    project: {
      id: row.project_id,
      key: row.project_key,
      name: row.project_name,
    },
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }));

  return {
    query,
    filters: {
      projectId: projectIdNorm,
      projectKey: projectKeyNorm,
      status: statusNorm,
      assigneeId: assigneeIdNorm,
    },
    limit: limitNorm,
    offset: offsetNorm,
    issues,
  };
}

// GET /api/search?q=...&projectId=...&projectKey=...&status=...&assigneeId=...&limit=...&offset=...
// Global issue search (key/title/description) with optional filters.
router.get('/', authRequired, async (req, res, next) => {
  try {
    // Support both assigneeId and assignee for compatibility
    const assigneeId = req.query.assigneeId ?? req.query.assignee;

    const payload = await handleSearch({
      q: req.query.q,
      projectId: req.query.projectId,
      projectKey: req.query.projectKey,
      status: req.query.status,
      assigneeId,
      limit: req.query.limit,
      offset: req.query.offset,
    });

    return res.status(200).json(payload);
  } catch (err) {
    return next(err);
  }
});

// POST /api/search
// Accepts JSON body for complex filters.
router.post('/', authRequired, async (req, res, next) => {
  try {
    const body = req.body ?? {};

    const payload = await handleSearch({
      q: body.q,
      projectId: body.projectId,
      projectKey: body.projectKey,
      status: body.status,
      assigneeId: body.assigneeId ?? body.assignee,
      limit: body.limit,
      offset: body.offset,
    });

    return res.status(200).json(payload);
  } catch (err) {
    return next(err);
  }
});

export default router;
