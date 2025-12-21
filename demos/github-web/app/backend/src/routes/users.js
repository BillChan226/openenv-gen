import { Router } from 'express'
import User from '../models/User.js'
import { authenticate } from '../middleware/auth.js'

const router = Router()

// Get all users
router.get('/', authenticate, async (req, res, next) => {
  try {
    const users = await User.findAll()
    res.json(users)
  } catch (error) {
    next(error)
  }
})

// Get user by ID
router.get('/:id', authenticate, async (req, res, next) => {
  try {
    const user = await User.findByPk(req.params.id)
    if (!user) return res.status(404).json({ message: 'User not found' })
    res.json(user)
  } catch (error) {
    next(error)
  }
})

// Update user
router.put('/:id', authenticate, async (req, res, next) => {
  try {
    const user = await User.findByPk(req.params.id)
    if (!user) return res.status(404).json({ message: 'User not found' })

    // Only allow users to update their own profile (or admin)
    if (req.user.id !== user.id && req.user.role !== 'admin') {
      return res.status(403).json({ message: 'Forbidden' })
    }

    await user.update(req.body)
    res.json(user)
  } catch (error) {
    next(error)
  }
})

// Delete user
router.delete('/:id', authenticate, async (req, res, next) => {
  try {
    const user = await User.findByPk(req.params.id)
    if (!user) return res.status(404).json({ message: 'User not found' })
    await user.destroy()
    res.status(204).send()
  } catch (error) {
    next(error)
  }
})

export default router
