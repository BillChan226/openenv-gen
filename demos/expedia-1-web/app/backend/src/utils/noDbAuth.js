const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

// Extremely small in-memory auth fallback for local/dev environments where Postgres
// isn't running. This is ONLY enabled when ALLOW_NO_DB_AUTH=true.
//
// It supports:
// - POST /api/auth/register
// - POST /api/auth/login
// - GET  /api/auth/me
// - GET  /api/me (via server alias)
//
// NOTE: Data is not persisted across restarts.

const usersByEmail = new Map();

function isEnabled() {
  return String(process.env.ALLOW_NO_DB_AUTH || '').toLowerCase() === 'true';
}

function signToken(user) {
  const expiresIn = Number(process.env.JWT_EXPIRES_IN_SECONDS || 7200);
  const token = jwt.sign(
    { email: user.email },
    process.env.JWT_SECRET || 'dev_secret',
    {
      subject: user.id,
      issuer: process.env.JWT_ISSUER || 'voyager',
      audience: process.env.JWT_AUDIENCE || 'voyager-web',
      expiresIn,
    }
  );
  return { token, expiresIn };
}

function sanitizeUser(user) {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    phone: user.phone ?? null,
    created_at: user.created_at,
    updated_at: user.updated_at,
  };
}

async function register({ email, password, name, phone }) {
  if (usersByEmail.has(email)) {
    const err = new Error('Email is already registered');
    err.status = 409;
    err.code = 'EMAIL_IN_USE';
    throw err;
  }

  const passwordHash = await bcrypt.hash(password, 10);
  const now = new Date().toISOString();
  const user = {
    id: `local_${Math.random().toString(36).slice(2)}`,
    email,
    passwordHash,
    name,
    phone: phone ?? null,
    created_at: now,
    updated_at: now,
  };
  usersByEmail.set(email, user);

  const { token, expiresIn } = signToken(user);
  return { user: sanitizeUser(user), access_token: token, expires_in: expiresIn };
}

async function login({ email, password }) {
  const user = usersByEmail.get(email);
  if (!user) {
    const err = new Error('Invalid email or password');
    err.status = 401;
    err.code = 'INVALID_CREDENTIALS';
    throw err;
  }

  const ok = await bcrypt.compare(password, user.passwordHash);
  if (!ok) {
    const err = new Error('Invalid email or password');
    err.status = 401;
    err.code = 'INVALID_CREDENTIALS';
    throw err;
  }

  const { token, expiresIn } = signToken(user);
  return { user: sanitizeUser(user), access_token: token, expires_in: expiresIn };
}

function getUserByEmail(email) {
  const user = usersByEmail.get(email);
  return user ? sanitizeUser(user) : null;
}

function me(authUser) {
  // authUser comes from JWT middleware: { id, email }
  if (!authUser?.email) return { user: null };
  const user = getUserByEmail(authUser.email);
  return { user };
}

module.exports = {
  isEnabled,
  register,
  login,
  me,
  getUserByEmail,
  signToken,
};
