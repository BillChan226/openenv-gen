import React from 'react'
import { useAuth } from '../context/AuthContext'

function Dashboard() {
  const { user } = useAuth()

  return (
    <div data-testid="dashboard-page">
      <h1 className="text-2xl font-bold mb-6" data-testid="dashboard-title">Dashboard</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6" data-testid="dashboard-welcome">
        <h2 className="text-lg font-semibold mb-2">Welcome, {user?.name || user?.email}!</h2>
        <p className="text-gray-600">This is your personal dashboard.</p>
      </div>

      {/* {{GENERATED_DASHBOARD_CONTENT}} */}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="dashboard-widgets">
        {/* Placeholder widgets - to be generated based on app type */}
        <div className="bg-white rounded-lg shadow p-6" data-testid="widget-1">
          <h3 className="font-semibold mb-2">Widget 1</h3>
          <p className="text-gray-600">Content placeholder</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6" data-testid="widget-2">
          <h3 className="font-semibold mb-2">Widget 2</h3>
          <p className="text-gray-600">Content placeholder</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6" data-testid="widget-3">
          <h3 className="font-semibold mb-2">Widget 3</h3>
          <p className="text-gray-600">Content placeholder</p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
