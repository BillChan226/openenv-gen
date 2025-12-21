import React from 'react'

/**
 * Card Component - Content container pattern
 *
 * Provides visual grouping and clickable areas for agent training
 */
function Card({ title, children, footer, onClick, className = '', testId }) {
  const isClickable = !!onClick

  return (
    <div
      className={`bg-white rounded-lg shadow ${isClickable ? 'cursor-pointer hover:shadow-lg transition-shadow' : ''} ${className}`}
      onClick={onClick}
      data-testid={testId}
    >
      {title && (
        <div className="px-6 py-4 border-b" data-testid={`${testId}-header`}>
          <h3 className="text-lg font-semibold">{title}</h3>
        </div>
      )}

      <div className="p-6" data-testid={`${testId}-body`}>
        {children}
      </div>

      {footer && (
        <div className="px-6 py-4 border-t bg-gray-50" data-testid={`${testId}-footer`}>
          {footer}
        </div>
      )}
    </div>
  )
}

export default Card
