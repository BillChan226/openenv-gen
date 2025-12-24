import { Router } from 'express'
import { body, validationResult } from 'express-validator'
import User from '../models/User.js'
import { authConfig } from '../config/auth.js'
import { authenticate, createSession } from '../middleware/auth.js'

const router = Router()

// Register
router.post('/register',
  body('email').isEmail(),
  body('password').isLength({ min: 6 }),
  body('username').notEmpty(),
  async (req, res, next) => {
    try {
      const errors = validationResult(req)
      if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() })
      }

      const { username, name, email, password } = req.body

      // Check if user already exists
      const existing = await User.findOne({ where: { email } })
      if (existing) {
        return res.status(400).json({ error: 'User already exists' })
      }

      // Create user (plain text password for demo)
      const user = await User.create({
        username,
        name: name || username,
        email,
        password, // Plain text for agent training simplicity
      })

      // Generate simple session token
      const token = createSession(user.id)

      res.status(201).json({ user, token })
    } catch (error) {
      next(error)
    }
  }
)

// Login
router.post('/login',
  body('email').isEmail(),
  body('password').notEmpty(),
  async (req, res, next) => {
    try {
      const { email, password } = req.body
      const user = await User.findOne({ where: { email } })

      // Simple password check (plain text comparison)
      if (!user || user.password !== password) {
        return res.status(401).json({ error: 'Invalid credentials' })
      }

      // Generate simple session token
      const token = createSession(user.id)

      res.json({ user, token })
    } catch (error) {
      next(error)
    }
  }
)

// Get current user
router.get('/me', authenticate, async (req, res) => {
  res.json(req.user)
})

// Logout (client-side only in this simple version)
router.post('/logout', (req, res) => {
  res.json({ message: 'Logged out successfully' })
})

export default router
