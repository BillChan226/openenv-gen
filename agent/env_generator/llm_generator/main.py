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
import json
from datetime import datetime
from enum import Enum
from pathlib import Path

# ===== Global JSON Patch to Handle Non-Serializable Objects =====
# This ensures all json.dumps calls in the entire application handle
# Message objects and other non-serializable types gracefully.
# IMPORTANT: Only applies to data serialization, NOT to API requests.

_original_json_dumps = json.dumps
_in_api_call = False  # Flag to detect nested calls

def _safe_json_dumps(obj, **kwargs):
    """Patched json.dumps that handles non-serializable objects."""
    global _in_api_call
    
    # If already using default handler (likely API call), don't interfere
    if 'default' in kwargs and kwargs['default'] is not None:
        return _original_json_dumps(obj, **kwargs)
    
    def default_handler(o):
        # Check the type name to avoid importing the class
        type_name = type(o).__name__
        
        # Skip Message and LLMResponse objects - let them serialize normally
        # These are used in API calls and should keep their structure
        if type_name in ('Message', 'LLMResponse'):
            if hasattr(o, 'to_dict'):
                return o.to_dict()
        
        # For other objects with to_dict, use it
        if hasattr(o, 'to_dict'):
            return o.to_dict()
        
        # Handle objects with __dict__ but avoid complex nested structures
        if hasattr(o, '__dict__'):
            # Only serialize simple objects, not complex nested ones
            d = {}
            for k, v in o.__dict__.items():
                if not k.startswith('_'):
                    if isinstance(v, (str, int, float, bool, type(None), list, dict)):
                        d[k] = v
                    else:
                        d[k] = str(v)
            return d
        
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Enum):
            return o.value
        
        # Fallback to string representation
        return str(o)
    
    kwargs['default'] = default_handler
    return _original_json_dumps(obj, **kwargs)

# Apply the monkey patch globally
json.dumps = _safe_json_dumps

# ===== End Global JSON Patch =====

# Add paths for imports
_agents_dir = Path(__file__).parent.parent.parent.absolute()
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

_llm_generator_dir = Path(__file__).parent.absolute()
if str(_llm_generator_dir) not in sys.path:
    sys.path.insert(0, str(_llm_generator_dir))

from utils.config import LLMConfig, LLMProvider
from multi_agent import Orchestrator


def setup_logging(verbose: bool = False, log_file: Path = None):
    """Setup logging configuration.
    
    Args:
        verbose: Enable debug logging
        log_file: Optional path to log file. If provided, logs will be saved to file.
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    fmt = "%(asctime)s [%(levelname).1s] %(name)s: %(message)s"
    date_fmt = "%H:%M:%S"
    
    handlers = [logging.StreamHandler()]
    
    # Add file handler if log_file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(fmt, date_fmt))
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=date_fmt,
        handlers=handlers,
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
    parser.add_argument("--reference-images", nargs="*", default=[], 
                       help="Reference screenshot paths for design (e.g., screenshot/expedia.png)")
    parser.add_argument("--reference-dir", default=None,
                       help="Directory containing reference screenshots")
    parser.add_argument("--log", action="store_true",
                       help="Save logs to file (output_dir/logs/generation.log)")
    
    args = parser.parse_args()
    
    # Setup log file path if --log is specified
    output_dir = Path(args.output) / args.name
    log_file = output_dir / "logs" / f"generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log" if args.log else None
    
    setup_logging(args.verbose, log_file)
    logger = logging.getLogger("main")
    
    if log_file:
        logger.info(f"Logging to file: {log_file}")
    
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
    
    # output_dir already defined above for logging
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting multi-agent generation: {args.name}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Model: {args.model} ({args.provider})")
    
    # Collect reference images
    reference_images = list(args.reference_images)
    if args.reference_dir:
        ref_dir = Path(args.reference_dir)
        if ref_dir.exists():
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                reference_images.extend([str(p) for p in ref_dir.glob(ext)])
    
    if reference_images:
        logger.info(f"Reference images: {len(reference_images)} files")
        for img in reference_images:
            logger.info(f"  - {img}")
    
    orchestrator = Orchestrator(
        llm_config=llm_config,
        output_dir=output_dir,
        name=args.name,
        verbose=args.verbose,
        reference_images=reference_images,
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
