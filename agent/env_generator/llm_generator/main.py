#!/usr/bin/env python
"""
LLM Generator - Main Entry Point

Multi-Agent Environment Generator with:
- Parallel code generation (Database, Backend, Frontend agents)
- Real-time progress events
- Checkpoint system for resume
- Dynamic port allocation
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add paths for imports
_agents_dir = Path(__file__).parent.parent.parent.absolute()
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

_llm_generator_dir = Path(__file__).parent.absolute()
if str(_llm_generator_dir) not in sys.path:
    sys.path.insert(0, str(_llm_generator_dir))

from utils.config import LLMConfig, LLMProvider
from multi_agent import Orchestrator


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    fmt = "%(asctime)s [%(levelname).1s] %(name)s: %(message)s"
    date_fmt = "%H:%M:%S"
    
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=date_fmt,
        handlers=[logging.StreamHandler()],
    )
    
    # Suppress noisy loggers
    for name in ["openai", "httpx", "httpcore", "urllib3", "asyncio", "aiohttp", "playwright"]:
        logging.getLogger(name).setLevel(logging.WARNING)


async def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Environment Generator"
    )
    
    parser.add_argument("--name", required=True, help="Project name")
    parser.add_argument("--description", default="", help="Project description")
    parser.add_argument("--output", default="./generated", help="Output directory")
    parser.add_argument("--model", default="gpt-4", help="LLM model")
    parser.add_argument("--provider", default="openai", 
                       choices=["openai", "google", "anthropic", "azure", "local"])
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger("main")
    
    # Get provider and API key
    provider_map = {
        "openai": (LLMProvider.OPENAI, "OPENAI_API_KEY"),
        "google": (LLMProvider.GOOGLE, "GOOGLE_API_KEY"),
        "anthropic": (LLMProvider.ANTHROPIC, "ANTHROPIC_API_KEY"),
        "azure": (LLMProvider.AZURE, "AZURE_OPENAI_API_KEY"),
        "local": (LLMProvider.LOCAL, None),
    }
    
    provider_enum, api_key_env = provider_map.get(args.provider, (LLMProvider.OPENAI, "OPENAI_API_KEY"))
    
    api_key = None
    if api_key_env:
        api_key = os.environ.get(api_key_env) or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print(f"Error: {api_key_env} environment variable not set")
            sys.exit(1)
    
    llm_config = LLMConfig(
        provider=provider_enum,
        model_name=args.model,
        api_key=api_key,
        temperature=0.7,
        max_tokens=32000,
        timeout=1800,
    )
    
    output_dir = Path(args.output) / args.name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting multi-agent generation: {args.name}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Model: {args.model} ({args.provider})")
    
    orchestrator = Orchestrator(
        llm_config=llm_config,
        output_dir=output_dir,
        verbose=args.verbose,
    )
    
    requirements = []
    if args.description:
        requirements.append(args.description)
    
    result = await orchestrator.run(
        goal=args.description or f"Build a {args.name} web application",
        requirements=requirements,
        resume=args.resume,
    )
    
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"  Phases: {', '.join(result.phases_completed)}")
    print(f"  Issues: {result.issues_found} found, {result.issues_fixed} fixed")
    print(f"  Duration: {result.duration:.1f}s")
    print(f"  Output: {result.project_path}")
    
    # Show ports used
    status = orchestrator.get_status()
    print(f"\n  Ports allocated:")
    print(f"    API: {status['ports']['api']}")
    print(f"    UI: {status['ports']['ui']}")
    print("=" * 60)
    
    if result.success:
        print("\nNext Steps:")
        print(f"  1. cd {result.project_path}")
        print(f"  2. docker-compose -f docker/docker-compose.yml up --build")
        print(f"  3. Open http://localhost:{status['ports']['ui']}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
