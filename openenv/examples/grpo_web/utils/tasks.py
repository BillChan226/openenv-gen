"""
MiniWoB++ Task Definitions and Curriculum Learning

This module provides the complete task lists for MiniWoB++ benchmark,
organized by category and difficulty for curriculum learning strategies.

Total tasks: ~125 tasks across multiple categories
"""

from typing import Dict, List, Optional, Tuple


# =============================================================================
# ORIGINAL MINIWOB TASKS (74 tasks)
# =============================================================================

MINIWOB_ORIGINAL_TASKS = [
    "bisect-angle",
    "book-flight",
    "choose-date",
    "choose-list",
    "circle-center",
    "click-button",
    "click-button-sequence",
    "click-checkboxes",
    "click-collapsible",
    "click-collapsible-2",
    "click-color",
    "click-dialog",
    "click-dialog-2",
    "click-link",
    "click-menu",
    "click-menu-2",
    "click-option",
    "click-pie",
    "click-scroll-list",
    "click-shades",
    "click-shape",
    "click-tab",
    "click-tab-2",
    "click-test",
    "click-test-2",
    "click-widget",
    "copy-paste",
    "copy-paste-2",
    "count-shape",
    "count-sides",
    "drag-box",
    "drag-circle",
    "drag-cube",
    "drag-items",
    "drag-items-grid",
    "drag-shapes",
    "drag-sort-numbers",
    "email-inbox",
    "enter-date",
    "enter-password",
    "enter-text",
    "enter-text-2",
    "enter-text-dynamic",
    "enter-time",
    "find-midpoint",
    "find-word",
    "focus-text",
    "focus-text-2",
    "grid-coordinate",
    "guess-number",
    "highlight-text",
    "highlight-text-2",
    "identify-shape",
    "login-user",
    "navigate-tree",
    "number-checkboxes",
    "read-table",
    "read-table-2",
    "resize-textarea",
    "right-angle",
    "scroll-text",
    "scroll-text-2",
    "search-engine",
    "simple-algebra",
    "simple-arithmetic",
    "social-media",
    "terminal",
    "text-editor",
    "text-transform",
    "tic-tac-toe",
    "use-autocomplete",
    "use-colorwheel",
    "use-colorwheel-2",
    "use-slider",
    "use-slider-2",
    "use-spinner",
    "visual-addition",
]

# =============================================================================
# NO-DELAY TASKS (6 tasks)
# =============================================================================
# Tasks without animation delays for more stable training

MINIWOB_NODELAY_TASKS = [
    "book-flight-nodelay",
    "choose-date-nodelay",
    "click-collapsible-nodelay",
    "click-collapsible-2-nodelay",
    "click-pie-nodelay",
    "use-autocomplete-nodelay",
]

# =============================================================================
# ADDITIONAL TASKS (MiniWoB++) (9 tasks)
# =============================================================================
# Harder versions and new tasks introduced in MiniWoB++

MINIWOB_ADDITIONAL_TASKS = [
    "click-checkboxes-large",
    "click-checkboxes-soft",
    "click-checkboxes-transfer",
    "click-tab-2-hard",
    "login-user-popup",
    "multi-layouts",
    "multi-orderings",
    "social-media-all",
    "social-media-some",
    "email-inbox-forward-nl",
    "email-inbox-forward-nl-turk",
    "email-inbox-nl-turk",
]

# =============================================================================
# DEBUG TASKS (13 tasks)
# =============================================================================
# Easier versions suitable for debugging and initial training

MINIWOB_DEBUG_TASKS = [
    "choose-date-easy",
    "choose-date-medium",
    "click-tab-2-easy",
    "click-tab-2-medium",
    "click-test-transfer",
    "email-inbox-delete",
    "email-inbox-forward",
    "email-inbox-important",
    "email-inbox-noscroll",
    "email-inbox-reply",
    "email-inbox-star-reply",
    "unicode-test",
]

# =============================================================================
# FLIGHT SEARCH TASKS (3 tasks)
# =============================================================================
# Ports of FormWoB tasks from original World of Bits paper

MINIWOB_FLIGHT_TASKS = [
    "flight.Alaska",
    "flight.Alaska-auto",
    "flight.AA",
]

# =============================================================================
# HIDDEN TEST TASKS (18 tasks)
# =============================================================================
# Tasks intended for evaluation, originally not available from OpenAI

MINIWOB_HIDDEN_TEST_TASKS = [
    "ascending-numbers",
    "buy-ticket",
    "daily-calendar",
    "drag-single-shape",
    "drag-shapes-2",
    "draw-circle",
    "draw-line",
    "find-greatest",
    "form-sequence",
    "form-sequence-2",
    "form-sequence-3",
    "generate-number",
    "hot-cold",
    "odd-or-even",
    "order-food",
    "phone-book",
    "sign-agreement",
    "stock-market",
]

# =============================================================================
# DIFFICULTY-BASED TASK LISTS
# =============================================================================

# Easy tasks - single step or very simple interactions
MINIWOB_EASY_TASKS = [
    # Click tasks (single click)
    "click-test",
    "click-test-2",
    "click-button",
    "click-link",
    "click-dialog",
    "click-dialog-2",
    "click-option",
    "click-color",
    "click-shape",
    # Focus/input tasks (single action)
    "focus-text",
    "focus-text-2",
    "enter-text",
    "enter-text-2",
    "enter-text-dynamic",
    "enter-password",
    # Simple math
    "simple-arithmetic",
    "simple-algebra",
    # Debug/easy versions
    "click-tab-2-easy",
    "click-tab-2-medium",
    "choose-date-easy",
    "choose-date-medium",
    "click-test-transfer",
    "unicode-test",
]

# Medium tasks - require multiple steps or more precise interactions
MINIWOB_MEDIUM_TASKS = [
    # Multi-element selection
    "click-checkboxes",
    "click-checkboxes-large",
    "click-checkboxes-soft",
    "click-checkboxes-transfer",
    "click-button-sequence",
    # Dropdown/menu selection
    "choose-list",
    "click-menu",
    "click-menu-2",
    # Visual tasks
    "click-pie",
    "click-pie-nodelay",
    "click-shades",
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
    "click-tab-2-hard",
    # Widget interaction
    "click-widget",
    "click-collapsible",
    "click-collapsible-2",
    "click-collapsible-nodelay",
    "click-collapsible-2-nodelay",
    "resize-textarea",
    "text-transform",
    "text-editor",
    # Copy/paste
    "copy-paste",
    "copy-paste-2",
    # Form fields
    "enter-date",
    "enter-time",
    "guess-number",
    # Reading tasks
    "read-table",
    "read-table-2",
    "find-word",
    "highlight-text",
    "highlight-text-2",
    # Email tasks (simpler versions)
    "email-inbox-delete",
    "email-inbox-important",
    "email-inbox-reply",
    "email-inbox-star-reply",
    "email-inbox-noscroll",
    # Slider/spinner
    "use-slider",
    "use-slider-2",
    "use-spinner",
    # Autocomplete
    "use-autocomplete",
    "use-autocomplete-nodelay",
    # Colorwheel
    "use-colorwheel",
    "use-colorwheel-2",
    # Drag tasks (simple)
    "drag-box",
    "drag-circle",
    "drag-single-shape",
]

# Hard tasks - complex multi-step reasoning and navigation
MINIWOB_HARD_TASKS = [
    # Multi-step forms
    "book-flight",
    "book-flight-nodelay",
    "multi-layouts",
    "multi-orderings",
    "form-sequence",
    "form-sequence-2",
    "form-sequence-3",
    # Date pickers
    "choose-date",
    "choose-date-nodelay",
    # Login flows
    "login-user",
    "login-user-popup",
    # Email (complex versions)
    "email-inbox",
    "email-inbox-forward",
    "email-inbox-forward-nl",
    "email-inbox-forward-nl-turk",
    "email-inbox-nl-turk",
    # Tree navigation
    "navigate-tree",
    # Search
    "search-engine",
    # Social media
    "social-media",
    "social-media-all",
    "social-media-some",
    # Terminal/Command line
    "terminal",
    # Games
    "tic-tac-toe",
    # Visual reasoning
    "visual-addition",
    "bisect-angle",
    "circle-center",
    "right-angle",
    "find-midpoint",
    # Grid/table tasks
    "grid-coordinate",
    "number-checkboxes",
    # Drawing
    "draw-line",
    "draw-circle",
    # Drag tasks (complex)
    "drag-cube",
    "drag-items",
    "drag-items-grid",
    "drag-shapes",
    "drag-shapes-2",
    "drag-sort-numbers",
    # Hidden test tasks
    "ascending-numbers",
    "buy-ticket",
    "daily-calendar",
    "find-greatest",
    "generate-number",
    "hot-cold",
    "odd-or-even",
    "order-food",
    "phone-book",
    "sign-agreement",
    "stock-market",
    # Flight tasks
    "flight.Alaska",
    "flight.Alaska-auto",
    "flight.AA",
]

# =============================================================================
# ALL TASKS COMBINED
# =============================================================================

MINIWOB_ALL_TASKS = (
    MINIWOB_ORIGINAL_TASKS
    + MINIWOB_NODELAY_TASKS
    + MINIWOB_ADDITIONAL_TASKS
    + MINIWOB_DEBUG_TASKS
    + MINIWOB_FLIGHT_TASKS
    + MINIWOB_HIDDEN_TEST_TASKS
)

# Deduplicated list (some tasks appear in multiple categories)
MINIWOB_ALL_TASKS_UNIQUE = sorted(list(set(MINIWOB_ALL_TASKS)))

# =============================================================================
# TASK METADATA
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
        "description": "Click on a specific button in a generated form",
        "expected_steps": 1,
        "skills": ["click", "text-matching"],
    },
    "enter-text": {
        "difficulty": "easy",
        "description": "Enter given text to a textfield",
        "expected_steps": 1,
        "skills": ["fill", "text-input"],
    },
    "login-user": {
        "difficulty": "hard",
        "description": "Enter user login details into the form",
        "expected_steps": 3,
        "skills": ["fill", "click", "form-completion"],
    },
    "book-flight": {
        "difficulty": "hard",
        "description": "Search for flight results",
        "expected_steps": 8,
        "skills": ["fill", "select", "click", "date-picker", "multi-step"],
    },
    "email-inbox": {
        "difficulty": "hard",
        "description": "Navigate through an email inbox and perform some actions",
        "expected_steps": 5,
        "skills": ["click", "scroll", "read", "multi-step"],
    },
    "navigate-tree": {
        "difficulty": "hard",
        "description": "Navigate a file tree to find a specified file or folder",
        "expected_steps": 4,
        "skills": ["click", "tree-navigation"],
    },
    "tic-tac-toe": {
        "difficulty": "hard",
        "description": "Win a game of tic-tac-toe",
        "expected_steps": 5,
        "skills": ["click", "game-strategy"],
    },
    "drag-sort-numbers": {
        "difficulty": "hard",
        "description": "Drag numbers into sorted ascending order",
        "expected_steps": 6,
        "skills": ["drag", "sorting"],
    },
}


# =============================================================================
# CURRICULUM LEARNING UTILITIES
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
            - "category": Original -> Additional -> Hidden
            - "skill": Group by required skills
            - "random": Random ordering
        num_stages: Number of curriculum stages

    Returns:
        List of task lists for each stage
    """
    if strategy == "difficulty":
        return [MINIWOB_EASY_TASKS, MINIWOB_MEDIUM_TASKS, MINIWOB_HARD_TASKS]

    elif strategy == "category":
        return [
            MINIWOB_ORIGINAL_TASKS,
            MINIWOB_ADDITIONAL_TASKS + MINIWOB_DEBUG_TASKS,
            MINIWOB_HIDDEN_TEST_TASKS + MINIWOB_FLIGHT_TASKS,
        ]

    elif strategy == "skill":
        # Group by primary skill
        click_tasks = [t for t in MINIWOB_ALL_TASKS_UNIQUE if "click" in t]
        form_tasks = [t for t in MINIWOB_ALL_TASKS_UNIQUE if any(k in t for k in ["enter", "login", "email", "form"])]
        nav_tasks = [t for t in MINIWOB_ALL_TASKS_UNIQUE if any(k in t for k in ["navigate", "scroll", "tab", "drag"])]
        other_tasks = [t for t in MINIWOB_ALL_TASKS_UNIQUE if t not in click_tasks + form_tasks + nav_tasks]
        return [click_tasks, form_tasks, nav_tasks + other_tasks]

    elif strategy == "random":
        import random
        tasks = MINIWOB_ALL_TASKS_UNIQUE.copy()
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
        skill: Skill name (e.g., "click", "fill", "scroll", "drag")

    Returns:
        List of task names requiring that skill
    """
    skill_lower = skill.lower()

    if skill_lower == "click":
        return [t for t in MINIWOB_ALL_TASKS_UNIQUE if "click" in t]
    elif skill_lower == "fill" or skill_lower == "type" or skill_lower == "enter":
        return [t for t in MINIWOB_ALL_TASKS_UNIQUE if any(k in t for k in ["enter", "text", "password", "login"])]
    elif skill_lower == "scroll":
        return [t for t in MINIWOB_ALL_TASKS_UNIQUE if "scroll" in t]
    elif skill_lower == "select" or skill_lower == "choose":
        return [t for t in MINIWOB_ALL_TASKS_UNIQUE if any(k in t for k in ["choose", "option", "checkbox", "select"])]
    elif skill_lower == "navigate":
        return [t for t in MINIWOB_ALL_TASKS_UNIQUE if any(k in t for k in ["navigate", "tab", "tree", "menu"])]
    elif skill_lower == "drag":
        return [t for t in MINIWOB_ALL_TASKS_UNIQUE if "drag" in t]
    elif skill_lower == "form":
        return [t for t in MINIWOB_ALL_TASKS_UNIQUE if any(k in t for k in ["form", "login", "email", "book"])]
    else:
        return []


def get_tasks_by_category(category: str) -> List[str]:
    """
    Get tasks by category.

    Args:
        category: Category name (original, nodelay, additional, debug, flight, hidden)

    Returns:
        List of task names in that category
    """
    category_lower = category.lower()

    category_map = {
        "original": MINIWOB_ORIGINAL_TASKS,
        "nodelay": MINIWOB_NODELAY_TASKS,
        "no-delay": MINIWOB_NODELAY_TASKS,
        "additional": MINIWOB_ADDITIONAL_TASKS,
        "debug": MINIWOB_DEBUG_TASKS,
        "flight": MINIWOB_FLIGHT_TASKS,
        "hidden": MINIWOB_HIDDEN_TEST_TASKS,
        "test": MINIWOB_HIDDEN_TEST_TASKS,
        "easy": MINIWOB_EASY_TASKS,
        "medium": MINIWOB_MEDIUM_TASKS,
        "hard": MINIWOB_HARD_TASKS,
        "all": MINIWOB_ALL_TASKS_UNIQUE,
    }

    return category_map.get(category_lower, [])


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


def get_task_count() -> Dict[str, int]:
    """
    Get count of tasks in each category.

    Returns:
        Dict mapping category name to task count
    """
    return {
        "original": len(MINIWOB_ORIGINAL_TASKS),
        "nodelay": len(MINIWOB_NODELAY_TASKS),
        "additional": len(MINIWOB_ADDITIONAL_TASKS),
        "debug": len(MINIWOB_DEBUG_TASKS),
        "flight": len(MINIWOB_FLIGHT_TASKS),
        "hidden_test": len(MINIWOB_HIDDEN_TEST_TASKS),
        "easy": len(MINIWOB_EASY_TASKS),
        "medium": len(MINIWOB_MEDIUM_TASKS),
        "hard": len(MINIWOB_HARD_TASKS),
        "total_unique": len(MINIWOB_ALL_TASKS_UNIQUE),
    }


# =============================================================================
# WEBARENA TASK CATEGORIES (for future use)
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
