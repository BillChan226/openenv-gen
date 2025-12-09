"""
Prompt Template Module - Manages prompt templates for LLM interactions

Supports:
- Template definition and rendering
- Variable substitution
- Prompt composition
- Built-in templates for common patterns
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from string import Template
import json
import re


@dataclass
class PromptTemplate:
    """
    Prompt template with variable substitution
    
    Usage:
        template = PromptTemplate(
            name="task_planner",
            template="Plan the following task: {task}\nConstraints: {constraints}",
            variables=["task", "constraints"]
        )
        prompt = template.render(task="Build a website", constraints="Use Python")
    """
    name: str
    template: str
    description: str = ""
    variables: list[str] = field(default_factory=list)
    examples: list[dict] = field(default_factory=list)
    
    def render(self, **kwargs) -> str:
        """
        Render template with variables
        
        Args:
            **kwargs: Variable values
            
        Returns:
            Rendered prompt string
        """
        result = self.template
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            result = result.replace(f"{{{key}}}", str(value))
        return result
    
    def validate(self, **kwargs) -> tuple[bool, list[str]]:
        """
        Validate that all required variables are provided
        
        Returns:
            (is_valid, missing_variables)
        """
        missing = [v for v in self.variables if v not in kwargs]
        return len(missing) == 0, missing
    
    def get_variables(self) -> list[str]:
        """Extract variables from template"""
        pattern = r'\{(\w+)\}'
        return list(set(re.findall(pattern, self.template)))


class PromptBuilder:
    """
    Fluent interface for building prompts
    
    Usage:
        prompt = (PromptBuilder()
            .system("You are a helpful assistant.")
            .context("The user is working on a Python project.")
            .task("Help them debug their code.")
            .constraints(["Be concise", "Provide working code"])
            .examples([{"input": "...", "output": "..."}])
            .build())
    """
    
    def __init__(self):
        self._system: str = ""
        self._context: str = ""
        self._task: str = ""
        self._constraints: list[str] = []
        self._examples: list[dict] = []
        self._additional: list[str] = []
        self._format: str = ""
    
    def system(self, content: str) -> "PromptBuilder":
        """Set system/role description"""
        self._system = content
        return self
    
    def context(self, content: str) -> "PromptBuilder":
        """Add context information"""
        self._context = content
        return self
    
    def task(self, content: str) -> "PromptBuilder":
        """Set the main task"""
        self._task = content
        return self
    
    def constraints(self, items: list[str]) -> "PromptBuilder":
        """Add constraints/rules"""
        self._constraints.extend(items)
        return self
    
    def examples(self, items: list[dict]) -> "PromptBuilder":
        """Add few-shot examples"""
        self._examples.extend(items)
        return self
    
    def additional(self, content: str) -> "PromptBuilder":
        """Add additional instructions"""
        self._additional.append(content)
        return self
    
    def output_format(self, format_spec: str) -> "PromptBuilder":
        """Specify output format"""
        self._format = format_spec
        return self
    
    def build(self) -> str:
        """Build the final prompt"""
        parts = []
        
        if self._system:
            parts.append(self._system)
        
        if self._context:
            parts.append(f"\n## Context\n{self._context}")
        
        if self._task:
            parts.append(f"\n## Task\n{self._task}")
        
        if self._constraints:
            constraints_text = "\n".join(f"- {c}" for c in self._constraints)
            parts.append(f"\n## Constraints\n{constraints_text}")
        
        if self._examples:
            examples_text = ""
            for i, ex in enumerate(self._examples, 1):
                examples_text += f"\n### Example {i}\n"
                examples_text += f"Input: {ex.get('input', '')}\n"
                examples_text += f"Output: {ex.get('output', '')}\n"
            parts.append(f"\n## Examples{examples_text}")
        
        if self._additional:
            additional_text = "\n".join(self._additional)
            parts.append(f"\n## Additional Instructions\n{additional_text}")
        
        if self._format:
            parts.append(f"\n## Output Format\n{self._format}")
        
        return "\n".join(parts)
    
    def build_system_and_user(self) -> tuple[str, str]:
        """
        Build as separate system and user messages
        
        Returns:
            (system_prompt, user_prompt)
        """
        system = self._system or "You are a helpful AI assistant."
        
        user_parts = []
        
        if self._context:
            user_parts.append(f"Context: {self._context}")
        
        if self._task:
            user_parts.append(f"Task: {self._task}")
        
        if self._constraints:
            constraints_text = "\n".join(f"- {c}" for c in self._constraints)
            user_parts.append(f"Constraints:\n{constraints_text}")
        
        if self._examples:
            examples_text = ""
            for i, ex in enumerate(self._examples, 1):
                examples_text += f"\nExample {i}:\n"
                examples_text += f"Input: {ex.get('input', '')}\n"
                examples_text += f"Output: {ex.get('output', '')}\n"
            user_parts.append(f"Examples:{examples_text}")
        
        if self._additional:
            user_parts.append("\n".join(self._additional))
        
        if self._format:
            user_parts.append(f"Output Format: {self._format}")
        
        return system, "\n\n".join(user_parts)


# ===== Built-in Templates =====

PLANNER_SYSTEM_PROMPT = """You are an expert task planner. Your job is to break down complex tasks into smaller, actionable steps.

For each step, provide:
1. A clear description of what needs to be done
2. The expected outcome
3. Any dependencies on previous steps

Always think step by step and ensure the plan is complete and executable."""

PLANNER_TEMPLATE = PromptTemplate(
    name="task_planner",
    description="Breaks down a complex task into actionable steps",
    template="""Analyze and create a detailed plan for the following task:

## Task
{task}

## Available Tools
{tools}

## Constraints
{constraints}

## Output Format
Respond with a JSON array of steps:
```json
[
  {{
    "step_id": 1,
    "description": "Step description",
    "action": "tool_name or 'think'",
    "action_input": {{}},
    "expected_output": "What this step should produce",
    "dependencies": []
  }}
]
```

Create a comprehensive plan:""",
    variables=["task", "tools", "constraints"]
)


REACT_SYSTEM_PROMPT = """You are a reasoning agent that solves problems step by step.

Follow the ReAct (Reasoning + Acting) pattern:
1. Thought: Analyze the current situation and decide what to do next
2. Action: Choose a tool to use or decide to give final answer
3. Observation: Observe the result of your action
4. Repeat until you can provide a final answer

Always explain your reasoning before taking an action."""

REACT_TEMPLATE = PromptTemplate(
    name="react_step",
    description="Single step in ReAct reasoning loop",
    template="""## Task
{task}

## Available Tools
{tools}

## Previous Steps
{history}

## Current Observation
{observation}

Based on the above, provide your next step.

Respond in this exact format:
Thought: [Your reasoning about what to do next]
Action: [tool_name OR "finish"]
Action Input: [JSON input for the tool OR final answer if Action is "finish"]
""",
    variables=["task", "tools", "history", "observation"]
)


SUMMARIZER_TEMPLATE = PromptTemplate(
    name="summarizer",
    description="Summarizes content",
    template="""Summarize the following content:

{content}

Requirements:
- Keep the summary concise but comprehensive
- Preserve key information and main points
- Use clear and simple language
{additional_requirements}

Summary:""",
    variables=["content", "additional_requirements"]
)


ANALYZER_TEMPLATE = PromptTemplate(
    name="analyzer",
    description="Analyzes content and extracts information",
    template="""Analyze the following content and extract relevant information:

## Content
{content}

## Analysis Focus
{focus}

## Output Format
{output_format}

Analysis:""",
    variables=["content", "focus", "output_format"]
)


CODE_GENERATOR_TEMPLATE = PromptTemplate(
    name="code_generator",
    description="Generates code based on requirements",
    template="""Generate code based on the following requirements:

## Requirements
{requirements}

## Language
{language}

## Constraints
{constraints}

## Context (existing code)
{context}

Provide clean, well-documented code:""",
    variables=["requirements", "language", "constraints", "context"]
)


EVALUATOR_TEMPLATE = PromptTemplate(
    name="evaluator",
    description="Evaluates results against criteria",
    template="""Evaluate the following result against the given criteria:

## Task Description
{task}

## Result to Evaluate
{result}

## Evaluation Criteria
{criteria}

Provide your evaluation in the following format:
1. Score (1-10): 
2. Strengths:
3. Weaknesses:
4. Suggestions for improvement:
5. Overall assessment:""",
    variables=["task", "result", "criteria"]
)


class PromptRegistry:
    """
    Registry for managing prompt templates
    """
    
    def __init__(self):
        self._templates: dict[str, PromptTemplate] = {}
        self._register_builtin()
    
    def _register_builtin(self) -> None:
        """Register built-in templates"""
        builtins = [
            PLANNER_TEMPLATE,
            REACT_TEMPLATE,
            SUMMARIZER_TEMPLATE,
            ANALYZER_TEMPLATE,
            CODE_GENERATOR_TEMPLATE,
            EVALUATOR_TEMPLATE,
        ]
        for template in builtins:
            self.register(template)
    
    def register(self, template: PromptTemplate) -> None:
        """Register a template"""
        self._templates[template.name] = template
    
    def get(self, name: str) -> Optional[PromptTemplate]:
        """Get template by name"""
        return self._templates.get(name)
    
    def render(self, name: str, **kwargs) -> str:
        """Render a template by name"""
        template = self.get(name)
        if not template:
            raise ValueError(f"Template not found: {name}")
        return template.render(**kwargs)
    
    def list_templates(self) -> list[str]:
        """List all template names"""
        return list(self._templates.keys())
    
    def __contains__(self, name: str) -> bool:
        return name in self._templates


# Global registry
prompt_registry = PromptRegistry()


# ===== Helper Functions =====

def format_tools_for_prompt(tools: list[dict]) -> str:
    """
    Format tool definitions for inclusion in prompts
    
    Args:
        tools: List of tool definitions (from ToolRegistry.to_openai_functions())
        
    Returns:
        Formatted string describing available tools
    """
    lines = []
    for tool in tools:
        name = tool.get("name", "unknown")
        desc = tool.get("description", "")
        params = tool.get("parameters", {}).get("properties", {})
        
        param_strs = []
        for pname, pinfo in params.items():
            ptype = pinfo.get("type", "any")
            pdesc = pinfo.get("description", "")
            param_strs.append(f"    - {pname} ({ptype}): {pdesc}")
        
        lines.append(f"### {name}")
        lines.append(f"{desc}")
        if param_strs:
            lines.append("Parameters:")
            lines.extend(param_strs)
        lines.append("")
    
    return "\n".join(lines)


def format_history_for_prompt(history: list[dict]) -> str:
    """
    Format action history for inclusion in prompts
    
    Args:
        history: List of {thought, action, action_input, observation}
        
    Returns:
        Formatted history string
    """
    if not history:
        return "No previous steps."
    
    lines = []
    for i, step in enumerate(history, 1):
        lines.append(f"### Step {i}")
        if "thought" in step:
            lines.append(f"Thought: {step['thought']}")
        if "action" in step:
            lines.append(f"Action: {step['action']}")
        if "action_input" in step:
            input_str = json.dumps(step['action_input']) if isinstance(step['action_input'], dict) else str(step['action_input'])
            lines.append(f"Action Input: {input_str}")
        if "observation" in step:
            lines.append(f"Observation: {step['observation']}")
        lines.append("")
    
    return "\n".join(lines)

