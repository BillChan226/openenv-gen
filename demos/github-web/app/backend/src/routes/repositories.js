import { Router } from 'express'
import { Op } from 'sequelize'
import { Repository, User, Star, Issue } from '../models/index.js'
import { authenticate } from '../middleware/auth.js'

const router = Router()

// Get all repositories (public + user's private)
router.get('/', async (req, res) => {
  try {
    const { user_id, search } = req.query
    const where = {}

    if (user_id) {
      where.owner_id = user_id
    } else {
      // Only show public repos if not filtering by user
      where.is_private = false
    }

    if (search) {
      where[Op.or] = [
        { name: { [Op.iLike]: `%${search}%` } },
        { description: { [Op.iLike]: `%${search}%` } },
      ]
    }

    const repositories = await Repository.findAll({
      where,
      include: [
        {
          model: User,
          as: 'owner',
          attributes: ['id', 'username', 'name', 'avatar_url'],
        },
      ],
      order: [['updated_at', 'DESC']],
    })

    res.json(repositories)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// Get single repository
router.get('/:owner/:repo', async (req, res) => {
  try {
    const repository = await Repository.findOne({
      include: [
        {
          model: User,
          as: 'owner',
          attributes: ['id', 'username', 'name', 'avatar_url'],
          where: { username: req.params.owner },
        },
      ],
      where: { name: req.params.repo },
    })

    if (!repository) {
      return res.status(404).json({ error: 'Repository not found' })
    }

    res.json(repository)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// Create repository
router.post('/', authenticate, async (req, res) => {
  try {
    const { name, description, is_private, language } = req.body

    const repository = await Repository.create({
      owner_id: req.user.id,
      name,
      description,
      is_private: is_private || false,
      language,
    })

    const result = await Repository.findByPk(repository.id, {
      include: [
        {
          model: User,
          as: 'owner',
          attributes: ['id', 'username', 'name', 'avatar_url'],
        },
      ],
    })

    res.status(201).json(result)
  } catch (error) {
    if (error.name === 'SequelizeUniqueConstraintError') {
      return res.status(400).json({ error: 'Repository name already exists' })
    }
    res.status(500).json({ error: error.message })
  }
})

// Update repository
router.put('/:id', authenticate, async (req, res) => {
  try {
    const repository = await Repository.findByPk(req.params.id)

    if (!repository) {
      return res.status(404).json({ error: 'Repository not found' })
    }

    if (repository.owner_id !== req.user.id) {
      return res.status(403).json({ error: 'Not authorized' })
    }

    await repository.update(req.body)

    const result = await Repository.findByPk(repository.id, {
      include: [
        {
          model: User,
          as: 'owner',
          attributes: ['id', 'username', 'name', 'avatar_url'],
        },
      ],
    })

    res.json(result)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// Delete repository
router.delete('/:id', authenticate, async (req, res) => {
  try {
    const repository = await Repository.findByPk(req.params.id)

    if (!repository) {
      return res.status(404).json({ error: 'Repository not found' })
    }

    if (repository.owner_id !== req.user.id) {
      return res.status(403).json({ error: 'Not authorized' })
    }

    await repository.destroy()
    res.json({ message: 'Repository deleted' })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// Star/unstar repository
router.post('/:id/star', authenticate, async (req, res) => {
  try {
    const repository = await Repository.findByPk(req.params.id)

    if (!repository) {
      return res.status(404).json({ error: 'Repository not found' })
    }

    const existing = await Star.findOne({
      where: {
        user_id: req.user.id,
        repository_id: req.params.id,
      },
    })

    if (existing) {
      // Unstar
      await existing.destroy()
      await repository.decrement('stars_count')
      return res.json({ starred: false, stars_count: repository.stars_count - 1 })
    } else {
      // Star
      await Star.create({
        user_id: req.user.id,
        repository_id: req.params.id,
      })
      await repository.increment('stars_count')
      return res.json({ starred: true, stars_count: repository.stars_count + 1 })
    }
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// Check if user starred repository
router.get('/:id/starred', authenticate, async (req, res) => {
  try {
    const star = await Star.findOne({
      where: {
        user_id: req.user.id,
        repository_id: req.params.id,
      },
    })

    res.json({ starred: !!star })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

export default router
