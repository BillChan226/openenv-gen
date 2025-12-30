export function Avatar({ src, name, size = 28 }) {
  const initials = (name || '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('');

  return (
    <div
      className="rounded-full bg-bg-muted border border-border overflow-hidden flex items-center justify-center text-xs text-fg-muted"
      style={{ width: size, height: size }}
      title={name}
    >
      {src ? <img src={src} alt={name || 'User'} className="w-full h-full object-cover" /> : initials}
    </div>
  );
}
