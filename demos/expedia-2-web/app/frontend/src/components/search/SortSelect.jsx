import React from 'react';

export function SortSelect({ value, options = [], onChange }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-semibold text-slate-700">Sort</span>
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow-sm outline-none transition focus:border-blue-600 focus:ring-2 focus:ring-blue-200"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default SortSelect;
