"""
Prompt Loader - shared Jinja2 template loader for Agents/utils modules.

We keep prompts in `Agents/utils/prompts/` so they can be shared across the agent stack.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


@lru_cache(maxsize=1)
def _env() -> Environment:
    prompts_dir = Path(__file__).parent / "prompts"
    return Environment(
        loader=FileSystemLoader(str(prompts_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(template_name: str, **kwargs: Any) -> str:
    """Render a prompt template from Agents/utils/prompts/"""
    return _env().get_template(template_name).render(**kwargs)


