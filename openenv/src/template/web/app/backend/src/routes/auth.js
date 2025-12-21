import { Router } from 'express'
import jwt from 'jsonwebtoken'
import { body, validationResult } from 'express-validator'
import User from '../models/User.js'
import { authConfig } from '../config/auth.js'
import { authenticate } from '../middleware/auth.js'

const router = Router()

// Register
router.post('/register',
  body('email').isEmail(),
  body('password').isLength({ min: 6 }),
  body('name').notEmpty(),
  async (req, res, next) => {
    try {
      const errors = validationResult(req)
      if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() })
      }

      const { name, email, password } = req.body
      const user = await User.create({ name, email, password })
      const token = jwt.sign({ userId: user.id }, authConfig.jwtSecret, { expiresIn: authConfig.jwtExpiresIn })

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

      if (!user || !(await user.validatePassword(password))) {
        return res.status(401).json({ message: 'Invalid credentials' })
      }

      const token = jwt.sign({ userId: user.id }, authConfig.jwtSecret, { expiresIn: authConfig.jwtExpiresIn })
      res.json({ user, token })
    } catch (error) {
      next(error)
    }
  }
)

// Get current user
router.get('/me', authenticate, (req, res) => {
  res.json(req.user)
})

export default router
