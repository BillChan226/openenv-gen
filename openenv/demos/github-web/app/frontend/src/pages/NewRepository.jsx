import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { repositoriesAPI } from '../api/repositories'
import { useAuth } from '../context/AuthContext'
import Input from '../components/common/Input'
import Select from '../components/common/Select'
import Button from '../components/common/Button'
import Card from '../components/common/Card'

/**
 * New Repository Page - GitHub-style
 */
function NewRepository() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_private: false,
    language: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const languageOptions = [
    { value: '', label: 'Select language' },
    { value: 'JavaScript', label: 'JavaScript' },
    { value: 'TypeScript', label: 'TypeScript' },
    { value: 'Python', label: 'Python' },
    { value: 'Java', label: 'Java' },
    { value: 'C', label: 'C' },
    { value: 'C++', label: 'C++' },
    { value: 'Go', label: 'Go' },
    { value: 'Rust', label: 'Rust' },
    { value: 'Ruby', label: 'Ruby' },
    { value: 'PHP', label: 'PHP' },
    { value: 'HTML', label: 'HTML' },
    { value: 'CSS', label: 'CSS' },
  ]

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!formData.name.trim()) {
      setError('Repository name is required')
      return
    }

    try {
      setLoading(true)
      const response = await repositoriesAPI.create(formData)
      const repo = response.data
      navigate(`/${repo.owner.username}/${repo.name}`)
    } catch (err) {
      setError(err.response?.data?.error || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto py-8" data-testid="new-repo-page">
      <h1 className="text-3xl font-bold text-gray-900 mb-6" data-testid="page-title">
        Create a new repository
      </h1>

      <Card testId="new-repo-form-card">
        <form onSubmit={handleSubmit} data-testid="new-repo-form">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4" data-testid="error-message">
              {error}
            </div>
          )}

          {/* Owner */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Owner
            </label>
            <div className="bg-gray-50 px-4 py-2 rounded-md border border-gray-300">
              <span className="text-gray-900 font-medium" data-testid="owner-name">
                {user?.username}
              </span>
            </div>
          </div>

          {/* Repository Name */}
          <Input
            label="Repository name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="my-awesome-project"
            required
            testId="repo-name-input"
          />

          <div className="mb-4 text-sm text-gray-600">
            Your repository will be available at:{' '}
            <span className="font-mono bg-gray-100 px-2 py-1 rounded" data-testid="repo-url-preview">
              github.com/{user?.username}/{formData.name || 'repository-name'}
            </span>
          </div>

          {/* Description */}
          <div className="mb-4">
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-gray-500">(optional)</span>
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              rows="3"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:border-blue-500"
              placeholder="A brief description of your repository"
              data-testid="repo-description-input"
            />
          </div>

          {/* Language */}
          <Select
            label="Primary language"
            name="language"
            value={formData.language}
            onChange={handleChange}
            options={languageOptions}
            placeholder="Select language"
            testId="repo-language-select"
          />

          {/* Visibility */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Visibility
            </label>
            <div className="space-y-3">
              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="radio"
                  name="is_private"
                  checked={!formData.is_private}
                  onChange={() => setFormData({ ...formData, is_private: false })}
                  className="mt-1"
                  data-testid="public-radio"
                />
                <div>
                  <div className="font-medium text-gray-900">Public</div>
                  <div className="text-sm text-gray-600">
                    Anyone on the internet can see this repository
                  </div>
                </div>
              </label>

              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="radio"
                  name="is_private"
                  checked={formData.is_private}
                  onChange={() => setFormData({ ...formData, is_private: true })}
                  className="mt-1"
                  data-testid="private-radio"
                />
                <div>
                  <div className="font-medium text-gray-900">Private</div>
                  <div className="text-sm text-gray-600">
                    You choose who can see and commit to this repository
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t">
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate('/')}
              testId="cancel-btn"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={loading}
              testId="create-repo-btn"
            >
              Create repository
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}

export default NewRepository
