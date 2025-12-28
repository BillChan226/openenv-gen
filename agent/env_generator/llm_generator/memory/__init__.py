"""
Memory System for LLM Generator

Based on utils/memory.py base classes:
- ShortTermMemory
- LongTermMemory
- WorkingMemory
- LLMSummarizingCondenser
- AgentMemory

This module provides:
1. GeneratorMemory - Extended AgentMemory for code generation
2. MemoryBank - Structured project documentation (Cursor Memory Bank style)
"""

from .generator_memory import GeneratorMemory
from .memory_bank import MemoryBank

__all__ = ["GeneratorMemory", "MemoryBank"]
