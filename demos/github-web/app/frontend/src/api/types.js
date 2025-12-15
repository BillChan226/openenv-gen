/**
 * Type definitions for API responses
 *
 * Helps with code generation and provides clear API contracts.
 * These are JSDoc-style type definitions (no TypeScript needed).
 */

/**
 * @typedef {Object} User
 * @property {string} id
 * @property {string} name
 * @property {string} email
 * @property {string} role - 'admin' | 'user'
 * @property {string} createdAt
 * @property {string} updatedAt
 */

/**
 * @typedef {Object} AuthResponse
 * @property {User} user
 * @property {string} token
 */

/**
 * @typedef {Object} PaginatedResponse
 * @property {Array} data
 * @property {number} total
 * @property {number} page
 * @property {number} perPage
 */

/**
 * @typedef {Object} ErrorResponse
 * @property {string} message
 * @property {Array} [errors]
 */

// {{GENERATED_TYPES}}

export {}
