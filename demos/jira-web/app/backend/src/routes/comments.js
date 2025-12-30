import express from 'express';

import pool from '../db/pool.js';
import { ApiError } from '../middleware/apiError.js';
import { authRequired } from '../middleware/auth.js';

const router = express.Router();

function mapCommentRow(row) {
  return {
    id: row.id,
    issueId: row.issue_id,
    authorUserId: row.author_user_id,
    bodyMarkdown: row.body_markdown,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

// GET /api/comments?issueId=...
router.get('/', authRequired, async (req, res, next) => {
  try {
    const issueId = String(req.query.issueId ?? '').trim();
    if (!issueId) return next(ApiError.badRequest('issueId is required', { fields: ['issueId'] }));

    const { rows } = await pool.query(
      `SELECT id, issue_id, author_user_id, body_markdown, created_at, updated_at
       FROM comment
       WHERE issue_id = $1
       ORDER BY created_at DESC`,
      [issueId]
    );

    return res.status(200).json({ items: rows.map(mapCommentRow) });
  } catch (err) {
    return next(err);
  }
});

// POST /api/comments
router.post('/', authRequired, async (req, res, next) => {
  try {
    const { issueId, bodyMarkdown } = req.body ?? {};
    if (!issueId || !bodyMarkdown) {
      return next(ApiError.badRequest('issueId and bodyMarkdown are required', { fields: ['issueId', 'bodyMarkdown'] }));
    }

    const { rows: issueRows } = await pool.query(
      `SELECT i.id, i.key, i.project_id
       FROM issue i
       WHERE i.id = $1
       LIMIT 1`,
      [issueId]
    );

    const issue = issueRows[0];
    if (!issue) return next(ApiError.notFound('Issue not found', { issueId }));

    const authorId = req.user?.id;

    const { rows } = await pool.query(
      `INSERT INTO comment (issue_id, author_user_id, body_markdown)
       VALUES ($1, $2, $3)
       RETURNING id, issue_id, author_user_id, body_markdown, created_at, updated_at`,
      [issueId, authorId, String(bodyMarkdown)]
    );

    const comment = rows[0];

    await pool.query(
      `INSERT INTO activity_event (project_id, issue_id, actor_user_id, type, summary, metadata)
       VALUES ($1, $2, $3, 'ISSUE_COMMENT_ADDED', $4, $5)`,
      [issue.project_id, issueId, authorId, `Comment added to ${issue.key}`, { commentId: comment.id }]
    );

    return res.status(201).json({ comment: mapCommentRow(comment) });
  } catch (err) {
    return next(err);
  }
});

// PATCH /api/comments/:commentId
router.patch('/:commentId', authRequired, async (req, res, next) => {
  try {
    const commentId = req.params.commentId;
    const { bodyMarkdown } = req.body ?? {};
    if (!bodyMarkdown) {
      return next(ApiError.badRequest('bodyMarkdown is required', { fields: ['bodyMarkdown'] }));
    }

    const { rows: existingRows } = await pool.query(
      `SELECT c.id, c.issue_id, c.author_user_id, i.key AS issue_key, i.project_id
       FROM comment c
       JOIN issue i ON i.id = c.issue_id
       WHERE c.id = $1
       LIMIT 1`,
      [commentId]
    );

    const existing = existingRows[0];
    if (!existing) return next(ApiError.notFound('Comment not found', { commentId }));

    if (existing.author_user_id !== req.user?.id) {
      return next(ApiError.forbidden('You can only edit your own comments'));
    }

    const { rows } = await pool.query(
      `UPDATE comment
       SET body_markdown = $2
       WHERE id = $1
       RETURNING id, issue_id, author_user_id, body_markdown, created_at, updated_at`,
      [commentId, String(bodyMarkdown)]
    );

    await pool.query(
      `INSERT INTO activity_event (project_id, issue_id, actor_user_id, type, summary, metadata)
       VALUES ($1, $2, $3, 'ISSUE_COMMENT_UPDATED', $4, $5)`,
      [existing.project_id, existing.issue_id, req.user.id, `Comment updated on ${existing.issue_key}`, { commentId }]
    );

    return res.status(200).json({ comment: mapCommentRow(rows[0]) });
  } catch (err) {
    return next(err);
  }
});

// DELETE /api/comments/:commentId
router.delete('/:commentId', authRequired, async (req, res, next) => {
  try {
    const commentId = req.params.commentId;

    const { rows: existingRows } = await pool.query(
      `SELECT c.id, c.issue_id, c.author_user_id, i.key AS issue_key, i.project_id
       FROM comment c
       JOIN issue i ON i.id = c.issue_id
       WHERE c.id = $1
       LIMIT 1`,
      [commentId]
    );

    const existing = existingRows[0];
    if (!existing) return next(ApiError.notFound('Comment not found', { commentId }));

    if (existing.author_user_id !== req.user?.id) {
      return next(ApiError.forbidden('You can only delete your own comments'));
    }

    await pool.query('DELETE FROM comment WHERE id = $1', [commentId]);

    await pool.query(
      `INSERT INTO activity_event (project_id, issue_id, actor_user_id, type, summary, metadata)
       VALUES ($1, $2, $3, 'ISSUE_COMMENT_DELETED', $4, $5)`,
      [existing.project_id, existing.issue_id, req.user.id, `Comment deleted on ${existing.issue_key}`, { commentId }]
    );

    return res.status(204).send();
  } catch (err) {
    return next(err);
  }
});

export default router;
