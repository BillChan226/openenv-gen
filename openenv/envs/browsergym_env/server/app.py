"""FastAPI server for the BrowserGym environment.

Uses http_server_sessionworker which provides dedicated worker threads per session
for Playwright/greenlet compatibility.
"""

import os

# Use the sessionworker version for Playwright compatibility
from openenv.core.env_server.http_server_sessionworker import create_app
from browsergym_env.models import BrowserGymAction, BrowserGymObservation
from browsergym_env.server.browsergym_environment import BrowserGymEnvironment

# Get configuration from environment variables
benchmark = os.environ.get("BROWSERGYM_BENCHMARK", "miniwob")
task_name = os.environ.get("BROWSERGYM_TASK_NAME")  # Optional, can be None
headless = os.environ.get("BROWSERGYM_HEADLESS", "true").lower() == "true"
viewport_width = int(os.environ.get("BROWSERGYM_VIEWPORT_WIDTH", "1280"))
viewport_height = int(os.environ.get("BROWSERGYM_VIEWPORT_HEIGHT", "720"))
timeout = float(os.environ.get("BROWSERGYM_TIMEOUT", "10000"))
port = int(os.environ.get("BROWSERGYM_PORT", "8000"))


# Factory function to create BrowserGymEnvironment instances
def create_browsergym_environment():
    """Factory function that creates BrowserGymEnvironment with config."""
    return BrowserGymEnvironment(
        benchmark=benchmark,
        task_name=task_name,
        headless=headless,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        timeout=timeout,
    )


# Create the FastAPI app
# Pass the factory function instead of an instance for WebSocket session support
app = create_app(
    create_browsergym_environment,
    BrowserGymAction,
    BrowserGymObservation,
    env_name="browsergym_env",
)


def main():
    """Main entry point for running the server."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
