const { execSync } = require('child_process');
const path = require('path');

const { isDockerAvailable } = require('./dockerCheck');

function safeExec(cmd, opts = {}) {
  try {
    return execSync(cmd, {
      stdio: ['ignore', 'pipe', 'ignore'],
      timeout: 2000,
      encoding: 'utf8',
      ...opts,
    });
  } catch (err) {
    // Surface the error so callers can return a meaningful message.
    return { __error: true, message: err?.message || String(err) };
  }
}

function getComposeProjectRoot() {
  // docker-compose.yml lives in /docker; backend is /app/backend
  return path.join(__dirname, '../../docker');
}

function getRunningServices() {
  const dockerAvailable = isDockerAvailable();
  if (!dockerAvailable) {
    return {
      services: [],
      dockerAvailable,
      mode: 'unavailable',
      error: 'Docker daemon not reachable (docker.sock).',
    };
  }

  const cwd = getComposeProjectRoot();

  // Prefer compose v2.
  const outV2 = safeExec('docker compose ps --services --filter status=running', { cwd });
  if (outV2 && !outV2.__error) {
    const services = outV2
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);
    return { services, dockerAvailable, mode: 'docker-compose-v2' };
  }

  // Fallback to legacy docker-compose.
  const outV1 = safeExec('docker-compose ps --services --filter status=running', { cwd });
  if (outV1 && !outV1.__error) {
    const services = outV1
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);
    return { services, dockerAvailable, mode: 'docker-compose-v1' };
  }

  const errMsg =
    (outV2 && outV2.__error && outV2.message) ||
    (outV1 && outV1.__error && outV1.message) ||
    'Docker CLI present but compose commands failed.';

  return {
    services: [],
    dockerAvailable,
    mode: 'docker-present-but-inaccessible',
    error: errMsg,
  };
}

module.exports = { getRunningServices };
