import { useMemo, useState } from 'react';
import { Plus } from 'lucide-react';

import { useToast } from '../state/ToastContext.jsx';
import { getProjects, createProject } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { Spinner } from '../shared/ui/Spinner.jsx';
import { EmptyState } from '../shared/ui/EmptyState.jsx';
import { CreateProjectModal } from '../projects/CreateProjectModal.jsx';
import { ProjectCard } from '../projects/ProjectCard.jsx';

export default function DashboardPage() {
  const toast = useToast();
  const { data, loading, error, refetch } = useResource(() => getProjects(), []);

  const projects = useMemo(() => {
    // Backend returns { items: [...] }
    const p = data?.items || data?.projects || data || [];
    return Array.isArray(p) ? p : [];
  }, [data]);

  const [createOpen, setCreateOpen] = useState(false);

  async function onCreate(payload) {
    const created = await createProject(payload);
    toast.push({ title: 'Project created', variant: 'success' });
    setCreateOpen(false);
    await refetch();
    return created;
  }

  return (
    <div>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Projects</h1>
          <p className="text-sm text-fg-muted mt-1">Pick a project to view issues.</p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setCreateOpen(true)}
          data-testid="create-project"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Create project
        </button>
      </div>

      <div className="mt-6">
        {loading && (
          <div className="flex items-center gap-2 text-fg-muted">
            <Spinner size="sm" />
            Loading projects…
          </div>
        )}
        {error && (
          <div className="surface p-4">
            <div className="text-sm font-medium">Failed to load projects</div>
            <div className="text-sm text-fg-muted mt-1">{error}</div>
            <button className="btn mt-3" onClick={refetch} data-testid="retry-projects">
              Retry
            </button>
          </div>
        )}

        {!loading && !error && projects.length === 0 && (
          <EmptyState
            title="No projects"
            description="Create your first project to start tracking issues."
            action={
              <button className="btn btn-primary" onClick={() => setCreateOpen(true)} data-testid="empty-create-project">
                Create project
              </button>
            }
          />
        )}

        {!loading && !error && projects.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {projects.map((p) => (
              <ProjectCard key={p.id || p.key} project={p} />
            ))}
          </div>
        )}
      </div>

      <CreateProjectModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreate={onCreate}
      />
    </div>
  );
}
