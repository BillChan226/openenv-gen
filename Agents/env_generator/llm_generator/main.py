#!/usr/bin/env python
"""
LLM Generator - Main Entry Point

Usage:
    python -m llm_generator.main --name calendar --description "A calendar app"
    
    # Or with environment variable
    OPENAI_API_KEY=sk-... python -m llm_generator.main --name shop --domain ecommerce
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
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


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
        "--description",
        default="",
        help="Environment description",
    )
    parser.add_argument(
        "--output",
        default="./generated",
        help="Output directory (default: ./generated)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4",
        help="LLM model to use (default: gpt-4)",
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
    
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Usage: OPENAI_API_KEY=sk-... python -m llm_generator.main --name calendar")
        sys.exit(1)
    
    # Create LLM config
    llm_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name=args.model,
        api_key=api_key,
        temperature=0.7,
        max_tokens=4096,
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
    if args.description:
        requirements.append(args.description)
    
    # Run generation
    result = await coordinator.run(
        goal=args.description or f"Build a {args.name} web application",
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
