import React, { useState } from 'react'

/**
 * Tabs Component - Multi-view navigation pattern
 *
 * Teaches agents about:
 * - Tab navigation
 * - State management
 * - Active state indicators
 */
function Tabs({ tabs, defaultTab = 0, testId }) {
  const [activeTab, setActiveTab] = useState(defaultTab)

  return (
    <div data-testid={testId}>
      {/* Tab Headers */}
      <div className="border-b border-gray-200" data-testid={`${testId}-headers`}>
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab, idx) => (
            <button
              key={idx}
              onClick={() => setActiveTab(idx)}
              className={`
                py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap
                ${
                  activeTab === idx
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
              data-testid={`${testId}-tab-${idx}`}
              aria-selected={activeTab === idx}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-4" data-testid={`${testId}-content`}>
        {tabs[activeTab]?.content}
      </div>
    </div>
  )
}

export default Tabs
