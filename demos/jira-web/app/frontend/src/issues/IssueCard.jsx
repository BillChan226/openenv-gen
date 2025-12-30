import { Avatar } from '../shared/ui/Avatar.jsx';
import { PRIORITIES } from '../projects/constants.js';

function PriorityBadge({ priority }) {
  const p = PRIORITIES.find((x) => x.id === priority);
  const tone = p?.tone || 'muted';
  const cls =
    tone === 'danger'
      ? 'badge badge-danger'
      : tone === 'warning'
        ? 'badge badge-warning'
        : tone === 'info'
          ? 'badge badge-info'
          : 'badge';
  return <span className={cls}>{p?.label || priority}</span>;
}

export function IssueCard({ issue, onOpen }) {
  const assignee = issue.assignee || issue.assigneeUser;
  return (
    <button
      type="button"
      className="surface p-3 w-full text-left hover:bg-bg-muted transition"
      onClick={onOpen}
      data-testid={`issue-card-${issue.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-xs text-fg-muted font-mono">{issue.key}</div>
          <div className="text-sm font-medium mt-1 truncate">{issue.summary || issue.title}</div>
        </div>
        <PriorityBadge priority={issue.priority} />
      </div>
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Avatar
            src={assignee?.avatarUrl || assignee?.avatar_url || issue.assigneeAvatarUrl}
            name={assignee?.name || issue.assigneeName || 'Unassigned'}
            size={22}
          />
          <div className="text-xs text-fg-muted truncate">
            {assignee?.name || issue.assigneeName || 'Unassigned'}
          </div>
        </div>
      </div>
    </button>
  );
}
