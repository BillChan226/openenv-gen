"""
MiniWoB++ Task Definitions and Curriculum Learning

This module provides task lists organized by difficulty and
utilities for curriculum learning strategies.
"""

from typing import Dict, List, Optional, Tuple


# =============================================================================
# Easy Tasks (Start Here)
# =============================================================================
# These tasks involve simple, single-step interactions

MINIWOB_EASY_TASKS = [
    # Click tasks
    "click-test",
    "click-button",
    "click-button-sequence",
    "click-link",
    "click-dialog",
    "click-dialog-2",
    # Focus/input tasks
    "focus-text",
    "focus-text-2",
    "enter-text",
    "enter-text-dynamic",
    "enter-text-2",
    # Simple navigation
    "simple-arithmetic",
    "simple-algebra",
]


# =============================================================================
# Medium Tasks
# =============================================================================
# These tasks require multiple steps or more precise interactions

MINIWOB_MEDIUM_TASKS = [
    # Multi-element selection
    "click-checkboxes",
    "click-checkboxes-large",
    "click-checkboxes-soft",
    "click-checkboxes-transfer",
    # Dropdown/option selection
    "click-option",
    "choose-list",
    # Visual tasks
    "click-pie",
    "click-shades",
    "click-shape",
    "click-color",
    "count-shape",
    "count-sides",
    "identify-shape",
    # Scrolling tasks
    "click-scroll-list",
    "scroll-text",
    "scroll-text-2",
    # Tab navigation
    "click-tab",
    "click-tab-2",
    "click-tab-2-easy",
    "click-tab-2-medium",
    "click-tab-2-hard",
    # Widget interaction
    "click-widget",
    "resize-textarea",
    "text-transform",
    "copy-paste",
    "copy-paste-2",
    # Form fields
    "enter-password",
    "enter-date",
    "enter-time",
    "guess-number",
    # Email tasks (simpler versions)
    "email-inbox",
    "email-inbox-delete",
    "email-inbox-important",
    "email-inbox-reply",
    "email-inbox-star-reply",
    "read-table",
    "read-table-2",
]


# =============================================================================
# Hard Tasks
# =============================================================================
# These require complex multi-step reasoning and navigation

MINIWOB_HARD_TASKS = [
    # Multi-step forms
    "book-flight",
    "book-flight-nodelay",
    # Date pickers
    "choose-date",
    "choose-date-easy",
    "choose-date-medium",
    "choose-date-nodelay",
    # Login flows
    "login-user",
    "login-user-popup",
    # Email (complex versions)
    "email-inbox-forward",
    "email-inbox-forward-nl",
    "email-inbox-forward-nl-turk",
    "email-inbox-nl-turk",
    "email-inbox-noscroll",
    # Tree navigation
    "navigate-tree",
    # Search
    "search-engine",
    "find-word",
    "find-midword",
    # Social media
    "social-media",
    "social-media-all",
    "social-media-some",
    # Terminal/Command line
    "terminal",
    # Games
    "tic-tac-toe",
    "simon-says",
    # Autocomplete
    "use-autocomplete",
    "use-autocomplete-nodelay",
    # Spinner/sliders
    "use-spinner",
    "use-slider",
    "use-slider-2",
    # Visual reasoning
    "visual-addition",
    "bisect-angle",
    "circle-center",
    "right-angle",
    # Grid/table tasks
    "grid-coordinate",
    "number-checkboxes",
    # Drawing
    "draw-line",
    "drag-box",
    "drag-cube",
    "drag-item",
    "drag-items",
    "drag-items-grid",
    "drag-shapes",
    "drag-sort-numbers",
    # Hotkeys
    "hot-cold",
    "unicode-test",
    "multi-layouts",
    "multi-orderings",
]


# =============================================================================
# All Tasks Combined
# =============================================================================

MINIWOB_ALL_TASKS = MINIWOB_EASY_TASKS + MINIWOB_MEDIUM_TASKS + MINIWOB_HARD_TASKS


# =============================================================================
# Task Metadata
# =============================================================================

TASK_METADATA: Dict[str, Dict] = {
    "click-test": {
        "difficulty": "easy",
        "description": "Click on a single button",
        "expected_steps": 1,
        "skills": ["click"],
    },
    "click-button": {
        "difficulty": "easy",
        "description": "Click the button with specified text",
        "expected_steps": 1,
        "skills": ["click", "text-matching"],
    },
    "enter-text": {
        "difficulty": "easy",
        "description": "Type specified text into input field",
        "expected_steps": 1,
        "skills": ["fill", "text-input"],
    },
    "login-user": {
        "difficulty": "hard",
        "description": "Complete login form with username and password",
        "expected_steps": 3,
        "skills": ["fill", "click", "form-completion"],
    },
    "book-flight": {
        "difficulty": "hard",
        "description": "Complete multi-step flight booking form",
        "expected_steps": 8,
        "skills": ["fill", "select", "click", "date-picker", "multi-step"],
    },
    # Add more as needed
}


# =============================================================================
# Curriculum Learning Utilities
# =============================================================================


def get_curriculum(
    strategy: str = "difficulty",
    num_stages: int = 3,
) -> List[List[str]]:
    """
    Get task curriculum based on strategy.

    Args:
        strategy: Curriculum strategy
            - "difficulty": Easy -> Medium -> Hard
            - "skill": Group by required skills
            - "random": Random ordering
        num_stages: Number of curriculum stages

    Returns:
        List of task lists for each stage
    """
    if strategy == "difficulty":
        return [MINIWOB_EASY_TASKS, MINIWOB_MEDIUM_TASKS, MINIWOB_HARD_TASKS]

    elif strategy == "skill":
        # Group by primary skill
        click_tasks = [t for t in MINIWOB_ALL_TASKS if "click" in t]
        form_tasks = [t for t in MINIWOB_ALL_TASKS if any(k in t for k in ["enter", "login", "email"])]
        nav_tasks = [t for t in MINIWOB_ALL_TASKS if any(k in t for k in ["navigate", "scroll", "tab"])]
        other_tasks = [t for t in MINIWOB_ALL_TASKS if t not in click_tasks + form_tasks + nav_tasks]
        return [click_tasks, form_tasks, nav_tasks + other_tasks]

    elif strategy == "random":
        import random
        tasks = MINIWOB_ALL_TASKS.copy()
        random.shuffle(tasks)
        chunk_size = len(tasks) // num_stages
        return [tasks[i:i+chunk_size] for i in range(0, len(tasks), chunk_size)]

    else:
        raise ValueError(f"Unknown curriculum strategy: {strategy}")


def get_task_difficulty(task_name: str) -> str:
    """
    Get difficulty level for a task.

    Args:
        task_name: MiniWoB task name

    Returns:
        Difficulty level: "easy", "medium", or "hard"
    """
    if task_name in MINIWOB_EASY_TASKS:
        return "easy"
    elif task_name in MINIWOB_MEDIUM_TASKS:
        return "medium"
    elif task_name in MINIWOB_HARD_TASKS:
        return "hard"
    else:
        return "unknown"


def get_tasks_by_skill(skill: str) -> List[str]:
    """
    Get tasks that require a specific skill.

    Args:
        skill: Skill name (e.g., "click", "fill", "scroll")

    Returns:
        List of task names requiring that skill
    """
    skill_lower = skill.lower()

    if skill_lower == "click":
        return [t for t in MINIWOB_ALL_TASKS if "click" in t]
    elif skill_lower == "fill" or skill_lower == "type":
        return [t for t in MINIWOB_ALL_TASKS if any(k in t for k in ["enter", "text", "password"])]
    elif skill_lower == "scroll":
        return [t for t in MINIWOB_ALL_TASKS if "scroll" in t]
    elif skill_lower == "select":
        return [t for t in MINIWOB_ALL_TASKS if any(k in t for k in ["choose", "option", "checkbox"])]
    elif skill_lower == "navigate":
        return [t for t in MINIWOB_ALL_TASKS if any(k in t for k in ["navigate", "tab", "tree"])]
    else:
        return []


def suggest_next_tasks(
    completed_tasks: Dict[str, float],
    num_suggestions: int = 5,
) -> List[Tuple[str, str]]:
    """
    Suggest next tasks based on completion performance.

    Strategy:
    1. Find tasks at the "edge" of current ability
    2. Prefer tasks similar to ones with moderate success
    3. Avoid tasks that are too easy (mastered) or too hard (0% success)

    Args:
        completed_tasks: Dict mapping task name -> success rate
        num_suggestions: Number of tasks to suggest

    Returns:
        List of (task_name, reason) tuples
    """
    suggestions = []

    # Find tasks in learning zone (20-80% success)
    learning_zone = [
        (task, rate) for task, rate in completed_tasks.items()
        if 0.2 <= rate <= 0.8
    ]
    learning_zone.sort(key=lambda x: x[1])  # Sort by success rate

    for task, rate in learning_zone[:num_suggestions]:
        suggestions.append((task, f"In learning zone ({rate:.0%} success)"))

    # If not enough, add untried tasks of appropriate difficulty
    if len(suggestions) < num_suggestions:
        # Estimate current skill level
        avg_success = sum(completed_tasks.values()) / len(completed_tasks) if completed_tasks else 0

        if avg_success < 0.3:
            candidate_pool = MINIWOB_EASY_TASKS
        elif avg_success < 0.6:
            candidate_pool = MINIWOB_MEDIUM_TASKS
        else:
            candidate_pool = MINIWOB_HARD_TASKS

        # Add untried tasks
        for task in candidate_pool:
            if task not in completed_tasks and len(suggestions) < num_suggestions:
                suggestions.append((task, "Untried task at appropriate difficulty"))

    return suggestions


# =============================================================================
# Task Categories (for WebArena and other benchmarks)
# =============================================================================

WEBARENA_CATEGORIES = {
    "shopping": {
        "description": "E-commerce tasks (search, add to cart, checkout)",
        "task_ids": list(range(0, 165)),
    },
    "gitlab": {
        "description": "Code repository tasks (create issue, merge request)",
        "task_ids": list(range(165, 330)),
    },
    "reddit": {
        "description": "Social media tasks (post, comment, search)",
        "task_ids": list(range(330, 495)),
    },
    "wikipedia": {
        "description": "Information retrieval tasks",
        "task_ids": list(range(495, 660)),
    },
    "maps": {
        "description": "Geographic navigation tasks",
        "task_ids": list(range(660, 812)),
    },
}


def get_webarena_tasks(category: Optional[str] = None) -> List[int]:
    """
    Get WebArena task IDs.

    Args:
        category: Specific category or None for all

    Returns:
        List of task IDs
    """
    if category is None:
        return list(range(812))
    elif category in WEBARENA_CATEGORIES:
        return WEBARENA_CATEGORIES[category]["task_ids"]
    else:
        raise ValueError(f"Unknown WebArena category: {category}")
