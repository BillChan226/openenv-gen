import { DataTypes } from 'sequelize'
import { sequelize } from '../config/database.js'

const Issue = sequelize.define('Issue', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true,
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
  author_id: {
    type: DataTypes.UUID,
    allowNull: false,
    references: {
      model: 'users',
      key: 'id',
    },
    onDelete: 'CASCADE',
  },
  number: {
    type: DataTypes.INTEGER,
    allowNull: false,
    autoIncrement: true,
  },
  title: {
    type: DataTypes.STRING(500),
    allowNull: false,
  },
  body: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
  state: {
    type: DataTypes.STRING(20),
    defaultValue: 'open',
    validate: {
      isIn: [['open', 'closed']],
    },
  },
  labels: {
    type: DataTypes.ARRAY(DataTypes.TEXT),
    defaultValue: [],
  },
  closed_at: {
    type: DataTypes.DATE,
    allowNull: true,
  },
}, {
  tableName: 'issues',
  timestamps: true,
  underscored: true,
})

export default Issue
