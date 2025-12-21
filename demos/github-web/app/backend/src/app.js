import express from 'express'
import cors from 'cors'
import helmet from 'helmet'
import morgan from 'morgan'
import authRoutes from './routes/auth.js'
import userRoutes from './routes/users.js'
import repositoriesRoutes from './routes/repositories.js'
import issuesRoutes from './routes/issues.js'
import { errorHandler } from './middleware/error.js'

const app = express()

// Middleware
app.use(cors({
  origin: ['http://localhost:3001', 'http://localhost:3000'],
  credentials: true
}))
app.use(helmet({
  crossOriginResourcePolicy: { policy: 'cross-origin' }
}))
app.use(morgan('dev'))
app.use(express.json())

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

// Routes
app.use('/api/auth', authRoutes)
app.use('/api/users', userRoutes)
app.use('/api/repositories', repositoriesRoutes)
app.use('/api/issues', issuesRoutes)

// {{GENERATED_ROUTES}}

// Error handling
app.use(errorHandler)

export default app
