# AgentForge

A Multi-Agent System Framework for building intelligent agent-based applications.

**Author:** EchoRaven (haibot2@illinois.edu)

## Project Structure

```
AgentForge/
├── Agents/
│   ├── utils/                       # Core Infrastructure
│   │   ├── message.py               # Message protocol
│   │   ├── config.py                # Configuration management
│   │   ├── state.py                 # State management
│   │   ├── tool.py                  # Tool interface
│   │   ├── base_agent.py            # Base Agent class
│   │   ├── communication.py         # Communication (MessageBus)
│   │   ├── llm.py                   # LLM clients (OpenAI, Anthropic, etc.)
│   │   ├── prompt.py                # Prompt template management
│   │   ├── memory.py                # Memory systems
│   │   ├── planner.py               # Task planning
│   │   ├── reasoning.py             # ReAct reasoning engine
│   │   └── planning_agent.py        # Planning Agent base class
│   │
│   ├── examples/                    # Example Agents
│   │   ├── code_builder_agent.py    # Code Builder Agent
│   │   └── test_code_builder.py     # Test suite
│   │
│   ├── Sandbox-Creator/             # Environment creation (TBD)
│   ├── Task-Creator/                # Task creation (TBD)
│   ├── Task-Verifier/               # Task verification (TBD)
│   ├── Target-Agent/                # Target Agent (TBD)
│   ├── Data-Creator/                # Data creation (TBD)
│   └── Sandbox-Verifier/            # Environment verification (TBD)
│
└── README.md
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AgentForge Framework                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────── INTELLIGENCE LAYER ──────────────────────┐    │
│  │                                                                  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │    │
│  │  │   LLM    │  │  Prompt  │  │  Memory  │  │   Reasoning  │   │    │
│  │  │  Client  │  │ Templates│  │  System  │  │   (ReAct)    │   │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │    │
│  │                      │                                         │    │
│  │                 ┌────▼────────────────┐                        │    │
│  │                 │      Planner        │                        │    │
│  │                 └────────────┬────────┘                        │    │
│  │                              │                                  │    │
│  └──────────────────────────────┼──────────────────────────────────┘    │
│                                 │                                        │
│                    ┌────────────▼────────────┐                          │
│                    │     PlanningAgent       │                          │
│                    └────────────┬────────────┘                          │
│                                 │                                        │
│  ┌──────────────────────────────▼──────────────────────────────────┐    │
│  │                         BaseAgent                                │    │
│  └──────────────────────────────┬──────────────────────────────────┘    │
│                                 │                                        │
│  ┌────────────────────── CORE LAYER ──────────────────────────────┐    │
│  │                                                                  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │    │
│  │  │ Message  │  │  Config  │  │  State   │  │    Tool      │   │    │
│  │  │ Protocol │  │ Manager  │  │ Manager  │  │  Registry    │   │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │    │
│  │                                                                  │    │
│  │  ┌────────────────────────────────────────────────────────┐    │    │
│  │  │              Communication (MessageBus)                 │    │    │
│  │  └────────────────────────────────────────────────────────┘    │    │
│  │                                                                  │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Features

### Core Layer
- **Message Protocol**: Structured message types for agent communication
- **Configuration**: Flexible YAML/JSON configuration system
- **State Management**: Agent lifecycle and task state tracking
- **Tool System**: Extensible tool interface with registry
- **Communication**: Message bus for multi-agent coordination

### Intelligence Layer
- **LLM Integration**: Support for OpenAI, Anthropic, and local models
- **Planning**: LLM-powered task decomposition and planning
- **Reasoning**: ReAct, Chain-of-Thought, and other reasoning patterns
- **Memory**: Short-term, long-term, and working memory systems
- **Custom Prompts**: Flexible prompt template system

## Quick Start

### Basic Agent

```python
from Agents.utils import BaseAgent, AgentConfig, TaskMessage, ResultMessage

class MyAgent(BaseAgent):
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        result = await self.do_work(task.task_params)
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data=result,
        )

config = AgentConfig(agent_name="MyAgent")
agent = MyAgent(config)
await agent.initialize()
await agent.start()
```

### Planning Agent (with LLM)

```python
from Agents.utils import PlanningAgent, AgentConfig, LLMConfig, LLMProvider

config = AgentConfig(
    agent_name="SmartAgent",
    llm=LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4",
        api_key="your-api-key",
    ),
)

agent = PlanningAgent(config)
await agent.initialize()

# Create and execute a plan
plan = await agent.create_plan(
    task="Build a REST API",
    constraints=["Use Python", "Include tests"],
)

print(agent.print_plan())
await agent.execute_plan()
```

### Code Builder Example

```python
from Agents.examples.code_builder_agent import CodeBuilderAgent

agent = CodeBuilderAgent(
    api_key="your-api-key",
    model="gpt-4",
    workspace="./my_project",
)

await agent.initialize()
await agent.build(
    task="Create a Python calculator with add, subtract, multiply, divide",
    constraints=["Use classes", "Include error handling"],
)
```

## Requirements

```bash
# Core
pip install pyyaml>=6.0

# LLM Support (install as needed)
pip install openai>=1.0.0      # For OpenAI
pip install anthropic>=0.18.0  # For Anthropic Claude
pip install httpx>=0.24.0      # For local models
```

## Running Tests

```bash
cd Agents/examples
python test_code_builder.py
```

## License

MIT
