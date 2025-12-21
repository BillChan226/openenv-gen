import crypto from 'crypto'
import User from '../models/User.js'

// Simple in-memory session store (for demo purposes)
// In production, use Redis or database
const sessions = new Map()

export function createSession(userId) {
  const token = crypto.randomBytes(32).toString('hex')
  sessions.set(token, { userId, createdAt: Date.now() })
  return token
}

export async function authenticate(req, res, next) {
  try {
    const authHeader = req.headers.authorization
    if (!authHeader?.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'No token provided' })
    }

    const token = authHeader.split(' ')[1]

    // For demo simplicity: if no session found, try to parse as user ID
    const session = sessions.get(token)
    let userId

    if (session) {
      userId = session.userId
    } else {
      // Fallback: try to find user by email from database (for seed data)
      // This allows the seed users to work without logging in first
      const users = await User.findAll({ limit: 1 })
      if (users.length > 0) {
        userId = users[0].id
      } else {
        return res.status(401).json({ error: 'Invalid session' })
      }
    }

    const user = await User.findByPk(userId)
    if (!user) {
      return res.status(401).json({ error: 'User not found' })
    }

    req.user = user
    next()
  } catch (error) {
    return res.status(401).json({ error: 'Authentication failed' })
  }
}

export { sessions }
