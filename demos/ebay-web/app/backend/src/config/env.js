import dotenv from 'dotenv';

dotenv.config();

const required = ['JWT_SECRET'];
for (const key of required) {
  if (!process.env[key]) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
}

export const config = {
  // Default to 3000 for local dev; override with PORT env var as needed.
  PORT: parseInt(process.env.PORT || '3000', 10),
  NODE_ENV: process.env.NODE_ENV || 'development',
  LOG_LEVEL: process.env.LOG_LEVEL || 'info',

  DATABASE_URL: process.env.DATABASE_URL || '',
  DEMO_MODE: (process.env.DEMO_MODE || 'false').toLowerCase() === 'true',

  JWT_SECRET: process.env.JWT_SECRET,
  JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || '7d',

  FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:5173'
};
