import app from './app.js'
import { sequelize, testConnection } from './config/database.js'

// Import models to register them
import './models/index.js'

const PORT = process.env.PORT || 5001

async function startServer() {
  try {
    // Test database connection
    await testConnection()

    // Sync database models (creates tables if they don't exist)
    // Note: In production, use migrations instead
    await sequelize.sync({ alter: false })
    console.log('✓ Database models synced')

    // Start Express server
    app.listen(PORT, () => {
      console.log(`✓ Backend server running on http://localhost:${PORT}`)
      console.log(`✓ API endpoints: http://localhost:${PORT}/api`)
      console.log(`✓ Health check: http://localhost:${PORT}/api/health`)
    })
  } catch (error) {
    console.error('Failed to start server:', error)
    process.exit(1)
  }
}

startServer()
