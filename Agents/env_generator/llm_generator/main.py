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
import json
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.config import AgentConfig, LLMConfig, LLMProvider, LogLevel, LoggingConfig, ExecutionConfig, MemoryConfig

from .agents.orchestrator import GeneratorOrchestrator
from .context import GenerationContext
from .events import EventEmitter, EventType, ConsoleListener, FileLogger, RealTimeTextLogger


async def main():
    parser = argparse.ArgumentParser(
        description="Generate OpenEnv-compatible environments using LLM"
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
        "--domain",
        default="custom",
        help="Domain type (e.g., 'calendar', 'ecommerce', 'custom')",
    )
    parser.add_argument(
        "--output",
        default="./generated",
        help="Output directory (default: ./generated)",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.1",
        help="LLM model to use (default: gpt-5.1)",
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
    
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Usage: OPENAI_API_KEY=sk-... python -m llm_generator.main --name calendar")
        sys.exit(1)
    
    # Create config
    config = AgentConfig(
        agent_name="EnvGenerator",
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name=args.model,
            api_key=api_key,
            temperature=0.7,
            max_tokens=128000,  # GPT-5.1 max is 128k completion tokens
        ),
        logging=LoggingConfig(
            level=LogLevel.DEBUG if args.verbose else LogLevel.INFO,
        ),
        execution=ExecutionConfig(
            max_retries=2,
            task_timeout=300,  # 5 minutes per task
        ),
        memory=MemoryConfig(
            short_term_memory_size=50,
        ),
    )
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create event emitter for real-time progress
    emitter = EventEmitter()
    emitter.on_all(ConsoleListener(verbose=args.verbose))
    
    # Log to JSON file (structured)
    json_log_file = output_dir / f"{args.name}_generation.log"
    emitter.on_all(FileLogger(str(json_log_file)))
    
    # Log to text file (human-readable, can be tailed with `tail -f`)
    text_log_file = output_dir / f"{args.name}_realtime.log"
    emitter.on_all(RealTimeTextLogger(str(text_log_file)))
    
    print(f"\n📝 Real-time log: tail -f {text_log_file}\n")
    
    # Create and initialize orchestrator with event emitter
    orchestrator = GeneratorOrchestrator(
        config=config,
        output_dir=output_dir,
        event_emitter=emitter,
        verbose=args.verbose,
        resume=args.resume,
    )
    
    await orchestrator.initialize()
    
    # Try to load learned patterns from previous generations
    memory_file = output_dir / ".generator_memory.json"
    if orchestrator.load_memory(str(memory_file)):
        print(f"  Loaded learned patterns from previous sessions")
        memory_stats = orchestrator.get_memory_stats()
        print(f"  Fix patterns learned: {memory_stats.get('fix_patterns_learned', 0)}")
    
    # Generate environment
    result = await orchestrator.generate_environment(
        name=args.name,
        description=args.description or f"A {args.domain} application with full CRUD capabilities",
        domain_type=args.domain,
    )
    
    # Save learned patterns for future use
    orchestrator.save_memory(str(memory_file))
    
    # Save result to file
    result_file = output_dir / args.name / "generation_result.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    # Print next steps
    print("\n" + "="*60)
    print("📋 Next Steps:")
    print("="*60)
    print(f"  1. cd {result['output_dir']}")
    print(f"  2. Review generated code")
    print(f"  3. docker-compose up --build")
    print("\n  Or run locally:")
    print(f"    # Backend: cd {args.name}_api && pip install -r requirements.txt && uvicorn main:app --reload")
    print(f"    # Frontend: cd {args.name}_ui && npm install && npm run dev")
    print("="*60 + "\n")
    print(f"  📝 Real-time log: {text_log_file}")
    print(f"  📄 JSON log: {json_log_file}")
    print(f"  📊 Result file: {result_file}")
    
    # Cleanup
    await orchestrator.cleanup()
    
    return 0 if result['success'] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

