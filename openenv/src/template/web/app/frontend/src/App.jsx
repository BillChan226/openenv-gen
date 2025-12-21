import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import ProtectedRoute from './components/common/ProtectedRoute'

/**
 * Main App Component
 *
 * Template placeholders:
 * - {{GENERATED_IMPORTS}} - Additional page/component imports
 * - {{GENERATED_ROUTES}} - Additional route definitions
 */
function App() {
  return (
    <Layout>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        {/* {{GENERATED_ROUTES}} */}
      </Routes>
    </Layout>
  )
}

export default App
