import { Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useEffect, useMemo } from 'react';

import { ProjectHeader } from '../projects/ProjectHeader.jsx';
import { BoardView } from '../projects/views/BoardView.jsx';
import { ListView } from '../projects/views/ListView.jsx';
import { SummaryView } from '../projects/views/SummaryView.jsx';

const allowed = new Set(['board', 'list', 'summary']);

export default function ProjectPage() {
  const { projectKey, view } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const normalized = (view || '').toLowerCase();
  const effectiveView = allowed.has(normalized) ? normalized : 'board';

  // Persist last view per project
  useEffect(() => {
    if (!projectKey) return;
    if (allowed.has(normalized)) {
      localStorage.setItem(`jira_last_view_${projectKey}`, normalized);
    }
  }, [projectKey, normalized]);

  useEffect(() => {
    if (!projectKey) return;
    if (!allowed.has(normalized)) {
      const last = localStorage.getItem(`jira_last_view_${projectKey}`);
      const target = allowed.has(last) ? last : 'board';
      navigate(`/projects/${encodeURIComponent(projectKey)}/${target}${location.search}`, { replace: true });
    }
  }, [projectKey, normalized, navigate, location.search]);

  const ViewComponent = useMemo(() => {
    if (effectiveView === 'list') return ListView;
    if (effectiveView === 'summary') return SummaryView;
    return BoardView;
  }, [effectiveView]);

  if (!projectKey) return <Navigate to="/dashboard" replace />;

  return (
    <div className="space-y-4">
      <ProjectHeader projectKey={projectKey} view={effectiveView} />
      <ViewComponent projectKey={projectKey} />
    </div>
  );
}
