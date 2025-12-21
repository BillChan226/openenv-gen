import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { repositoriesAPI } from '../api/repositories'
import Card from '../components/common/Card'
import Avatar from '../components/common/Avatar'
import Badge from '../components/common/Badge'

/**
 * GitHub Home Page - Explore Public Repositories
 */
function Home() {
  const [repositories, setRepositories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadRepositories()
  }, [])

  const loadRepositories = async () => {
    try {
      setLoading(true)
      const data = await repositoriesAPI.getAll()
      setRepositories(data || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12" data-testid="home-loading">
        <div className="text-gray-600">Loading repositories...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded" data-testid="home-error">
        Error loading repositories: {error}
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto py-8" data-testid="home-page">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold text-gray-900 mb-4" data-testid="home-title">
          Explore Public Repositories
        </h1>
        <p className="text-xl text-gray-600 mb-8" data-testid="home-description">
          Discover amazing open source projects from the community
        </p>
      </div>

      {/* Repository List */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Trending Repositories
        </h2>

        {repositories.length === 0 ? (
          <Card testId="no-repos">
            <div className="text-center py-12 text-gray-500">
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
              <p className="text-lg">No repositories found</p>
            </div>
          </Card>
        ) : (
          repositories.map((repo) => (
            <Card key={repo.id} testId={`repo-card-${repo.id}`} className="hover:border-blue-300">
              <Link to={`/${repo.owner.username}/${repo.name}`} className="block">
                <div className="flex items-start space-x-4">
                  {/* Owner Avatar */}
                  <Avatar
                    src={repo.owner.avatar_url}
                    name={repo.owner.name || repo.owner.username}
                    size="md"
                    testId={`repo-owner-avatar-${repo.id}`}
                  />

                  {/* Repository Info */}
                  <div className="flex-1 min-w-0">
                    {/* Title */}
                    <div className="flex items-center space-x-2 mb-2">
                      <h3 className="text-xl font-semibold text-blue-600 hover:underline" data-testid={`repo-name-${repo.id}`}>
                        {repo.owner.username} / {repo.name}
                      </h3>
                      {repo.is_private && (
                        <Badge variant="warning" size="sm" testId={`repo-private-badge-${repo.id}`}>
                          Private
                        </Badge>
                      )}
                    </div>

                    {/* Description */}
                    {repo.description && (
                      <p className="text-gray-600 mb-3" data-testid={`repo-description-${repo.id}`}>
                        {repo.description}
                      </p>
                    )}

                    {/* Metadata */}
                    <div className="flex items-center space-x-6 text-sm text-gray-600">
                      {/* Language */}
                      {repo.language && (
                        <div className="flex items-center space-x-1" data-testid={`repo-language-${repo.id}`}>
                          <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                          <span>{repo.language}</span>
                        </div>
                      )}

                      {/* Stars */}
                      <div className="flex items-center space-x-1" data-testid={`repo-stars-${repo.id}`}>
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                        <span>{repo.stars_count}</span>
                      </div>

                      {/* Forks */}
                      <div className="flex items-center space-x-1" data-testid={`repo-forks-${repo.id}`}>
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                          <path d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5h1.5a2.25 2.25 0 002.25-2.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zm3.75 7.378a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm3-8.75a.75.75 0 100-1.5.75.75 0 000 1.5z"/>
                        </svg>
                        <span>{repo.forks_count}</span>
                      </div>

                      {/* Issues */}
                      {repo.issues_count > 0 && (
                        <div className="flex items-center space-x-1" data-testid={`repo-issues-${repo.id}`}>
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"/>
                            <path d="M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"/>
                          </svg>
                          <span>{repo.issues_count} issues</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Link>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}

export default Home
