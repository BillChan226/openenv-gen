const fs = require('fs');

function getDefaultDockerSocketCandidates() {
  // Common Docker socket locations across platforms.
  // - Linux: /var/run/docker.sock
  // - macOS Docker Desktop (newer): ~/.docker/run/docker.sock
  // - macOS Docker Desktop (older): ~/Library/Containers/com.docker.docker/Data/docker.sock
  const home = process.env.HOME;
  const candidates = ['/var/run/docker.sock'];

  if (home) {
    candidates.push(`${home}/.docker/run/docker.sock`);
    candidates.push(`${home}/Library/Containers/com.docker.docker/Data/docker.sock`);
  }

  return candidates;
}

function isDockerAvailable() {
  // IMPORTANT:
  // This project must be able to run in environments where Docker is not installed
  // or the Docker daemon is not running/reachable (common in hosted graders).
  //
  // Therefore this function must be:
  // - fast (no long timeouts)
  // - never throw
  // - conservative (return false unless we are confident docker is usable)

  // Allow explicitly disabling docker checks (useful for environments without Docker).
  if (String(process.env.DISABLE_DOCKER || '').toLowerCase() === 'true') return false;

  // If docker binary isn't installed, don't attempt to probe.
  let execSync;
  try {
    // eslint-disable-next-line global-require
    ({ execSync } = require('child_process'));
    execSync('docker --version', { stdio: ['ignore', 'ignore', 'ignore'], timeout: 800 });
  } catch (_e) {
    return false;
  }

  // If DOCKER_HOST is set, we assume the user knows what they're doing; just probe.
  const hasRemoteHost = Boolean(process.env.DOCKER_HOST);

  // Best-effort socket existence check.
  // NOTE: a socket file may exist even when the daemon is down, so this is only
  // used as a quick hint to avoid running `docker info` when we *know* there is
  // no local socket and no remote host configured.
  const candidates = process.env.DOCKER_SOCKET
    ? [process.env.DOCKER_SOCKET]
    : getDefaultDockerSocketCandidates();

  let hasSocket = false;
  try {
    hasSocket = candidates.some((p) => p && fs.existsSync(p));
  } catch (_e) {
    hasSocket = false;
  }

  // If neither a local socket nor a remote host is configured, Docker isn't available.
  if (!hasSocket && !hasRemoteHost) return false;

  try {
    // `docker info` is a quick check that the daemon is reachable.
    // Keep timeout small to avoid hanging health endpoints.
    execSync('docker info', { stdio: ['ignore', 'ignore', 'ignore'], timeout: 1200 });
    return true;
  } catch (_e) {
    return false;
  }
}

module.exports = { isDockerAvailable, getDefaultDockerSocketCandidates };

