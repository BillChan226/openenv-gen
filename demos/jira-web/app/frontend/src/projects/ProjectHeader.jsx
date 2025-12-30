import { NavLink } from 'react-router-dom';
import { useMemo, useState } from 'react';
import { Plus } from 'lucide-react';

import { getProjectByKey } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { Spinner } from '../shared/ui/Spinner.jsx';
import { CreateIssueModal } from '../issues/CreateIssueModal.jsx';
import { useToast } from '../state/ToastContext.jsx';

export function ProjectHeader({ projectKey, view }) {
  const toast = useToast();
  const { data, loading, error } = useResource(() => getProjectByKey(projectKey), [projectKey]);
  const project = useMemo(() => data?.project || data || null, [data]);

  const [createOpen, setCreateOpen] = useState(false);

  return (
    <div className="surface p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold">{project?.name || projectKey}</h1>
            <span className="chip">{projectKey}</span>
          </div>
          {project?.description && <div className="text-sm text-fg-muted mt-1">{project.description}</div>}
          {loading && (
            <div className="mt-2 text-sm text-fg-muted flex items-center gap-2">
              <Spinner size="sm" /> Loading project…
            </div>
          )}
          {error && <div className="mt-2 text-sm text-danger">{error}</div>}
        </div>

        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setCreateOpen(true)}
          data-testid="create-issue"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Create issue
        </button>
      </div>

      <div className="mt-4 flex gap-2">
        <NavLink
          className={({ isActive }) => 'btn ' + (isActive ? 'btn-primary' : '')}
          to={`/projects/${encodeURIComponent(projectKey)}/board`}
          data-testid="view-board"
        >
          Board
        </NavLink>
        <NavLink
          className={({ isActive }) => 'btn ' + (isActive ? 'btn-primary' : '')}
          to={`/projects/${encodeURIComponent(projectKey)}/list`}
          data-testid="view-list"
        >
          List
        </NavLink>
        <NavLink
          className={({ isActive }) => 'btn ' + (isActive ? 'btn-primary' : '')}
          to={`/projects/${encodeURIComponent(projectKey)}/summary`}
          data-testid="view-summary"
        >
          Summary
        </NavLink>
        <div className="flex-1" />
        <div className="text-xs text-fg-muted self-center">Current: {view}</div>
      </div>

      <CreateIssueModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        projectKey={projectKey}
        onCreated={() => {
          toast.push({ title: 'Issue created', variant: 'success' });
        }}
      />
    </div>
  );
}
