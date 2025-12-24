/**
 * Auth API endpoints
 *
 * Simplified for agent training - focuses on form interaction patterns
 */

import client from './client'

export const authAPI = {
  /**
   * Login with email and password
   * Returns: { user, token }
   */
  login: (email, password) => client.post('/auth/login', { email, password }),

  /**
   * Register new user
   * Returns: { user, token }
   */
  register: (userData) => client.post('/auth/register', userData),

  /**
   * Get current user
   * Returns: user object
   */
  me: () => client.get('/auth/me'),

  /**
   * Logout (client-side only for simplicity)
   */
  logout: () => {
    localStorage.removeItem('session_token')
    return Promise.resolve()
  },
}

export default authAPI
