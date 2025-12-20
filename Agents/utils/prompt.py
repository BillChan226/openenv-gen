"""
Prompt Template Module - Jinja2-based prompt management system

Inspired by OpenHands, this module provides:
- Jinja2 template rendering with includes
- Structured prompt sections with XML-like tags
- Dynamic context injection
- Prompt refinement and cleanup
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, Template, BaseLoader, TemplateNotFound


class StringLoader(BaseLoader):
    """Loader that loads templates from a dictionary of strings."""
    
    def __init__(self, templates: dict[str, str]):
        self.templates = templates
    
    def get_source(self, environment, template):
        if template in self.templates:
            source = self.templates[template]
            return source, template, lambda: True
        raise TemplateNotFound(template)


@dataclass
class RuntimeInfo:
    """Runtime information for prompt context."""
    date: str = ""
    working_dir: str = ""
    available_hosts: dict[str, int] = field(default_factory=dict)
    additional_instructions: str = ""


@dataclass 
class ProjectInfo:
    """Information about the project being generated."""
    name: str = ""
    description: str = ""
    domain_type: str = "custom"
    output_dir: str = ""


class PromptManager:
    """
    Manages prompt templates using Jinja2.
    
    This class loads templates from a directory and provides methods to render them
    with dynamic context. Supports template includes and structured sections.
    
    Usage:
        manager = PromptManager(prompt_dir="./prompts")
        system_msg = manager.get_system_message(
            project_info=project_info,
            runtime_info=runtime_info
        )
    """
    
    def __init__(
        self,
        prompt_dir: Optional[str] = None,
        system_prompt_filename: str = "system_prompt.j2",
        fallback_templates: Optional[dict[str, str]] = None,
    ):
        """
        Initialize PromptManager.
        
        Args:
            prompt_dir: Directory containing .j2 template files
            system_prompt_filename: Name of the system prompt template file
            fallback_templates: Dictionary of template strings to use if files not found
        """
        self.prompt_dir = prompt_dir
        self.system_prompt_filename = system_prompt_filename
        self.fallback_templates = fallback_templates or {}
        
        # Initialize Jinja2 environment
        if prompt_dir and Path(prompt_dir).exists():
            self.env = Environment(
                loader=FileSystemLoader(prompt_dir),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        elif fallback_templates:
            self.env = Environment(
                loader=StringLoader(fallback_templates),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.env = Environment(trim_blocks=True, lstrip_blocks=True)
        
        # Load templates
        self._system_template: Optional[Template] = None
        self._user_template: Optional[Template] = None
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load templates from directory or fallback."""
        try:
            self._system_template = self.env.get_template(self.system_prompt_filename)
        except TemplateNotFound:
            # Use default system prompt
            self._system_template = self.env.from_string(DEFAULT_SYSTEM_PROMPT)
        
        try:
            self._user_template = self.env.get_template("user_prompt.j2")
        except TemplateNotFound:
            self._user_template = self.env.from_string(DEFAULT_USER_PROMPT)
    
    def get_system_message(self, **context) -> str:
        """
        Render the system prompt template.
        
        Args:
            **context: Variables to pass to the template
            
        Returns:
            Rendered system message
        """
        if not self._system_template:
            return ""
        
        rendered = self._system_template.render(**context).strip()
        return refine_prompt(rendered)
    
    def get_user_message(self, **context) -> str:
        """
        Render the user prompt template.
        
        Args:
            **context: Variables to pass to the template
            
        Returns:
            Rendered user message
        """
        if not self._user_template:
            return ""
        
        return self._user_template.render(**context).strip()
    
    def render_template(self, template_name: str, **context) -> str:
        """
        Render a named template.
        
        Args:
            template_name: Name of the template file (e.g., "reflection.j2")
            **context: Variables to pass to the template
            
        Returns:
            Rendered template string
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context).strip()
        except TemplateNotFound:
            return ""
    
    def render_string(self, template_string: str, **context) -> str:
        """
        Render a template from a string.
        
        Args:
            template_string: Jinja2 template string
            **context: Variables to pass to the template
            
        Returns:
            Rendered string
        """
        template = self.env.from_string(template_string)
        return template.render(**context).strip()


def refine_prompt(prompt: str) -> str:
    """
    Refine and clean up a prompt string.
    
    - Remove excessive whitespace
    - Normalize line endings
    - Strip trailing spaces
    
    Args:
        prompt: Raw prompt string
        
    Returns:
        Cleaned prompt string
    """
    lines = prompt.split('\n')
    
    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in lines]
    
    # Remove excessive blank lines (more than 2 consecutive)
    result_lines = []
    blank_count = 0
    for line in lines:
        if line == '':
            blank_count += 1
            if blank_count <= 2:
                result_lines.append(line)
        else:
            blank_count = 0
            result_lines.append(line)
    
    return '\n'.join(result_lines).strip()


# ===== Default Templates =====

DEFAULT_SYSTEM_PROMPT = """You are an expert code generator that creates high-quality, production-ready code.

<ROLE>
Your primary role is to generate clean, well-structured code files for web applications.
You should be thorough, methodical, and prioritize code quality.
</ROLE>

<EFFICIENCY>
* Combine multiple operations when possible
* Use efficient patterns and avoid redundancy
* Generate complete files rather than fragments
</EFFICIENCY>

<CODE_QUALITY>
* Write clean, efficient code with minimal but useful comments
* Follow language-specific conventions and best practices
* Ensure proper error handling and edge case coverage
* Use consistent naming conventions
* Place imports at the top of files
</CODE_QUALITY>

<FILE_GUIDELINES>
* Always use absolute paths when specified
* Do not create duplicate files with different names
* Ensure generated code is syntactically correct
* For JSON files: Use proper formatting with 2-space indentation
</FILE_GUIDELINES>

<OUTPUT_FORMAT>
* Output PURE CODE ONLY - no markdown fences, no line numbers
* The output should be directly saveable as a file
* Do not include explanatory text in code output
</OUTPUT_FORMAT>

{% if project_info %}
<PROJECT_CONTEXT>
Project: {{ project_info.name }}
Description: {{ project_info.description }}
Domain: {{ project_info.domain_type }}
Output Directory: {{ project_info.output_dir }}
</PROJECT_CONTEXT>
{% endif %}

{% if runtime_info %}
<RUNTIME_INFO>
Date: {{ runtime_info.date }}
Working Directory: {{ runtime_info.working_dir }}
{% if runtime_info.additional_instructions %}
Additional Instructions: {{ runtime_info.additional_instructions }}
{% endif %}
</RUNTIME_INFO>
{% endif %}

{% if tools_description %}
<AVAILABLE_TOOLS>
{{ tools_description }}
</AVAILABLE_TOOLS>
{% endif %}

{% if memory_context %}
<MEMORY_CONTEXT>
{{ memory_context }}
</MEMORY_CONTEXT>
{% endif %}
"""

DEFAULT_USER_PROMPT = """{% if task %}
## Task
{{ task }}
{% endif %}

{% if context %}
## Context
{{ context }}
{% endif %}

{% if constraints %}
## Constraints
{% for constraint in constraints %}
- {{ constraint }}
{% endfor %}
{% endif %}

{% if existing_files %}
## Existing Files
{% for file in existing_files %}
- {{ file }}
{% endfor %}
{% endif %}
"""


# ===== Template Library =====

TEMPLATE_LIBRARY = {
    "think_before_file": """Before generating {{ file_path }}, analyze what's needed:

FILE TO GENERATE: {{ file_path }}
PURPOSE: {{ purpose }}

{% if existing_files %}
ALREADY GENERATED FILES:
{% for f in existing_files %}
- {{ f }}
{% endfor %}
{% else %}
NO FILES GENERATED YET - this is the first file.
{% endif %}

Think step by step:
1. What already generated files should I read for context?
2. What patterns should I search (grep) for?
3. What's my approach for generating this file?
4. What considerations/pitfalls should I be careful about?

Respond in JSON format:
{
  "needs_context": [],
  "needs_grep": [],
  "approach": "...",
  "considerations": ["..."]
}
""",

    "reflection": """Review the generated code for issues:

FILES GENERATED:
{% for file in files %}
- {{ file }}
{% endfor %}

Check for:
1. Syntax errors
2. Missing imports
3. Undefined references
4. Type mismatches
5. Incomplete implementations

{% if enable_runtime_test %}
Also check if the code can run successfully.
{% endif %}

List any issues found (empty list if none):
""",

    "fix_issues": """Fix the following issues in the code:

ISSUES:
{% for issue in issues %}
{{ loop.index }}. {{ issue }}
{% endfor %}

For each issue:
1. Identify the file and location
2. Determine the fix needed
3. Apply the fix using available tools

Provide fixes in order of priority.
""",

    "plan_phase": """Plan the files to generate for the {{ phase }} phase.

Environment: {{ env_name }}
Description: {{ env_description }}

{% if existing_files %}
Already generated:
{% for f in existing_files %}
- {{ f }}
{% endfor %}
{% endif %}

{% if reference_files %}
Reference structure:
{% for f in reference_files %}
- {{ f.path }}: {{ f.purpose }}
{% endfor %}
{% endif %}

Create a plan with files to generate. For each file specify:
- path: File path
- purpose: What this file does
- dependencies: Other files it depends on
- instructions: Specific requirements

Output as JSON array.
""",

    "memory_summary": """Summarize the following events for context preservation:

<PREVIOUS_SUMMARY>
{{ previous_summary }}
</PREVIOUS_SUMMARY>

<EVENTS>
{% for event in events %}
{{ event }}
{% endfor %}
</EVENTS>

Create a concise summary tracking:
- USER_CONTEXT: Key requirements and goals
- COMPLETED: Tasks done with brief results
- PENDING: Tasks still needed
- CURRENT_STATE: Relevant state information
- CODE_STATE: File paths and key structures (if applicable)

Keep the summary focused and actionable.
""",
}


def get_template(name: str) -> str:
    """Get a template from the library by name."""
    return TEMPLATE_LIBRARY.get(name, "")


# ===== Helper Functions =====

def format_tools_for_prompt(tools: list[dict]) -> str:
    """
    Format tool definitions for inclusion in prompts.
    
    Args:
        tools: List of tool definitions in OpenAI function format
        
    Returns:
        Formatted string describing available tools
    """
    lines = []
    for tool in tools:
        func = tool.get("function", tool)
        name = func.get("name", "unknown")
        desc = func.get("description", "")
        params = func.get("parameters", {}).get("properties", {})
        required = func.get("parameters", {}).get("required", [])
        
        lines.append(f"### {name}")
        lines.append(f"{desc}")
        
        if params:
            lines.append("Parameters:")
            for pname, pinfo in params.items():
                ptype = pinfo.get("type", "any")
                pdesc = pinfo.get("description", "")
                req = "(required)" if pname in required else "(optional)"
                lines.append(f"  - {pname} ({ptype}) {req}: {pdesc}")
        
        lines.append("")
    
    return "\n".join(lines)


def format_history_for_prompt(history: list[dict]) -> str:
    """
    Format action history for inclusion in prompts.
    
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
            import json
            input_str = json.dumps(step['action_input']) if isinstance(step['action_input'], dict) else str(step['action_input'])
            lines.append(f"Action Input: {input_str}")
        if "observation" in step:
            obs = step['observation']
            if len(str(obs)) > 500:
                obs = str(obs)[:500] + "... [truncated]"
            lines.append(f"Observation: {obs}")
        lines.append("")
    
    return "\n".join(lines)


# ========== PLANNER PROMPTS ==========

class PromptTemplate:
    """Simple prompt template with variable substitution."""
    
    def __init__(self, template: str = None, name: str = None, variables: list = None):
        self.template = template or ""
        self.name = name
        self.variables = variables or []
    
    def format(self, **kwargs) -> str:
        """Format the template with the given keyword arguments."""
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    
    def render(self, **kwargs) -> str:
        """Alias for format() for compatibility."""
        return self.format(**kwargs)
    
    def __str__(self) -> str:
        return self.template


PLANNER_SYSTEM_PROMPT = """You are a Planning Agent responsible for creating and managing execution plans.

Your role is to:
1. Analyze tasks and break them down into actionable steps
2. Create detailed plans with clear objectives
3. Assign priorities and estimate durations
4. Monitor progress and adjust plans as needed

Guidelines:
- Be specific and actionable in your step descriptions
- Consider dependencies between steps
- Estimate realistic timeframes
- Include contingencies for potential issues
"""


PLANNER_TEMPLATE = """## Task
{task_description}

## Current Context
{context}

## Available Tools
{tools}

## Instructions
Create a detailed plan to accomplish this task. For each step:
1. Describe what needs to be done
2. Specify which tool(s) to use
3. Define success criteria
4. Note any dependencies on other steps

Output your plan in the following format:

### Step 1: [Step Title]
- **Action**: [What to do]
- **Tool**: [Tool to use]
- **Expected Outcome**: [What success looks like]
- **Dependencies**: [Any previous steps required]

[Continue for all steps...]

### Summary
- Total steps: [N]
- Estimated duration: [Time estimate]
- Critical path: [Key dependencies]
"""


# ========== REACT PROMPTS ==========

REACT_SYSTEM_PROMPT = """You are an AI assistant that uses the ReAct (Reasoning + Acting) framework.

For each step:
1. **Thought**: Reason about what to do next based on the current situation
2. **Action**: Choose an action from the available tools
3. **Action Input**: Provide the input for the action
4. **Observation**: Observe the result and learn from it

Guidelines:
- Think step by step before acting
- Use tools effectively to gather information
- Learn from observations to refine your approach
- Continue until the task is complete or you need to ask for help

Available tools will be provided for each task. Use them wisely.
"""


REACT_TEMPLATE = """## Task
{task_description}

## Available Tools
{tools}

## Previous Steps
{history}

## Instructions
Based on the task and previous steps:
1. Think about what to do next
2. Choose an appropriate action
3. Execute the action with proper inputs

Format your response as:

Thought: [Your reasoning about what to do next]
Action: [The tool to use]
Action Input: [The input for the tool in JSON format]

Or if you're done:

Thought: [Final reasoning]
Final Answer: [Your final response to the task]
"""
