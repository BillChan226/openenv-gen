import { useEffect, useMemo, useState } from 'react';
import { Modal } from '../shared/ui/Modal.jsx';

function slugToKey(name) {
  const cleaned = String(name || '')
    .toUpperCase()
    .replace(/[^A-Z0-9 ]+/g, ' ')
    .trim();

  if (!cleaned) return '';

  // Prefer initials if multiple words, otherwise take leading chars.
  const parts = cleaned.split(/\s+/).filter(Boolean);
  let k = '';
  if (parts.length >= 2) {
    k = parts
      .map((p) => p[0])
      .join('')
      .slice(0, 10);
  } else {
    k = parts[0].slice(0, 10);
  }

  // Ensure starts with a letter.
  if (!/^[A-Z]/.test(k)) k = `P${k}`.slice(0, 10);
  return k.slice(0, 10);
}

export function CreateProjectModal({ open, onClose, onCreate }) {
  const [name, setName] = useState('');
  const [key, setKey] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const suggestedKey = useMemo(() => slugToKey(name), [name]);

  useEffect(() => {
    // Auto-suggest a key from name, but don't overwrite user edits.
    if (!open) return;
    if (!key && suggestedKey) setKey(suggestedKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, suggestedKey]);

  function reset() {
    setName('');
    setKey('');
    setDescription('');
    setError(null);
  }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError('Name is required');
      return;
    }
    const trimmedKey = key.trim().toUpperCase();
    if (!trimmedKey || !/^[A-Z][A-Z0-9]{1,9}$/.test(trimmedKey)) {
      setError('Key must be 2-10 chars, uppercase letters/numbers, starting with a letter');
      return;
    }

    setLoading(true);
    try {
      await onCreate({
        name: name.trim(),
        key: trimmedKey,
        description: description.trim() || null,
      });
      reset();
    } catch (e2) {
      // Keep modal open and show inline error.
      setError(e2?.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal
      open={open}
      title="Create project"
      onClose={() => {
        reset();
        onClose();
      }}
      testid="create-project-modal"
      footer={
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="btn"
            onClick={() => {
              reset();
              onClose();
            }}
            data-testid="create-project-cancel"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="create-project-form"
            className="btn btn-primary"
            disabled={loading}
            data-testid="create-project-submit"
          >
            {loading ? 'Creating…' : 'Create'}
          </button>
        </div>
      }
    >
      <form id="create-project-form" onSubmit={submit} className="space-y-4">
        <div>
          <label className="text-sm font-medium" htmlFor="proj-name">
            Name
          </label>
          <input
            id="proj-name"
            className="input mt-1"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Acme Platform"
            data-testid="project-name"
          />
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="proj-key">
            Key
          </label>
          <input
            id="proj-key"
            className="input mt-1 font-mono"
            value={key}
            onChange={(e) => setKey(e.target.value.toUpperCase())}
            placeholder={suggestedKey || 'ACME'}
            data-testid="project-key"
          />
          <div className="text-xs text-fg-muted mt-1">Suggested: {suggestedKey || '—'}</div>
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="proj-desc">
            Description
          </label>
          <textarea
            id="proj-desc"
            className="input mt-1 min-h-24"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional"
            data-testid="project-description"
          />
        </div>
        {error && <div className="text-sm text-danger">{error}</div>}
      </form>
    </Modal>
  );
}
