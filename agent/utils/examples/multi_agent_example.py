"""
Example: Multi-Agent Collaborative System

Demonstrates how to use MessageBus to implement multi-agent collaboration
This is a simplified version of the Sandbox-Creator architecture
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import (
    BaseAgent,
    AgentConfig,
    AgentRole,
    TaskMessage,
    ResultMessage,
    StatusMessage,
    MessageBus,
    create_task_message,
    create_result_message,
    ExecutionConfig,
    MessageType,
)


class CoordinatorAgent(BaseAgent):
    """
    Coordinator Agent
    
    Responsibilities:
    - Receive external task requests
    - Decompose and distribute tasks to Workers
    - Aggregate results
    """
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        super().__init__(config, role=AgentRole.COORDINATOR)
        self._bus = message_bus
        self._pending_results: dict[str, list] = {}  # task_id -> [sub_results]
        self._task_workers: dict[str, list[str]] = {}  # task_id -> [worker_ids]
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process task - decompose and distribute"""
        self._logger.info(f"Coordinator received task: {task.task_name}")
        
        # Get available Workers
        worker_ids = [
            aid for aid in self._bus.list_agents() 
            if aid != self.agent_id
        ]
        
        if not worker_ids:
            return create_result_message(
                source_id=self.agent_id,
                target_id=task.header.source_agent_id,
                task_id=task.task_id,
                success=False,
                error_message="No workers available",
            )
        
        # Decompose task (example: distribute to all workers)
        sub_tasks = task.task_params.get("sub_tasks", [{"name": "default"}])
        
        self._pending_results[task.task_id] = []
        self._task_workers[task.task_id] = []
        
        # Distribute sub-tasks
        for i, sub_task in enumerate(sub_tasks):
            worker_id = worker_ids[i % len(worker_ids)]
            
            sub_task_msg = create_task_message(
                source_id=self.agent_id,
                target_id=worker_id,
                task_name=f"{task.task_name}_part_{i}",
                task_params={
                    "parent_task_id": task.task_id,
                    **sub_task,
                },
            )
            
            self._task_workers[task.task_id].append(worker_id)
            await self._bus.send(sub_task_msg)
        
        self._logger.info(f"Distributed {len(sub_tasks)} sub-tasks")
        
        # Note: Return placeholder result, actual result aggregated after all sub-tasks complete
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data={"status": "distributed", "sub_task_count": len(sub_tasks)},
        )
    
    async def on_result_received(self, result: ResultMessage) -> None:
        """Receive Worker results"""
        parent_task_id = result.metadata.get("parent_task_id")
        
        if parent_task_id and parent_task_id in self._pending_results:
            self._pending_results[parent_task_id].append(result.result_data)
            
            # Check if all sub-tasks completed
            expected_count = len(self._task_workers.get(parent_task_id, []))
            current_count = len(self._pending_results[parent_task_id])
            
            if current_count >= expected_count:
                self._logger.info(f"All sub-tasks completed for {parent_task_id}")
                # Aggregate results (simple merge here)
                aggregated = {
                    "task_id": parent_task_id,
                    "results": self._pending_results[parent_task_id],
                    "total_sub_tasks": expected_count,
                }
                print(f"\n=== FINAL RESULT ===\n{aggregated}\n")


class WorkerAgent(BaseAgent):
    """
    Worker Agent
    
    Responsible for executing specific sub-tasks
    """
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        super().__init__(config, role=AgentRole.WORKER)
        self._bus = message_bus
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Execute task"""
        self._logger.info(f"Worker {self.name} processing: {task.task_name}")
        
        # Simulate work
        await asyncio.sleep(0.5)
        
        # Create result
        result = create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data={
                "worker": self.name,
                "task": task.task_name,
                "processed": task.task_params,
            },
        )
        
        # Save parent_task_id to metadata
        if "parent_task_id" in task.task_params:
            result.metadata["parent_task_id"] = task.task_params["parent_task_id"]
        
        return result
    
    async def on_task_completed(self, task: TaskMessage, result: ResultMessage) -> None:
        """Send result to Coordinator after task completion"""
        await self._bus.send(result)


async def main():
    """Main function - demonstrates Multi-Agent collaboration"""
    print("=== Multi-Agent Example ===\n")
    
    # Create message bus
    bus = MessageBus()
    
    # Create Coordinator
    coordinator_config = AgentConfig(
        agent_id="coordinator",
        agent_name="MainCoordinator",
        execution=ExecutionConfig(max_concurrent_tasks=10),
    )
    coordinator = CoordinatorAgent(coordinator_config, bus)
    
    # Create Workers
    workers = []
    for i in range(3):
        worker_config = AgentConfig(
            agent_id=f"worker_{i}",
            agent_name=f"Worker-{i}",
        )
        worker = WorkerAgent(worker_config, bus)
        workers.append(worker)
    
    # Register all Agents to message bus
    bus.register_agent(coordinator)
    for worker in workers:
        bus.register_agent(worker)
    
    # Initialize and start all Agents
    await coordinator.initialize()
    await coordinator.start()
    
    for worker in workers:
        await worker.initialize()
        await worker.start()
    
    # Start message bus
    await bus.start()
    
    print(f"System started with {len(bus.list_agents())} agents")
    print(f"Bus stats: {bus.get_stats()}\n")
    
    # Create a composite task
    main_task = create_task_message(
        source_id="external",
        target_id="coordinator",
        task_name="build_sandbox",
        task_params={
            "sub_tasks": [
                {"name": "setup_environment", "type": "python"},
                {"name": "install_dependencies", "packages": ["numpy", "pandas"]},
                {"name": "configure_network", "port": 8080},
                {"name": "setup_storage", "size": "10GB"},
            ],
        },
    )
    
    # Send task
    await coordinator.receive_message(main_task)
    
    # Wait for processing to complete
    await asyncio.sleep(5)
    
    # Print final status
    print("\n=== Final Status ===")
    print(f"Coordinator: {coordinator.metrics.to_dict()}")
    for worker in workers:
        print(f"{worker.name}: {worker.metrics.to_dict()}")
    
    # Cleanup
    await bus.stop()
    await coordinator.stop()
    for worker in workers:
        await worker.stop()
    
    print("\n=== Shutdown Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
