import { Router } from 'express'
import { Issue, Repository, User, IssueComment } from '../models/index.js'
import { authenticate } from '../middleware/auth.js'

const router = Router()

// Get issues for a repository
router.get('/repository/:repoId', async (req, res) => {
  try {
    const { state } = req.query // 'open', 'closed', or undefined (all)
    const where = { repository_id: req.params.repoId }

    if (state) {
      where.state = state
    }

    const issues = await Issue.findAll({
      where,
      include: [
        {
          model: User,
          as: 'author',
          attributes: ['id', 'username', 'name', 'avatar_url'],
        },
      ],
      order: [['created_at', 'DESC']],
    })

    res.json(issues)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// Get single issue
router.get('/:id', async (req, res) => {
  try {
    const issue = await Issue.findByPk(req.params.id, {
      include: [
        {
          model: User,
          as: 'author',
          attributes: ['id', 'username', 'name', 'avatar_url'],
        },
        {
          model: Repository,
          as: 'repository',
          include: [
            {
              model: User,
              as: 'owner',
              attributes: ['id', 'username', 'name'],
            },
          ],
        },
        {
          model: IssueComment,
          as: 'comments',
          include: [
            {
              model: User,
              as: 'author',
              attributes: ['id', 'username', 'name', 'avatar_url'],
            },
          ],
          order: [['created_at', 'ASC']],
        },
      ],
    })

    if (!issue) {
      return res.status(404).json({ error: 'Issue not found' })
    }

    res.json(issue)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// Create issue
router.post('/', authenticate, async (req, res) => {
  try {
    const { repository_id, title, body, labels } = req.body

    // Verify repository exists
    const repository = await Repository.findByPk(repository_id)
    if (!repository) {
      return res.status(404).json({ error: 'Repository not found' })
    }

    const issue = await Issue.create({
      repository_id,
      author_id: req.user.id,
      title,
      body,
      labels: labels || [],
    })

    // Increment issue count
    await repository.increment('issues_count')

    const result = await Issue.findByPk(issue.id, {
      include: [
        {
          model: User,
          as: 'author',
          attributes: ['id', 'username', 'name', 'avatar_url'],
        },
      ],
    })

    res.status(201).json(result)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// Update issue (close/reopen, edit)
router.put('/:id', authenticate, async (req, res) => {
  try {
    const issue = await Issue.findByPk(req.params.id, {
      include: [{ model: Repository, as: 'repository' }],
    })

    if (!issue) {
      return res.status(404).json({ error: 'Issue not found' })
    }

    // Only author or repo owner can update
    if (issue.author_id !== req.user.id && issue.repository.owner_id !== req.user.id) {
      return res.status(403).json({ error: 'Not authorized' })
    }

    const updateData = {}
    if (req.body.title !== undefined) updateData.title = req.body.title
    if (req.body.body !== undefined) updateData.body = req.body.body
    if (req.body.labels !== undefined) updateData.labels = req.body.labels
    if (req.body.state !== undefined) {
      updateData.state = req.body.state
      if (req.body.state === 'closed') {
        updateData.closed_at = new Date()
      } else {
        updateData.closed_at = null
      }
    }

    await issue.update(updateData)

    const result = await Issue.findByPk(issue.id, {
      include: [
        {
          model: User,
          as: 'author',
          attributes: ['id', 'username', 'name', 'avatar_url'],
        },
      ],
    })

    res.json(result)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// Add comment to issue
router.post('/:id/comments', authenticate, async (req, res) => {
  try {
    const issue = await Issue.findByPk(req.params.id)

    if (!issue) {
      return res.status(404).json({ error: 'Issue not found' })
    }

    const comment = await IssueComment.create({
      issue_id: req.params.id,
      author_id: req.user.id,
      body: req.body.body,
    })

    const result = await IssueComment.findByPk(comment.id, {
      include: [
        {
          model: User,
          as: 'author',
          attributes: ['id', 'username', 'name', 'avatar_url'],
        },
      ],
    })

    res.status(201).json(result)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

export default router
