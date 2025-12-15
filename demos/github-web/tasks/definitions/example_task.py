"""Example task definitions for {{ENV_NAME}}.

These serve as templates for generating new tasks.
"""

from typing import Any, Dict, Tuple

from ..base import BaseTask, MultiStepTask, TaskConfig
from ..registry import register_task
from ..validators import PageValidator, DBValidator


@register_task()
class LoginTask(BaseTask):
    """Task: Log in to the application.

    Goal: Navigate to login page and log in with test credentials.
    Success: User is redirected to dashboard.
    """

    config = TaskConfig(
        task_id="login",
        task_name="User Login",
        goal="Log in with email 'user@example.com' and password 'user123'",
        start_url="/login",
        max_steps=10,
        difficulty="easy",
        tags=["authentication", "form"],
    )

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        # Success if redirected to dashboard
        if PageValidator.url_contains(page, "/dashboard"):
            return 1.0, True, "Login successful!"

        # Partial credit for being on login page with email filled
        if PageValidator.element_exists(page, "[data-testid='login-email']"):
            email_filled = PageValidator.element_text_contains(
                page, "[data-testid='login-email']", "user@example.com"
            )
            if email_filled:
                return 0.2, False, "Email entered"

        return 0.0, False, ""


@register_task()
class RegisterTask(BaseTask):
    """Task: Create a new user account.

    Goal: Navigate to registration and create account.
    Success: User account created in database.
    """

    config = TaskConfig(
        task_id="register",
        task_name="User Registration",
        goal="Create a new account with name 'Test User', email 'newuser@example.com', and password 'password123'",
        start_url="/register",
        max_steps=15,
        difficulty="easy",
        tags=["authentication", "form"],
    )

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        # Success if user exists in database
        if DBValidator.record_exists(
            db_state,
            "Users",
            {"email": "newuser@example.com"},
        ):
            return 1.0, True, "Registration successful!"

        # Partial credit for being on dashboard (after successful registration)
        if PageValidator.url_contains(page, "/dashboard"):
            return 0.8, False, "Redirected to dashboard"

        return 0.0, False, ""


@register_task()
class NavigationTask(BaseTask):
    """Task: Navigate to a specific page.

    Goal: Find and navigate to the dashboard.
    Success: Dashboard page is loaded.
    """

    config = TaskConfig(
        task_id="navigate-dashboard",
        task_name="Navigate to Dashboard",
        goal="Navigate to the dashboard page",
        start_url="/",
        max_steps=5,
        difficulty="easy",
        tags=["navigation"],
    )

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        if PageValidator.url_contains(page, "/dashboard"):
            return 1.0, True, "Found dashboard!"
        return 0.0, False, ""


@register_task()
class LoginAndNavigateTask(MultiStepTask):
    """Multi-step task: Login then navigate.

    Demonstrates multi-step task with partial rewards.
    """

    config = TaskConfig(
        task_id="login-and-navigate",
        task_name="Login and Navigate",
        goal="Log in and then navigate to dashboard settings",
        start_url="/login",
        max_steps=20,
        difficulty="medium",
        tags=["authentication", "navigation", "multi-step"],
    )

    subtasks = [
        {"name": "login", "reward": 0.5},
        {"name": "navigate_dashboard", "reward": 0.3},
        {"name": "find_settings", "reward": 0.2},
    ]

    def _check_subtask(
        self,
        index: int,
        page: Any,
        db_state: Dict[str, Any],
    ) -> bool:
        if index == 0:  # login
            return PageValidator.url_contains(page, "/dashboard")
        elif index == 1:  # navigate_dashboard
            return PageValidator.url_contains(page, "/dashboard")
        elif index == 2:  # find_settings
            return PageValidator.url_contains(page, "/settings")
        return False


# {{GENERATED_TASKS}}
