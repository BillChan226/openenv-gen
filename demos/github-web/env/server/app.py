"""FastAPI server for the github-web environment.

This environment is registered into BrowserGym as browsergym/github-web.{task_id}.

Usage:
    # Register and use via BrowserGym
    import gymnasium as gym
    from env.server.environment import register_all_tasks

    register_all_tasks()
    env = gym.make("browsergym/github-web.login")
    obs, info = env.reset()
    # ... interact with environment
    env.close()
"""

import os

# Import to trigger auto-registration of tasks
from .environment import register_all_tasks, WebTask

# Configuration from environment variables
APP_URL = os.environ.get("APP_URL", "http://frontend:3000")
API_URL = os.environ.get("API_URL", "http://backend:5000")


def main():
    """Entry point for registering tasks and starting the environment."""
    # Register all tasks from the task registry
    register_all_tasks(app_url=APP_URL, api_url=API_URL)
    print(f"✓ Registered github-web tasks into BrowserGym")
    print(f"✓ App URL: {APP_URL}")
    print(f"✓ API URL: {API_URL}")

    # List registered tasks
    from tasks import list_tasks
    tasks = list_tasks()
    print(f"✓ Available tasks ({len(tasks)}):")
    for task in tasks:
        print(f"  - browsergym/github-web.{task['id']}: {task['goal'][:50]}...")


if __name__ == "__main__":
    main()
