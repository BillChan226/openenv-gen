import React, { useEffect } from 'react'
import Button from './Button'

/**
 * Modal Component - Dialog pattern for agent training
 *
 * Teaches agents about:
 * - Modal interactions
 * - Focus management
 * - Close patterns (button, overlay, escape)
 */
function Modal({ isOpen, onClose, title, children, footer, size = 'md', testId }) {
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      data-testid={testId}
    >
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={onClose}
        data-testid={`${testId}-overlay`}
      />

      {/* Modal */}
      <div className={`relative bg-white rounded-lg shadow-xl ${sizes[size]} w-full mx-4`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b" data-testid={`${testId}-header`}>
          <h2 className="text-xl font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            data-testid={`${testId}-close`}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-4" data-testid={`${testId}-body`}>
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="flex justify-end gap-2 p-4 border-t" data-testid={`${testId}-footer`}>
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

export default Modal
