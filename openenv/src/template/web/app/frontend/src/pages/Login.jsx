import React, { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Input from '../components/common/Input'
import Button from '../components/common/Button'

function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const from = location.state?.from?.pathname || '/dashboard'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto" data-testid="login-page">
      <h1 className="text-2xl font-bold text-center mb-6" data-testid="login-title">Sign In</h1>

      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4" data-testid="login-error">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} data-testid="login-form">
        <Input
          label="Email"
          type="email"
          name="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          testId="login-email"
        />
        <Input
          label="Password"
          type="password"
          name="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          testId="login-password"
        />
        <Button
          type="submit"
          variant="primary"
          className="w-full"
          isLoading={isLoading}
          testId="login-submit"
        >
          Sign In
        </Button>
      </form>

      <p className="text-center mt-4 text-gray-600">
        Don't have an account?{' '}
        <Link to="/register" className="text-blue-600 hover:underline" data-testid="login-register-link">
          Register
        </Link>
      </p>
    </div>
  )
}

export default Login
