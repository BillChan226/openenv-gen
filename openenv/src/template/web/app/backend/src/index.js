import 'dotenv/config'
import app from './app.js'
import { sequelize } from './config/database.js'

const PORT = process.env.PORT || 5000

async function start() {
  try {
    // Test database connection
    await sequelize.authenticate()
    console.log('Database connected successfully')

    // Sync models (in dev mode)
    if (process.env.NODE_ENV !== 'production') {
      await sequelize.sync({ alter: true })
      console.log('Database synced')
    }

    app.listen(PORT, '0.0.0.0', () => {
      console.log(`Server running on port ${PORT}`)
    })
  } catch (error) {
    console.error('Failed to start server:', error)
    process.exit(1)
  }
}

start()
