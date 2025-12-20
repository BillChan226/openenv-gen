"""
Path Utilities

Shared path resolution functions to ensure consistent path handling across all tools.
"""

from pathlib import Path
from typing import Union


def resolve_path(path: str, output_dir: Path) -> Path:
    """
    Resolve a path relative to output_dir, avoiding double concatenation.
    
    This is the canonical path resolution function that all tools should use.
    
    Args:
        path: User-provided path (can be relative, absolute, or containing output_dir)
        output_dir: The base output directory
    
    Returns:
        Resolved absolute path
        
    Handles these cases:
    - Empty path: returns output_dir
    - Absolute paths: returns as-is (after checking for duplication)
    - Relative paths: joins with output_dir
    - Paths with output_dir prefix: removes prefix before joining
    - Paths with project name prefix: removes prefix before joining
    - Paths with env_generator/generated pattern: handles correctly
    """
    if not path:
        return output_dir
    
    path_obj = Path(path)
    
    # If absolute, check for path duplication
    if path_obj.is_absolute():
        output_dir_str = str(output_dir)
        path_str = str(path_obj)
        
        # Check for double occurrence of output_dir in path
        if path_str.count(output_dir_str) > 1:
            # Find the last occurrence and use that
            idx = path_str.rfind(output_dir_str)
            if idx > 0:
                return Path(path_str[idx:])
        
        # Check for double occurrence of project name
        project_name = output_dir.name
        parts = path_obj.parts
        occurrences = [i for i, part in enumerate(parts) if part == project_name]
        if len(occurrences) > 1:
            # Reconstruct from the last occurrence of project_name back to its parent structure
            last_idx = occurrences[-1]
            # Find where output_dir ends in the path and take from there
            return path_obj
        
        return path_obj
    
    # For relative paths, clean up any duplications
    output_dir_str = str(output_dir)
    output_dir_name = output_dir.name
    clean_path = path
    
    # Remove full output_dir prefix if present (possibly multiple times)
    while True:
        if clean_path.startswith(output_dir_str + "/"):
            clean_path = clean_path[len(output_dir_str) + 1:]
        elif clean_path.startswith(output_dir_str):
            clean_path = clean_path[len(output_dir_str):].lstrip("/").lstrip("\\")
        else:
            break
    
    # Check if path contains output_dir anywhere (double concatenation)
    if output_dir_str in clean_path:
        idx = clean_path.find(output_dir_str)
        remaining = clean_path[idx + len(output_dir_str):].lstrip("/").lstrip("\\")
        clean_path = remaining if remaining else ""
    
    # Remove project name prefix if present (e.g., "atlassian_home/app/..." -> "app/...")
    while True:
        if clean_path.startswith(output_dir_name + "/"):
            clean_path = clean_path[len(output_dir_name) + 1:]
        elif clean_path.startswith(output_dir_name + "\\"):
            clean_path = clean_path[len(output_dir_name) + 1:]
        elif clean_path == output_dir_name:
            clean_path = ""
            break
        else:
            break
    
    # Handle "env_generator/generated/project_name" pattern
    relative_pattern = f"env_generator/generated/{output_dir_name}"
    if clean_path.startswith(relative_pattern + "/"):
        clean_path = clean_path[len(relative_pattern) + 1:]
    elif clean_path.startswith(relative_pattern):
        clean_path = clean_path[len(relative_pattern):].lstrip("/").lstrip("\\")
    
    # Now join with output_dir
    if clean_path:
        return output_dir / clean_path
    return output_dir


def resolve_output_dir(output_dir: Union[str, Path, None]) -> Path:
    """
    Resolve and clean the output directory path.
    
    This ensures the output_dir itself doesn't have path duplication issues.
    
    Args:
        output_dir: The output directory path (string, Path, or None)
    
    Returns:
        Clean Path object
    """
    if not output_dir:
        return Path.cwd()
    
    path = Path(output_dir) if isinstance(output_dir, str) else output_dir
    path_str = str(path)
    parts = path.parts
    
    if len(parts) < 2:
        return path
    
    # Check for duplication: same directory name appears multiple times in unexpected positions
    project_name = parts[-1]  # Last part is the project name
    
    # Count occurrences of project_name
    occurrences = [i for i, part in enumerate(parts) if part == project_name]
    
    if len(occurrences) > 1:
        # We have duplication - take from the LAST occurrence
        # But we need to preserve the proper parent structure
        # e.g., /Users/x/gen/atlassian_home/env_generator/generated/atlassian_home
        #       should become /Users/x/gen/atlassian_home
        
        # Find the first occurrence and use path up to that point
        first_idx = occurrences[0]
        clean_parts = parts[:first_idx + 1]
        return Path(*clean_parts)
    
    return path


def normalize_path_for_tracking(path: str, output_dir: Path) -> str:
    """
    Normalize a file path to be relative to output_dir.
    
    Used for tracking which files have been created/modified.
    
    Args:
        path: The path to normalize
        output_dir: The base output directory
    
    Returns:
        Path relative to output_dir as string
    """
    output_dir_str = str(output_dir)
    project_name = output_dir.name
    
    normalized = path
    
    # Remove leading output_dir if present (possibly multiple times)
    while True:
        if normalized.startswith(output_dir_str + "/"):
            normalized = normalized[len(output_dir_str) + 1:]
        elif normalized.startswith(output_dir_str):
            normalized = normalized[len(output_dir_str):].lstrip("/")
        else:
            break
    
    # Remove project name if it appears at the start
    while True:
        if normalized.startswith(project_name + "/"):
            normalized = normalized[len(project_name) + 1:]
        else:
            break
    
    # Handle relative output path pattern
    relative_pattern = f"env_generator/generated/{project_name}"
    while True:
        if normalized.startswith(relative_pattern + "/"):
            normalized = normalized[len(relative_pattern) + 1:]
        elif normalized.startswith(relative_pattern):
            normalized = normalized[len(relative_pattern):].lstrip("/")
        else:
            break
    
    return normalized


__all__ = [
    "resolve_path",
    "resolve_output_dir", 
    "normalize_path_for_tracking",
]

