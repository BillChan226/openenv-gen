import { useNavigate } from 'react-router-dom';

export function ProjectCard({ project }) {
  const navigate = useNavigate();
  const key = project.key || project.projectKey || project.project_key;

  return (
    <button
      type="button"
      className="surface p-4 text-left hover:bg-bg-muted transition"
      onClick={() => navigate(`/projects/${encodeURIComponent(key)}/board`)}
      data-testid={`project-card-${key}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-base font-semibold">{project.name}</div>
          <div className="text-xs text-fg-muted mt-0.5">{key}</div>
        </div>
        <div className="chip">{project.issueCount ?? project.issue_count ?? 0} issues</div>
      </div>
      {project.description && <div className="text-sm text-fg-muted mt-3 line-clamp-3">{project.description}</div>}
    </button>
  );
}
