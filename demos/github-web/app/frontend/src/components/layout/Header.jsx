import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Avatar from '../common/Avatar'
import Dropdown from '../common/Dropdown'

/**
 * GitHub-style Header Component
 */
function Header() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const userMenuItems = [
    {
      label: 'Your profile',
      onClick: () => navigate(`/${user?.username}`),
    },
    {
      label: 'Your repositories',
      onClick: () => navigate('/dashboard'),
    },
    { divider: true },
    {
      label: 'Sign out',
      onClick: handleLogout,
      danger: true,
    },
  ]

  return (
    <header className="bg-gray-900 text-white" data-testid="header">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-4">
            <Link
              to="/"
              className="flex items-center space-x-2 hover:text-gray-300"
              data-testid="logo"
            >
              {/* GitHub-style octicon logo */}
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
              </svg>
              <span className="text-xl font-semibold">GitHub</span>
            </Link>

            {/* Search bar (placeholder) */}
            <div className="hidden md:block">
              <input
                type="text"
                placeholder="Search repositories..."
                className="bg-gray-800 text-white px-3 py-1 rounded-md border border-gray-700 focus:outline-none focus:border-blue-500 w-64"
                data-testid="search-input"
              />
            </div>
          </div>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-4" data-testid="nav">
            <Link
              to="/"
              className="text-gray-300 hover:text-white px-2 py-1"
              data-testid="nav-home"
            >
              Explore
            </Link>
          </nav>

          {/* User Actions */}
          <div className="flex items-center space-x-4" data-testid="auth-section">
            {isAuthenticated ? (
              <>
                <Link
                  to="/new"
                  className="flex items-center space-x-1 text-gray-300 hover:text-white"
                  data-testid="new-repo-link"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <span>New</span>
                </Link>

                <Dropdown
                  trigger={
                    <div className="cursor-pointer">
                      <Avatar
                        src={user?.avatar_url}
                        name={user?.name || user?.username}
                        size="sm"
                        testId="user-avatar"
                      />
                    </div>
                  }
                  items={userMenuItems}
                  align="right"
                  testId="user-menu"
                />
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-gray-300 hover:text-white px-3 py-1"
                  data-testid="nav-login"
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="bg-white text-gray-900 hover:bg-gray-100 px-3 py-1 rounded-md font-medium"
                  data-testid="nav-register"
                >
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
