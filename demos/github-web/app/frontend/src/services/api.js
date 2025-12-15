/**
 * Legacy API exports - Use src/api/ folder for new code
 *
 * This file maintains backward compatibility.
 * For new environments, use the structured api/ folder:
 *   - src/api/client.js - Base client
 *   - src/api/auth.js - Auth endpoints
 *   - src/api/{resource}.js - Resource endpoints
 */

import client from '../api/client'
import { authAPI } from '../api/auth'
import { enableMocks } from '../api/mocks'

// Enable mocks if configured
enableMocks(client)

// Legacy exports for backward compatibility
export const authService = authAPI
export default client

// Generic CRUD service factory
export function createResourceService(resource) {
  return {
    getAll: (params) => client.get(`/${resource}`, { params }),
    getById: (id) => client.get(`/${resource}/${id}`),
    create: (data) => client.post(`/${resource}`, data),
    update: (id, data) => client.put(`/${resource}/${id}`, data),
    delete: (id) => client.delete(`/${resource}/${id}`),
  }
}

// {{GENERATED_SERVICES}}
