import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import RepositoryDetail from './pages/RepositoryDetail'
import NewRepository from './pages/NewRepository'
import IssuesList from './pages/IssuesList'
import IssueDetail from './pages/IssueDetail'
import NewIssue from './pages/NewIssue'
import ProtectedRoute from './components/common/ProtectedRoute'

/**
 * GitHub App
 */
function App() {
  return (
    <Layout>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Repository Routes */}
        <Route path="/:owner/:repo" element={<RepositoryDetail />} />
        <Route path="/:owner/:repo/issues" element={<IssuesList />} />
        <Route path="/:owner/:repo/issues/:number" element={<IssueDetail />} />

        {/* Protected Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/new"
          element={
            <ProtectedRoute>
              <NewRepository />
            </ProtectedRoute>
          }
        />
        <Route
          path="/:owner/:repo/issues/new"
          element={
            <ProtectedRoute>
              <NewIssue />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Layout>
  )
}

export default App
