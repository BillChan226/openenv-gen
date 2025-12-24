import React, { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { issuesAPI } from '../api/issues'
import { repositoriesAPI } from '../api/repositories'
import { useAuth } from '../context/AuthContext'
import Button from '../components/common/Button'
import Badge from '../components/common/Badge'
import Avatar from '../components/common/Avatar'

/**
 * Issues List Page - GitHub-style
 */
function IssuesList() {
  const { owner, repo } = useParams()
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [repository, setRepository] = useState(null)
  const [issues, setIssues] = useState([])
  const [filter, setFilter] = useState('open') // 'open', 'closed', 'all'
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadData()
  }, [owner, repo, filter])

  const loadData = async () => {
    try {
      setLoading(true)

      // Load repository
      const repoResponse = await repositoriesAPI.getByOwnerAndName(owner, repo)
      setRepository(repoResponse.data)

      // Load issues
      const params = filter === 'all' ? {} : { state: filter }
      const issuesResponse = await issuesAPI.getByRepository(repoResponse.data.id, params)
      setIssues(issuesResponse.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading && !repository) {
    return (
      <div className="flex justify-center items-center py-12" data-testid="issues-loading">
        <div className="text-gray-600">Loading issues...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded" data-testid="issues-error">
        Error: {error}
      </div>
    )
  }

  const openCount = issues.filter((i) => i.state === 'open').length
  const closedCount = issues.filter((i) => i.state === 'closed').length

  return (
    <div className="max-w-6xl mx-auto py-6" data-testid="issues-list-page">
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link
          to={`/${owner}/${repo}`}
          className="text-blue-600 hover:underline text-lg font-semibold"
          data-testid="repo-link"
        >
          {owner} / {repo}
        </Link>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900" data-testid="page-title">
          Issues
        </h1>
        {isAuthenticated && (
          <Button
            variant="primary"
            onClick={() => navigate(`/${owner}/${repo}/issues/new`)}
            testId="new-issue-btn"
          >
            New issue
          </Button>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="border-b mb-4">
        <div className="flex space-x-6">
          <button
            onClick={() => setFilter('open')}
            className={`pb-3 px-2 border-b-2 font-medium ${
              filter === 'open'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
            data-testid="filter-open"
          >
            <svg className="w-4 h-4 inline mr-1" fill="currentColor" viewBox="0 0 16 16">
              <path d="M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"/>
              <path d="M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"/>
            </svg>
            Open ({openCount})
          </button>
          <button
            onClick={() => setFilter('closed')}
            className={`pb-3 px-2 border-b-2 font-medium ${
              filter === 'closed'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
            data-testid="filter-closed"
          >
            <svg className="w-4 h-4 inline mr-1" fill="currentColor" viewBox="0 0 16 16">
              <path d="M11.28 6.78a.75.75 0 00-1.06-1.06L7.25 8.69 5.78 7.22a.75.75 0 00-1.06 1.06l2 2a.75.75 0 001.06 0l3.5-3.5z"/>
              <path d="M16 8A8 8 0 110 8a8 8 0 0116 0zm-1.5 0a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z"/>
            </svg>
            Closed ({closedCount})
          </button>
        </div>
      </div>

      {/* Issues List */}
      {issues.length === 0 ? (
        <div className="border rounded-lg bg-gray-50 p-12 text-center text-gray-500" data-testid="no-issues">
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
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p className="text-lg font-medium">No {filter} issues</p>
          {filter === 'open' && isAuthenticated && (
            <Button
              variant="primary"
              size="sm"
              className="mt-4"
              onClick={() => navigate(`/${owner}/${repo}/issues/new`)}
              testId="no-issues-create-btn"
            >
              Create the first issue
            </Button>
          )}
        </div>
      ) : (
        <div className="border rounded-lg divide-y" data-testid="issues-list">
          {issues.map((issue) => (
            <Link
              key={issue.id}
              to={`/${owner}/${repo}/issues/${issue.number}`}
              className="block px-6 py-4 hover:bg-gray-50 transition"
              data-testid={`issue-${issue.number}`}
            >
              <div className="flex items-start space-x-4">
                {/* Status Icon */}
                <svg
                  className={`w-5 h-5 mt-1 flex-shrink-0 ${
                    issue.state === 'open' ? 'text-green-600' : 'text-purple-600'
                  }`}
                  fill="currentColor"
                  viewBox="0 0 16 16"
                >
                  {issue.state === 'open' ? (
                    <>
                      <path d="M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z"/>
                      <path d="M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"/>
                    </>
                  ) : (
                    <>
                      <path d="M11.28 6.78a.75.75 0 00-1.06-1.06L7.25 8.69 5.78 7.22a.75.75 0 00-1.06 1.06l2 2a.75.75 0 001.06 0l3.5-3.5z"/>
                      <path d="M16 8A8 8 0 110 8a8 8 0 0116 0zm-1.5 0a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z"/>
                    </>
                  )}
                </svg>

                {/* Issue Content */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 mb-1" data-testid={`issue-${issue.number}-title`}>
                    {issue.title}
                  </h3>
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <span data-testid={`issue-${issue.number}-number`}>
                      #{issue.number}
                    </span>
                    <span>opened by</span>
                    <span className="font-medium">{issue.author.username}</span>
                  </div>

                  {/* Labels */}
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

                {/* Author Avatar */}
                <Avatar
                  src={issue.author.avatar_url}
                  name={issue.author.name || issue.author.username}
                  size="sm"
                  testId={`issue-${issue.number}-avatar`}
                />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default IssuesList
