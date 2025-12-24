import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { issuesAPI } from '../api/issues'
import { repositoriesAPI } from '../api/repositories'
import Input from '../components/common/Input'
import Button from '../components/common/Button'
import Card from '../components/common/Card'

/**
 * New Issue Page - GitHub-style
 */
function NewIssue() {
  const { owner, repo } = useParams()
  const navigate = useNavigate()

  const [repository, setRepository] = useState(null)
  const [formData, setFormData] = useState({
    title: '',
    body: '',
    labels: '',
  })
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadRepository()
  }, [owner, repo])

  const loadRepository = async () => {
    try {
      setLoading(true)
      const response = await repositoriesAPI.getByOwnerAndName(owner, repo)
      setRepository(response.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData({
      ...formData,
      [name]: value,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!formData.title.trim()) {
      setError('Title is required')
      return
    }

    if (!repository) return

    try {
      setSubmitting(true)
      const labels = formData.labels
        .split(',')
        .map((l) => l.trim())
        .filter((l) => l)

      const response = await issuesAPI.create({
        repository_id: repository.id,
        title: formData.title,
        body: formData.body,
        labels,
      })

      const issue = response.data
      navigate(`/${owner}/${repo}/issues/${issue.number}`)
    } catch (err) {
      setError(err.response?.data?.error || err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12" data-testid="new-issue-loading">
        <div className="text-gray-600">Loading...</div>
      </div>
    )
  }

  if (error && !repository) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded" data-testid="new-issue-error">
        Repository not found
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-8" data-testid="new-issue-page">
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
        <span className="text-gray-600">New</span>
      </div>

      <h1 className="text-3xl font-bold text-gray-900 mb-6" data-testid="page-title">
        New Issue
      </h1>

      <Card testId="new-issue-form-card">
        <form onSubmit={handleSubmit} data-testid="new-issue-form">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4" data-testid="error-message">
              {error}
            </div>
          )}

          {/* Title */}
          <Input
            label="Title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            placeholder="Brief description of the issue"
            required
            testId="issue-title-input"
          />

          {/* Body */}
          <div className="mb-4">
            <label htmlFor="body" className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-gray-500">(optional)</span>
            </label>
            <textarea
              id="body"
              name="body"
              value={formData.body}
              onChange={handleChange}
              rows="8"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:border-blue-500 font-mono text-sm"
              placeholder="Provide a detailed description of the issue..."
              data-testid="issue-body-textarea"
            />
            <p className="text-xs text-gray-500 mt-1">
              You can use Markdown formatting
            </p>
          </div>

          {/* Labels */}
          <Input
            label="Labels"
            name="labels"
            value={formData.labels}
            onChange={handleChange}
            placeholder="bug, enhancement, documentation (comma-separated)"
            testId="issue-labels-input"
          />
          <p className="text-xs text-gray-500 mt-1 mb-6">
            Separate multiple labels with commas
          </p>

          {/* Submit Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t">
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate(`/${owner}/${repo}/issues`)}
              testId="cancel-btn"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={submitting}
              testId="submit-issue-btn"
            >
              Submit new issue
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}

export default NewIssue
