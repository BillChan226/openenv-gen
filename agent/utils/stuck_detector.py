"""
Stuck Detection Module - Detects when agent is stuck in loops

Inspired by OpenHands StuckDetector, this module provides:
- Detection of repeated action-observation patterns
- Detection of repeated error loops
- Detection of monologue loops (agent talking to itself)
- Automatic loop breaking suggestions
"""

from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime

from .prompt_loader import render_prompt

@dataclass
class StuckAnalysis:
    """Analysis result when agent is detected as stuck."""
    loop_type: str  # Type of loop detected
    loop_repeat_times: int  # How many times the pattern repeated
    loop_start_idx: int  # Index where the loop started
    suggestion: str = ""  # Suggestion for breaking the loop


@dataclass
class HistoryEvent:
    """Generic event in agent history."""
    event_type: str  # "action", "observation", "error", "message"
    content: Any
    source: str = "agent"  # "agent", "user", "system"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, HistoryEvent):
            return False
        return (
            self.event_type == other.event_type and
            self._normalize_content(self.content) == self._normalize_content(other.content)
        )
    
    @staticmethod
    def _normalize_content(content: Any) -> str:
        """Normalize content for comparison."""
        s = str(content)
        # Remove timestamps, IDs, PIDs that might differ
        import re
        s = re.sub(r'\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\b', '[TIME]', s)
        s = re.sub(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', '[UUID]', s)
        s = re.sub(r'\bpid[=:]\s*\d+\b', 'pid=[PID]', s, flags=re.IGNORECASE)
        return s


class StuckDetector:
    """
    Detects when an agent is stuck in a loop.
    
    Scenarios detected:
    1. Repeated action-observation pairs (same action, same result)
    2. Repeated action-error pairs (same action keeps failing)
    3. Monologue (agent sending same message repeatedly)
    4. Alternating pattern (A-B-A-B-A-B loop)
    5. Context window errors (repeated condensation failures)
    
    Usage:
        detector = StuckDetector()
        detector.add_event(HistoryEvent(event_type="action", content="run_command ls"))
        detector.add_event(HistoryEvent(event_type="observation", content="file1.txt"))
        
        if detector.is_stuck():
            analysis = detector.get_analysis()
            print(f"Stuck in {analysis.loop_type} loop!")
    """
    
    # Common syntax error messages that indicate a real issue
    SYNTAX_ERROR_PATTERNS = [
        "SyntaxError:",
        "IndentationError:",
        "TabError:",
        "ModuleNotFoundError:",
        "ImportError:",
    ]
    
    def __init__(
        self,
        max_history: int = 100,
        min_loop_detection: int = 3,
    ):
        """
        Args:
            max_history: Maximum history events to keep
            min_loop_detection: Minimum repetitions to detect a loop
        """
        self.max_history = max_history
        self.min_loop_detection = min_loop_detection
        self._history: list[HistoryEvent] = []
        self._stuck_analysis: Optional[StuckAnalysis] = None
    
    def add_event(self, event: HistoryEvent) -> None:
        """Add an event to history."""
        self._history.append(event)
        
        # Trim history if too long
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]
    
    def add_action(self, content: Any) -> None:
        """Convenience method to add an action event."""
        self.add_event(HistoryEvent(event_type="action", content=content, source="agent"))
    
    def record_action(self, tool_name: str) -> None:
        """Record a tool call action (just the tool name, for loop detection)."""
        self.add_event(HistoryEvent(event_type="action", content=tool_name, source="agent"))
    
    def add_observation(self, content: Any) -> None:
        """Convenience method to add an observation event."""
        self.add_event(HistoryEvent(event_type="observation", content=content, source="system"))
    
    def add_error(self, content: Any) -> None:
        """Convenience method to add an error event."""
        self.add_event(HistoryEvent(event_type="error", content=content, source="system"))
    
    def add_message(self, content: Any, source: str = "agent") -> None:
        """Convenience method to add a message event."""
        self.add_event(HistoryEvent(event_type="message", content=content, source=source))
    
    def clear(self) -> None:
        """Clear history."""
        self._history.clear()
        self._stuck_analysis = None
    
    def is_stuck(self) -> bool:
        """
        Check if the agent is stuck in a loop.
        
        Returns:
            True if a loop pattern is detected
        """
        self._stuck_analysis = None
        
        if len(self._history) < self.min_loop_detection:
            return False
        
        # Check various loop scenarios
        if self._check_repeated_action_observation():
            return True
        
        if self._check_repeated_action_error():
            return True
        
        if self._check_monologue():
            return True
        
        if self._check_alternating_pattern():
            return True
        
        # NEW: Check for same tool called many times (even with different args)
        if self._check_tool_name_loop():
            return True
        
        return False
    
    def get_analysis(self) -> Optional[StuckAnalysis]:
        """Get the stuck analysis if stuck was detected."""
        return self._stuck_analysis
    
    def _get_recent_events(self, event_type: str, count: int) -> list[HistoryEvent]:
        """Get recent events of a specific type."""
        events = [e for e in self._history if e.event_type == event_type]
        return events[-count:] if len(events) >= count else events
    
    def _check_repeated_action_observation(self) -> bool:
        """Check for repeated same action with same observation (at least 8 repetitions)."""
        actions = self._get_recent_events("action", 8)
        observations = self._get_recent_events("observation", 8)
        
        if len(actions) < 8 or len(observations) < 8:
            return False
        
        # Check if all 8 recent actions are the same
        if not all(actions[0] == a for a in actions):
            return False
        
        # Check if all 8 recent observations are the same
        if not all(observations[0] == o for o in observations):
            return False
        
        self._stuck_analysis = StuckAnalysis(
            loop_type="repeated_action_observation",
            loop_repeat_times=8,
            loop_start_idx=len(self._history) - 16,
            suggestion="Try a different approach or break down the task differently.",
        )
        return True
    
    def _check_repeated_action_error(self) -> bool:
        """Check for repeated same action with errors."""
        actions = self._get_recent_events("action", 3)
        errors = self._get_recent_events("error", 3)
        
        if len(actions) < 3 or len(errors) < 3:
            return False
        
        # Check if last 3 actions are the same
        if not all(actions[0] == a for a in actions):
            return False
        
        # Check if last 3 results are all errors
        self._stuck_analysis = StuckAnalysis(
            loop_type="repeated_action_error",
            loop_repeat_times=3,
            loop_start_idx=len(self._history) - 6,
            suggestion="The same action keeps failing. Analyze the error and try a fundamentally different approach.",
        )
        return True
    
    def _check_monologue(self) -> bool:
        """Check for agent sending the same message repeatedly."""
        messages = [
            e for e in self._history
            if e.event_type == "message" and e.source == "agent"
        ]
        
        if len(messages) < 3:
            return False
        
        recent = messages[-3:]
        
        if not all(recent[0] == m for m in recent):
            return False
        
        # Check if there are any observations between messages
        start_idx = self._history.index(recent[0]) if recent[0] in self._history else -1
        if start_idx >= 0:
            between = self._history[start_idx:]
            has_observation = any(e.event_type == "observation" for e in between)
            if not has_observation:
                self._stuck_analysis = StuckAnalysis(
                    loop_type="monologue",
                    loop_repeat_times=3,
                    loop_start_idx=start_idx,
                    suggestion="Agent is repeating itself. Take a concrete action instead of just messaging.",
                )
                return True
        
        return False
    
    def _check_alternating_pattern(self) -> bool:
        """Check for alternating A-B-A-B pattern (at least 10 events = 5 repetitions)."""
        if len(self._history) < 20:
            return False
        
        # Get last 20 events for more robust detection
        recent = self._history[-20:]
        
        # Check for A-B-A-B... pattern (at least 10 alternations)
        pattern_a = recent[::2]  # Events at positions 0, 2, 4, ...
        pattern_b = recent[1::2]  # Events at positions 1, 3, 5, ...
        
        if len(pattern_a) < 10 or len(pattern_b) < 10:
            return False
        
        if (all(pattern_a[0] == e for e in pattern_a) and
            all(pattern_b[0] == e for e in pattern_b)):
            
            self._stuck_analysis = StuckAnalysis(
                loop_type="alternating_pattern",
                loop_repeat_times=10,
                loop_start_idx=len(self._history) - 20,
                suggestion="Agent is in an A-B-A-B loop. Break the pattern by trying something completely different.",
            )
            return True
        
        return False
    
    def _check_tool_name_loop(self) -> bool:
        """
        Check if the same tool is called many times consecutively (even with different args).
        
        This catches patterns like:
            lint("file1.jsx") -> lint("file2.jsx") -> lint("file3.jsx") -> ...
        Where the tool name is the same but arguments differ.
        """
        actions = self._get_recent_events("action", 30)
        if len(actions) < 20:
            return False
        
        # Extract tool names from actions (format: "tool_name" or "tool_name(args)")
        tool_names = []
        for action in actions[-30:]:
            content = str(action.content)
            # Extract just the tool name
            if "(" in content:
                tool_name = content.split("(")[0]
            else:
                tool_name = content.split()[0] if content else ""
            tool_names.append(tool_name)
        
        if not tool_names:
            return False
        
        # Check if 80%+ of recent calls are the same tool
        from collections import Counter
        counts = Counter(tool_names)
        most_common_tool, most_common_count = counts.most_common(1)[0]
        
        if most_common_count >= 20:
            self._stuck_analysis = StuckAnalysis(
                loop_type="repeated_tool_loop",
                loop_repeat_times=most_common_count,
                loop_start_idx=len(self._history) - 30,
                suggestion=f"Tool '{most_common_tool}' has been called {most_common_count} times. "
                          f"This indicates a loop. Call finish() to complete the task.",
            )
            return True
        
        return False
    
    def get_loop_breaker_prompt(self) -> str:
        """
        Get a prompt to help break the detected loop.
        
        Returns:
            Prompt string to inject into agent conversation
        """
        if not self._stuck_analysis:
            return ""
        
        analysis = self._stuck_analysis
        
        return render_prompt(
            "stuck_loop_breaker.j2",
            loop_type=analysis.loop_type,
            loop_repeat_times=analysis.loop_repeat_times,
            suggestion=analysis.suggestion,
        )


def create_stuck_detector(max_history: int = 100) -> StuckDetector:
    """Create a new stuck detector instance."""
    return StuckDetector(max_history=max_history)

