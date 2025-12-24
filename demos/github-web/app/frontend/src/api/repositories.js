/**
 * Repositories API endpoints
 */
import client from './client'

export const repositoriesAPI = {
  // Get all public repositories or user's repositories
  getAll: (params) => client.get('/repositories', { params }),

  // Get single repository by owner/name
  getByOwnerAndName: (owner, repo) => client.get(`/repositories/${owner}/${repo}`),

  // Create a new repository
  create: (data) => client.post('/repositories', data),

  // Update repository
  update: (id, data) => client.put(`/repositories/${id}`, data),

  // Delete repository
  delete: (id) => client.delete(`/repositories/${id}`),

  // Star/unstar repository
  toggleStar: (id) => client.post(`/repositories/${id}/star`),

  // Check if repository is starred
  isStarred: (id) => client.get(`/repositories/${id}/starred`),
}
