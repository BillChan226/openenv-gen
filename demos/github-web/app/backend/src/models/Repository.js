import { DataTypes } from 'sequelize'
import { sequelize } from '../config/database.js'

const Repository = sequelize.define('Repository', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true,
  },
  owner_id: {
    type: DataTypes.UUID,
    allowNull: false,
    references: {
      model: 'users',
      key: 'id',
    },
    onDelete: 'CASCADE',
  },
  name: {
    type: DataTypes.STRING(255),
    allowNull: false,
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
  is_private: {
    type: DataTypes.BOOLEAN,
    defaultValue: false,
  },
  default_branch: {
    type: DataTypes.STRING(100),
    defaultValue: 'main',
  },
  language: {
    type: DataTypes.STRING(50),
    allowNull: true,
  },
  stars_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0,
  },
  forks_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0,
  },
  issues_count: {
    type: DataTypes.INTEGER,
    defaultValue: 0,
  },
}, {
  tableName: 'repositories',
  timestamps: true,
  underscored: true,
  indexes: [
    {
      unique: true,
      fields: ['owner_id', 'name'],
    },
  ],
})

export default Repository
