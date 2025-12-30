import { useMemo } from 'react';

import { getIssues } from '../../services/api.js';
import { useResource } from '../../hooks/useResource.js';
import { Spinner } from '../../shared/ui/Spinner.jsx';
import { STATUSES } from '../constants.js';
import { EmptyState } from '../../shared/ui/EmptyState.jsx';

function Bar({ label, value, max }) {
  const pct = max ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <div className="w-28 text-xs text-fg-muted">{label}</div>
      <div className="flex-1 h-2 bg-bg-muted rounded">
        <div className="h-2 bg-primary rounded" style={{ width: `${pct}%` }} />
      </div>
      <div className="w-10 text-right text-xs text-fg-muted">{value}</div>
    </div>
  );
}

export function SummaryView({ projectKey }) {
  const { data, loading, error, refetch } = useResource(() => getIssues({ projectKey }), [projectKey]);

  const issues = useMemo(() => {
    const arr = data?.items || data?.issues || data || [];
    return Array.isArray(arr) ? arr : [];
  }, [data]);

  const counts = useMemo(() => {
    const c = Object.fromEntries(STATUSES.map((s) => [s.id, 0]));
    for (const it of issues) c[it.status] = (c[it.status] || 0) + 1;
    return c;
  }, [issues]);

  const max = useMemo(() => Math.max(1, ...Object.values(counts)), [counts]);

  const workload = useMemo(() => {
    const map = new Map();
    for (const it of issues) {
      const name = it.assigneeName || it.assignee?.name || 'Unassigned';
      map.set(name, (map.get(name) || 0) + 1);
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  }, [issues]);

  const recent = useMemo(() => {
    const copy = [...issues];
    copy.sort((a, b) => new Date(b.updatedAt || b.updated_at || b.createdAt || 0) - new Date(a.updatedAt || a.updated_at || a.createdAt || 0));
    return copy.slice(0, 8);
  }, [issues]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-fg-muted">
        <Spinner size="sm" /> Loading summary…
      </div>
    );
  }

  if (error) {
    return (
      <div className="surface p-4">
        <div className="text-sm font-medium">Failed to load summary</div>
        <div className="text-sm text-fg-muted mt-1">{error}</div>
        <button className="btn mt-3" onClick={refetch} data-testid="retry-summary">
          Retry
        </button>
      </div>
    );
  }

  if (issues.length === 0) {
    return <EmptyState title="No issues" description="Create an issue to see summary statistics." />;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="surface p-4 lg:col-span-2">
        <div className="text-sm font-semibold">Issue count by status</div>
        <div className="mt-4 flex flex-col gap-3">
          {STATUSES.map((s) => (
            <Bar key={s.id} label={s.label} value={counts[s.id] || 0} max={max} />
          ))}
        </div>
      </div>

      <div className="surface p-4">
        <div className="text-sm font-semibold">Assignee workload</div>
        <div className="mt-4 space-y-2">
          {workload.map(([name, count]) => (
            <div key={name} className="flex items-center justify-between">
              <div className="text-sm truncate">{name}</div>
              <div className="chip">{count}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="surface p-4 lg:col-span-3">
        <div className="text-sm font-semibold">Recent activity</div>
        <div className="mt-3 space-y-2">
          {recent.map((it) => (
            <div key={it.id} className="flex items-center justify-between border-b border-border pb-2">
              <div className="min-w-0">
                <div className="text-sm truncate">
                  <span className="font-mono text-xs text-fg-muted mr-2">{it.key}</span>
                  {it.summary || it.title}
                </div>
                <div className="text-xs text-fg-muted mt-0.5">Status: {it.status}</div>
              </div>
              <div className="text-xs text-fg-muted">
                {new Date(it.updatedAt || it.updated_at || it.createdAt || Date.now()).toLocaleString()}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 flex gap-2 flex-wrap">
          {STATUSES.map((s) => (
            <a
              key={s.id}
              className="btn"
              href={`/projects/${encodeURIComponent(projectKey)}/list?status=${encodeURIComponent(s.id)}`}
              data-testid={`quicklink-${s.id}`}
            >
              {s.label}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
