import React from 'react'
import { Link } from 'react-router-dom'
import Button from '../components/common/Button'

function Home() {
  return (
    <div className="text-center py-12" data-testid="home-page">
      <h1 className="text-4xl font-bold text-gray-900 mb-4" data-testid="home-title">
        Welcome to {{ENV_TITLE}}
      </h1>
      <p className="text-xl text-gray-600 mb-8" data-testid="home-description">
        {{ENV_DESCRIPTION}}
      </p>
      <div className="space-x-4">
        <Link to="/register">
          <Button variant="primary" size="lg" testId="home-register-btn">
            Get Started
          </Button>
        </Link>
        <Link to="/login">
          <Button variant="secondary" size="lg" testId="home-login-btn">
            Sign In
          </Button>
        </Link>
      </div>

      {/* {{GENERATED_HOME_CONTENT}} */}
    </div>
  )
}

export default Home
