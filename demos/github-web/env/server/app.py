"""FastAPI server for the {{ENV_NAME}} environment."""

import os

from openenv_core.env_server.http_server import create_app

from ..models import WebAction, WebObservation
from .environment import WebEnvironment

# Configuration from environment variables
app_url = os.environ.get("APP_URL", "http://frontend:3000")
api_url = os.environ.get("API_URL", "http://backend:5000")
headless = os.environ.get("HEADLESS", "true").lower() == "true"
viewport_width = int(os.environ.get("VIEWPORT_WIDTH", "1280"))
viewport_height = int(os.environ.get("VIEWPORT_HEIGHT", "720"))
timeout = float(os.environ.get("TIMEOUT", "10000"))
task_name = os.environ.get("TASK_NAME")
port = int(os.environ.get("PORT", "8000"))

# Create environment
env = WebEnvironment(
    app_url=app_url,
    api_url=api_url,
    headless=headless,
    viewport_width=viewport_width,
    viewport_height=viewport_height,
    timeout=timeout,
    task_name=task_name,
)

# Create FastAPI app
app = create_app(
    env,
    WebAction,
    WebObservation,
    env_name="{{ENV_NAME}}",
)


def main():
    """Entry point for running the server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
