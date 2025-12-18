/**
 * Issues API endpoints
 */
import client from './client'

export const issuesAPI = {
  // Get issues for a repository
  getByRepository: (repoId, params) => client.get(`/issues/repository/${repoId}`, { params }),

  // Get single issue with comments
  getById: (id) => client.get(`/issues/${id}`),

  // Create new issue
  create: (data) => client.post('/issues', data),

  // Update issue (title, body, labels, state)
  update: (id, data) => client.put(`/issues/${id}`, data),

  // Add comment to issue
  addComment: (issueId, body) => client.post(`/issues/${issueId}/comments`, { body }),
}
