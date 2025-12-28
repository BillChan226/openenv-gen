"""
Reasoning Debugger - LLM-based chain-of-thought debugging

Uses LLM to reason about errors across the full stack and provide
actionable fix suggestions with code changes.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from workspace import Workspace


@dataclass
class CodeChange:
    """A specific code change to fix an issue."""
    file: str
    action: str  # replace, insert, delete, create
    target: str  # line number, function name, or pattern to find
    replacement: str
    explanation: str = ""


@dataclass
class DebugDiagnosis:
    """Result of LLM reasoning about an error."""
    origin_layer: str  # frontend, backend, database, config, docker
    immediate_cause: str
    root_cause: str
    affected_files: List[str]
    fix_steps: List[str]
    code_changes: List[CodeChange]
    confidence: float
    reasoning: str  # Chain-of-thought reasoning


class ReasoningDebugger:
    """
    Use LLM to reason about errors across the full stack.
    
    This debugger:
    1. Takes an error message and relevant context (code, logs, config)
    2. Uses LLM to reason step-by-step about the cause
    3. Returns actionable fix suggestions with specific code changes
    """
    
    def __init__(self, llm_client=None, workspace: Workspace = None):
        """
        Args:
            llm_client: LLM client with chat_with_response method
            workspace: Workspace for file operations
        """
        self.llm = llm_client
        self.workspace = workspace
    
    async def debug_error(
        self,
        error: str,
        context: Dict[str, str],
        additional_info: str = "",
    ) -> DebugDiagnosis:
        """
        Use LLM to diagnose an error with chain-of-thought reasoning.
        
        Args:
            error: The error message
            context: Dict with keys like 'frontend_code', 'backend_code', 
                     'database_schema', 'docker_compose', 'logs'
            additional_info: Any additional context
        
        Returns:
            DebugDiagnosis with root cause and fix suggestions
        """
        if not self.llm:
            return self._fallback_diagnosis(error)
        
        prompt = self._build_debug_prompt(error, context, additional_info)
        
        try:
            response = await self.llm.chat_with_response(
                prompt=prompt,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            
            return self._parse_response(response.content)
        except Exception as e:
            # Fallback to pattern-based diagnosis
            return self._fallback_diagnosis(error, str(e))
    
    def _build_debug_prompt(
        self,
        error: str,
        context: Dict[str, str],
        additional_info: str,
    ) -> str:
        """Build the prompt for LLM debugging."""
        
        # Truncate context values to avoid token limits
        truncated_context = {}
        for key, value in context.items():
            if isinstance(value, str) and len(value) > 3000:
                truncated_context[key] = value[:3000] + "\n... (truncated)"
            else:
                truncated_context[key] = value
        
        return f"""You are an expert full-stack debugger. Analyze this error and trace it across all layers of a web application.

ERROR MESSAGE:
{error}

CONTEXT:
{json.dumps(truncated_context, indent=2)}

{f"ADDITIONAL INFO: {additional_info}" if additional_info else ""}

Think step by step:
1. What layer does this error originate from? (frontend/backend/database/config/docker)
2. What is the immediate cause visible in the error message?
3. What is the ROOT CAUSE? (This might be in a different layer than where the error appears)
4. What files need to be changed to fix this?
5. What are the specific code changes needed?

IMPORTANT: For route ordering issues in Express, specific routes (like /search) MUST come BEFORE parameterized routes (like /:id).

Respond with valid JSON in this exact format:
{{
    "origin_layer": "frontend|backend|database|config|docker",
    "immediate_cause": "What the error message directly indicates",
    "root_cause": "The actual underlying problem that caused this error",
    "affected_files": ["list of file paths that need changes"],
    "fix_steps": [
        "Step 1: Description of first fix",
        "Step 2: Description of second fix"
    ],
    "code_changes": [
        {{
            "file": "path/to/file.js",
            "action": "replace|insert|delete|create",
            "target": "line number, function name, or code pattern to find",
            "replacement": "the new code to use",
            "explanation": "why this change fixes the issue"
        }}
    ],
    "confidence": 0.0 to 1.0,
    "reasoning": "Your step-by-step reasoning process"
}}"""
    
    def _parse_response(self, response_content: str) -> DebugDiagnosis:
        """Parse LLM response into DebugDiagnosis."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_content)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            data = json.loads(json_match.group())
            
            # Parse code changes
            code_changes = []
            for change in data.get("code_changes", []):
                code_changes.append(CodeChange(
                    file=change.get("file", ""),
                    action=change.get("action", "replace"),
                    target=change.get("target", ""),
                    replacement=change.get("replacement", ""),
                    explanation=change.get("explanation", ""),
                ))
            
            return DebugDiagnosis(
                origin_layer=data.get("origin_layer", "unknown"),
                immediate_cause=data.get("immediate_cause", ""),
                root_cause=data.get("root_cause", ""),
                affected_files=data.get("affected_files", []),
                fix_steps=data.get("fix_steps", []),
                code_changes=code_changes,
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return DebugDiagnosis(
                origin_layer="unknown",
                immediate_cause=f"Failed to parse LLM response: {e}",
                root_cause="LLM response parsing error",
                affected_files=[],
                fix_steps=["Manual investigation required"],
                code_changes=[],
                confidence=0.0,
                reasoning=response_content[:500],
            )
    
    def _fallback_diagnosis(self, error: str, parse_error: str = "") -> DebugDiagnosis:
        """Fallback diagnosis when LLM is not available."""
        from .debug_tools import CrossLayerDebugger
        
        debugger = CrossLayerDebugger()
        trace = debugger.trace_error(error)
        
        return DebugDiagnosis(
            origin_layer=trace.origin_layer,
            immediate_cause=trace.immediate_cause,
            root_cause=trace.root_cause,
            affected_files=trace.affected_files,
            fix_steps=[trace.fix_suggestion],
            code_changes=[],
            confidence=trace.confidence,
            reasoning=f"Pattern-based diagnosis (LLM unavailable: {parse_error})" if parse_error else "Pattern-based diagnosis",
        )
    
    async def debug_with_context_collection(
        self,
        error: str,
        workspace_root: Path,
    ) -> DebugDiagnosis:
        """
        Debug an error by automatically collecting relevant context.
        
        Reads relevant files from workspace to build context.
        """
        context = {}
        
        # Try to collect frontend API code
        api_file = workspace_root / "app/frontend/src/services/api.js"
        if api_file.exists():
            context["frontend_api"] = api_file.read_text()[:2000]
        
        # Try to collect backend routes
        routes_dir = workspace_root / "app/backend/src/routes"
        if routes_dir.exists():
            routes_content = []
            for route_file in routes_dir.glob("*.js"):
                routes_content.append(f"// {route_file.name}\n{route_file.read_text()[:1000]}")
            context["backend_routes"] = "\n\n".join(routes_content)[:3000]
        
        # Try to collect database schema
        schema_file = workspace_root / "app/database/init/01_schema.sql"
        if schema_file.exists():
            context["database_schema"] = schema_file.read_text()[:2000]
        
        # Try to collect docker-compose
        compose_file = workspace_root / "docker/docker-compose.yml"
        if compose_file.exists():
            context["docker_compose"] = compose_file.read_text()
        
        # Try to collect env config
        env_file = workspace_root / "app/backend/src/config/env.js"
        if env_file.exists():
            context["backend_config"] = env_file.read_text()
        
        return await self.debug_error(error, context)


class IterativeDebugger:
    """
    Iterative debugger that combines fix attempts with verification.
    
    Implements the fix -> verify -> analyze -> fix feedback loop.
    """
    
    def __init__(
        self,
        reasoning_debugger: ReasoningDebugger,
        max_iterations: int = 5,
    ):
        self.debugger = reasoning_debugger
        self.max_iterations = max_iterations
        self.history: List[Dict[str, Any]] = []
    
    async def debug_iteratively(
        self,
        initial_error: str,
        context: Dict[str, str],
        verify_fn=None,  # async function that returns (success: bool, new_error: str)
        apply_fix_fn=None,  # async function that applies CodeChange
    ) -> Dict[str, Any]:
        """
        Iteratively debug and fix an issue.
        
        Args:
            initial_error: The initial error message
            context: Context for debugging
            verify_fn: Async function to verify if fix worked
            apply_fix_fn: Async function to apply code changes
        
        Returns:
            Dict with success status, iterations, and history
        """
        current_error = initial_error
        
        for iteration in range(self.max_iterations):
            # 1. Diagnose current error
            diagnosis = await self.debugger.debug_error(current_error, context)
            
            self.history.append({
                "iteration": iteration + 1,
                "error": current_error,
                "diagnosis": {
                    "root_cause": diagnosis.root_cause,
                    "fix_steps": diagnosis.fix_steps,
                    "confidence": diagnosis.confidence,
                },
            })
            
            # 2. Apply fixes if we have code changes and an apply function
            if apply_fix_fn and diagnosis.code_changes:
                for change in diagnosis.code_changes:
                    try:
                        await apply_fix_fn(change)
                    except Exception as e:
                        self.history[-1]["apply_error"] = str(e)
            
            # 3. Verify if fix worked
            if verify_fn:
                success, new_error = await verify_fn()
                
                if success:
                    return {
                        "success": True,
                        "iterations": iteration + 1,
                        "final_diagnosis": diagnosis,
                        "history": self.history,
                    }
                
                # Update error for next iteration
                if new_error and new_error != current_error:
                    current_error = new_error
                else:
                    # Same error, increase context or give up
                    break
            else:
                # No verification function, return diagnosis
                return {
                    "success": None,  # Unknown - no verification
                    "iterations": 1,
                    "final_diagnosis": diagnosis,
                    "history": self.history,
                }
        
        return {
            "success": False,
            "iterations": self.max_iterations,
            "final_diagnosis": diagnosis if 'diagnosis' in dir() else None,
            "history": self.history,
            "message": "Max iterations reached without fix",
        }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ReasoningDebugger",
    "IterativeDebugger",
    "DebugDiagnosis",
    "CodeChange",
]

