import { DataTypes } from 'sequelize'
import { sequelize } from '../config/database.js'

const IssueComment = sequelize.define('IssueComment', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true,
  },
  issue_id: {
    type: DataTypes.UUID,
    allowNull: false,
    references: {
      model: 'issues',
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
  body: {
    type: DataTypes.TEXT,
    allowNull: false,
  },
}, {
  tableName: 'issue_comments',
  timestamps: true,
  underscored: true,
})

export default IssueComment
