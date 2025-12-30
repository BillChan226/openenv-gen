import http from 'http';
import app from './app.js';
import { config } from './config/env.js';
import { createLogger } from './utils/logger.js';
import { waitForDbReady } from './db/pool.js';

const logger = createLogger(config.LOG_LEVEL);

const server = http.createServer(app);

server.listen(config.PORT, async () => {
  logger.info(`Backend listening on port ${config.PORT}`, { env: config.NODE_ENV });

  // Don't block startup; just log readiness. Health endpoint will reflect DB status.
  if (process.env.ALLOW_NO_DB !== '1') {
    void waitForDbReady();
  }
});

server.on('error', (err) => {
  logger.error('Server error', { message: err.message });
  process.exit(1);
});
