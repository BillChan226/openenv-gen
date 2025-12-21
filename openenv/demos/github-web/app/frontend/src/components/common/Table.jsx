import React from 'react'
import Button from './Button'

/**
 * Table Component - Data display pattern
 *
 * Teaches agents about:
 * - Tabular data
 * - Row actions
 * - Sorting indicators
 * - Empty states
 */
function Table({ columns, data, onRowClick, actions, emptyMessage = 'No data', testId }) {
  if (data.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500" data-testid={`${testId}-empty`}>
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto" data-testid={testId}>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr data-testid={`${testId}-header`}>
            {columns.map((col, idx) => (
              <th
                key={idx}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                data-testid={`${testId}-header-${col.key}`}
              >
                {col.label}
              </th>
            ))}
            {actions && <th className="px-6 py-3 text-right">Actions</th>}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200" data-testid={`${testId}-body`}>
          {data.map((row, rowIdx) => (
            <tr
              key={rowIdx}
              onClick={() => onRowClick?.(row)}
              className={onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}
              data-testid={`${testId}-row-${rowIdx}`}
            >
              {columns.map((col, colIdx) => (
                <td
                  key={colIdx}
                  className="px-6 py-4 whitespace-nowrap text-sm"
                  data-testid={`${testId}-cell-${rowIdx}-${col.key}`}
                >
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
              {actions && (
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                  <div className="flex justify-end gap-2">
                    {actions(row, rowIdx)}
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default Table
