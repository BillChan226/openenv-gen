import React, { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';

import clsx from 'clsx';
import useDebounce from '../../hooks/useDebounce.js';

export function SearchBar({
  placeholder = 'Search',
  defaultValue = '',
  icon,
  onSubmit,
  onChange,
  className,
}) {
  const [value, setValue] = useState(defaultValue);
  const debounced = useDebounce(value, 250);

  useEffect(() => {
    onChange?.(debounced);
  }, [debounced, onChange]);

  useEffect(() => {
    setValue(defaultValue || '');
  }, [defaultValue]);

  const leading = useMemo(() => icon || <Search className="h-4 w-4" />, [icon]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.(value.trim());
      }}
      className={clsx(
        'group flex items-center gap-2 rounded-2xl bg-zinc-100/80 ring-1 ring-transparent focus-within:ring-[#FF3008]/40 focus-within:bg-white transition px-3 py-2',
        className,
      )}
    >
      <span className="text-zinc-500 group-focus-within:text-[#FF3008] transition">{leading}</span>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-transparent outline-none text-sm text-zinc-900 placeholder:text-zinc-500"
      />
      {value ? (
        <button
          type="button"
          onClick={() => {
            setValue('');
            onSubmit?.('');
          }}
          className="rounded-xl px-2 py-1 text-xs font-semibold text-zinc-600 hover:bg-zinc-200 hover:text-zinc-900 transition"
        >
          Clear
        </button>
      ) : null}
    </form>
  );
}

export default SearchBar;
