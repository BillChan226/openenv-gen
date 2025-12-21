import { Sequelize } from 'sequelize'

export const sequelize = new Sequelize({
  dialect: 'postgres',
  host: process.env.DB_HOST || 'database',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || '{{ENV_NAME}}_db',
  username: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  logging: process.env.NODE_ENV !== 'production' ? console.log : false,
})

export default sequelize
