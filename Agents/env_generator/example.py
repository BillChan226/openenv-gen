"""
Example usage of the EnvGenerator Multi-Agent System

This script demonstrates how to use the EnvGeneratorOrchestrator
to generate OpenEnv-compatible environments.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import AgentConfig, LLMConfig, LLMProvider, ExecutionConfig, MemoryConfig
from env_generator.orchestrator import EnvGeneratorOrchestrator


async def main():
    """Demo the EnvGenerator orchestrator"""
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        print("\nRunning in demo mode (will fail on LLM calls)...\n")
    
    # Create configuration
    config = AgentConfig(
        agent_id="env_generator_demo",
        agent_name="EnvGeneratorDemo",
        agent_type="coordinator",
        description="Demo environment generator",
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key=api_key,
            temperature=0.3,
            max_tokens=4096,
        ),
        execution=ExecutionConfig(
            max_concurrent_tasks=1,
            task_timeout=600,  # 10 minutes
            max_retries=2,
        ),
        memory=MemoryConfig(
            short_term_memory_size=50,
            long_term_memory_enabled=True,
        ),
    )
    
    # Create orchestrator
    orchestrator = EnvGeneratorOrchestrator(
        config=config,
        output_base_dir="./generated_envs",
    )
    
    # Initialize
    print("\n" + "=" * 60)
    print("EnvGenerator Multi-Agent System Demo")
    print("=" * 60)
    
    print("\nInitializing orchestrator...")
    success = await orchestrator.initialize()
    
    if not success:
        print("Failed to initialize orchestrator")
        return
    
    print("Orchestrator initialized successfully")
    print(f"\nOrchestrator Status:")
    status = orchestrator.get_status()
    print(f"  - Agent ID: {status['agent_id']}")
    print(f"  - State: {status['state']}")
    print(f"  - Tools: {status['tools']}")
    print(f"  - Capabilities: {status['capabilities']}")
    
    # Example 1: Generate from description
    print("\n" + "-" * 60)
    print("Example 1: Generate Calendar Environment")
    print("-" * 60)
    
    description = """
    A Google Calendar-like application with:
    - User authentication (register, login, logout)
    - Calendar management (create, list, update, delete calendars)
    - Event management (create, list, update, delete events)
    - Event attendees and invitations
    - Recurring events support
    - Free/busy query
    - Email notifications for invitations
    """
    
    print(f"\nDescription:\n{description}")
    print("\nStarting generation...")
    
    result = await orchestrator.generate_environment(
        name="calendar",
        description=description,
        domain_type="calendar",
        constraints=[
            "Use SQLite for simplicity",
            "Include JWT authentication",
            "Follow Google Calendar API patterns",
        ],
    )
    
    print(f"\nGeneration Result:")
    print(f"  - Success: {result.success}")
    print(f"  - Output Directory: {result.output_dir}")
    print(f"  - Generated Files: {len(result.generated_files)}")
    
    if result.generated_files:
        print(f"\nGenerated Files:")
        for f in result.generated_files[:10]:
            print(f"    - {f}")
        if len(result.generated_files) > 10:
            print(f"    ... and {len(result.generated_files) - 10} more")
    
    if result.errors:
        print(f"\nErrors:")
        for e in result.errors:
            print(f"    - {e}")
    
    if result.validation_report:
        print(f"\nValidation Report:")
        for key, value in result.validation_report.items():
            if key != "details":
                print(f"    - {key}: {value}")
    
    # Cleanup
    print("\n" + "-" * 60)
    print("Cleaning up...")
    await orchestrator.cleanup()
    print("Done!")
    
    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)
    
    return result


async def demo_data_driven():
    """Demo data-driven environment generation"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    config = AgentConfig(
        agent_id="env_generator_data",
        agent_name="DataDrivenGenerator",
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key=api_key,
        ),
    )
    
    orchestrator = EnvGeneratorOrchestrator(config)
    await orchestrator.initialize()
    
    # Sample data for inference
    reference_data = {
        "products": [
            {"id": 1, "name": "Widget", "price": 9.99, "stock": 100, "category": "electronics"},
            {"id": 2, "name": "Gadget", "price": 19.99, "stock": 50, "category": "electronics"},
            {"id": 3, "name": "Gizmo", "price": 29.99, "stock": 25, "category": "tools"},
        ],
        "users": [
            {"id": 1, "email": "admin@example.com", "role": "admin"},
            {"id": 2, "email": "user@example.com", "role": "customer"},
        ],
        "orders": [
            {"id": 1, "user_id": 2, "product_id": 1, "quantity": 3, "status": "pending"},
            {"id": 2, "user_id": 2, "product_id": 2, "quantity": 1, "status": "shipped"},
        ],
    }
    
    print("\nGenerating inventory environment from reference data...")
    
    result = await orchestrator.generate_environment(
        name="inventory",
        reference_data=reference_data,
        domain_type="ecommerce",
    )
    
    await orchestrator.cleanup()
    return result


if __name__ == "__main__":
    asyncio.run(main())

