/**
 * Mock data for frontend development
 *
 * Enable with: VITE_USE_MOCKS=true
 * Allows frontend to work without backend
 */

export const mockUsers = [
  { id: '1', name: 'Admin User', email: 'admin@example.com', role: 'admin' },
  { id: '2', name: 'Test User', email: 'user@example.com', role: 'user' },
  { id: '3', name: 'Jane Smith', email: 'jane@example.com', role: 'user' },
]

// {{GENERATED_MOCK_DATA}}

/**
 * Mock API interceptor
 * Intercepts API calls and returns mock data
 */
export function createMockInterceptor(config) {
  const { url, method } = config

  // Auth endpoints
  if (url === '/api/auth/login' && method === 'post') {
    return {
      data: {
        user: mockUsers[1],
        token: 'mock-session-token',
      },
    }
  }

  if (url === '/api/auth/me' && method === 'get') {
    return { data: mockUsers[1] }
  }

  // Users endpoints
  if (url === '/api/users' && method === 'get') {
    return { data: mockUsers }
  }

  // {{GENERATED_MOCK_RESPONSES}}

  return config
}

/**
 * Enable mock mode
 */
export function enableMocks(client) {
  if (import.meta.env.VITE_USE_MOCKS === 'true') {
    client.interceptors.request.use(
      (config) => {
        console.log('[MOCK]', config.method.toUpperCase(), config.url)
        const mockResponse = createMockInterceptor(config)
        if (mockResponse.data) {
          // Return mock data immediately
          return Promise.reject({
            config,
            response: { data: mockResponse.data, status: 200 },
          })
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    client.interceptors.response.use(
      (response) => response,
      (error) => {
        // If error was from mock interceptor, return the mock data
        if (error.response?.status === 200) {
          return Promise.resolve(error.response)
        }
        return Promise.reject(error)
      }
    )
  }
}
