import dotenv from 'dotenv';

/* eslint-disable no-undef */


dotenv.config();

export const env = {
  NODE_ENV: process.env.NODE_ENV || 'development',
  PORT: Number(process.env.PORT || 3000),
  // If DATABASE_URL is not provided, backend will automatically fall back to an in-memory DB.
  DATABASE_URL: process.env.DATABASE_URL || '',
  // Force DB mode: 'postgres' | 'memory'
  DB_MODE: process.env.DB_MODE || '',
  JWT_SECRET: process.env.JWT_SECRET || 'dev_secret_change_me',
  CORS_ORIGIN: process.env.CORS_ORIGIN || '*'
};
