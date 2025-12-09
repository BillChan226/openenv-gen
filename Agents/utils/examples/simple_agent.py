"""
Example: Simple Agent Implementation

Demonstrates how to use the utils module to create a basic Agent
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import (
    BaseAgent,
    AgentConfig,
    AgentRole,
    TaskMessage,
    ResultMessage,
    create_result_message,
    create_task_message,
    MessageBus,
    LLMConfig,
    ExecutionConfig,
)


class SimpleWorkerAgent(BaseAgent):
    """
    Simple Worker Agent
    
    Receives tasks, simulates processing, returns results
    """
    
    async def on_initialize(self) -> None:
        """Custom initialization logic"""
        self._logger.info(f"Custom initialization for {self.name}")
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process task"""
        self._logger.info(f"Processing task: {task.task_name}")
        
        # Simulate work
        await asyncio.sleep(1)
        
        # Get task parameters
        params = task.task_params
        
        # Return result
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data={
                "status": "completed",
                "processed_params": params,
                "agent": self.name,
            },
            reply_to=task.header.message_id,
        )
    
    async def on_task_completed(self, task: TaskMessage, result: ResultMessage) -> None:
        """Task completion callback"""
        self._logger.info(f"Task {task.task_id} completed successfully")


async def main():
    """Main function"""
    # Create configuration
    config = AgentConfig(
        agent_id="worker_001",
        agent_name="SimpleWorker",
        agent_type="worker",
        execution=ExecutionConfig(
            max_concurrent_tasks=3,
            task_timeout=60,
        ),
    )
    
    # Create Agent
    agent = SimpleWorkerAgent(config, role=AgentRole.WORKER)
    
    # Initialize
    await agent.initialize()
    print(f"Agent initialized: {agent.get_status()}")
    
    # Start
    await agent.start()
    print(f"Agent started: {agent.state}")
    
    # Create task
    task = create_task_message(
        source_id="coordinator",
        target_id=agent.agent_id,
        task_name="test_task",
        task_params={"input": "hello", "count": 5},
    )
    
    # Send task
    await agent.receive_message(task)
    
    # Wait for processing
    await asyncio.sleep(3)
    
    # Check status
    print(f"Agent metrics: {agent.metrics.to_dict()}")
    
    # Stop
    await agent.stop()
    await agent.cleanup()
    
    print("Agent shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
