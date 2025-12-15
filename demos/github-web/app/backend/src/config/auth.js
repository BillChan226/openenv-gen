/**
 * Simplified auth for agent training
 *
 * Focus: Form interaction patterns, not production security
 * - No JWT complexity
 * - No password hashing
 * - Simple session tokens
 */

export const authConfig = {
  sessionSecret: 'simple-session-secret',
  sessionExpiry: 24 * 60 * 60 * 1000, // 24 hours

  // Predefined test users (passwords in plain text for agent training)
  testUsers: [
    { id: '1', email: 'admin@example.com', password: 'admin123', role: 'admin', name: 'Admin User' },
    { id: '2', email: 'user@example.com', password: 'user123', role: 'user', name: 'Test User' },
  ],
}

export default authConfig
