import React from 'react';
import clsx from 'clsx';

export function Chip({ children, active = false, className, as: Comp = 'button', ...props }) {
  return (
    <Comp
      className={clsx(
        'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#FF3008]/30',
        active
          ? 'ring-1 ring-[#FF3008]/25 bg-[#FF3008] text-white'
          : 'ring-1 ring-zinc-200 bg-white text-zinc-900 hover:bg-zinc-50',
        className
      )}
      {...props}
    >
      {children}
    </Comp>
  );
}

export default Chip;
