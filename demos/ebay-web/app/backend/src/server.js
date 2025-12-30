import { createApp } from './app.js';
import { config } from './config/env.js';
import { logger } from './utils/logger.js';

const app = createApp();

app.listen(config.PORT, () => {
  logger.info(`backend listening on :${config.PORT}`, {
    env: config.NODE_ENV,
    demoMode: config.DEMO_MODE
  });
});
