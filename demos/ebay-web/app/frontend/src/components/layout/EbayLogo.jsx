export function EbayLogo({ className = 'text-5xl leading-none' }) {
  return (
    <div className={className} aria-label="eBay" data-testid="brand-logo">
      <span className="font-bold" style={{ color: '#E53238' }}>
        e
      </span>
      <span className="font-bold" style={{ color: '#0064D2' }}>
        B
      </span>
      <span className="font-bold" style={{ color: '#F5AF02' }}>
        a
      </span>
      <span className="font-bold" style={{ color: '#86B817' }}>
        y
      </span>
    </div>
  );
}
