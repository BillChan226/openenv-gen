import React from 'react'

/**
 * Select Component - Dropdown pattern
 *
 * Teaches agents about dropdown interactions
 */
function Select({ label, name, value, onChange, options, error, required, placeholder, testId }) {
  return (
    <div className="mb-4">
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">
          {label}{required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <select
        id={name}
        name={name}
        value={value}
        onChange={onChange}
        required={required}
        className={`w-full px-3 py-2 border rounded-md ${error ? 'border-red-500' : 'border-gray-300'}`}
        data-testid={testId}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt, idx) => (
          <option key={idx} value={opt.value} data-testid={`${testId}-option-${opt.value}`}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
    </div>
  )
}

export default Select
