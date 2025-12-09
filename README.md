# AgentForge

A Multi-Agent System Framework for building intelligent agent-based applications.

**Author:** EchoRaven (haibot2@illinois.edu)

## Project Structure

```
AgentForge/
├── Agents/
│   ├── utils/                    # 核心基础设施 (已完成)
│   │   ├── message.py           # 消息协议
│   │   ├── config.py            # 配置管理
│   │   ├── state.py             # 状态管理
│   │   ├── tool.py              # 工具接口
│   │   ├── base_agent.py        # Agent基类
│   │   ├── communication.py     # 通信机制
│   │   └── examples/            # 使用示例
│   │
│   ├── Sandbox-Creator/         # 环境创建系统 (待开发)
│   ├── Task-Creator/            # 任务创建系统 (待开发)
│   ├── Task-Verifier/           # 任务验证系统 (待开发)
│   ├── Target-Agent/            # 目标Agent (待开发)
│   ├── Data-Creator/            # 数据创建系统 (待开发)
│   └── Sandbox-Verifier/        # 环境验证系统 (待开发)
│
└── README.md
```

## Core Components (utils/)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          BaseAgent                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ Message  │  │  Config  │  │  State   │  │    Tool      │    │
│  │ Protocol │  │ Manager  │  │ Manager  │  │  Registry    │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                    Communication Layer                           │
│        (MessageBus / EventEmitter / MessageRouter)              │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

- **Message Protocol**: Structured message types for agent communication
- **Configuration**: Flexible YAML/JSON configuration system
- **State Management**: Agent lifecycle and task state tracking
- **Tool System**: Extensible tool interface with registry
- **Communication**: Message bus for multi-agent coordination

## Quick Start

```python
from Agents.utils import BaseAgent, AgentConfig, TaskMessage, ResultMessage

class MyAgent(BaseAgent):
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        # Your task processing logic
        result = await self.do_work(task.task_params)
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data=result,
        )

# Create and run
config = AgentConfig(agent_name="MyAgent")
agent = MyAgent(config)
await agent.initialize()
await agent.start()
```

## Requirements

- Python >= 3.10
- pyyaml >= 6.0

## License

MIT
