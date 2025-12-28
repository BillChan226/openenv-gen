"""
Generator Memory - Extended AgentMemory for code generation tasks.

Based on utils/memory.py AgentMemory class.
Adds specialized functionality for:
- File operation tracking
- Lint state tracking
- Phase-aware context
- Code generation specific summaries
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

# Import base classes from utils/memory.py
import sys
_agents_dir = Path(__file__).parent.parent.parent.parent.absolute()
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

from utils.memory import (
    AgentMemory,
    ShortTermMemory,
    LongTermMemory,
    WorkingMemory,
    LLMSummarizingCondenser,
    MemoryItem,
)
from utils.llm import LLM


class GeneratorMemory(AgentMemory):
    """
    Extended AgentMemory for code generation tasks.
    
    Features:
    - File operation tracking (created, modified, linted)
    - Phase-aware context management
    - Code-specific summarization prompts
    - Tool call deduplication awareness
    """
    
    def __init__(
        self,
        llm: LLM = None,
        short_term_size: int = 100,
        long_term_size: int = 1000,
        condenser_max_size: int = 80,
    ):
        # Create LLM wrapper for condenser
        async def llm_func(prompt: str) -> str:
            if llm:
                return await llm.chat(prompt, temperature=0.3)
            return "[Condensation unavailable - no LLM provided]"
        
        super().__init__(
            short_term_size=short_term_size,
            long_term_size=long_term_size,
            condenser_llm_func=llm_func if llm else None,
            condenser_max_size=condenser_max_size,
        )
        
        self._logger = logging.getLogger("generator_memory")
        
        # File operation tracking
        self._files_created: Set[str] = set()
        self._files_modified: Set[str] = set()
        self._files_linted: Set[str] = set()
        self._lint_results: Dict[str, bool] = {}  # path -> passed
        
        # Tool call tracking for deduplication
        self._tool_calls: Dict[str, int] = {}  # tool_name -> count
        self._consecutive_same_tool: int = 0
        self._last_tool: str = ""
        
        # Phase tracking
        self._current_phase: str = ""
        self._phase_start_time: Optional[datetime] = None
        
        # Error tracking
        self._errors: List[Dict[str, Any]] = []
    
    # ==================== File Tracking ====================
    
    def record_file_created(self, path: str) -> None:
        """Record a file creation."""
        normalized = self._normalize_path(path)
        self._files_created.add(normalized)
        
        # Also add to working memory
        self.working.set("last_file_created", normalized)
        
        # Add to short-term memory
        self.remember(
            f"Created file: {normalized}",
            memory_type="short",
            metadata={"type": "file_created", "path": normalized},
            importance=0.7,
        )
    
    def record_file_modified(self, path: str) -> None:
        """Record a file modification."""
        normalized = self._normalize_path(path)
        self._files_modified.add(normalized)
        
        self.working.set("last_file_modified", normalized)
        self.remember(
            f"Modified file: {normalized}",
            memory_type="short",
            metadata={"type": "file_modified", "path": normalized},
            importance=0.6,
        )
    
    def record_lint(self, path: str, passed: bool) -> None:
        """Record a lint operation."""
        normalized = self._normalize_path(path)
        self._files_linted.add(normalized)
        self._lint_results[normalized] = passed
        
        # Only log to memory if failed (to save space)
        if not passed:
            self.remember(
                f"Lint failed: {normalized}",
                memory_type="short",
                metadata={"type": "lint_failed", "path": normalized},
                importance=0.8,
            )
    
    def is_file_linted(self, path: str) -> bool:
        """Check if a file has been linted."""
        return self._normalize_path(path) in self._files_linted
    
    def get_unlinted_files(self) -> List[str]:
        """Get files that have been created but not linted."""
        return list(self._files_created - self._files_linted)
    
    def get_file_stats(self) -> Dict[str, int]:
        """Get file operation statistics."""
        return {
            "created": len(self._files_created),
            "modified": len(self._files_modified),
            "linted": len(self._files_linted),
            "lint_passed": sum(1 for v in self._lint_results.values() if v),
            "lint_failed": sum(1 for v in self._lint_results.values() if not v),
        }
    
    # ==================== Tool Tracking ====================
    
    def record_tool_call(self, tool_name: str) -> Dict[str, Any]:
        """
        Record a tool call and return loop detection info.
        
        Returns:
            Dict with 'is_duplicate', 'consecutive_count', 'total_count'
        """
        self._tool_calls[tool_name] = self._tool_calls.get(tool_name, 0) + 1
        
        if tool_name == self._last_tool:
            self._consecutive_same_tool += 1
        else:
            self._consecutive_same_tool = 1
        
        self._last_tool = tool_name
        
        return {
            "is_duplicate": tool_name == "lint" and self._consecutive_same_tool > 5,
            "consecutive_count": self._consecutive_same_tool,
            "total_count": self._tool_calls[tool_name],
        }
    
    def should_force_finish(self) -> tuple[bool, str]:
        """
        Check if the agent should be forced to finish.
        
        Returns:
            (should_finish, reason)
        """
        # All created files are linted
        if self._files_created and not self.get_unlinted_files():
            return True, "All created files have been linted"
        
        # Too many consecutive same tool calls
        if self._consecutive_same_tool > 50:
            return True, f"Too many consecutive {self._last_tool} calls"
        
        # Lint called more than 2x the number of files
        lint_count = self._tool_calls.get("lint", 0)
        if lint_count > len(self._files_created) * 2 and lint_count > 10:
            return True, "Excessive lint calls detected"
        
        return False, ""
    
    # ==================== Phase Tracking ====================
    
    def set_phase(self, phase: str) -> None:
        """Set current phase and log duration of previous."""
        if self._current_phase and self._phase_start_time:
            duration = (datetime.now() - self._phase_start_time).seconds
            self.remember(
                f"Phase '{self._current_phase}' completed in {duration}s",
                memory_type="long",
                metadata={"type": "phase_complete", "phase": self._current_phase},
                importance=0.8,
            )
        
        self._current_phase = phase
        self._phase_start_time = datetime.now()
        
        # Update working memory
        self.working.set("current_phase", phase)
        self.working.set("phase_start", datetime.now().isoformat())
    
    # ==================== Error Tracking ====================
    
    def record_error(self, error: str, context: str = "") -> None:
        """Record an error."""
        self._errors.append({
            "error": error[:500],
            "context": context[:200],
            "time": datetime.now().isoformat(),
            "phase": self._current_phase,
        })
        
        # Add to short-term with high importance
        self.remember(
            f"Error in {self._current_phase}: {error[:200]}",
            memory_type="short",
            metadata={"type": "error", "context": context},
            importance=0.9,
        )
    
    # ==================== Context Generation ====================
    
    def get_operation_context(self) -> str:
        """
        Get current operation state as context string.
        
        More detailed than base class get_context_string().
        """
        lines = ["=== OPERATION STATE ==="]
        
        # Phase info
        if self._current_phase:
            duration = (datetime.now() - self._phase_start_time).seconds if self._phase_start_time else 0
            lines.append(f"Phase: {self._current_phase} ({duration}s)")
        
        # File stats
        stats = self.get_file_stats()
        lines.append(f"Files: {stats['created']} created, {stats['linted']} linted")
        
        # Unlinted files
        unlinted = self.get_unlinted_files()
        if unlinted:
            lines.append(f"Unlinted: {', '.join(unlinted[:5])}")
            if len(unlinted) > 5:
                lines.append(f"  ... and {len(unlinted) - 5} more")
        
        # Recent errors
        if self._errors:
            lines.append(f"Recent error: {self._errors[-1]['error'][:100]}")
        
        # Tool call warning
        should_finish, reason = self.should_force_finish()
        if should_finish:
            lines.append(f"WARNING: {reason}")
        
        lines.append("=== END STATE ===")
        return "\n".join(lines)
    
    def get_full_context(self) -> str:
        """
        Get complete context combining base class and operation context.
        """
        base_context = self.get_context_string(max_items=15)
        op_context = self.get_operation_context()
        
        return f"{base_context}\n\n{op_context}"
    
    # ==================== Reset ====================
    
    def reset_for_task(self) -> None:
        """Reset task-specific tracking while preserving long-term memory."""
        # Clear file tracking
        self._files_created.clear()
        self._files_modified.clear()
        self._files_linted.clear()
        self._lint_results.clear()
        
        # Clear tool tracking
        self._tool_calls.clear()
        self._consecutive_same_tool = 0
        self._last_tool = ""
        
        # Clear errors
        self._errors.clear()
        
        # Clear working memory but keep short/long term
        self.working.clear()
    
    def reset_all(self) -> None:
        """Full reset including all memory."""
        self.reset_for_task()
        self.short_term.clear()
        # Don't clear long-term - it should persist
    
    # ==================== Helpers ====================
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a file path for consistent tracking."""
        # Remove common prefixes
        path = str(path)
        
        # Remove leading ./
        if path.startswith("./"):
            path = path[2:]
        
        # Remove leading /
        if path.startswith("/"):
            # Try to make relative
            try:
                path = str(Path(path).name)
            except:
                pass
        
        return path
    
    def stats(self) -> dict:
        """Extended stats including file operations."""
        base_stats = super().stats()
        base_stats.update({
            "files_created": len(self._files_created),
            "files_modified": len(self._files_modified),
            "files_linted": len(self._files_linted),
            "current_phase": self._current_phase,
            "errors": len(self._errors),
            "tool_calls": dict(self._tool_calls),
        })
        return base_stats

