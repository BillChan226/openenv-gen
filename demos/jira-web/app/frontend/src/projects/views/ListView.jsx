import { useMemo, useState } from 'react';

import { getIssues, updateIssue } from '../../services/api.js';
import { useResource } from '../../hooks/useResource.js';
import { Spinner } from '../../shared/ui/Spinner.jsx';
import { EmptyState } from '../../shared/ui/EmptyState.jsx';
import { STATUSES } from '../constants.js';
import { IssueDrawer } from '../../issues/IssueDrawer.jsx';
import { useToast } from '../../state/ToastContext.jsx';

function sortItems(items, sortBy, dir) {
  const m = dir === 'desc' ? -1 : 1;
  const copy = [...items];
  copy.sort((a, b) => {
    const av = a[sortBy];
    const bv = b[sortBy];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * m;
    return String(av).localeCompare(String(bv)) * m;
  });
  return copy;
}

export function ListView({ projectKey }) {
  const toast = useToast();
  const { data, loading, error, refetch } = useResource(() => getIssues({ projectKey }), [projectKey]);

  const issues = useMemo(() => {
    const arr = data?.items || data?.issues || data || [];
    return Array.isArray(arr) ? arr : [];
  }, [data]);

  const [sortBy, setSortBy] = useState('createdAt');
  const [dir, setDir] = useState('desc');
  const sorted = useMemo(() => sortItems(issues, sortBy, dir), [issues, sortBy, dir]);

  const [activeIssueId, setActiveIssueId] = useState(null);

  function toggleSort(field) {
    if (sortBy === field) setDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortBy(field);
      setDir('asc');
    }
  }

  async function changeStatus(issueId, status) {
    try {
      await updateIssue(issueId, { status });
      toast.push({ title: 'Status updated', variant: 'success' });
      await refetch();
    } catch (e) {
      toast.push({ title: 'Failed to update status', message: e?.message, variant: 'error' });
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-fg-muted">
        <Spinner size="sm" /> Loading list…
      </div>
    );
  }

  if (error) {
    return (
      <div className="surface p-4">
        <div className="text-sm font-medium">Failed to load issues</div>
        <div className="text-sm text-fg-muted mt-1">{error}</div>
        <button className="btn mt-3" onClick={refetch} data-testid="retry-issues-list">
          Retry
        </button>
      </div>
    );
  }

  if (issues.length === 0) {
    return <EmptyState title="No issues" description="Create an issue to populate the list." />;
  }

  return (
    <>
      <div className="surface overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-bg-muted/50 text-fg-muted">
            <tr>
              <th className="px-3 py-2 text-left">
                <button className="btn btn-ghost" onClick={() => toggleSort('key')} data-testid="sort-key">
                  Key
                </button>
              </th>
              <th className="px-3 py-2 text-left">
                <button className="btn btn-ghost" onClick={() => toggleSort('summary')} data-testid="sort-title">
                  Title
                </button>
              </th>
              <th className="px-3 py-2 text-left">
                <button className="btn btn-ghost" onClick={() => toggleSort('status')} data-testid="sort-status">
                  Status
                </button>
              </th>
              <th className="px-3 py-2 text-left">
                <button className="btn btn-ghost" onClick={() => toggleSort('priority')} data-testid="sort-priority">
                  Priority
                </button>
              </th>
              <th className="px-3 py-2 text-left">Assignee</th>
              <th className="px-3 py-2 text-left">
                <button className="btn btn-ghost" onClick={() => toggleSort('createdAt')} data-testid="sort-created">
                  Created
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((it) => (
              <tr
                key={it.id}
                className="border-t border-border hover:bg-bg-muted/30 cursor-pointer"
                onClick={() => setActiveIssueId(it.id)}
                data-testid={`issue-row-${it.id}`}
              >
                <td className="px-3 py-2 font-mono text-xs">{it.key}</td>
                <td className="px-3 py-2">{it.summary || it.title}</td>
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <select
                    className="input h-9"
                    value={it.status}
                    onChange={(e) => changeStatus(it.id, e.target.value)}
                    data-testid={`status-select-${it.id}`}
                  >
                    {STATUSES.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2">{it.priority}</td>
                <td className="px-3 py-2">{it.assigneeName || it.assignee?.name || 'Unassigned'}</td>
                <td className="px-3 py-2 text-fg-muted">{it.createdAt ? new Date(it.createdAt).toLocaleDateString() : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <IssueDrawer
        issueId={activeIssueId}
        open={!!activeIssueId}
        onClose={() => setActiveIssueId(null)}
        onUpdated={() => refetch()}
      />
    </>
  );
}
