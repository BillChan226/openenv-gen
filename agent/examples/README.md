# AgentForge Examples

## Code Builder Agent

An intelligent agent that can build code projects using GPT-4 (or GPT-5 when available).

### Features

- **Planning**: Automatically breaks down coding tasks into steps
- **Reasoning**: Uses ReAct pattern to solve problems
- **Memory**: Remembers context and past actions
- **Tools**: File operations + code execution

### Tools Available

| Tool | Description |
|------|-------------|
| `create_file` | Create a new file |
| `write_file` | Write/update file content |
| `read_file` | Read file content |
| `delete_file` | Delete a file |
| `run_code` | Execute Python code |
| `list_files` | List workspace files |

### Quick Start

```bash
# Set your API key
export OPENAI_API_KEY="your-api-key"

# Run the demo
cd AgentForge/Agents/examples
python code_builder_agent.py
```

### Usage in Code

```python
import asyncio
from code_builder_agent import CodeBuilderAgent

async def main():
    # Create agent
    agent = CodeBuilderAgent(
        api_key="your-api-key",  # or use OPENAI_API_KEY env var
        model="gpt-4",           # or "gpt-4-turbo"
        workspace="./my_project",
    )
    
    # Initialize (loads tools, planner, reasoner)
    await agent.initialize()
    
    # Build something
    result = await agent.build(
        task="Create a REST API with Flask",
        constraints=[
            "Use blueprints",
            "Include error handling",
            "Add a health check endpoint",
        ],
    )
    
    # Check result
    print(f"Success: {result['success']}")
    print(f"Files created in: {result['workspace']}")

asyncio.run(main())
```

### Monitor Progress

```python
# While building, you can check status
print(agent.print_plan())
# Plan: Create a REST API...
# Steps:
#   ✅ 1. Create project structure
#   🔄 2. Implement main app
#   ⏳ 3. Add routes
#   ...

# Get detailed status
status = agent.get_plan_status()
print(f"Progress: {status['progress_percent']}")
print(f"Completed: {status['completed_steps']}/{status['total_steps']}")

# Check memory
print(agent.memory.stats())
```

### Quick Code Generation

For simple tasks without full planning:

```python
# Quick code without planning
result = await agent.quick_code("Calculate fibonacci numbers")
print(result)
```

### Customization

```python
# Custom planner prompt
agent.planner.system_prompt = "You are a backend specialist..."

# Custom reasoner prompt
agent.reasoner.system_prompt = "You write production-quality code..."

# Access memory directly
agent.memory.remember("Use Django for this project", memory_type="long")
```

### Workspace Structure

After running, files are created in the workspace directory:

```
workspace/
├── calculator.py
├── main.py
├── tests/
│   └── test_calculator.py
└── ...
```

