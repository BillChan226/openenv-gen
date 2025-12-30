import { useEffect, useMemo, useState } from 'react';

import { Modal } from '../shared/ui/Modal.jsx';
import { createIssue, getUsers } from '../services/api.js';
import { STATUSES, PRIORITIES, TYPES } from '../projects/constants.js';
import { useResource } from '../hooks/useResource.js';
import { useToast } from '../state/ToastContext.jsx';

export function CreateIssueModal({ open, onClose, projectKey, onCreated }) {
  const toast = useToast();
  const { data: usersData } = useResource(() => getUsers(), []);
  const users = useMemo(() => usersData?.users || usersData || [], [usersData]);

  const [summary, setSummary] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState('TASK');
  const [priority, setPriority] = useState('MEDIUM');
  const [assigneeId, setAssigneeId] = useState('');
  const [labels, setLabels] = useState('');
  const [status, setStatus] = useState('TODO');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
  }, [open]);

  function reset() {
    setSummary('');
    setDescription('');
    setType('TASK');
    setPriority('MEDIUM');
    setAssigneeId('');
    setLabels('');
    setStatus('TODO');
    setError(null);
  }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    if (!summary.trim()) {
      setError('Title is required');
      return;
    }

    const payload = {
      projectKey,
      summary: summary.trim(),
      description: description.trim() || null,
      type,
      priority,
      status,
      labels: labels
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      assigneeId: assigneeId ? Number(assigneeId) : null,
    };

    setLoading(true);
    try {
      await createIssue(payload);
      toast.push({ title: 'Issue created', message: 'Your issue has been created.', variant: 'success' });
      onCreated?.();
      reset();
      onClose();
    } catch (e2) {
      toast.push({ title: 'Failed to create issue', message: e2?.message, variant: 'error' });
      setError(e2?.message || 'Failed to create issue');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal
      open={open}
      title={`Create issue in ${projectKey}`}
      onClose={() => {
        reset();
        onClose();
      }}
      testid="create-issue-modal"
      footer={
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="btn"
            onClick={() => {
              reset();
              onClose();
            }}
            data-testid="create-issue-cancel"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="create-issue-form"
            className="btn btn-primary"
            disabled={loading}
            data-testid="create-issue-submit"
          >
            {loading ? 'Creating…' : 'Create'}
          </button>
        </div>
      }
    >
      <form id="create-issue-form" onSubmit={submit} className="space-y-4">
        <div>
          <label className="text-sm font-medium" htmlFor="issue-title">
            Title
          </label>
          <input
            id="issue-title"
            className="input mt-1"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="Short summary"
            data-testid="issue-title"
          />
        </div>

        <div>
          <label className="text-sm font-medium" htmlFor="issue-desc">
            Description (markdown)
          </label>
          <textarea
            id="issue-desc"
            className="input mt-1 min-h-28"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional"
            data-testid="issue-description"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium" htmlFor="issue-type">
              Type
            </label>
            <select
              id="issue-type"
              className="input mt-1 h-10"
              value={type}
              onChange={(e) => setType(e.target.value)}
              data-testid="issue-type"
            >
              {TYPES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="issue-priority">
              Priority
            </label>
            <select
              id="issue-priority"
              className="input mt-1 h-10"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              data-testid="issue-priority"
            >
              {PRIORITIES.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-sm font-medium" htmlFor="issue-assignee">
              Assignee
            </label>
            <select
              id="issue-assignee"
              className="input mt-1 h-10"
              value={assigneeId}
              onChange={(e) => setAssigneeId(e.target.value)}
              data-testid="issue-assignee"
            >
              <option value="">Unassigned</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name || u.email}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="issue-status">
              Status
            </label>
            <select
              id="issue-status"
              className="input mt-1 h-10"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              data-testid="issue-status"
            >
              {STATUSES.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium" htmlFor="issue-labels">
            Labels (comma-separated)
          </label>
          <input
            id="issue-labels"
            className="input mt-1"
            value={labels}
            onChange={(e) => setLabels(e.target.value)}
            placeholder="frontend, api"
            data-testid="issue-labels"
          />
        </div>

        {error && <div className="text-sm text-danger">{error}</div>}
      </form>
    </Modal>
  );
}
