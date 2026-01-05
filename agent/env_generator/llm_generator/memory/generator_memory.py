"""
Generator Memory - Enhanced Memory System for Multi-Agent Code Generation

Key Features:
1. Conversation Context Management - Intelligent condensation when context grows too large
2. Tool Call Tracking - Record tool calls for pattern detection and optimization
3. File Operation Tracking - Track created, modified, linted files
4. Knowledge Persistence - Important learnings that persist across tasks
5. Cross-Agent Memory Sharing - Share important info via MessageBus

Integration Points:
- run_agentic_loop: Auto-condense when messages exceed threshold
- tool_execute: Record tool calls and results
- task_complete: Summarize and persist important learnings
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime
from dataclasses import dataclass, field
import json
import asyncio

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


# ==================== Message Condensation ====================

MESSAGE_CONDENSER_PROMPT = """You are condensing conversation history for an AI coding agent.

The agent is working on code generation tasks with these tools: write_file, read_file, lint, etc.

CONDENSE the following message history while preserving:
1. **Task Progress**: What has been accomplished, what's remaining
2. **Key Decisions**: Important choices made and why
3. **File Operations**: Files created/modified (with paths)
4. **Errors & Fixes**: Problems encountered and how they were resolved
5. **Current State**: Where the agent currently is in its workflow

DO NOT preserve:
- Redundant tool calls (e.g., multiple lint attempts on same file)
- Verbose file contents (just note "wrote X to path")
- Repetitive thinking/reasoning

<MESSAGE_HISTORY>
{messages}
</MESSAGE_HISTORY>

Provide a structured summary (max 1500 tokens):"""


@dataclass
class ConversationCondenser:
    """
    Condenses LLM conversation messages when they grow too long.
    
    Unlike memory-based condensation, this works directly on the
    messages list used in the agentic loop.
    """
    
    llm: Optional[LLM] = None
    max_messages: int = 60  # Trigger condensation after this many messages
    keep_recent: int = 15   # Always keep this many recent messages
    _condensation_count: int = 0
    _last_summary: str = ""
    
    async def maybe_condense(self, messages: List[Dict]) -> List[Dict]:
        """
        Condense messages if they exceed threshold.
        
        Args:
            messages: List of message dicts (role, content)
            
        Returns:
            Condensed messages list (or original if no condensation needed)
        """
        if len(messages) <= self.max_messages:
            return messages
        
        if not self.llm:
            # No LLM available - simple truncation
            return self._simple_truncate(messages)
        
        return await self._llm_condense(messages)
    
    def _get_role(self, msg) -> str:
        """Get role from message (works with both dict and Message objects)."""
        if hasattr(msg, 'role'):
            return msg.role
        elif isinstance(msg, dict):
            return msg.get("role", "unknown")
        return "unknown"
    
    def _get_content(self, msg) -> str:
        """Get content from message (works with both dict and Message objects)."""
        if hasattr(msg, 'content'):
            return msg.content or ""
        elif isinstance(msg, dict):
            return msg.get("content", "")
        return str(msg)
    
    def _find_safe_cutoff(self, other_msgs: List, target_keep: int) -> int:
        """Find a safe cut-off point that doesn't break assistant+tool message pairs."""
        cut_off = len(other_msgs) - target_keep
        
        if cut_off <= 0:
            return 0
        
        # Walk backward to find a safe starting point
        # Can't start with a tool message (needs parent assistant with tool_calls)
        while cut_off > 0 and cut_off < len(other_msgs):
            role = self._get_role(other_msgs[cut_off])
            if role == "tool":
                # Can't start with a tool message
                cut_off -= 1
            elif role == "assistant":
                # Check if this assistant has tool_calls
                msg = other_msgs[cut_off]
                has_tool_calls = False
                if hasattr(msg, 'tool_calls'):
                    has_tool_calls = bool(msg.tool_calls)
                elif isinstance(msg, dict):
                    has_tool_calls = bool(msg.get('tool_calls'))
                
                if has_tool_calls:
                    # Check if next message is a tool response
                    next_idx = cut_off + 1
                    if next_idx < len(other_msgs) and self._get_role(other_msgs[next_idx]) == "tool":
                        # Can't split between assistant and its tool responses
                        cut_off -= 1
                    else:
                        break
                else:
                    break
            else:
                # user message - safe to start here
                break
        
        return max(0, cut_off)
    
    def _simple_truncate(self, messages: List) -> List:
        """Simple truncation without LLM."""
        # Keep system message + recent messages
        system_msgs = [m for m in messages if self._get_role(m) == "system"]
        other_msgs = [m for m in messages if self._get_role(m) != "system"]
        
        if len(other_msgs) <= self.keep_recent:
            return messages
        
        # Find safe cut-off point
        cut_off = self._find_safe_cutoff(other_msgs, self.keep_recent)
        
        if cut_off <= 0:
            return messages
        
        to_keep = other_msgs[cut_off:]
        
        # Create simple summary
        truncated_count = cut_off
        summary_content = f"[Previous {truncated_count} messages condensed. Key actions were performed - see recent history for current state.]"
        
        # Return same type as input - check if using Message objects
        if hasattr(messages[0], 'role'):
            # Import Message class dynamically
            from utils.llm import Message
            summary_msg = Message.user(summary_content)
        else:
            summary_msg = {"role": "user", "content": summary_content}
        
        return system_msgs + [summary_msg] + to_keep
    
    async def _llm_condense(self, messages: List) -> List:
        """Condense using LLM summarization."""
        # Keep system messages and recent messages
        system_msgs = [m for m in messages if self._get_role(m) == "system"]
        other_msgs = [m for m in messages if self._get_role(m) != "system"]
        
        if len(other_msgs) <= self.keep_recent:
            return messages
        
        # Find safe cut-off point
        cut_off = self._find_safe_cutoff(other_msgs, self.keep_recent)
        
        if cut_off <= 0:
            # Can't condense safely
            return messages
        
        to_condense = other_msgs[:cut_off]
        to_keep = other_msgs[cut_off:]
        
        # Format messages for condensation
        formatted = []
        for msg in to_condense:
            role = self._get_role(msg)
            content = self._get_content(msg)
            if isinstance(content, list):
                # Handle multi-part content
                content = " ".join(str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in content)
            # Truncate very long content
            if len(str(content)) > 2000:
                content = str(content)[:2000] + "... [truncated]"
            formatted.append(f"[{role}] {content}")
        
        messages_text = "\n\n".join(formatted)
        
        # Generate summary
        prompt = MESSAGE_CONDENSER_PROMPT.format(messages=messages_text)
        
        try:
            summary = await self.llm.chat(prompt, temperature=0.3)
            self._last_summary = summary
            self._condensation_count += 1
            
            summary_content = f"[CONTEXT SUMMARY #{self._condensation_count}]\n{summary}\n\n---\nRecent conversation continues below:"
            
            # Return same type as input - check if using Message objects
            if messages and hasattr(messages[0], 'role'):
                from utils.llm import Message
                summary_msg = Message.user(summary_content)
            else:
                summary_msg = {"role": "user", "content": summary_content}
            
            return system_msgs + [summary_msg] + to_keep
            
        except Exception as e:
            logging.getLogger("condenser").error(f"LLM condensation failed: {e}")
            return self._simple_truncate(messages)
    
    @property
    def summary(self) -> str:
        return self._last_summary


# ==================== Enhanced Generator Memory ====================

class GeneratorMemory(AgentMemory):
    """
    Enhanced memory system for code generation agents.
    
    New Features:
    1. Conversation condensation - Works with messages list
    2. Knowledge extraction - Auto-extract learnings from completed tasks
    3. Cross-agent sharing - Share important info with other agents
    4. Semantic recall - Search memory by meaning (when embeddings available)
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
        
        self._llm = llm
        self._logger = logging.getLogger("generator_memory")
        
        # Conversation condenser (for messages list)
        self.conversation_condenser = ConversationCondenser(llm=llm)
        
        # File operation tracking
        self._files_created: Set[str] = set()
        self._files_modified: Set[str] = set()
        self._files_linted: Set[str] = set()
        self._lint_results: Dict[str, bool] = {}  # path -> passed
        
        # Tool call tracking
        self._tool_calls: List[Dict[str, Any]] = []
        self._tool_call_counts: Dict[str, int] = {}
        self._consecutive_same_tool: int = 0
        self._last_tool: str = ""
        
        # Knowledge store (important learnings)
        self._knowledge: List[Dict[str, Any]] = []
        
        # Phase tracking
        self._current_phase: str = ""
        self._phase_start_time: Optional[datetime] = None
        
        # Error tracking
        self._errors: List[Dict[str, Any]] = []
        
        # Cross-agent message queue
        self._outgoing_knowledge: List[Dict[str, Any]] = []
        
        # Working memory (current task context, plans, etc.)
        self._working_memory: Dict[str, Any] = {}
    
    # ==================== Conversation Management ====================
    
    async def condense_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Condense conversation messages if they're too long.
        
        Call this in the agentic loop periodically.
        
        Args:
            messages: Current messages list
            
        Returns:
            Condensed messages (or original if no condensation needed)
        """
        return await self.conversation_condenser.maybe_condense(messages)
    
    def should_condense_messages(self, messages: List[Dict]) -> bool:
        """Check if messages should be condensed."""
        return len(messages) > self.conversation_condenser.max_messages
    
    # ==================== Tool Call Tracking ====================
    
    def record_tool_call(
        self, 
        tool_name: str, 
        tool_args: Dict[str, Any], 
        result: Any,
        success: bool = True,
        duration_ms: int = 0
    ) -> Dict[str, Any]:
        """
        Record a tool call with full details.
        
        Args:
            tool_name: Name of the tool
            tool_args: Arguments passed to tool
            result: Tool result (will be truncated)
            success: Whether the call succeeded
            duration_ms: Execution time in milliseconds
            
        Returns:
            Dict with loop detection info
        """
        # Update counts
        self._tool_call_counts[tool_name] = self._tool_call_counts.get(tool_name, 0) + 1
        
        if tool_name == self._last_tool:
            self._consecutive_same_tool += 1
        else:
            self._consecutive_same_tool = 1
        self._last_tool = tool_name
        
        # Create record
        record = {
            "tool": tool_name,
            "args_summary": self._summarize_args(tool_args),
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms,
        }
        
        # Track errors
        if not success:
            record["error"] = str(result)[:500]
        
        self._tool_calls.append(record)
        
        # Keep last 100 tool calls
        if len(self._tool_calls) > 100:
            self._tool_calls = self._tool_calls[-100:]
        
        # Auto-extract knowledge from certain tool results
        self._maybe_extract_knowledge(tool_name, tool_args, result, success)
        
        return {
            "consecutive_count": self._consecutive_same_tool,
            "total_count": self._tool_call_counts[tool_name],
            "is_potential_loop": self._consecutive_same_tool > 5,
        }
    
    def _summarize_args(self, args: Dict[str, Any]) -> str:
        """Summarize tool arguments for logging."""
        summary = []
        for key, value in args.items():
            if key in ("content", "code", "data") and len(str(value)) > 100:
                summary.append(f"{key}=[{len(str(value))} chars]")
            else:
                val_str = str(value)[:50]
                summary.append(f"{key}={val_str}")
        return ", ".join(summary)
    
    def _maybe_extract_knowledge(
        self, 
        tool_name: str, 
        tool_args: Dict[str, Any],
        result: Any,
        success: bool
    ) -> None:
        """Auto-extract knowledge from certain tool results."""
        if not success:
            return
            
        # === Auto-save Plan updates ===
        if tool_name == "plan":
            action = tool_args.get("action", "create")
            items = tool_args.get("items", [])
            if action == "create" and items:
                # Save complete plan to working memory
                plan_summary = f"Plan created with {len(items)} items: " + "; ".join(items[:5])
                if len(items) > 5:
                    plan_summary += f"... and {len(items) - 5} more"
                self._working_memory["current_plan"] = {
                    "items": items,
                    "created_at": datetime.now().isoformat(),
                    "completed": []
                }
                self.add_knowledge(plan_summary, category="plan", importance=0.8)
            elif action == "complete":
                item_idx = tool_args.get("item_index", 0)
                plan = self._working_memory.get("current_plan", {})
                if plan and item_idx < len(plan.get("items", [])):
                    completed_item = plan["items"][item_idx]
                    plan.setdefault("completed", []).append(completed_item)
        
        # === Auto-save key decisions from think() ===
        if tool_name == "think":
            thought = tool_args.get("thought", "")
            # Only save substantial thoughts that look like decisions
            decision_keywords = ["decided", "will use", "choosing", "approach", "strategy", 
                               "architecture", "because", "therefore", "conclusion"]
            if len(thought) > 100 and any(kw in thought.lower() for kw in decision_keywords):
                self.add_knowledge(
                    thought[:500] + ("..." if len(thought) > 500 else ""),
                    category="decision",
                    importance=0.7
                )
        
        # === Extract from error fixes ===
        if tool_name == "lint":
            path = tool_args.get("path", "")
            if path in self._lint_results and not self._lint_results.get(path, True):
                # Was failing, now passes - record the fix
                self.add_knowledge(
                    f"Fixed lint errors in {path}",
                    category="bug_fix",
                    importance=0.7
                )
        
        # === Extract from write_file (file creation) ===
        if tool_name == "write_file":
            path = tool_args.get("path", "")
            if path:
                self._files_created.add(self._normalize_path(path))
        
        # === Auto-save important API/endpoint info from send_message ===
        if tool_name == "send_message":
            content = tool_args.get("content", "")
            msg_type = tool_args.get("msg_type", "")
            # Save API-related info shared between agents
            if "api" in content.lower() or "endpoint" in content.lower() or "schema" in content.lower():
                self.add_knowledge(
                    f"Shared info: {content[:300]}",
                    category="tech_context",
                    importance=0.6
                )
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics."""
        return {
            "total_calls": len(self._tool_calls),
            "by_tool": dict(self._tool_call_counts),
            "last_tool": self._last_tool,
            "consecutive_same": self._consecutive_same_tool,
            "recent_errors": [
                tc for tc in self._tool_calls[-20:] 
                if not tc.get("success", True)
            ]
        }
    
    # ==================== Knowledge Management ====================
    
    def add_knowledge(
        self, 
        content: str, 
        category: str = "general",
        importance: float = 0.5,
        share_with: List[str] = None
    ) -> str:
        """
        Add a piece of knowledge.
        
        Args:
            content: The knowledge content
            category: Category (bug_fix, pattern, decision, etc.)
            importance: Importance score (0-1)
            share_with: List of agent IDs to share with
            
        Returns:
            Knowledge ID
        """
        knowledge_id = f"k_{len(self._knowledge)}_{datetime.now().strftime('%H%M%S')}"
        
        entry = {
            "id": knowledge_id,
            "content": content,
            "category": category,
            "importance": importance,
            "timestamp": datetime.now().isoformat(),
            "phase": self._current_phase,
        }
        
        self._knowledge.append(entry)
        
        # Also add to long-term memory
        self.remember(
            content,
            memory_type="long",
            metadata={"category": category, "knowledge_id": knowledge_id},
            importance=importance
        )
        
        # Queue for cross-agent sharing
        if share_with:
            self._outgoing_knowledge.append({
                "knowledge": entry,
                "targets": share_with,
            })
        
        self._logger.debug(f"Added knowledge [{category}]: {content[:100]}")
        return knowledge_id
    
    def recall_knowledge(
        self, 
        query: str = None, 
        category: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recall knowledge by query or category.
        
        Args:
            query: Text query to search
            category: Filter by category
            limit: Maximum results
            
        Returns:
            List of matching knowledge entries
        """
        results = self._knowledge.copy()
        
        # Filter by category
        if category:
            results = [k for k in results if k.get("category") == category]
        
        # Filter by query
        if query:
            query_lower = query.lower()
            results = [k for k in results if query_lower in k.get("content", "").lower()]
        
        # Sort by importance
        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        
        return results[:limit]
    
    def get_outgoing_knowledge(self) -> List[Dict[str, Any]]:
        """Get and clear outgoing knowledge queue."""
        outgoing = self._outgoing_knowledge.copy()
        self._outgoing_knowledge.clear()
        return outgoing
    
    # ==================== File Tracking ====================
    
    def record_file_created(self, path: str) -> None:
        """Record a file creation."""
        normalized = self._normalize_path(path)
        self._files_created.add(normalized)
        
        self.working.set("last_file_created", normalized)
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
        NO_LINT_EXTENSIONS = {'.json', '.md', '.sql', '.txt', '.env', '.yml', '.yaml', '.toml', '.lock', '.png', '.jpg', '.svg'}
        
        unlinted = []
        for path in (self._files_created - self._files_linted):
            ext = Path(path).suffix.lower()
            if ext not in NO_LINT_EXTENSIONS:
                unlinted.append(path)
        
        return unlinted
    
    def get_file_stats(self) -> Dict[str, int]:
        """Get file operation statistics."""
        return {
            "created": len(self._files_created),
            "modified": len(self._files_modified),
            "linted": len(self._files_linted),
            "lint_passed": sum(1 for v in self._lint_results.values() if v),
            "lint_failed": sum(1 for v in self._lint_results.values() if not v),
        }
    
    # ==================== Phase Tracking ====================
    
    def set_phase(self, phase: str) -> None:
        """Set current phase and log duration of previous."""
        if self._current_phase and self._phase_start_time:
            duration = (datetime.now() - self._phase_start_time).seconds
            self.add_knowledge(
                f"Phase '{self._current_phase}' completed in {duration}s",
                category="progress",
                importance=0.6
            )
        
        self._current_phase = phase
        self._phase_start_time = datetime.now()
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
        
        self.remember(
            f"Error in {self._current_phase}: {error[:200]}",
            memory_type="short",
            metadata={"type": "error", "context": context},
            importance=0.9,
        )
    
    # ==================== Context Generation ====================
    
    def get_memory_context(self, include_knowledge: bool = True) -> str:
        """
        Get memory context string for injection into prompts.
        
        Args:
            include_knowledge: Whether to include knowledge entries
            
        Returns:
            Formatted context string
        """
        lines = []
        
        # Condensed summary
        if self.conversation_condenser.summary:
            lines.append("## Previous Context Summary")
            lines.append(self.conversation_condenser.summary[:800])
            lines.append("")
        
        # Current phase
        if self._current_phase:
            duration = 0
            if self._phase_start_time:
                duration = (datetime.now() - self._phase_start_time).seconds
            lines.append(f"## Current Phase: {self._current_phase} ({duration}s)")
            lines.append("")
        
        # File stats
        stats = self.get_file_stats()
        if stats["created"] > 0:
            lines.append("## File Progress")
            lines.append(f"- Created: {stats['created']} files")
            lines.append(f"- Linted: {stats['linted']} ({stats['lint_passed']} passed)")
            unlinted = self.get_unlinted_files()
            if unlinted:
                lines.append(f"- Awaiting lint: {', '.join(unlinted[:5])}")
            lines.append("")
        
        # Recent knowledge
        if include_knowledge and self._knowledge:
            recent_knowledge = sorted(
                self._knowledge, 
                key=lambda x: x.get("importance", 0), 
                reverse=True
            )[:5]
            if recent_knowledge:
                lines.append("## Key Learnings")
                for k in recent_knowledge:
                    lines.append(f"- [{k['category']}] {k['content'][:100]}")
                lines.append("")
        
        # Recent errors
        if self._errors:
            lines.append("## Recent Issues")
            for err in self._errors[-3:]:
                lines.append(f"- {err['error'][:100]}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_operation_context(self) -> str:
        """Get current operation state as context string."""
        lines = ["=== OPERATION STATE ==="]
        
        if self._current_phase:
            duration = (datetime.now() - self._phase_start_time).seconds if self._phase_start_time else 0
            lines.append(f"Phase: {self._current_phase} ({duration}s)")
        
        stats = self.get_file_stats()
        lines.append(f"Files: {stats['created']} created, {stats['linted']} linted")
        
        unlinted = self.get_unlinted_files()
        if unlinted:
            lines.append(f"Unlinted: {', '.join(unlinted[:5])}")
        
        if self._errors:
            lines.append(f"Recent error: {self._errors[-1]['error'][:100]}")
        
        tool_stats = self.get_tool_stats()
        if tool_stats["consecutive_same"] > 3:
            lines.append(f"WARNING: {tool_stats['consecutive_same']} consecutive {self._last_tool} calls")
        
        lines.append("=== END STATE ===")
        return "\n".join(lines)
    
    # ==================== Task Lifecycle ====================
    
    async def on_task_complete(self, task_summary: str = "") -> None:
        """
        Called when a task completes. Extracts and persists learnings.
        
        Args:
            task_summary: Optional summary of what was accomplished
        """
        # Update condenser summary with recent events
        await self.update_summary()
        
        # Auto-extract knowledge from task
        if self._files_created:
            self.add_knowledge(
                f"Task created {len(self._files_created)} files: {', '.join(list(self._files_created)[:5])}",
                category="progress",
                importance=0.6
            )
        
        if task_summary:
            self.add_knowledge(task_summary, category="task_complete", importance=0.7)
    
    def reset_for_task(self) -> None:
        """Reset task-specific tracking while preserving long-term memory."""
        self._files_created.clear()
        self._files_modified.clear()
        self._files_linted.clear()
        self._lint_results.clear()
        self._tool_calls.clear()
        self._tool_call_counts.clear()
        self._consecutive_same_tool = 0
        self._last_tool = ""
        self._errors.clear()
        self.working.clear()
    
    def reset_all(self) -> None:
        """Full reset including all memory."""
        self.reset_for_task()
        self.short_term.clear()
        self._knowledge.clear()
        # Don't clear long-term - it should persist
    
    # ==================== Persistence ====================
    
    def save_state(self, filepath: str) -> None:
        """Save memory state to file."""
        state = {
            "knowledge": self._knowledge,
            "files_created": list(self._files_created),
            "current_phase": self._current_phase,
            "tool_call_counts": self._tool_call_counts,
            "condenser_summary": self.conversation_condenser.summary,
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
        
        # Also save long-term memory
        self.long_term.save(str(Path(filepath).parent / "long_term.json"))
    
    def load_state(self, filepath: str) -> None:
        """Load memory state from file."""
        if not Path(filepath).exists():
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        self._knowledge = state.get("knowledge", [])
        self._files_created = set(state.get("files_created", []))
        self._current_phase = state.get("current_phase", "")
        self._tool_call_counts = state.get("tool_call_counts", {})
        self.conversation_condenser._last_summary = state.get("condenser_summary", "")
        
        # Load long-term memory
        lt_path = Path(filepath).parent / "long_term.json"
        if lt_path.exists():
            self.long_term.load(str(lt_path))
    
    # ==================== Helpers ====================
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a file path for consistent tracking."""
        path = str(path)
        if path.startswith("./"):
            path = path[2:]
        if path.startswith("/"):
            try:
                path = str(Path(path).name)
            except:
                pass
        return path
    
    def stats(self) -> dict:
        """Extended stats."""
        base_stats = super().stats()
        base_stats.update({
            "files_created": len(self._files_created),
            "files_modified": len(self._files_modified),
            "files_linted": len(self._files_linted),
            "current_phase": self._current_phase,
            "errors": len(self._errors),
            "knowledge_count": len(self._knowledge),
            "tool_calls": len(self._tool_calls),
            "condensation_count": self.conversation_condenser._condensation_count,
        })
        return base_stats
