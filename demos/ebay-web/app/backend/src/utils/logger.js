const LOG_LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };

function getCurrentLevel() {
  const level = process.env.LOG_LEVEL || 'info';
  return LOG_LEVELS[level] ?? LOG_LEVELS.info;
}

function format(level, message, meta) {
  const ts = new Date().toISOString();
  const metaStr = meta ? ` ${JSON.stringify(meta)}` : '';
  return `${ts} [${level.toUpperCase()}] ${message}${metaStr}`;
}

export const logger = {
  error: (msg, meta) => {
    if (LOG_LEVELS.error <= getCurrentLevel()) console.error(format('error', msg, meta));
  },
  warn: (msg, meta) => {
    if (LOG_LEVELS.warn <= getCurrentLevel()) console.warn(format('warn', msg, meta));
  },
  info: (msg, meta) => {
    if (LOG_LEVELS.info <= getCurrentLevel()) console.log(format('info', msg, meta));
  },
  debug: (msg, meta) => {
    if (LOG_LEVELS.debug <= getCurrentLevel()) console.log(format('debug', msg, meta));
  }
};
