/**
 * Base API client configuration
 *
 * Centralized axios setup with interceptors for:
 * - Auth token injection
 * - Error handling
 * - Mock data (optional)
 */

import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
})

// Request interceptor - add auth token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('session_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor - handle errors
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('session_token')
      window.location.href = '/login'
    }
    return Promise.reject(error.response?.data || error)
  }
)

export default client
