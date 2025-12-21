"""GitHub-specific task definitions for github-web environment.

These tasks test various GitHub workflows like login, creating repos, starring, etc.
"""

from typing import Any, Dict, Tuple

from ..base import BaseTask, MultiStepTask, TaskConfig
from ..registry import register_task
from ..validators import PageValidator, DBValidator


@register_task()
class LoginTask(BaseTask):
    """Task: Log in to GitHub.

    Goal: Log in with test user credentials.
    Success: User is redirected to dashboard.
    """

    config = TaskConfig(
        task_id="login",
        task_name="GitHub Login",
        goal="Log in with email 'test@example.com' and password 'test123'",
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
            return 0.0, False, ""

        return 0.0, False, ""


@register_task()
class RegisterTask(BaseTask):
    """Task: Create a new GitHub account.

    Goal: Register a new user.
    Success: User account created and redirected.
    """

    config = TaskConfig(
        task_id="register",
        task_name="GitHub Registration",
        goal="Create a new account with name 'New User', username 'newuser', email 'newuser@example.com', and password 'password123'",
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
        # Success if redirected to dashboard after registration
        if PageValidator.url_contains(page, "/dashboard"):
            return 1.0, True, "Registration successful!"

        return 0.0, False, ""


@register_task()
class ViewRepositoryTask(BaseTask):
    """Task: Navigate to view a specific repository.

    Goal: Find and view the octocat/Hello-World repository.
    Success: Repository page is loaded.
    """

    config = TaskConfig(
        task_id="view-repository",
        task_name="View Repository",
        goal="Navigate to the octocat/Hello-World repository page",
        start_url="/",
        max_steps=10,
        difficulty="easy",
        tags=["navigation", "repository"],
    )

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        if PageValidator.url_contains(page, "/octocat/Hello-World"):
            return 1.0, True, "Found the repository!"
        return 0.0, False, ""


@register_task()
class CreateRepositoryTask(BaseTask):
    """Task: Create a new repository.

    Goal: Log in and create a new repository.
    Success: New repository exists in database.
    """

    config = TaskConfig(
        task_id="create-repository",
        task_name="Create Repository",
        goal="Log in as testuser (test@example.com / test123) and create a new public repository named 'my-new-repo' with description 'A test repository'",
        start_url="/login",
        max_steps=25,
        difficulty="medium",
        tags=["authentication", "repository", "form"],
    )

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        # Check if on a repository page with the new repo name
        if "/my-new-repo" in page.url:
            return 1.0, True, "Repository created!"

        # Partial credit for reaching new repo form
        if PageValidator.url_contains(page, "/new"):
            return 0.3, False, "On new repository form"

        # Partial credit for logging in
        if PageValidator.url_contains(page, "/dashboard"):
            return 0.2, False, "Logged in successfully"

        return 0.0, False, ""


@register_task()
class ViewIssuesTask(BaseTask):
    """Task: Navigate to view issues of a repository.

    Goal: View the issues list for Hello-World repository.
    Success: Issues page is displayed.
    """

    config = TaskConfig(
        task_id="view-issues",
        task_name="View Repository Issues",
        goal="Navigate to the issues page of octocat/Hello-World repository",
        start_url="/",
        max_steps=10,
        difficulty="easy",
        tags=["navigation", "issues"],
    )

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        if PageValidator.url_contains(page, "/octocat/Hello-World/issues"):
            return 1.0, True, "Found the issues page!"

        # Partial credit for finding the repository
        if PageValidator.url_contains(page, "/octocat/Hello-World"):
            return 0.5, False, "Found the repository"

        return 0.0, False, ""


@register_task()
class ViewIssueDetailTask(BaseTask):
    """Task: View a specific issue.

    Goal: Navigate to view issue #1 of Hello-World.
    Success: Issue detail page is displayed.
    """

    config = TaskConfig(
        task_id="view-issue",
        task_name="View Issue Detail",
        goal="Navigate to issue #1 'Add README badges' in the octocat/Hello-World repository",
        start_url="/",
        max_steps=15,
        difficulty="easy",
        tags=["navigation", "issues"],
    )

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        if PageValidator.url_contains(page, "/octocat/Hello-World/issues/1"):
            return 1.0, True, "Found the issue!"

        # Partial credit for finding issues list
        if PageValidator.url_contains(page, "/octocat/Hello-World/issues"):
            return 0.5, False, "Found issues list"

        return 0.0, False, ""


@register_task()
class CreateIssueTask(BaseTask):
    """Task: Create a new issue.

    Goal: Create a new issue in a repository.
    Success: Issue is created.
    """

    config = TaskConfig(
        task_id="create-issue",
        task_name="Create Issue",
        goal="Log in as testuser (test@example.com / test123) and create a new issue in octocat/Hello-World with title 'Bug report' and body 'Found a bug in the code'",
        start_url="/login",
        max_steps=30,
        difficulty="medium",
        tags=["authentication", "issues", "form"],
    )

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        # Check if on an issue detail page (new issue created)
        if "/issues/" in page.url and "/new" not in page.url:
            if PageValidator.url_contains(page, "/octocat/Hello-World/issues/"):
                return 1.0, True, "Issue created!"

        # Partial credit for reaching new issue form
        if PageValidator.url_contains(page, "/issues/new"):
            return 0.4, False, "On new issue form"

        # Partial credit for finding issues page
        if PageValidator.url_contains(page, "/octocat/Hello-World/issues"):
            return 0.3, False, "On issues page"

        # Partial credit for logging in
        if PageValidator.url_contains(page, "/dashboard"):
            return 0.1, False, "Logged in"

        return 0.0, False, ""


@register_task()
class ExploreRepositoriesTask(BaseTask):
    """Task: Explore public repositories.

    Goal: Browse and explore available repositories.
    Success: View at least 3 different repository pages.
    """

    config = TaskConfig(
        task_id="explore-repositories",
        task_name="Explore Repositories",
        goal="Browse the home page and explore different repositories. Visit at least 3 different repository pages.",
        start_url="/",
        max_steps=20,
        difficulty="easy",
        tags=["navigation", "exploration"],
    )

    def __init__(self):
        super().__init__()
        self._visited_repos = set()

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        url = page.url

        # Check if on a repository page (pattern: /owner/repo)
        parts = url.split("/")
        if len(parts) >= 4 and parts[1] and parts[2]:
            # Avoid issues/new pages
            if "issues" not in url and "new" not in url:
                repo_path = f"{parts[1]}/{parts[2]}"
                if repo_path not in ["login", "register", "dashboard"]:
                    self._visited_repos.add(repo_path)

        visited_count = len(self._visited_repos)
        if visited_count >= 3:
            return 1.0, True, f"Explored {visited_count} repositories!"

        return visited_count / 3.0, False, f"Visited {visited_count}/3 repositories"


@register_task()
class LoginAndCreateRepoTask(MultiStepTask):
    """Multi-step task: Login and create a repository.

    Demonstrates multi-step task with partial rewards.
    """

    config = TaskConfig(
        task_id="login-create-repo",
        task_name="Login and Create Repository",
        goal="Log in as testuser and create a new repository named 'workflow-test'",
        start_url="/login",
        max_steps=30,
        difficulty="medium",
        tags=["authentication", "repository", "multi-step"],
    )

    subtasks = [
        {"name": "login", "reward": 0.3},
        {"name": "navigate_new", "reward": 0.3},
        {"name": "create_repo", "reward": 0.4},
    ]

    def _check_subtask(
        self,
        index: int,
        page: Any,
        db_state: Dict[str, Any],
    ) -> bool:
        if index == 0:  # login
            return PageValidator.url_contains(page, "/dashboard")
        elif index == 1:  # navigate to new repo page
            return PageValidator.url_contains(page, "/new")
        elif index == 2:  # create repo
            return "/workflow-test" in page.url
        return False
