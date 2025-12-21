import React, { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { issuesAPI } from '../api/issues'
import { useAuth } from '../context/AuthContext'
import Button from '../components/common/Button'
import Badge from '../components/common/Badge'
import Avatar from '../components/common/Avatar'
import Card from '../components/common/Card'

/**
 * Issue Detail Page - GitHub-style
 */
function IssueDetail() {
  const { owner, repo, number } = useParams()
  const { isAuthenticated, user } = useAuth()
  const navigate = useNavigate()

  const [issue, setIssue] = useState(null)
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadIssue()
  }, [owner, repo, number])

  const loadIssue = async () => {
    try {
      setLoading(true)
      // In a real app, we'd need to find the issue by owner/repo/number
      // For demo, we'll just use the number directly
      const response = await issuesAPI.getById(number)
      setIssue(response.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCloseReopen = async () => {
    if (!issue) return

    try {
      const newState = issue.state === 'open' ? 'closed' : 'open'
      const response = await issuesAPI.update(issue.id, { state: newState })
      setIssue(response.data)
    } catch (err) {
      alert('Failed to update issue: ' + err.message)
    }
  }

  const handleAddComment = async (e) => {
    e.preventDefault()
    if (!comment.trim()) return

    try {
      setSubmitting(true)
      await issuesAPI.addComment(issue.id, comment)
      setComment('')
      await loadIssue() // Reload to get new comment
    } catch (err) {
      alert('Failed to add comment: ' + err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12" data-testid="issue-loading">
        <div className="text-gray-600">Loading issue...</div>
      </div>
    )
  }

  if (error || !issue) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded" data-testid="issue-error">
        Issue not found
      </div>
    )
  }

  const isAuthor = user?.id === issue.author_id
  const isRepoOwner = user?.id === issue.repository?.owner_id
  const canManage = isAuthor || isRepoOwner

  return (
    <div className="max-w-5xl mx-auto py-6" data-testid="issue-detail-page">
      {/* Breadcrumb */}
      <div className="mb-4 text-sm">
        <Link
          to={`/${owner}/${repo}`}
          className="text-blue-600 hover:underline"
          data-testid="repo-link"
        >
          {owner} / {repo}
        </Link>
        <span className="mx-2 text-gray-400">/</span>
        <Link
          to={`/${owner}/${repo}/issues`}
          className="text-blue-600 hover:underline"
          data-testid="issues-link"
        >
          Issues
        </Link>
        <span className="mx-2 text-gray-400">/</span>
        <span className="text-gray-600" data-testid="issue-number">
          #{issue.number}
        </span>
      </div>

      {/* Issue Header */}
      <div className="mb-6">
        <div className="flex items-start space-x-3 mb-4">
          <h1 className="text-3xl font-bold text-gray-900 flex-1" data-testid="issue-title">
            {issue.title}
          </h1>
          {canManage && (
            <Button
              variant={issue.state === 'open' ? 'secondary' : 'primary'}
              size="sm"
              onClick={handleCloseReopen}
              testId="close-reopen-btn"
            >
              {issue.state === 'open' ? 'Close issue' : 'Reopen issue'}
            </Button>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <Badge
            variant={issue.state === 'open' ? 'success' : 'danger'}
            testId="issue-state-badge"
          >
            <div className="flex items-center space-x-1">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
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
              <span className="capitalize">{issue.state}</span>
            </div>
          </Badge>

          <span className="text-gray-600">
            <span className="font-medium">{issue.author.username}</span> opened this issue
          </span>

          {/* Labels */}
          {issue.labels && issue.labels.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {issue.labels.map((label, idx) => (
                <Badge key={idx} variant="info" size="sm">
                  {label}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Issue Body */}
      <div className="space-y-4">
        <Card testId="issue-body-card">
          <div className="flex items-start space-x-4">
            <Avatar
              src={issue.author.avatar_url}
              name={issue.author.name || issue.author.username}
              size="md"
              testId="author-avatar"
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-3">
                <span className="font-semibold text-gray-900">{issue.author.username}</span>
                <span className="text-sm text-gray-500">
                  {new Date(issue.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="prose max-w-none" data-testid="issue-body">
                {issue.body ? (
                  <p className="text-gray-700 whitespace-pre-wrap">{issue.body}</p>
                ) : (
                  <p className="text-gray-500 italic">No description provided.</p>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* Comments */}
        {issue.comments && issue.comments.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Comments ({issue.comments.length})
            </h3>
            {issue.comments.map((comment) => (
              <Card key={comment.id} testId={`comment-${comment.id}`}>
                <div className="flex items-start space-x-4">
                  <Avatar
                    src={comment.author.avatar_url}
                    name={comment.author.name || comment.author.username}
                    size="md"
                    testId={`comment-${comment.id}-avatar`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-3">
                      <span className="font-semibold text-gray-900">
                        {comment.author.username}
                      </span>
                      <span className="text-sm text-gray-500">
                        {new Date(comment.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="prose max-w-none">
                      <p className="text-gray-700 whitespace-pre-wrap">{comment.body}</p>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Add Comment Form */}
        {isAuthenticated ? (
          <Card testId="comment-form-card">
            <form onSubmit={handleAddComment} data-testid="comment-form">
              <div className="flex items-start space-x-4">
                <Avatar
                  src={user?.avatar_url}
                  name={user?.name || user?.username}
                  size="md"
                  testId="current-user-avatar"
                />
                <div className="flex-1 min-w-0">
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    rows="4"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:border-blue-500"
                    placeholder="Add your comment..."
                    data-testid="comment-textarea"
                  />
                  <div className="flex justify-end mt-3">
                    <Button
                      type="submit"
                      variant="primary"
                      loading={submitting}
                      disabled={!comment.trim()}
                      testId="submit-comment-btn"
                    >
                      Comment
                    </Button>
                  </div>
                </div>
              </div>
            </form>
          </Card>
        ) : (
          <Card testId="login-prompt">
            <div className="text-center py-8">
              <p className="text-gray-600 mb-4">
                Sign in to add a comment
              </p>
              <Button
                variant="primary"
                onClick={() => navigate('/login')}
                testId="login-to-comment-btn"
              >
                Sign in
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}

export default IssueDetail
