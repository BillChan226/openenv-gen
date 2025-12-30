import express from 'express';

import pool from '../db/pool.js';
import { ApiError } from '../middleware/apiError.js';
import { authRequired } from '../middleware/auth.js';

const router = express.Router();

const SORT_FIELDS = {
  created: 'i.created_at',
  priority: 'i.priority',
  status: 'i.status',
  key: 'i.key',
};

function normalizeIssueRow(row) {
  return {
    id: row.id,
    projectId: row.project_key,
    projectDbId: row.project_id,
    key: row.key,
    seq: row.seq,
    summary: row.title,
    description: row.description,
    type: row.type,
    priority: row.priority,
    status: row.status,
    assigneeId: row.assignee_user_id,
    reporterId: row.reporter_user_id,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    labels: row.labels ?? [],
    activity: row.activity ?? [],
  };
}

async function getIssueActivity(issueId, limit = 50) {
  const { rows } = await pool.query(
    `SELECT id, type, summary, metadata, actor_user_id, created_at
     FROM activity_event
     WHERE issue_id = $1
     ORDER BY created_at DESC
     LIMIT $2`,
    [issueId, limit]
  );

  return rows.map((r) => ({
    id: r.id,
    type: r.type,
    summary: r.summary,
    metadata: r.metadata,
    actorUserId: r.actor_user_id,
    createdAt: r.created_at,
  }));
}

// GET /api/issues
router.get('/', authRequired, async (req, res, next) => {
  try {
    const {
      projectId,
      projectKey,
      status,
      assigneeId,
      assignee,
      q,
      type,
      priority,
      labels,
      sort = 'created',
      order = 'desc',
      page = '1',
      pageSize = '20',
    } = req.query;

    const project = projectId ?? projectKey;
    if (!project) {
      return next(ApiError.badRequest('projectId is required', { fields: ['projectId', 'projectKey'] }));
    }

    const assigneeFilter = assigneeId ?? assignee;

    const sortKey = String(sort || 'created');
    const sortExpr = SORT_FIELDS[sortKey];
    if (!sortExpr) {
      return next(ApiError.badRequest('Invalid sort field', { allowed: Object.keys(SORT_FIELDS) }));
    }

    const orderNorm = String(order || 'desc').toLowerCase() === 'asc' ? 'ASC' : 'DESC';

    const p = Math.max(1, Number(page) || 1);
    const ps = Math.min(100, Math.max(1, Number(pageSize) || 20));
    const offset = (p - 1) * ps;

    const where = ['p.key = $1'];
    const params = [String(project).toUpperCase()];

    if (status) {
      params.push(String(status));
      where.push(`i.status = $${params.length}`);
    }
    if (assigneeFilter) {
      params.push(String(assigneeFilter));
      where.push(`i.assignee_user_id = $${params.length}`);
    }
    if (type) {
      params.push(String(type).toUpperCase());
      where.push(`i.type = $${params.length}`);
    }
    if (priority) {
      params.push(String(priority).toUpperCase());
      where.push(`i.priority = $${params.length}`);
    }

    // labels can be comma-separated or repeated query params
    const labelList = Array.isArray(labels)
      ? labels
      : typeof labels === 'string'
        ? labels
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean)
        : [];

    if (labelList.length > 0) {
      params.push(labelList);
      where.push(
        `EXISTS (
          SELECT 1
          FROM issue_label il
          JOIN label l ON l.id = il.label_id
          WHERE il.issue_id = i.id AND l.name = ANY($${params.length}::text[])
        )`
      );
    }

    if (q) {
      params.push(String(q));
      where.push(`i.search_tsv @@ plainto_tsquery('english', $${params.length})`);
    }

    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

    const countRes = await pool.query(
      `SELECT COUNT(*)::int AS total
       FROM issue i
       JOIN project p ON p.id = i.project_id
       ${whereSql}`,
      params
    );

    params.push(ps);
    params.push(offset);

    const listRes = await pool.query(
      `SELECT
        i.id,
        i.project_id,
        p.key AS project_key,
        i.key,
        i.seq,
        i.title,
        i.description,
        i.type,
        i.priority,
        i.status,
        i.assignee_user_id,
        i.reporter_user_id,
        i.created_at,
        i.updated_at,
        COALESCE(
          (
            SELECT json_agg(l.name ORDER BY l.name)
            FROM issue_label il
            JOIN label l ON l.id = il.label_id
            WHERE il.issue_id = i.id
          ),
          '[]'::json
        ) AS labels
      FROM issue i
      JOIN project p ON p.id = i.project_id
      ${whereSql}
      ORDER BY ${sortExpr} ${orderNorm}, i.id ASC
      LIMIT $${params.length - 1} OFFSET $${params.length}`,
      params
    );

    return res.status(200).json({
      items: listRes.rows.map((r) => normalizeIssueRow(r)),
      page: p,
      pageSize: ps,
      total: countRes.rows[0]?.total ?? 0,
    });
  } catch (err) {
    return next(err);
  }
});

// POST /api/issues
router.post('/', authRequired, async (req, res, next) => {
  try {
    const body = req.body ?? {};

    // Accept both projectId and projectKey for compatibility.
    const projectKeyRaw = body.projectKey ?? body.projectId;
    const summary = body.summary;
    const description = body.description;

    const missing = [];
    if (!projectKeyRaw) missing.push('projectKey');
    if (!summary) missing.push('summary');
    if (missing.length) {
      return next(
        ApiError.badRequest('Missing required fields', {
          missing,
          required: ['projectKey', 'summary'],
        })
      );
    }

    const normalizeEnum = (value) => String(value).trim().toUpperCase().replace(/\s+/g, '_');

    const type = body.type ? normalizeEnum(body.type) : 'TASK';
    const priority = body.priority ? normalizeEnum(body.priority) : 'MEDIUM';
    const status = body.status ? normalizeEnum(body.status) : 'TODO';

    const projectKey = String(projectKeyRaw).trim().toUpperCase();

    const { rows: projRows } = await pool.query('SELECT id, key FROM project WHERE key = $1 LIMIT 1', [projectKey]);
    const project = projRows[0];
    if (!project) return next(ApiError.notFound('Project not found', { projectKey }));

    // Default reporter to authenticated user, but allow explicit reporterId if provided.
    const reporterId = body.reporterId ?? req.user?.id;
    if (!reporterId) return next(ApiError.unauthorized('Invalid session'));

    const assigneeId = body.assigneeId ?? null;

    // labels can be an array of strings or comma-separated string
    const labels = Array.isArray(body.labels)
      ? body.labels
      : typeof body.labels === 'string'
        ? body.labels
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean)
        : [];

    // Validate enums against DB allowed values (derived from seed/schema expectations)
    const allowed = {
      status: ['BACKLOG', 'TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE'],
      priority: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
      type: ['TASK', 'STORY', 'BUG', 'EPIC'],
    };

    const invalid = [];
    if (!allowed.status.includes(status)) invalid.push({ field: 'status', value: status, allowed: allowed.status });
    if (!allowed.priority.includes(priority)) invalid.push({ field: 'priority', value: priority, allowed: allowed.priority });
    if (!allowed.type.includes(type)) invalid.push({ field: 'type', value: type, allowed: allowed.type });
    if (invalid.length) {
      return next(ApiError.badRequest('Invalid enum value(s)', { invalid }));
    }

    const { rows: seqRows } = await pool.query(
      'SELECT COALESCE(MAX(seq), 0)::int + 1 AS next_seq FROM issue WHERE project_id = $1',
      [project.id]
    );
    const nextSeq = seqRows[0].next_seq;
    const issueKey = `${project.key}-${nextSeq}`;

    const { rows } = await pool.query(
      `INSERT INTO issue (project_id, key, seq, title, description, type, priority, status, assignee_user_id, reporter_user_id)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
       RETURNING id, project_id, key, seq, title, description, type, priority, status, assignee_user_id, reporter_user_id, created_at, updated_at`,
      [
        project.id,
        issueKey,
        nextSeq,
        String(summary),
        description ?? null,
        type,
        priority,
        status,
        assigneeId,
        reporterId,
      ]
    );

    const issue = rows[0];

    // Upsert labels and attach to issue
    for (const labelNameRaw of labels) {
      const labelName = String(labelNameRaw).trim();
      if (!labelName) continue;

      const labelRes = await pool.query(
        `INSERT INTO label (project_id, name, color)
         VALUES ($1, $2, '#2684FF')
         ON CONFLICT (project_id, name) DO UPDATE SET name = EXCLUDED.name
         RETURNING id, name`,
        [project.id, labelName]
      );

      const labelId = labelRes.rows[0].id;
      await pool.query(
        `INSERT INTO issue_label (issue_id, label_id)
         VALUES ($1, $2)
         ON CONFLICT DO NOTHING`,
        [issue.id, labelId]
      );
    }

    await pool.query(
      `INSERT INTO activity_event (project_id, issue_id, actor_user_id, type, summary, metadata)
       VALUES ($1, $2, $3, 'ISSUE_CREATED', $4, $5)`,
      [project.id, issue.id, reporterId, `Issue ${issueKey} created`, { issueKey }]
    );

    const activity = await getIssueActivity(issue.id);

    // Fetch labels to return
    const labelsRes = await pool.query(
      `SELECT COALESCE(json_agg(l.name ORDER BY l.name), '[]'::json) AS labels
       FROM issue_label il
       JOIN label l ON l.id = il.label_id
       WHERE il.issue_id = $1`,
      [issue.id]
    );

    return res.status(201).json({
      issue: normalizeIssueRow({
        ...issue,
        project_key: project.key,
        labels: labelsRes.rows[0]?.labels ?? [],
        activity,
      }),
    });
  } catch (err) {
    return next(err);
  }
});

// GET /api/issues/:issueId
router.get('/:issueId', authRequired, async (req, res, next) => {
  try {
    const issueId = req.params.issueId;

    const { rows } = await pool.query(
      `SELECT
        i.id,
        i.project_id,
        p.key AS project_key,
        i.key,
        i.seq,
        i.title,
        i.description,
        i.type,
        i.priority,
        i.status,
        i.assignee_user_id,
        i.reporter_user_id,
        i.created_at,
        i.updated_at,
        COALESCE(
          (
            SELECT json_agg(l.name ORDER BY l.name)
            FROM issue_label il
            JOIN label l ON l.id = il.label_id
            WHERE il.issue_id = i.id
          ),
          '[]'::json
        ) AS labels
      FROM issue i
      JOIN project p ON p.id = i.project_id
      WHERE i.id = $1
      LIMIT 1`,
      [issueId]
    );

    const row = rows[0];
    if (!row) return next(ApiError.notFound('Issue not found', { issueId }));

    const activity = await getIssueActivity(row.id);

    return res.status(200).json({ issue: normalizeIssueRow({ ...row, activity }) });
  } catch (err) {
    return next(err);
  }
});

// PATCH /api/issues/:issueId
router.patch('/:issueId', authRequired, async (req, res, next) => {
  try {
    const issueId = req.params.issueId;
    const { summary, description, priority, type, assigneeId, status } = req.body ?? {};

    const { rows: existingRows } = await pool.query(
      `SELECT i.id, i.project_id, p.key AS project_key, i.key, i.title, i.description, i.priority, i.type, i.status, i.assignee_user_id
       FROM issue i JOIN project p ON p.id = i.project_id
       WHERE i.id = $1 LIMIT 1`,
      [issueId]
    );

    const existing = existingRows[0];
    if (!existing) return next(ApiError.notFound('Issue not found', { issueId }));

    const normalizeEnum = (value) => String(value).trim().toUpperCase().replace(/\s+/g, '_');

    const nextTitle = summary ?? existing.title;
    const nextDesc = description ?? existing.description;
    const nextPriority = priority ? normalizeEnum(priority) : existing.priority;
    const nextType = type ? normalizeEnum(type) : existing.type;
    const nextStatus = status ? normalizeEnum(status) : existing.status;
    const nextAssignee = assigneeId === undefined ? existing.assignee_user_id : assigneeId;

    const allowed = {
      status: ['BACKLOG', 'TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE'],
      priority: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
      type: ['TASK', 'STORY', 'BUG', 'EPIC'],
    };

    const invalid = [];
    if (status && !allowed.status.includes(nextStatus)) {
      invalid.push({ field: 'status', value: nextStatus, allowed: allowed.status });
    }
    if (priority && !allowed.priority.includes(nextPriority)) {
      invalid.push({ field: 'priority', value: nextPriority, allowed: allowed.priority });
    }
    if (type && !allowed.type.includes(nextType)) {
      invalid.push({ field: 'type', value: nextType, allowed: allowed.type });
    }
    if (invalid.length) {
      return next(ApiError.badRequest('Invalid enum value(s)', { invalid }));
    }

    const { rows } = await pool.query(
      `UPDATE issue
       SET title = $2,
           description = $3,
           priority = $4,
           type = $5,
           status = $6,
           assignee_user_id = $7
       WHERE id = $1
       RETURNING id, project_id, key, seq, title, description, type, priority, status, assignee_user_id, reporter_user_id, created_at, updated_at`,
      [issueId, nextTitle, nextDesc, nextPriority, nextType, nextStatus, nextAssignee]
    );

    const updated = rows[0];

    await pool.query(
      `INSERT INTO activity_event (project_id, issue_id, actor_user_id, type, summary, metadata)
       VALUES ($1, $2, $3, 'ISSUE_UPDATED', $4, $5)`,
      [existing.project_id, issueId, req.user.id, `Issue ${existing.key} updated`, { fields: Object.keys(req.body ?? {}) }]
    );

    const activity = await getIssueActivity(issueId);

    return res.status(200).json({ issue: normalizeIssueRow({ ...updated, project_key: existing.project_key, labels: [], activity }) });
  } catch (err) {
    return next(err);
  }
});

// PATCH /api/issues/:issueId/status
router.patch('/:issueId/status', authRequired, async (req, res, next) => {
  try {
    const issueId = req.params.issueId;
    const { status } = req.body ?? {};
    if (!status) return next(ApiError.badRequest('status is required', { fields: ['status'] }));

    const nextStatus = String(status).toUpperCase().replace(/\s+/g, '_');

    const { rows: existingRows } = await pool.query(
      `SELECT i.id, i.project_id, p.key AS project_key, i.key, i.status
       FROM issue i JOIN project p ON p.id = i.project_id
       WHERE i.id = $1 LIMIT 1`,
      [issueId]
    );
    const existing = existingRows[0];
    if (!existing) return next(ApiError.notFound('Issue not found', { issueId }));

    const { rows } = await pool.query(
      `UPDATE issue
       SET status = $2
       WHERE id = $1
       RETURNING id, project_id, key, seq, title, description, type, priority, status, assignee_user_id, reporter_user_id, created_at, updated_at`,
      [issueId, nextStatus]
    );

    const updated = rows[0];

    await pool.query(
      `INSERT INTO activity_event (project_id, issue_id, actor_user_id, type, summary, metadata)
       VALUES ($1, $2, $3, 'ISSUE_STATUS_CHANGED', $4, $5)`,
      [existing.project_id, issueId, req.user.id, `Issue ${existing.key} status changed`, { from: existing.status, to: nextStatus }]
    );

    const activity = await getIssueActivity(issueId);

    return res.status(200).json({ issue: normalizeIssueRow({ ...updated, project_key: existing.project_key, labels: [], activity }) });
  } catch (err) {
    return next(err);
  }
});

export default router;
