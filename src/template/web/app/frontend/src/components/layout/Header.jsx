import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Button from '../common/Button'

function Header() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <header className="bg-white shadow-sm" data-testid="header">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="text-xl font-bold text-blue-600" data-testid="logo">
            {{ENV_TITLE}}
          </Link>

          <nav className="flex items-center space-x-4" data-testid="nav">
            <Link to="/" className="text-gray-600 hover:text-gray-900" data-testid="nav-home">
              Home
            </Link>
            {/* {{GENERATED_NAV_LINKS}} */}
          </nav>

          <div className="flex items-center space-x-4" data-testid="auth-section">
            {isAuthenticated ? (
              <>
                <Link to="/dashboard" className="text-gray-600 hover:text-gray-900" data-testid="nav-dashboard">
                  Dashboard
                </Link>
                <span data-testid="user-email">{user?.email}</span>
                <Button variant="secondary" size="sm" onClick={handleLogout} testId="logout-btn">
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Link to="/login"><Button variant="secondary" size="sm" testId="login-btn">Login</Button></Link>
                <Link to="/register"><Button variant="primary" size="sm" testId="register-btn">Register</Button></Link>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
