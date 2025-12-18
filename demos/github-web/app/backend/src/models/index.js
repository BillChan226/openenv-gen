import User from './User.js'
import Repository from './Repository.js'
import Star from './Star.js'
import Issue from './Issue.js'
import IssueComment from './IssueComment.js'

// Define associations
// User has many Repositories
User.hasMany(Repository, {
  foreignKey: 'owner_id',
  as: 'repositories',
})
Repository.belongsTo(User, {
  foreignKey: 'owner_id',
  as: 'owner',
})

// User <-> Repository (Stars) many-to-many
User.belongsToMany(Repository, {
  through: Star,
  foreignKey: 'user_id',
  otherKey: 'repository_id',
  as: 'starred_repositories',
})
Repository.belongsToMany(User, {
  through: Star,
  foreignKey: 'repository_id',
  otherKey: 'user_id',
  as: 'stargazers',
})

// Repository has many Issues
Repository.hasMany(Issue, {
  foreignKey: 'repository_id',
  as: 'issues',
})
Issue.belongsTo(Repository, {
  foreignKey: 'repository_id',
  as: 'repository',
})

// User has many Issues
User.hasMany(Issue, {
  foreignKey: 'author_id',
  as: 'authored_issues',
})
Issue.belongsTo(User, {
  foreignKey: 'author_id',
  as: 'author',
})

// Issue has many Comments
Issue.hasMany(IssueComment, {
  foreignKey: 'issue_id',
  as: 'comments',
})
IssueComment.belongsTo(Issue, {
  foreignKey: 'issue_id',
  as: 'issue',
})

// User has many Comments
User.hasMany(IssueComment, {
  foreignKey: 'author_id',
  as: 'authored_comments',
})
IssueComment.belongsTo(User, {
  foreignKey: 'author_id',
  as: 'author',
})

export {
  User,
  Repository,
  Star,
  Issue,
  IssueComment,
}
