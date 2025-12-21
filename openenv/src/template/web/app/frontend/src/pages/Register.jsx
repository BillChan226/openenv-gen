import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Input from '../components/common/Input'
import Button from '../components/common/Button'

function Register() {
  const [formData, setFormData] = useState({ name: '', email: '', password: '', confirmPassword: '' })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setIsLoading(true)
    try {
      await register({ name: formData.name, email: formData.email, password: formData.password })
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto" data-testid="register-page">
      <h1 className="text-2xl font-bold text-center mb-6" data-testid="register-title">Create Account</h1>

      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4" data-testid="register-error">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} data-testid="register-form">
        <Input label="Name" name="name" value={formData.name} onChange={handleChange} required testId="register-name" />
        <Input label="Email" type="email" name="email" value={formData.email} onChange={handleChange} required testId="register-email" />
        <Input label="Password" type="password" name="password" value={formData.password} onChange={handleChange} required testId="register-password" />
        <Input label="Confirm Password" type="password" name="confirmPassword" value={formData.confirmPassword} onChange={handleChange} required testId="register-confirm-password" />
        <Button type="submit" variant="primary" className="w-full" isLoading={isLoading} testId="register-submit">
          Create Account
        </Button>
      </form>

      <p className="text-center mt-4 text-gray-600">
        Already have an account? <Link to="/login" className="text-blue-600 hover:underline" data-testid="register-login-link">Sign In</Link>
      </p>
    </div>
  )
}

export default Register
