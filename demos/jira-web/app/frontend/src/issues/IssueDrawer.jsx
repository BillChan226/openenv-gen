import { useEffect, useMemo, useState } from 'react';
import { X, MessageSquare, Paperclip } from 'lucide-react';

import {
  getIssueById,
  updateIssue,
  getIssueComments,
  addIssueComment,
  updateComment,
  deleteComment,
  getUsers,
} from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { Spinner } from '../shared/ui/Spinner.jsx';
import { Avatar } from '../shared/ui/Avatar.jsx';
import { STATUSES, PRIORITIES, TYPES } from '../projects/constants.js';
import { useToast } from '../state/ToastContext.jsx';
import { useAuth } from '../state/AuthContext.jsx';

function Drawer({ open, onClose, children, testid }) {
  useEffect(() => {
    if (!open) return;
    function onKey(e) {
      if (e.key === 'Escape') onClose?.();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[95]">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-label="Close"
        data-testid={testid ? `${testid}-backdrop` : 'drawer-backdrop'}
      />
      <div className="absolute right-0 top-0 h-full w-full max-w-2xl bg-bg border-l border-border shadow-card overflow-auto">
        {children}
      </div>
    </div>
  );
}

function FieldRow({ label, children }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-start">
      <div className="text-xs text-fg-muted mt-2">{label}</div>
      <div className="sm:col-span-2">{children}</div>
    </div>
  );
}

export function IssueDrawer({ issueId, open, onClose, onUpdated }) {
  const toast = useToast();
  const { user } = useAuth();

  const {
    data: issueData,
    loading: issueLoading,
    error: issueError,
    refetch: refetchIssue,
  } = useResource(() => (issueId ? getIssueById(issueId) : Promise.resolve(null)), [issueId]);

  const issue = useMemo(() => issueData?.issue || issueData || null, [issueData]);

  const { data: usersData } = useResource(() => getUsers(), []);
  const users = useMemo(() => usersData?.users || usersData || [], [usersData]);

  const {
    data: commentsData,
    loading: commentsLoading,
    error: commentsError,
    refetch: refetchComments,
    setData: setCommentsData,
  } = useResource(() => (issueId ? getIssueComments(issueId) : Promise.resolve({ comments: [] })), [issueId]);

  const comments = useMemo(() => commentsData?.items || commentsData?.comments || (Array.isArray(commentsData) ? commentsData : []), [commentsData]);

  const [edit, setEdit] = useState(null);
  const [saving, setSaving] = useState(false);

  const [newComment, setNewComment] = useState('');
  const [commentBusy, setCommentBusy] = useState(false);

  useEffect(() => {
    if (!issue) return;
    setEdit({
      summary: issue.summary || issue.title || '',
      description: issue.description || '',
      status: issue.status,
      priority: issue.priority,
      type: issue.type,
      assigneeId: issue.assigneeId || issue.assignee_id || '',
      labels: (issue.labels || []).join(', '),
    });
  }, [issue]);

  async function savePatch(patch) {
    if (!issueId) return;
    setSaving(true);
    try {
      await updateIssue(issueId, patch);
      toast.push({ title: 'Issue updated', variant: 'success' });
      await refetchIssue();
      onUpdated?.();
    } catch (e) {
      toast.push({ title: 'Failed to update issue', message: e?.message, variant: 'error' });
    } finally {
      setSaving(false);
    }
  }

  async function addNewComment() {
    if (!newComment.trim()) return;
    setCommentBusy(true);
    try {
      const created = await addIssueComment(issueId, newComment.trim());
      setNewComment('');
      // optimistic insert
      const c = created?.comment || created;
      setCommentsData({ ...(commentsData || {}), items: [c, ...comments] });
      toast.push({ title: 'Comment added', variant: 'success' });
      await refetchComments();
    } catch (e) {
      toast.push({ title: 'Failed to add comment', message: e?.message, variant: 'error' });
    } finally {
      setCommentBusy(false);
    }
  }

  async function onEditComment(id, body) {
    try {
      await updateComment(id, { body });
      toast.push({ title: 'Comment updated', variant: 'success' });
      await refetchComments();
    } catch (e) {
      toast.push({ title: 'Failed to update comment', message: e?.message, variant: 'error' });
    }
  }

  async function onDeleteComment(id) {
    try {
      await deleteComment(id);
      toast.push({ title: 'Comment deleted', variant: 'success' });
      await refetchComments();
    } catch (e) {
      toast.push({ title: 'Failed to delete comment', message: e?.message, variant: 'error' });
    }
  }

  const assignee = useMemo(() => {
    if (!issue) return null;
    if (issue.assignee) return issue.assignee;
    const id = issue.assigneeId || issue.assignee_id;
    return users.find((u) => String(u.id) === String(id)) || null;
  }, [issue, users]);

  return (
    <Drawer open={open} onClose={onClose} testid="issue-drawer">
      <div className="p-5 border-b border-border flex items-start justify-between gap-3">
        <div>
          <div className="text-xs text-fg-muted font-mono">{issue?.key || ''}</div>
          <div className="text-lg font-semibold mt-1">{issue?.summary || issue?.title || 'Issue'}</div>
        </div>
        <button
          type="button"
          className="btn btn-ghost h-9 w-9 p-0"
          onClick={onClose}
          aria-label="Close"
          data-testid="close-issue"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <div className="p-5 space-y-6">
        {(issueLoading || !edit) && (
          <div className="flex items-center gap-2 text-fg-muted">
            <Spinner size="sm" /> Loading issue…
          </div>
        )}

        {issueError && <div className="text-sm text-danger">{issueError}</div>}

        {issue && edit && (
          <div className="space-y-4">
            <FieldRow label="Title">
              <input
                className="input"
                value={edit.summary}
                onChange={(e) => setEdit((s) => ({ ...s, summary: e.target.value }))}
                onBlur={() => savePatch({ summary: edit.summary.trim() })}
                data-testid="issue-edit-title"
              />
            </FieldRow>

            <FieldRow label="Description">
              <textarea
                className="input min-h-28"
                value={edit.description}
                onChange={(e) => setEdit((s) => ({ ...s, description: e.target.value }))}
                onBlur={() => savePatch({ description: edit.description.trim() || null })}
                data-testid="issue-edit-description"
              />
            </FieldRow>

            <FieldRow label="Status">
              <div className="flex flex-wrap gap-2">
                {STATUSES.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className={'btn ' + (edit.status === s.id ? 'btn-primary' : '')}
                    onClick={() => {
                      setEdit((st) => ({ ...st, status: s.id }));
                      savePatch({ status: s.id });
                    }}
                    disabled={saving}
                    data-testid={`issue-transition-${s.id}`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </FieldRow>

            <FieldRow label="Type">
              <select
                className="input h-10"
                value={edit.type}
                onChange={(e) => {
                  const v = e.target.value;
                  setEdit((s) => ({ ...s, type: v }));
                  savePatch({ type: v });
                }}
                data-testid="issue-edit-type"
              >
                {TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </FieldRow>

            <FieldRow label="Priority">
              <select
                className="input h-10"
                value={edit.priority}
                onChange={(e) => {
                  const v = e.target.value;
                  setEdit((s) => ({ ...s, priority: v }));
                  savePatch({ priority: v });
                }}
                data-testid="issue-edit-priority"
              >
                {PRIORITIES.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </FieldRow>

            <FieldRow label="Assignee">
              <div className="flex items-center gap-2">
                <Avatar src={assignee?.avatarUrl || assignee?.avatar_url} name={assignee?.name} size={26} />
                <select
                  className="input h-10"
                  value={edit.assigneeId || ''}
                  onChange={(e) => {
                    const v = e.target.value;
                    setEdit((s) => ({ ...s, assigneeId: v }));
                    savePatch({ assigneeId: v ? Number(v) : null });
                  }}
                  data-testid="issue-edit-assignee"
                >
                  <option value="">Unassigned</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name || u.email}
                    </option>
                  ))}
                </select>
              </div>
            </FieldRow>

            <FieldRow label="Labels">
              <input
                className="input"
                value={edit.labels}
                onChange={(e) => setEdit((s) => ({ ...s, labels: e.target.value }))}
                onBlur={() =>
                  savePatch({
                    labels: edit.labels
                      .split(',')
                      .map((x) => x.trim())
                      .filter(Boolean),
                  })
                }
                data-testid="issue-edit-labels"
              />
            </FieldRow>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-4">
              <div className="surface p-4">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <MessageSquare className="h-4 w-4" aria-hidden="true" /> Comments
                </div>

                <div className="mt-3">
                  <textarea
                    className="input min-h-20"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Add a comment (markdown supported)"
                    data-testid="new-comment"
                  />
                  <button
                    type="button"
                    className="btn btn-primary mt-2"
                    onClick={addNewComment}
                    disabled={commentBusy}
                    data-testid="add-comment"
                  >
                    {commentBusy ? 'Adding…' : 'Add comment'}
                  </button>
                </div>

                {commentsLoading && (
                  <div className="mt-3 text-sm text-fg-muted flex items-center gap-2">
                    <Spinner size="sm" /> Loading comments…
                  </div>
                )}
                {commentsError && <div className="mt-3 text-sm text-danger">{commentsError}</div>}

                <div className="mt-3 space-y-3">
                  {comments.map((c) => {
                    const canEdit = user?.id && (c.authorId || c.author_id) && String(user.id) === String(c.authorId || c.author_id);
                    return (
                      <CommentItem
                        key={c.id}
                        comment={c}
                        canEdit={canEdit}
                        onEdit={onEditComment}
                        onDelete={onDeleteComment}
                      />
                    );
                  })}
                </div>
              </div>

              <div className="surface p-4">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <Paperclip className="h-4 w-4" aria-hidden="true" /> Attachments
                </div>
                <div className="mt-3 text-sm text-fg-muted">
                  Attachments are not implemented in this demo.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
}

function CommentItem({ comment, canEdit, onEdit, onDelete }) {
  const author = comment.author || { name: comment.authorName || 'User', avatarUrl: comment.authorAvatarUrl };
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(comment.body || comment.content || '');

  useEffect(() => {
    setValue(comment.body || comment.content || '');
  }, [comment.body, comment.content]);

  return (
    <div className="border border-border rounded-md p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Avatar src={author.avatarUrl || author.avatar_url} name={author.name} size={22} />
          <div className="min-w-0">
            <div className="text-sm font-medium truncate">{author.name}</div>
            <div className="text-xs text-fg-muted">
              {comment.createdAt || comment.created_at ? new Date(comment.createdAt || comment.created_at).toLocaleString() : ''}
            </div>
          </div>
        </div>
        {canEdit && (
          <div className="flex gap-2">
            {!editing ? (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setEditing(true)}
                data-testid={`edit-comment-${comment.id}`}
              >
                Edit
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setEditing(false);
                  onEdit(comment.id, value);
                }}
                data-testid={`save-comment-${comment.id}`}
              >
                Save
              </button>
            )}
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => onDelete(comment.id)}
              data-testid={`delete-comment-${comment.id}`}
            >
              Delete
            </button>
          </div>
        )}
      </div>

      {!editing ? (
        <div className="mt-2 text-sm whitespace-pre-wrap">{comment.body || comment.content}</div>
      ) : (
        <textarea
          className="input mt-2 min-h-20"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          data-testid={`comment-editor-${comment.id}`}
        />
      )}
    </div>
  );
}
