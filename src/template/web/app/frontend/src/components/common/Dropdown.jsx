import React, { useState, useRef, useEffect } from 'react'

/**
 * Dropdown Component - Menu pattern with trigger and items
 *
 * Teaches agents about:
 * - Click outside detection
 * - Menu item selection
 * - Positioning
 * - Keyboard navigation
 */
function Dropdown({
  trigger,
  items,
  align = 'left',
  testId
}) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleItemClick = (item) => {
    if (item.onClick) {
      item.onClick()
    }
    if (!item.keepOpen) {
      setIsOpen(false)
    }
  }

  const alignmentClasses = {
    left: 'left-0',
    right: 'right-0',
    center: 'left-1/2 transform -translate-x-1/2',
  }

  return (
    <div className="relative inline-block" ref={dropdownRef} data-testid={testId}>
      {/* Trigger */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        data-testid={`${testId}-trigger`}
      >
        {trigger}
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className={`absolute ${alignmentClasses[align]} mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50`}
          data-testid={`${testId}-menu`}
        >
          <div className="py-1">
            {items.map((item, idx) => {
              if (item.divider) {
                return (
                  <div
                    key={idx}
                    className="border-t border-gray-100 my-1"
                    data-testid={`${testId}-divider-${idx}`}
                  />
                )
              }

              return (
                <button
                  key={idx}
                  onClick={() => handleItemClick(item)}
                  disabled={item.disabled}
                  className={`
                    w-full text-left px-4 py-2 text-sm
                    ${item.disabled
                      ? 'text-gray-400 cursor-not-allowed'
                      : 'text-gray-700 hover:bg-gray-100 cursor-pointer'
                    }
                    ${item.danger ? 'text-red-600 hover:bg-red-50' : ''}
                  `}
                  data-testid={`${testId}-item-${idx}`}
                >
                  {item.icon && <span className="mr-2">{item.icon}</span>}
                  {item.label}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default Dropdown
