import { useMemo, useState } from 'react';
import { DragDropContext, Draggable, Droppable } from '@hello-pangea/dnd';

import { getIssues, updateIssue } from '../../services/api.js';
import { useResource } from '../../hooks/useResource.js';
import { Spinner } from '../../shared/ui/Spinner.jsx';
import { EmptyState } from '../../shared/ui/EmptyState.jsx';
import { STATUSES } from '../constants.js';
import { IssueCard } from '../../issues/IssueCard.jsx';
import { IssueDrawer } from '../../issues/IssueDrawer.jsx';
import { useToast } from '../../state/ToastContext.jsx';

function groupByStatus(issues) {
  const map = new Map(STATUSES.map((s) => [s.id, []]));
  for (const it of issues) {
    const st = it.status;
    if (!map.has(st)) map.set(st, []);
    map.get(st).push(it);
  }
  return map;
}

export function BoardView({ projectKey }) {
  const toast = useToast();
  const { data, loading, error, refetch, setData } = useResource(
    () => getIssues({ projectKey }),
    [projectKey]
  );

  const issues = useMemo(() => {
    const arr = data?.items || data?.issues || data || [];
    return Array.isArray(arr) ? arr : [];
  }, [data]);

  const grouped = useMemo(() => groupByStatus(issues), [issues]);

  const [activeIssueId, setActiveIssueId] = useState(null);

  async function onDragEnd(result) {
    if (!result.destination) return;
    const { draggableId, destination, source } = result;
    if (destination.droppableId === source.droppableId && destination.index === source.index) return;

    const issueId = draggableId;
    const nextStatus = destination.droppableId;

    // optimistic update
    const prev = issues;
    const nextIssues = prev.map((i) => (String(i.id) === String(issueId) ? { ...i, status: nextStatus } : i));
    setData({ ...(data || {}), issues: nextIssues });

    try {
      await updateIssue(issueId, { status: nextStatus });
      toast.push({ title: 'Status updated', variant: 'success' });
      await refetch();
    } catch (e) {
      setData({ ...(data || {}), issues: prev });
      toast.push({ title: 'Failed to update status', message: e?.message, variant: 'error' });
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-fg-muted">
        <Spinner size="sm" /> Loading board…
      </div>
    );
  }

  if (error) {
    return (
      <div className="surface p-4">
        <div className="text-sm font-medium">Failed to load issues</div>
        <div className="text-sm text-fg-muted mt-1">{error}</div>
        <button className="btn mt-3" onClick={refetch} data-testid="retry-issues-board">
          Retry
        </button>
      </div>
    );
  }

  if (issues.length === 0) {
    return <EmptyState title="No issues" description="Create an issue to populate the board." />;
  }

  return (
    <>
      <DragDropContext onDragEnd={onDragEnd}>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {STATUSES.map((col) => {
            const items = grouped.get(col.id) || [];
            return (
              <div key={col.id} className="surface p-3 min-h-[220px]">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold">{col.label}</div>
                  <div className="chip">{items.length}</div>
                </div>

                <Droppable droppableId={col.id}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={
                        'mt-3 min-h-[140px] flex flex-col gap-2 rounded-md transition ' +
                        (snapshot.isDraggingOver ? 'bg-bg-muted/60' : '')
                      }
                      data-testid={`board-col-${col.id}`}
                    >
                      {items.map((it, idx) => (
                        <Draggable key={it.id} draggableId={String(it.id)} index={idx}>
                          {(dragProvided, dragSnapshot) => (
                            <div
                              ref={dragProvided.innerRef}
                              {...dragProvided.draggableProps}
                              {...dragProvided.dragHandleProps}
                              className={dragSnapshot.isDragging ? 'opacity-90' : ''}
                            >
                              <IssueCard issue={it} onOpen={() => setActiveIssueId(it.id)} />
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </div>
            );
          })}
        </div>
      </DragDropContext>

      <IssueDrawer
        issueId={activeIssueId}
        open={!!activeIssueId}
        onClose={() => setActiveIssueId(null)}
        onUpdated={() => refetch()}
      />
    </>
  );
}
