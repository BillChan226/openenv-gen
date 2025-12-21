import React from 'react'

/**
 * Badge Component - Labels, tags, status indicators
 *
 * Teaches agents about:
 * - Visual status indicators
 * - Color variants
 * - Removable badges
 */
function Badge({
  children,
  variant = 'default',
  size = 'md',
  onRemove,
  testId
}) {
  const variantClasses = {
    default: 'bg-gray-100 text-gray-800',
    primary: 'bg-blue-100 text-blue-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    info: 'bg-cyan-100 text-cyan-800',
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-sm',
    lg: 'px-3 py-1 text-base',
  }

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${variantClasses[variant]} ${sizeClasses[size]}`}
      data-testid={testId}
    >
      {children}
      {onRemove && (
        <button
          onClick={onRemove}
          className="ml-1 inline-flex items-center justify-center rounded-full hover:bg-black hover:bg-opacity-10 focus:outline-none"
          style={{ width: '14px', height: '14px' }}
          data-testid={`${testId}-remove`}
        >
          <span className="text-current" style={{ fontSize: '10px' }}>×</span>
        </button>
      )}
    </span>
  )
}

export default Badge
