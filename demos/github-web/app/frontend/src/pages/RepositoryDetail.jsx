import React, { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { repositoriesAPI } from '../api/repositories'
import { issuesAPI } from '../api/issues'
import { useAuth } from '../context/AuthContext'
import Avatar from '../components/common/Avatar'
import Button from '../components/common/Button'
import Tabs from '../components/common/Tabs'
import Badge from '../components/common/Badge'

/**
 * Repository Detail Page - GitHub-style
 */
function RepositoryDetail() {
  const { owner, repo } = useParams()
  const { isAuthenticated, user } = useAuth()
  const navigate = useNavigate()

  const [repository, setRepository] = useState(null)
  const [issues, setIssues] = useState([])
  const [starred, setStarred] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadRepositoryData()
  }, [owner, repo])

  const loadRepositoryData = async () => {
    try {
      setLoading(true)
      const repoResponse = await repositoriesAPI.getByOwnerAndName(owner, repo)
      setRepository(repoResponse.data)

      // Load issues for this repo
      const issuesResponse = await issuesAPI.getByRepository(repoResponse.data.id, { state: 'open' })
      setIssues(issuesResponse.data)

      // Check if starred (if authenticated)
      if (isAuthenticated) {
        try {
          const starResponse = await repositoriesAPI.isStarred(repoResponse.data.id)
          setStarred(starResponse.data.starred)
        } catch (err) {
          // Not authenticated or error
        }
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleStar = async () => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }

    try {
      const response = await repositoriesAPI.toggleStar(repository.id)
      setStarred(response.data.starred)
      setRepository({
        ...repository,
        stars_count: response.data.stars_count,
      })
    } catch (err) {
      console.error('Failed to toggle star:', err)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12" data-testid="repo-loading">
        <div className="text-gray-600">Loading repository...</div>
      </div>
    )
  }

  if (error || !repository) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded" data-testid="repo-error">
        Repository not found
      </div>
    )
  }

  const isOwner = isAuthenticated && user?.id === repository.owner_id

  const tabs = [
    {
      label: (
        <div className="flex items-center space-x-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
            <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z"/>
          </svg>
          <span>Code</span>
        </div>
      ),
      content: (
        <div className="py-8" data-testid="code-tab">
          <div className="border rounded-lg bg-gray-50 p-12 text-center text-gray-500">
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
                d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
              />
            </svg>
            <p className="text-lg font-medium">Code browser not implemented</p>
            <p className="text-sm mt-2">This is a demo environment focused on repository and issue management</p>
          </div>
        </div>
      ),
    },
    {
      label: (
        <div className="flex items-center space-x-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"/>
            <path d="M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"/>
          </svg>
          <span>Issues</span>
          <Badge variant="default" size="sm">{repository.issues_count}</Badge>
        </div>
      ),
      content: (
        <div className="py-4" data-testid="issues-tab">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Open Issues</h3>
            {isAuthenticated && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate(`/${owner}/${repo}/issues/new`)}
                testId="new-issue-btn"
              >
                New Issue
              </Button>
            )}
          </div>

          {issues.length === 0 ? (
            <div className="border rounded-lg bg-gray-50 p-12 text-center text-gray-500">
              <p>No open issues</p>
            </div>
          ) : (
            <div className="border rounded-lg divide-y">
              {issues.map((issue) => (
                <Link
                  key={issue.id}
                  to={`/${owner}/${repo}/issues/${issue.number}`}
                  className="block px-4 py-3 hover:bg-gray-50"
                  data-testid={`issue-item-${issue.number}`}
                >
                  <div className="flex items-start space-x-3">
                    <svg
                      className={`w-5 h-5 mt-0.5 ${
                        issue.state === 'open' ? 'text-green-600' : 'text-purple-600'
                      }`}
                      fill="currentColor"
                      viewBox="0 0 16 16"
                    >
                      <path d="M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"/>
                      <path d="M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"/>
                    </svg>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900">{issue.title}</h4>
                      <p className="text-sm text-gray-600 mt-1">
                        #{issue.number} opened by {issue.author.username}
                      </p>
                      {issue.labels && issue.labels.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                          {issue.labels.map((label, idx) => (
                            <Badge key={idx} variant="info" size="sm">
                              {label}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}

          <div className="mt-4 text-center">
            <Link
              to={`/${owner}/${repo}/issues`}
              className="text-blue-600 hover:underline"
              data-testid="view-all-issues-link"
            >
              View all issues →
            </Link>
          </div>
        </div>
      ),
    },
    {
      label: (
        <div className="flex items-center space-x-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
            <path d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z"/>
          </svg>
          <span>Pull Requests</span>
          <Badge variant="default" size="sm">0</Badge>
        </div>
      ),
      content: (
        <div className="py-8" data-testid="prs-tab">
          <div className="border rounded-lg bg-gray-50 p-12 text-center text-gray-500">
            <p className="text-lg font-medium">Pull Requests not implemented</p>
            <p className="text-sm mt-2">This demo focuses on repository and issue management</p>
          </div>
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-6xl mx-auto py-6" data-testid="repo-detail-page">
      {/* Repository Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <Avatar
              src={repository.owner.avatar_url}
              name={repository.owner.name || repository.owner.username}
              size="lg"
              testId="repo-owner-avatar"
            />
            <div>
              <div className="flex items-center space-x-2">
                <Link
                  to={`/${repository.owner.username}`}
                  className="text-blue-600 hover:underline text-lg"
                  data-testid="owner-name"
                >
                  {repository.owner.username}
                </Link>
                <span className="text-gray-400">/</span>
                <h1 className="text-2xl font-bold text-gray-900" data-testid="repo-name">
                  {repository.name}
                </h1>
                {repository.is_private && (
                  <Badge variant="warning" testId="private-badge">
                    Private
                  </Badge>
                )}
              </div>
              {repository.description && (
                <p className="text-gray-600 mt-2" data-testid="repo-description">
                  {repository.description}
                </p>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-2">
            <Button
              variant={starred ? 'primary' : 'secondary'}
              size="sm"
              onClick={handleStar}
              testId="star-btn"
            >
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4" fill={starred ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 20 20">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                </svg>
                <span>{starred ? 'Starred' : 'Star'}</span>
                <span className="font-semibold">{repository.stars_count}</span>
              </div>
            </Button>
          </div>
        </div>

        {/* Repository Stats */}
        <div className="flex items-center space-x-6 text-sm text-gray-600">
          {repository.language && (
            <div className="flex items-center space-x-1">
              <span className="w-3 h-3 rounded-full bg-blue-500"></span>
              <span data-testid="repo-language">{repository.language}</span>
            </div>
          )}
          <div data-testid="repo-stars">
            {repository.stars_count} stars
          </div>
          <div data-testid="repo-forks">
            {repository.forks_count} forks
          </div>
          <div data-testid="repo-issues">
            {repository.issues_count} issues
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs tabs={tabs} defaultTab={0} testId="repo-tabs" />
    </div>
  )
}

export default RepositoryDetail
