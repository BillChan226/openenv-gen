import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { repositoriesAPI } from '../api/repositories'
import Card from '../components/common/Card'
import Button from '../components/common/Button'
import Badge from '../components/common/Badge'
import Avatar from '../components/common/Avatar'

/**
 * Dashboard - User's repositories GitHub-style
 */
function Dashboard() {
  const { user } = useAuth()
  const [repositories, setRepositories] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadRepositories()
  }, [user])

  const loadRepositories = async () => {
    if (!user) return

    try {
      setLoading(true)
      const response = await repositoriesAPI.getAll({ user_id: user.id })
      setRepositories(response.data)
    } catch (err) {
      console.error('Failed to load repositories:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto py-8" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <Avatar
            src={user?.avatar_url}
            name={user?.name || user?.username}
            size="xl"
            testId="user-avatar"
          />
          <div>
            <h1 className="text-3xl font-bold text-gray-900" data-testid="dashboard-title">
              {user?.name || user?.username}
            </h1>
            <p className="text-gray-600" data-testid="user-email">
              {user?.email}
            </p>
            {user?.bio && (
              <p className="text-gray-700 mt-2" data-testid="user-bio">
                {user.bio}
              </p>
            )}
          </div>
        </div>

        <Link to="/new">
          <Button variant="primary" testId="new-repo-btn">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>New Repository</span>
            </div>
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <Card testId="stats-repos">
          <div className="text-center py-4">
            <div className="text-3xl font-bold text-gray-900">{repositories.length}</div>
            <div className="text-sm text-gray-600">Repositories</div>
          </div>
        </Card>
        <Card testId="stats-stars">
          <div className="text-center py-4">
            <div className="text-3xl font-bold text-gray-900">
              {repositories.reduce((sum, repo) => sum + repo.stars_count, 0)}
            </div>
            <div className="text-sm text-gray-600">Total Stars</div>
          </div>
        </Card>
        <Card testId="stats-issues">
          <div className="text-center py-4">
            <div className="text-3xl font-bold text-gray-900">
              {repositories.reduce((sum, repo) => sum + repo.issues_count, 0)}
            </div>
            <div className="text-sm text-gray-600">Open Issues</div>
          </div>
        </Card>
      </div>

      {/* Repositories */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Your Repositories</h2>

        {loading ? (
          <div className="text-center py-12 text-gray-600">Loading repositories...</div>
        ) : repositories.length === 0 ? (
          <Card testId="no-repos">
            <div className="text-center py-12">
              <svg
                className="w-16 h-16 mx-auto mb-4 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                />
              </svg>
              <p className="text-lg font-medium text-gray-900 mb-2">No repositories yet</p>
              <p className="text-gray-600 mb-4">Create your first repository to get started</p>
              <Link to="/new">
                <Button variant="primary" testId="create-first-repo-btn">
                  Create Repository
                </Button>
              </Link>
            </div>
          </Card>
        ) : (
          <div className="space-y-4">
            {repositories.map((repo) => (
              <Card key={repo.id} testId={`repo-${repo.id}`} className="hover:border-blue-300">
                <Link to={`/${user.username}/${repo.name}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <h3 className="text-xl font-semibold text-blue-600 hover:underline" data-testid={`repo-${repo.id}-name`}>
                          {repo.name}
                        </h3>
                        {repo.is_private && (
                          <Badge variant="warning" size="sm">Private</Badge>
                        )}
                      </div>

                      {repo.description && (
                        <p className="text-gray-600 mb-3" data-testid={`repo-${repo.id}-description`}>
                          {repo.description}
                        </p>
                      )}

                      <div className="flex items-center space-x-6 text-sm text-gray-600">
                        {repo.language && (
                          <div className="flex items-center space-x-1">
                            <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                            <span>{repo.language}</span>
                          </div>
                        )}
                        <div className="flex items-center space-x-1">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                          <span>{repo.stars_count}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5h1.5a2.25 2.25 0 002.25-2.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zm3.75 7.378a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm3-8.75a.75.75 0 100-1.5.75.75 0 000 1.5z"/>
                          </svg>
                          <span>{repo.forks_count}</span>
                        </div>
                        {repo.issues_count > 0 && (
                          <div className="flex items-center space-x-1">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                              <path d="M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"/>
                              <path d="M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"/>
                            </svg>
                            <span>{repo.issues_count} issues</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="text-sm text-gray-500">
                      Updated {new Date(repo.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                </Link>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
