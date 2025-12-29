#!/usr/bin/env python
"""
LLM Generator - Main Entry Point

Usage:
    # With inline prompt
    python -m llm_generator.main --name calendar --prompt "A calendar app"

    # With prompt file
    python -m llm_generator.main --name shop --prompt ./prompt.md

    # With environment variable
    OPENAI_API_KEY=sk-... python -m llm_generator.main --name shop --prompt ./prompt.md

Note: Reference images should be placed in the screenshot library at:
    llm_generator/screenshot/<project_name>/
The agent will automatically discover and use them during generation.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add Agents directory to path (where utils/ is located)
_agents_dir = Path(__file__).parent.parent.parent.absolute()
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

# Add llm_generator directory to path for direct script execution
_llm_generator_dir = Path(__file__).parent.absolute()
if str(_llm_generator_dir) not in sys.path:
    sys.path.insert(0, str(_llm_generator_dir))

from utils.config import LLMConfig, LLMProvider

# Use absolute imports for direct script execution
from agents import Coordinator
from progress import EventEmitter, ConsoleListener, FileLogger


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    # Set root level
    level = logging.DEBUG if verbose else logging.INFO
    
    # Custom format - more concise
    fmt = "%(asctime)s [%(levelname).1s] %(name)s: %(message)s"
    date_fmt = "%H:%M:%S"
    
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=date_fmt,
        handlers=[logging.StreamHandler()],
    )
    
    # Suppress noisy third-party loggers (only show WARNING and above)
    noisy_loggers = [
        "openai",
        "httpx",
        "httpcore",
        "urllib3",
        "asyncio",
        "aiohttp",
        "playwright",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


async def main():
    parser = argparse.ArgumentParser(
        description="Generate OpenEnv-compatible web environments using LLM"
    )
    
    parser.add_argument(
        "--name",
        required=True,
        help="Environment name (e.g., 'calendar', 'shop')",
    )
    parser.add_argument(
        "--prompt",
        default="",
        help="Environment description: either inline text or path to a .md/.txt file",
    )
    parser.add_argument(
        "--output",
        default="./generated",
        help="Output directory (default: ./generated)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4",
        help="LLM model to use (default: gpt-4, e.g., gemini-2.0-flash-exp for Google)",
    )
    parser.add_argument(
        "--provider",
        default="openai",
        choices=["openai", "google", "anthropic", "azure", "local"],
        help="LLM provider (default: openai)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous checkpoint if available",
    )
    
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger("main")

    # Parse prompt: could be inline text or a file path
    description = args.prompt
    if args.prompt:
        prompt_path = Path(args.prompt)
        # Check if it's a file path (exists and has .md or .txt extension)
        if prompt_path.exists() and prompt_path.suffix in (".md", ".txt"):
            description = prompt_path.read_text(encoding="utf-8").strip()
            logger.info(f"Loaded prompt from file: {args.prompt}")
        else:
            logger.info("Using inline prompt")

    # Determine provider and API key
    provider_map = {
        "openai": (LLMProvider.OPENAI, "OPENAI_API_KEY"),
        "google": (LLMProvider.GOOGLE, "GOOGLE_API_KEY"),
        "anthropic": (LLMProvider.ANTHROPIC, "ANTHROPIC_API_KEY"),
        "azure": (LLMProvider.AZURE, "AZURE_OPENAI_API_KEY"),
        "local": (LLMProvider.LOCAL, None),
    }
    
    provider_enum, api_key_env = provider_map.get(args.provider, (LLMProvider.OPENAI, "OPENAI_API_KEY"))
    
    # Check for API key (except for local provider)
    api_key = None
    if api_key_env:
        api_key = os.environ.get(api_key_env) or os.environ.get("GEMINI_API_KEY")  # Also check GEMINI_API_KEY
        if not api_key:
            print(f"Error: {api_key_env} environment variable not set")
            print(f"Usage: {api_key_env}=... python main.py --name calendar --provider {args.provider}")
            sys.exit(1)
    
    # Create LLM config
    llm_config = LLMConfig(
        provider=provider_enum,
        model_name=args.model,
        api_key=api_key,
        temperature=0.7,
        # Default to a larger output budget; can be constrained by provider/model limits.
        max_tokens=65536,
        timeout=1800,  # 30 minutes for large generations
    )
    
    # Create output directory
    output_dir = Path(args.output) / args.name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting generation: {args.name}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Model: {args.model}")
    
    # Create coordinator
    coordinator = Coordinator(
        llm_config=llm_config,
        output_dir=output_dir,
        enable_checkpoints=True,
    )
    
    # Build requirements list
    requirements = []
    if description:
        requirements.append(description)

    # Run generation
    result = await coordinator.run(
        goal=description or f"Build a {args.name} web application",
        requirements=requirements,
        resume=args.resume,
    )
    
    # Print result
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"  Tasks completed: {result.tasks_completed}")
    print(f"  Tasks failed: {result.tasks_failed}")
    print(f"  Issues fixed: {result.issues_fixed}")
    print(f"  Duration: {result.duration:.1f}s")
    print(f"  Output: {result.project_path}")
    print("=" * 60)
    
    if result.success:
        print("\n📋 Next Steps:")
        print(f"  1. cd {result.project_path}")
        print(f"  2. docker-compose -f docker/docker-compose.yml up --build")
        print(f"  3. Open http://localhost:3000")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
