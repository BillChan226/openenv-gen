"""Environment implementation for {{ENV_NAME}}.

Wraps the web application with BrowserGym/Playwright for agent interaction.
"""

import os
from typing import Any, Dict, Optional
from uuid import uuid4

import gymnasium as gym
import requests

from openenv_core.env_server.interfaces import Environment

from ..models import WebAction, WebObservation, WebState


class WebEnvironment(Environment):
    """Web environment implementation using BrowserGym.

    This environment wraps the generated web application and provides:
    - Browser automation via Playwright
    - Task management and reward computation
    - Database state access for validation

    Attributes:
        app_url: URL of the web application frontend
        api_url: URL of the backend API
        task_registry: Registry of available tasks
    """

    def __init__(
        self,
        app_url: str = "http://frontend:3000",
        api_url: str = "http://backend:5000",
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        timeout: float = 10000.0,
        task_name: Optional[str] = None,
    ):
        """Initialize the web environment.

        Args:
            app_url: Frontend application URL
            api_url: Backend API URL
            headless: Run browser in headless mode
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            timeout: Action timeout in milliseconds
            task_name: Initial task to load
        """
        super().__init__()

        self.app_url = app_url
        self.api_url = api_url
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.timeout = timeout
        self.task_name = task_name

        # Import task registry
        from tasks import get_task_class

        self.get_task_class = get_task_class

        # Initialize BrowserGym environment
        self._init_browser_env()

        # State tracking
        self._state = WebState(
            episode_id=str(uuid4()),
            step_count=0,
            task_name=task_name or "",
        )

        self._current_task = None
        self._last_obs: Optional[Dict[str, Any]] = None

    def _init_browser_env(self):
        """Initialize the Playwright browser environment."""
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(
                viewport={"width": self.viewport_width, "height": self.viewport_height}
            )
            self._page = self._context.new_page()
            self._page.set_default_timeout(self.timeout)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize browser: {e}")

    def reset(
        self,
        seed: Optional[int] = None,
        task_name: Optional[str] = None,
    ) -> WebObservation:
        """Reset the environment for a new episode.

        Args:
            seed: Random seed for reproducibility
            task_name: Task to load (overrides default)

        Returns:
            Initial observation
        """
        # Reset database state via API
        self._reset_database()

        # Get task
        task_name = task_name or self.task_name
        if task_name:
            task_class = self.get_task_class(task_name)
            self._current_task = task_class()
            goal = self._current_task.goal
        else:
            self._current_task = None
            goal = "Explore the application"

        # Reset state
        self._state = WebState(
            episode_id=str(uuid4()),
            step_count=0,
            task_name=task_name or "",
            goal=goal,
        )

        # Navigate to start page
        start_url = self._current_task.start_url if self._current_task else self.app_url
        self._page.goto(start_url)

        # Create initial observation
        return self._create_observation(done=False, reward=0.0)

    def step(self, action: WebAction) -> WebObservation:
        """Execute an action in the environment.

        Args:
            action: Action to execute

        Returns:
            Observation after the action
        """
        self._state.step_count += 1

        try:
            # Execute the action
            action_str = action.to_action_str()
            self._execute_action(action_str)

            # Check task completion and compute reward
            reward = 0.0
            done = False

            if self._current_task:
                reward, done, _ = self._current_task.validate(
                    page=self._page,
                    db_state=self._get_db_state(),
                )
                self._state.cum_reward += reward

            # Check max steps
            if self._state.max_steps and self._state.step_count >= self._state.max_steps:
                done = True

            return self._create_observation(done=done, reward=reward)

        except Exception as e:
            return self._create_observation(
                done=False,
                reward=0.0,
                error=str(e),
                last_action_error=True,
            )

    def _execute_action(self, action_str: str):
        """Execute a BrowserGym-style action string."""
        import re

        # Parse action string
        match = re.match(r"(\w+)\((.*)?\)", action_str)
        if not match:
            return

        action_type = match.group(1)
        args_str = match.group(2) or ""

        # Parse arguments
        args = []
        if args_str:
            # Simple argument parsing (handles quoted strings)
            for arg in re.findall(r"'([^']*)'|\"([^\"]*)\"|(\S+)", args_str):
                args.append(next(a for a in arg if a))

        # Execute action
        if action_type == "click":
            selector = args[0] if args else None
            if selector:
                self._page.click(f"[data-testid='{selector}']")
        elif action_type in ("type", "fill"):
            selector = args[0] if len(args) > 0 else None
            text = args[1] if len(args) > 1 else ""
            if selector:
                self._page.fill(f"[data-testid='{selector}']", text)
        elif action_type == "goto":
            url = args[0] if args else self.app_url
            self._page.goto(url)
        elif action_type == "scroll":
            direction = args[0] if args else "down"
            delta = 300 if direction == "down" else -300
            self._page.mouse.wheel(0, delta)
        elif action_type == "press":
            key = args[0] if args else "Enter"
            self._page.keyboard.press(key)
        elif action_type == "noop":
            pass
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def _create_observation(
        self,
        done: bool,
        reward: float,
        error: str = "",
        last_action_error: bool = False,
    ) -> WebObservation:
        """Create observation from current page state."""
        # Get page content
        url = self._page.url
        html = self._page.content()

        # Get accessibility tree
        try:
            axtree = self._page.accessibility.snapshot()
            axtree_txt = str(axtree) if axtree else ""
        except Exception:
            axtree_txt = ""

        # Get screenshot
        try:
            screenshot_bytes = self._page.screenshot()
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(screenshot_bytes))
            screenshot = [[[int(c) for c in pixel] for pixel in row] for row in list(img.getdata())]
            # Reshape to [height, width, channels]
            width, height = img.size
            screenshot = [screenshot[i * width:(i + 1) * width] for i in range(height)]
        except Exception:
            screenshot = None

        # Update state
        self._state.current_url = url
        self._state.db_state = self._get_db_state()

        return WebObservation(
            text=axtree_txt,
            url=url,
            screenshot=screenshot,
            goal=self._state.goal,
            html=html,
            axtree_txt=axtree_txt,
            error=error,
            last_action_error=last_action_error,
            done=done,
            reward=reward,
            metadata={
                "episode_id": self._state.episode_id,
                "step_count": self._state.step_count,
            },
        )

    def _reset_database(self):
        """Reset database to initial state via API."""
        try:
            response = requests.post(f"{self.api_url}/api/admin/reset")
            response.raise_for_status()
        except Exception:
            pass  # API might not have reset endpoint yet

    def _get_db_state(self) -> Dict[str, Any]:
        """Get current database state for validation."""
        try:
            response = requests.get(f"{self.api_url}/api/admin/state")
            if response.ok:
                return response.json()
        except Exception:
            pass
        return {}

    @property
    def state(self) -> WebState:
        """Get current environment state."""
        return self._state

    def close(self):
        """Clean up resources."""
        try:
            self._page.close()
            self._context.close()
            self._browser.close()
            self._playwright.stop()
        except Exception:
            pass
