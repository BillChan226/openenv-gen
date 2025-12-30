export function Spinner({ size = 'md' }) {
  const px = size === 'lg' ? 36 : size === 'sm' ? 16 : 24;
  return (
    <div
      className="inline-block animate-spin rounded-full border-2 border-border border-t-primary"
      style={{ width: px, height: px }}
      role="progressbar"
      aria-label="Loading"
    />
  );
}
