"""
Specs - Project structure specifications
"""

from .project_structure import (
    PROJECT_STRUCTURE,
    PHASES,
    get_allowed_paths,
    get_phase_spec,
    validate_path,
    format_structure_for_prompt,
)

__all__ = [
    "PROJECT_STRUCTURE",
    "PHASES",
    "get_allowed_paths",
    "get_phase_spec",
    "validate_path",
    "format_structure_for_prompt",
]
