import { DataTypes } from 'sequelize'
import { sequelize } from '../config/database.js'

const Star = sequelize.define('Star', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true,
  },
  user_id: {
    type: DataTypes.UUID,
    allowNull: false,
    references: {
      model: 'users',
      key: 'id',
    },
    onDelete: 'CASCADE',
  },
  repository_id: {
    type: DataTypes.UUID,
    allowNull: false,
    references: {
      model: 'repositories',
      key: 'id',
    },
    onDelete: 'CASCADE',
  },
}, {
  tableName: 'stars',
  timestamps: true,
  underscored: true,
  updatedAt: false,
  indexes: [
    {
      unique: true,
      fields: ['user_id', 'repository_id'],
    },
  ],
})

export default Star
