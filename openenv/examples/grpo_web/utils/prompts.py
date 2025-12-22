"""
Prompt Formatting and Action Parsing for Web Navigation

This module handles the conversion between web page observations and
text prompts for the language model, as well as parsing model outputs
back into BrowserGym actions.
"""

import re
from typing import List, Optional

# Regular expressions for action parsing
ACTION_PATTERN = re.compile(r"[A-Za-z_]+\s*\(.*?\)", re.DOTALL)
ACTION_PREFIX_RE = re.compile(
    r"^(action|next action|execute|command)\s*[:\-]\s*",
    re.IGNORECASE,
)
# Pattern to match Qwen3 think tags (for chain-of-thought reasoning)
# Matches both closed tags <think>...</think> and unclosed tags <think>...
THINK_TAG_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Pattern for unclosed think tags (when response is truncated)
UNCLOSED_THINK_PATTERN = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)

# BrowserGym action documentation for prompts
BROWSERGYM_ACTIONS = """
Available actions:
- noop()                          : Do nothing (observe the page)
- click('<element_id>')           : Click an element by its BID
- fill('<element_id>', 'text')    : Fill a text field with value
- type('<element_id>', 'text')    : Type text into an element
- select('<element_id>', 'value') : Select dropdown option
- scroll('up'|'down')             : Scroll the page
- goto('url')                     : Navigate to URL
- send_keys('key')                : Send keyboard key (e.g., 'Enter', 'Tab')
- hover('<element_id>')           : Hover over element
- check('<element_id>')           : Check a checkbox
- uncheck('<element_id>')         : Uncheck a checkbox
"""

# Compact action reference for shorter prompts
BROWSERGYM_ACTIONS_COMPACT = """Actions: noop(), click(bid), fill(bid,text), type(bid,text), select(bid,val), scroll(dir), goto(url), send_keys(key), hover(bid)"""


def format_web_prompt(
    step_num: int,
    observation,
    action_history: list,
    tokenizer,
    max_text_chars: int = 4000,
    include_screenshot: bool = False,
    compact: bool = False,
) -> str:
    """
    Format web page observation as text prompt for LLM.

    Creates a structured prompt containing:
    - System instructions with available actions
    - Current goal and URL
    - Page content (accessibility tree or HTML)
    - Previous action history
    - Error feedback if applicable

    Args:
        step_num: Current step number in episode (0-indexed)
        observation: BrowserGymObservation with page content
        action_history: List of previous action strings
        tokenizer: HuggingFace tokenizer with chat template
        max_text_chars: Maximum characters for page content
        include_screenshot: Whether to mention screenshot availability
        compact: Use shorter prompt format

    Returns:
        Formatted prompt string ready for model inference
    """
    actions_ref = BROWSERGYM_ACTIONS_COMPACT if compact else BROWSERGYM_ACTIONS

    system = f"""You are a web navigation agent. Complete the given goal by interacting with web pages.

{actions_ref}

Rules:
1. Output exactly ONE action per turn
2. Use element IDs (BIDs) from the page content - look for [XX] before element names
3. Copy element IDs exactly as shown (e.g., if you see [13] button, use click('13'))
4. If unsure, use noop() to observe
5. Keep reasoning very brief, then output the action"""

    # Extract observation fields
    goal = observation.goal or "(not provided)"
    url = observation.url or "(unknown)"

    # Get page content - prefer accessibility tree for cleaner representation
    page_content = _get_page_content(observation, max_text_chars)

    # Format action history (show last 5 actions)
    history_str = _format_action_history(action_history, max_items=5)

    # Error feedback
    error_note = ""
    if observation.last_action_error:
        error_msg = observation.error if hasattr(observation, 'error') else "Unknown error"
        error_note = f"\n\nWARNING: Last action failed! Error: {error_msg}"

    # Build user message
    if compact:
        user_content = f"""Step {step_num + 1} | Goal: {goal}
URL: {url}
{page_content}
History: {history_str}{error_note}
Action:"""
    else:
        user_content = f"""=== Web Navigation Task (Step {step_num + 1}) ===

GOAL: {goal}

CURRENT URL: {url}

PAGE CONTENT:
{page_content}

PREVIOUS ACTIONS:
{history_str}
{error_note}

What action should I take next? Output exactly one BrowserGym action:"""

    chat = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    return tokenizer.apply_chat_template(
        chat, tokenize=False, add_generation_prompt=True
    )


def format_web_prompt_with_cot(
    step_num: int,
    observation,
    action_history: list,
    tokenizer,
    max_text_chars: int = 4000,
) -> str:
    """
    Format prompt that encourages chain-of-thought reasoning.

    This variant asks the model to think step-by-step before
    outputting the action, similar to DeepSeek R1's approach.

    Args:
        step_num: Current step number
        observation: BrowserGymObservation
        action_history: Previous actions
        tokenizer: HuggingFace tokenizer
        max_text_chars: Max chars for page content

    Returns:
        Formatted prompt with CoT instruction
    """
    system = f"""You are a web navigation agent. Complete the given goal by interacting with web pages.

{BROWSERGYM_ACTIONS}

Think step by step:
1. What is the current state of the page?
2. What elements are available?
3. What action brings us closer to the goal?

Then output your action in the format: Action: <action>"""

    goal = observation.goal or "(not provided)"
    url = observation.url or "(unknown)"
    page_content = _get_page_content(observation, max_text_chars)
    history_str = _format_action_history(action_history, max_items=5)

    user_content = f"""Step {step_num + 1}

Goal: {goal}
URL: {url}

Page Content:
{page_content}

Previous Actions: {history_str}

Think through this step and provide your action:"""

    chat = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    return tokenizer.apply_chat_template(
        chat, tokenize=False, add_generation_prompt=True
    )


def parse_web_action(response_text: str, fallback: str = "noop()") -> str:
    """
    Parse action from model's text response.

    Attempts to extract a valid BrowserGym action string from
    the model's output, handling various formats and edge cases.
    Supports Qwen3's <think>...</think> tags for chain-of-thought reasoning.

    Args:
        response_text: Model's generated text
        fallback: Action to return if parsing fails

    Returns:
        BrowserGym action string (e.g., "click('btn-submit')")

    Examples:
        >>> parse_web_action("click('submit-btn')")
        "click('submit-btn')"

        >>> parse_web_action("Action: fill('email', 'test@test.com')")
        "fill('email', 'test@test.com')"

        >>> parse_web_action("I think we should click the button")
        "noop()"

        >>> parse_web_action("<think>I need to click submit</think>click('btn')")
        "click('btn')"
    """
    if not response_text:
        return fallback

    # Check if response has an unclosed <think> tag (truncated mid-thought)
    # In this case, the model never got to output the actual action
    has_open_think = "<think>" in response_text.lower()
    has_close_think = "</think>" in response_text.lower()

    if has_open_think and not has_close_think:
        # Response was truncated inside <think> section
        # Don't try to parse action from reasoning - return fallback
        return fallback

    # Strip <think>...</think> tags (Qwen3 chain-of-thought)
    # The action should be after the think tags
    clean_text = THINK_TAG_PATTERN.sub("", response_text).strip()

    # If we stripped think tags and got empty, return fallback
    if not clean_text:
        return fallback

    # Try to find action in each line
    lines = clean_text.splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Remove common prefixes like "Action:", "Next action:", etc.
        line = ACTION_PREFIX_RE.sub("", line)

        # Look for action pattern
        match = ACTION_PATTERN.search(line)
        if match:
            action = match.group(0).strip()
            # Normalize whitespace
            action = re.sub(r"\s+", " ", action)
            # Validate action
            if _is_valid_action(action):
                return action

    # Fall back to searching the whole cleaned response
    match = ACTION_PATTERN.search(clean_text)
    if match:
        action = match.group(0).strip()
        action = re.sub(r"\s+", " ", action)
        if _is_valid_action(action):
            return action

    return fallback


def parse_web_action_with_reasoning(
    response_text: str,
    fallback: str = "noop()",
) -> tuple[str, Optional[str]]:
    """
    Parse action and extract reasoning from CoT response.

    Supports Qwen3's <think>...</think> tags for chain-of-thought reasoning.

    Args:
        response_text: Model's generated text with reasoning
        fallback: Action to return if parsing fails

    Returns:
        Tuple of (action, reasoning) where reasoning may be None

    Examples:
        >>> parse_web_action_with_reasoning("<think>Need to click button</think>click('btn')")
        ("click('btn')", "Need to click button")
    """
    action = parse_web_action(response_text, fallback)

    # Try to extract reasoning
    reasoning = None
    if response_text:
        # First, try to extract from <think>...</think> tags (Qwen3)
        think_match = re.search(r"<think>(.*?)</think>", response_text, re.DOTALL | re.IGNORECASE)
        if think_match:
            reasoning = think_match.group(1).strip()
        else:
            # Fall back to extracting text before the action
            match = ACTION_PATTERN.search(response_text)
            if match:
                reasoning_text = response_text[:match.start()].strip()
                if reasoning_text:
                    reasoning = reasoning_text

    return action, reasoning


def _get_page_content(observation, max_chars: int) -> str:
    """
    Extract and truncate page content from observation.

    Prefers accessibility tree > pruned HTML > raw text.
    """
    # Priority: axtree > pruned_html > text
    content = (
        observation.axtree_txt
        or observation.pruned_html
        or observation.text
        or "(page content not available)"
    )

    if len(content) > max_chars:
        # Truncate and add indicator
        content = content[:max_chars] + "\n... (truncated)"

    return content


def _format_action_history(action_history: List[str], max_items: int = 5) -> str:
    """
    Format action history for inclusion in prompt.
    """
    if not action_history:
        return "(none yet)"

    # Take last N actions
    recent = action_history[-max_items:]
    start_idx = len(action_history) - len(recent) + 1

    lines = [f"  {start_idx + i}. {act}" for i, act in enumerate(recent)]
    return "\n".join(lines)


def _is_valid_action(action: str) -> bool:
    """
    Check if an action string is a valid BrowserGym action.
    """
    valid_prefixes = [
        "noop(",
        "click(",
        "fill(",
        "type(",
        "select(",
        "scroll(",
        "goto(",
        "send_keys(",
        "hover(",
        "check(",
        "uncheck(",
        "press(",
        "focus(",
        "clear(",
        "drag_and_drop(",
        "upload_file(",
    ]
    return any(action.lower().startswith(prefix) for prefix in valid_prefixes)


def extract_element_ids(observation) -> List[str]:
    """
    Extract all element IDs (BIDs) from observation.

    Useful for validating that model-generated actions
    reference actual elements on the page.

    Args:
        observation: BrowserGymObservation

    Returns:
        List of element ID strings
    """
    # BIDs are typically in format like [123] or bid="123"
    bid_pattern = re.compile(r'\[(\d+)\]|bid="(\d+)"')

    text = observation.axtree_txt or observation.pruned_html or ""
    matches = bid_pattern.findall(text)

    # Flatten and deduplicate
    bids = set()
    for match in matches:
        for group in match:
            if group:
                bids.add(group)

    return sorted(bids, key=lambda x: int(x) if x.isdigit() else x)
