const LOG_LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };

function formatMessage(level, message, meta) {
  const timestamp = new Date().toISOString();
  const metaStr = meta ? ` ${JSON.stringify(meta)}` : '';
  return `${timestamp} [${level.toUpperCase()}] ${message}${metaStr}`;
}

export function createLogger(levelName = 'info') {
  const currentLevel = LOG_LEVELS[levelName] ?? LOG_LEVELS.info;
  return {
    error: (msg, meta) => LOG_LEVELS.error <= currentLevel && console.error(formatMessage('error', msg, meta)),
    warn: (msg, meta) => LOG_LEVELS.warn <= currentLevel && console.warn(formatMessage('warn', msg, meta)),
    info: (msg, meta) => LOG_LEVELS.info <= currentLevel && console.log(formatMessage('info', msg, meta)),
    debug: (msg, meta) => LOG_LEVELS.debug <= currentLevel && console.log(formatMessage('debug', msg, meta)),
  };
}
