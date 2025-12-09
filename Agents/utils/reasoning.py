"""
Reasoning Module - ReAct (Reasoning + Acting) engine

Supports:
- ReAct loop for step-by-step reasoning
- Tool execution integration
- Thought chain management
- Multiple reasoning strategies
- Custom prompt templates
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Optional
from uuid import uuid4
import json
import re
import logging

from .llm import LLM, Message, LLMConfig, LLMResponse
from .prompt import (
    PromptTemplate,
    REACT_SYSTEM_PROMPT, 
    REACT_TEMPLATE, 
    format_tools_for_prompt, 
    format_history_for_prompt
)
from .memory import WorkingMemory, AgentMemory
from .tool import ToolRegistry, ToolResult


class ReasoningAction(Enum):
    """Types of actions in reasoning"""
    THINK = "think"      # Internal reasoning
    TOOL = "tool"        # Tool execution
    FINISH = "finish"    # Final answer
    ASK = "ask"          # Ask for clarification


@dataclass
class ReasoningStep:
    """Single step in reasoning chain"""
    step_id: int
    thought: str
    action: str  # Tool name, "think", "finish", or "ask"
    action_input: Any = None
    observation: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ReasoningResult:
    """Result of reasoning process"""
    success: bool
    answer: Any = None
    steps: list[ReasoningStep] = field(default_factory=list)
    total_tokens: int = 0
    total_time: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "answer": self.answer,
            "steps": [s.to_dict() for s in self.steps],
            "total_tokens": self.total_tokens,
            "total_time": self.total_time,
            "error": self.error,
        }


# Default templates (can be customized)
DEFAULT_REACT_SYSTEM_PROMPT = REACT_SYSTEM_PROMPT

DEFAULT_REACT_TEMPLATE = REACT_TEMPLATE


class ReActEngine:
    """
    ReAct (Reasoning + Acting) Engine
    
    Implements the ReAct pattern for step-by-step problem solving:
    1. Thought: Analyze the situation
    2. Action: Choose a tool or decide to finish
    3. Observation: Get result of action
    4. Repeat until done
    
    Usage:
        # With default templates
        engine = ReActEngine(llm_config, tool_registry)
        result = await engine.run("What is the capital of France?")
        
        # With custom templates
        custom_system = "You are a specialized reasoning agent..."
        custom_template = PromptTemplate(
            name="my_react",
            template="Task: {task}\\nTools: {tools}\\n...",
            variables=["task", "tools", "history", "observation"]
        )
        engine = ReActEngine(
            llm_config,
            tool_registry,
            system_prompt=custom_system,
            react_template=custom_template,
        )
    """
    
    def __init__(
        self,
        llm_config: LLMConfig,
        tool_registry: ToolRegistry = None,
        max_steps: int = 10,
        memory: AgentMemory = None,
        system_prompt: str = None,
        react_template: PromptTemplate = None,
    ):
        """
        Initialize ReActEngine
        
        Args:
            llm_config: LLM configuration
            tool_registry: Registry of available tools
            max_steps: Maximum reasoning steps
            memory: Agent memory system
            system_prompt: Custom system prompt (optional)
            react_template: Custom ReAct template (optional)
        """
        self.llm = LLM(llm_config)
        self.tools = tool_registry or ToolRegistry()
        self.max_steps = max_steps
        self.memory = memory
        self._system_prompt = system_prompt or DEFAULT_REACT_SYSTEM_PROMPT
        self._react_template = react_template or DEFAULT_REACT_TEMPLATE
        self._logger = logging.getLogger("ReActEngine")
    
    @property
    def system_prompt(self) -> str:
        """Get current system prompt"""
        return self._system_prompt
    
    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Set custom system prompt"""
        self._system_prompt = value
    
    @property
    def react_template(self) -> PromptTemplate:
        """Get current ReAct template"""
        return self._react_template
    
    @react_template.setter
    def react_template(self, value: PromptTemplate) -> None:
        """Set custom ReAct template"""
        self._react_template = value
    
    def set_templates(
        self,
        system_prompt: str = None,
        react_template: PromptTemplate = None,
    ) -> None:
        """
        Set custom templates
        
        Args:
            system_prompt: Custom system prompt
            react_template: Custom ReAct template
        """
        if system_prompt:
            self._system_prompt = system_prompt
        if react_template:
            self._react_template = react_template
    
    def reset_templates(self) -> None:
        """Reset to default templates"""
        self._system_prompt = DEFAULT_REACT_SYSTEM_PROMPT
        self._react_template = DEFAULT_REACT_TEMPLATE
    
    async def run(
        self,
        task: str,
        context: str = None,
        tools: list[dict] = None,
        **template_vars,
    ) -> ReasoningResult:
        """
        Run ReAct reasoning loop
        
        Args:
            task: Task/question to solve
            context: Additional context
            tools: Tool definitions (uses registered tools if not provided)
            **template_vars: Additional variables for custom templates
            
        Returns:
            Reasoning result with answer and step history
        """
        start_time = datetime.now()
        steps: list[ReasoningStep] = []
        total_tokens = 0
        
        # Get tool definitions
        if tools is None:
            tools = self.tools.to_openai_functions()
        tools_str = format_tools_for_prompt(tools) if tools else "No tools available. Use 'think' for reasoning or 'finish' to provide final answer."
        
        # Initialize working memory if available
        if self.memory:
            self.memory.working.set_task(str(uuid4()))
            self.memory.working.set("task", task)
        
        current_observation = context or "Task started. Begin your reasoning."
        
        for step_num in range(1, self.max_steps + 1):
            # Format history
            history_str = format_history_for_prompt([s.to_dict() for s in steps])
            
            # Build template variables
            template_variables = {
                "task": task,
                "tools": tools_str,
                "history": history_str,
                "observation": current_observation,
                **template_vars,  # Allow custom variables
            }
            
            # Generate next step
            prompt = self._react_template.render(**template_variables)
            
            response = await self.llm.chat_with_response(
                prompt=prompt,
                system=self._system_prompt,
                temperature=0.7,
            )
            
            total_tokens += response.total_tokens
            
            # Parse response
            thought, action, action_input = self._parse_response(response.content)
            
            step = ReasoningStep(
                step_id=step_num,
                thought=thought,
                action=action,
                action_input=action_input,
            )
            
            # Execute action
            if action.lower() == "finish":
                step.observation = "Task completed."
                steps.append(step)
                
                # Store in memory
                if self.memory:
                    self.memory.working.add_step(
                        thought=thought,
                        action=action,
                        action_input=action_input,
                        observation=step.observation,
                    )
                
                return ReasoningResult(
                    success=True,
                    answer=action_input,
                    steps=steps,
                    total_tokens=total_tokens,
                    total_time=(datetime.now() - start_time).total_seconds(),
                )
            
            elif action.lower() == "think":
                step.observation = "Thought recorded. Continue reasoning."
                current_observation = step.observation
                
            elif action.lower() == "ask":
                step.observation = f"Need clarification: {action_input}"
                steps.append(step)
                
                return ReasoningResult(
                    success=False,
                    answer=action_input,
                    steps=steps,
                    total_tokens=total_tokens,
                    total_time=(datetime.now() - start_time).total_seconds(),
                    error="Clarification needed",
                )
            
            else:
                # Execute tool
                try:
                    observation = await self._execute_tool(action, action_input)
                    step.observation = observation
                    current_observation = observation
                except Exception as e:
                    step.observation = f"Error executing {action}: {str(e)}"
                    current_observation = step.observation
            
            steps.append(step)
            
            # Store in memory
            if self.memory:
                self.memory.working.add_step(
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=step.observation,
                )
        
        # Max steps reached
        return ReasoningResult(
            success=False,
            steps=steps,
            total_tokens=total_tokens,
            total_time=(datetime.now() - start_time).total_seconds(),
            error=f"Max steps ({self.max_steps}) reached without completion",
        )
    
    async def run_stream(
        self,
        task: str,
        context: str = None,
        tools: list[dict] = None,
        **template_vars,
    ) -> AsyncIterator[ReasoningStep]:
        """
        Run ReAct with streaming steps
        
        Yields:
            Each reasoning step as it's completed
        """
        # Get tool definitions
        if tools is None:
            tools = self.tools.to_openai_functions()
        tools_str = format_tools_for_prompt(tools) if tools else "No tools available."
        
        steps: list[ReasoningStep] = []
        current_observation = context or "Task started."
        
        for step_num in range(1, self.max_steps + 1):
            history_str = format_history_for_prompt([s.to_dict() for s in steps])
            
            template_variables = {
                "task": task,
                "tools": tools_str,
                "history": history_str,
                "observation": current_observation,
                **template_vars,
            }
            
            prompt = self._react_template.render(**template_variables)
            
            response = await self.llm.chat(
                prompt=prompt,
                system=self._system_prompt,
            )
            
            thought, action, action_input = self._parse_response(response)
            
            step = ReasoningStep(
                step_id=step_num,
                thought=thought,
                action=action,
                action_input=action_input,
            )
            
            if action.lower() == "finish":
                step.observation = "Task completed."
                yield step
                return
            
            elif action.lower() in ["think", "ask"]:
                step.observation = "Recorded."
                current_observation = step.observation
            
            else:
                try:
                    observation = await self._execute_tool(action, action_input)
                    step.observation = observation
                    current_observation = observation
                except Exception as e:
                    step.observation = f"Error: {str(e)}"
                    current_observation = step.observation
            
            steps.append(step)
            yield step
    
    def _parse_response(self, response: str) -> tuple[str, str, Any]:
        """
        Parse LLM response to extract thought, action, and action input
        
        Returns:
            (thought, action, action_input)
        """
        thought = ""
        action = "think"
        action_input = None
        
        # Extract Thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|$)', response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
        
        # Extract Action
        action_match = re.search(r'Action:\s*(\w+)', response, re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip()
        
        # Extract Action Input
        input_match = re.search(r'Action Input:\s*(.+?)(?=Thought:|Action:|$)', response, re.DOTALL | re.IGNORECASE)
        if input_match:
            input_str = input_match.group(1).strip()
            
            # Try to parse as JSON
            try:
                # Handle JSON in code blocks
                json_match = re.search(r'```(?:json)?\s*(.+?)\s*```', input_str, re.DOTALL)
                if json_match:
                    input_str = json_match.group(1)
                
                action_input = json.loads(input_str)
            except json.JSONDecodeError:
                # Keep as string
                action_input = input_str
        
        return thought, action, action_input
    
    async def _execute_tool(self, tool_name: str, tool_input: Any) -> str:
        """Execute a tool and return observation"""
        tool = self.tools.get(tool_name)
        
        if not tool:
            return f"Tool '{tool_name}' not found. Available tools: {', '.join(t.name for t in self.tools.get_all())}"
        
        # Prepare input
        if isinstance(tool_input, dict):
            kwargs = tool_input
        elif tool_input is None:
            kwargs = {}
        else:
            # Assume single parameter
            params = tool.definition.parameters
            if params:
                kwargs = {params[0].name: tool_input}
            else:
                kwargs = {}
        
        # Execute
        result = await tool(**kwargs)
        
        if result.success:
            return str(result.data) if result.data is not None else "Success (no output)"
        else:
            return f"Tool error: {result.error_message}"


class ChainOfThought:
    """
    Chain of Thought (CoT) reasoning
    
    Simpler than ReAct - just asks the LLM to think step by step
    
    Supports custom system prompt.
    """
    
    DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant that solves problems step by step. Show your reasoning process clearly before giving the final answer."
    
    def __init__(
        self, 
        llm_config: LLMConfig,
        system_prompt: str = None,
    ):
        self.llm = LLM(llm_config)
        self._system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
    
    @property
    def system_prompt(self) -> str:
        return self._system_prompt
    
    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        self._system_prompt = value
    
    async def reason(
        self,
        task: str,
        examples: list[dict] = None,
    ) -> str:
        """
        Perform chain of thought reasoning
        
        Args:
            task: Problem to solve
            examples: Few-shot examples with 'question' and 'reasoning'
            
        Returns:
            Final answer
        """
        prompt_parts = []
        
        # Add examples if provided
        if examples:
            prompt_parts.append("Here are some examples of step-by-step reasoning:\n")
            for i, ex in enumerate(examples, 1):
                prompt_parts.append(f"Example {i}:")
                prompt_parts.append(f"Question: {ex.get('question', '')}")
                prompt_parts.append(f"Reasoning: {ex.get('reasoning', '')}")
                prompt_parts.append("")
        
        prompt_parts.append(f"Now, solve this problem step by step:")
        prompt_parts.append(f"Question: {task}")
        prompt_parts.append("")
        prompt_parts.append("Let's think step by step:")
        
        response = await self.llm.chat(
            prompt="\n".join(prompt_parts),
            system=self._system_prompt,
        )
        
        return response


class SelfAsk:
    """
    Self-Ask reasoning pattern
    
    The model asks and answers sub-questions to reach the final answer
    
    Supports custom system prompt.
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant that solves problems by asking and answering sub-questions.

For each step, either:
1. Ask a follow-up question that helps solve the problem (format: "Follow-up: <question>")
2. Answer the follow-up question (format: "Intermediate answer: <answer>")
3. Provide the final answer (format: "Final answer: <answer>")

Think about what information you need to solve the problem."""
    
    def __init__(
        self, 
        llm_config: LLMConfig,
        system_prompt: str = None,
    ):
        self.llm = LLM(llm_config)
        self._system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
    
    @property
    def system_prompt(self) -> str:
        return self._system_prompt
    
    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        self._system_prompt = value
    
    async def reason(
        self,
        task: str,
        max_questions: int = 5,
    ) -> dict:
        """
        Perform self-ask reasoning
        
        Returns:
            Dict with 'answer' and 'qa_chain'
        """
        qa_chain = []
        current_context = task
        
        for _ in range(max_questions):
            response = await self.llm.chat(
                prompt=f"Problem: {task}\n\nContext so far:\n{current_context}\n\nWhat's your next step?",
                system=self._system_prompt,
            )
            
            # Check if final answer
            if "final answer:" in response.lower():
                match = re.search(r'final answer:\s*(.+)', response, re.IGNORECASE | re.DOTALL)
                if match:
                    return {
                        "answer": match.group(1).strip(),
                        "qa_chain": qa_chain,
                    }
            
            # Extract follow-up question
            followup_match = re.search(r'follow-up:\s*(.+?)(?=intermediate|final|$)', response, re.IGNORECASE | re.DOTALL)
            if followup_match:
                question = followup_match.group(1).strip()
                
                # Get intermediate answer
                answer_match = re.search(r'intermediate answer:\s*(.+)', response, re.IGNORECASE | re.DOTALL)
                answer = answer_match.group(1).strip() if answer_match else ""
                
                qa_chain.append({"question": question, "answer": answer})
                current_context += f"\nQ: {question}\nA: {answer}"
        
        # Return best effort
        return {
            "answer": qa_chain[-1]["answer"] if qa_chain else "Could not determine answer",
            "qa_chain": qa_chain,
        }


class ReflectionEngine:
    """
    Reflection-based reasoning
    
    Generates an initial response, then reflects on it to improve
    
    Supports custom prompts for initial response and reflection.
    """
    
    DEFAULT_INITIAL_SYSTEM = "You are a helpful assistant. Provide a thorough answer to the user's question."
    DEFAULT_REFLECTION_SYSTEM = "You are a critical reviewer. Analyze the response and provide improvements."
    
    def __init__(
        self, 
        llm_config: LLMConfig,
        initial_system_prompt: str = None,
        reflection_system_prompt: str = None,
    ):
        self.llm = LLM(llm_config)
        self._initial_system = initial_system_prompt or self.DEFAULT_INITIAL_SYSTEM
        self._reflection_system = reflection_system_prompt or self.DEFAULT_REFLECTION_SYSTEM
    
    def set_prompts(
        self,
        initial_system: str = None,
        reflection_system: str = None,
    ) -> None:
        """Set custom prompts"""
        if initial_system:
            self._initial_system = initial_system
        if reflection_system:
            self._reflection_system = reflection_system
    
    async def reason(
        self,
        task: str,
        max_reflections: int = 2,
    ) -> dict:
        """
        Perform reflection-based reasoning
        
        Returns:
            Dict with 'final_answer', 'initial_answer', and 'reflections'
        """
        # Initial response
        initial = await self.llm.chat(
            prompt=task,
            system=self._initial_system,
        )
        
        current_answer = initial
        reflections = []
        
        for i in range(max_reflections):
            # Reflect
            reflection_prompt = f"""Review and improve this response:

Task: {task}

Current Response:
{current_answer}

Please:
1. Identify any errors, gaps, or areas for improvement
2. Provide a better, more complete response

Format:
Critique: <your critique>
Improved Response: <improved answer>"""
            
            reflection = await self.llm.chat(
                prompt=reflection_prompt,
                system=self._reflection_system,
            )
            
            # Extract improved response
            improved_match = re.search(r'improved response:\s*(.+)', reflection, re.IGNORECASE | re.DOTALL)
            if improved_match:
                improved = improved_match.group(1).strip()
            else:
                improved = reflection
            
            reflections.append({
                "iteration": i + 1,
                "critique": reflection,
                "improved": improved,
            })
            
            # Check if no significant changes
            if improved.lower().strip() == current_answer.lower().strip():
                break
            
            current_answer = improved
        
        return {
            "final_answer": current_answer,
            "initial_answer": initial,
            "reflections": reflections,
        }


# Helper function to create custom ReAct template
def create_react_template(
    name: str,
    template: str,
    variables: list[str] = None,
    description: str = "",
) -> PromptTemplate:
    """
    Helper to create a custom ReAct template
    
    Args:
        name: Template name
        template: Template string with {variable} placeholders
        variables: List of variable names (default: task, tools, history, observation)
        description: Template description
        
    Returns:
        PromptTemplate instance
        
    Example:
        template = create_react_template(
            name="simple_react",
            template='''
            Task: {task}
            
            Tools available: {tools}
            
            History: {history}
            
            Current observation: {observation}
            
            Respond with:
            Thought: your reasoning
            Action: tool_name or finish
            Action Input: input for the tool
            ''',
        )
    """
    return PromptTemplate(
        name=name,
        template=template.strip(),
        description=description,
        variables=variables or ["task", "tools", "history", "observation"],
    )
