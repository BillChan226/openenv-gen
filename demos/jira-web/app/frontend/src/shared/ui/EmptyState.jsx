export function EmptyState({ title, description, action }) {
  return (
    <div className="surface p-8 text-center">
      <div className="text-base font-semibold">{title}</div>
      {description && <div className="text-sm text-fg-muted mt-1">{description}</div>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
