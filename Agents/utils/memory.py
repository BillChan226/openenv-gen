"""
Memory Module - Provides memory management for Agents

Supports:
- Short-term memory (conversation history)
- Long-term memory (persistent storage)
- Working memory (current task context)
- Semantic memory (vector-based retrieval)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4
import json
import hashlib
from collections import deque


@dataclass
class MemoryItem:
    """Single memory item"""
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.5  # 0.0 - 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    embedding: Optional[list[float]] = None  # Vector embedding for semantic search
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryItem":
        return cls(
            id=data.get("id", str(uuid4())),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            importance=data.get("importance", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
        )
    
    def access(self) -> None:
        """Record memory access"""
        self.access_count += 1
        self.last_accessed = datetime.now()


class BaseMemory(ABC):
    """Base memory interface"""
    
    @abstractmethod
    def add(self, content: str, metadata: dict = None, importance: float = 0.5) -> str:
        """Add item to memory, returns item ID"""
        pass
    
    @abstractmethod
    def get(self, item_id: str) -> Optional[MemoryItem]:
        """Get item by ID"""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Search memory"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all memory"""
        pass
    
    @abstractmethod
    def to_list(self) -> list[MemoryItem]:
        """Get all items as list"""
        pass


class ShortTermMemory(BaseMemory):
    """
    Short-term memory (conversation buffer)
    
    - Fixed size buffer
    - FIFO eviction
    - Fast access
    """
    
    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self._buffer: deque[MemoryItem] = deque(maxlen=max_size)
        self._index: dict[str, MemoryItem] = {}
    
    def add(self, content: str, metadata: dict = None, importance: float = 0.5) -> str:
        item = MemoryItem(
            content=content,
            metadata=metadata or {},
            importance=importance,
        )
        
        # Remove oldest if at capacity
        if len(self._buffer) >= self.max_size:
            oldest = self._buffer[0]
            if oldest.id in self._index:
                del self._index[oldest.id]
        
        self._buffer.append(item)
        self._index[item.id] = item
        
        return item.id
    
    def get(self, item_id: str) -> Optional[MemoryItem]:
        item = self._index.get(item_id)
        if item:
            item.access()
        return item
    
    def search(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Simple text search"""
        query_lower = query.lower()
        results = []
        
        for item in self._buffer:
            if query_lower in item.content.lower():
                item.access()
                results.append(item)
        
        # Sort by relevance (simple: importance * recency)
        results.sort(key=lambda x: (x.importance, x.timestamp), reverse=True)
        return results[:limit]
    
    def get_recent(self, n: int = 5) -> list[MemoryItem]:
        """Get most recent items"""
        items = list(self._buffer)[-n:]
        items.reverse()
        return items
    
    def clear(self) -> None:
        self._buffer.clear()
        self._index.clear()
    
    def to_list(self) -> list[MemoryItem]:
        return list(self._buffer)
    
    def __len__(self) -> int:
        return len(self._buffer)


class WorkingMemory:
    """
    Working memory for current task context
    
    - Key-value storage
    - Task-specific information
    - Cleared between tasks
    """
    
    def __init__(self):
        self._storage: dict[str, Any] = {}
        self._task_id: Optional[str] = None
        self._history: list[dict] = []  # Action history for current task
    
    def set_task(self, task_id: str) -> None:
        """Set current task and clear previous context"""
        if self._task_id != task_id:
            self.clear()
            self._task_id = task_id
    
    def set(self, key: str, value: Any) -> None:
        """Set a value"""
        self._storage[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value"""
        return self._storage.get(key, default)
    
    def delete(self, key: str) -> bool:
        """Delete a value"""
        if key in self._storage:
            del self._storage[key]
            return True
        return False
    
    def has(self, key: str) -> bool:
        """Check if key exists"""
        return key in self._storage
    
    def add_step(self, thought: str = None, action: str = None, 
                 action_input: Any = None, observation: str = None) -> None:
        """Add a step to action history"""
        step = {}
        if thought:
            step["thought"] = thought
        if action:
            step["action"] = action
        if action_input is not None:
            step["action_input"] = action_input
        if observation:
            step["observation"] = observation
        
        step["timestamp"] = datetime.now().isoformat()
        self._history.append(step)
    
    def get_history(self) -> list[dict]:
        """Get action history"""
        return self._history.copy()
    
    def get_last_observation(self) -> Optional[str]:
        """Get the last observation"""
        if self._history:
            return self._history[-1].get("observation")
        return None
    
    def clear(self) -> None:
        """Clear working memory"""
        self._storage.clear()
        self._history.clear()
        self._task_id = None
    
    def to_dict(self) -> dict:
        """Export as dictionary"""
        return {
            "task_id": self._task_id,
            "storage": self._storage.copy(),
            "history": self._history.copy(),
        }


class LongTermMemory(BaseMemory):
    """
    Long-term memory with persistence
    
    - Persistent storage
    - Importance-based retention
    - Supports serialization
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._memories: dict[str, MemoryItem] = {}
    
    def add(self, content: str, metadata: dict = None, importance: float = 0.5) -> str:
        item = MemoryItem(
            content=content,
            metadata=metadata or {},
            importance=importance,
        )
        
        # Evict if at capacity (remove least important + least accessed)
        if len(self._memories) >= self.max_size:
            self._evict()
        
        self._memories[item.id] = item
        return item.id
    
    def _evict(self) -> None:
        """Evict least valuable memory"""
        if not self._memories:
            return
        
        # Score = importance * 0.5 + recency * 0.3 + access_frequency * 0.2
        now = datetime.now()
        
        def score(item: MemoryItem) -> float:
            age_hours = (now - item.timestamp).total_seconds() / 3600
            recency = 1.0 / (1.0 + age_hours)
            frequency = min(1.0, item.access_count / 10.0)
            return item.importance * 0.5 + recency * 0.3 + frequency * 0.2
        
        # Find lowest score
        min_item = min(self._memories.values(), key=score)
        del self._memories[min_item.id]
    
    def get(self, item_id: str) -> Optional[MemoryItem]:
        item = self._memories.get(item_id)
        if item:
            item.access()
        return item
    
    def search(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Text search with ranking"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_items = []
        for item in self._memories.values():
            content_lower = item.content.lower()
            
            # Simple relevance scoring
            score = 0.0
            
            # Exact match bonus
            if query_lower in content_lower:
                score += 2.0
            
            # Word overlap
            content_words = set(content_lower.split())
            overlap = len(query_words & content_words)
            score += overlap * 0.5
            
            # Importance weight
            score *= (0.5 + item.importance * 0.5)
            
            if score > 0:
                scored_items.append((score, item))
        
        # Sort by score
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for _, item in scored_items[:limit]:
            item.access()
            results.append(item)
        
        return results
    
    def update_importance(self, item_id: str, importance: float) -> bool:
        """Update item importance"""
        item = self._memories.get(item_id)
        if item:
            item.importance = max(0.0, min(1.0, importance))
            return True
        return False
    
    def clear(self) -> None:
        self._memories.clear()
    
    def to_list(self) -> list[MemoryItem]:
        return list(self._memories.values())
    
    def save(self, filepath: str) -> None:
        """Save to file"""
        data = {
            "max_size": self.max_size,
            "memories": [m.to_dict() for m in self._memories.values()]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def load(self, filepath: str) -> None:
        """Load from file"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.max_size = data.get("max_size", self.max_size)
        self._memories.clear()
        
        for item_data in data.get("memories", []):
            item = MemoryItem.from_dict(item_data)
            self._memories[item.id] = item
    
    def __len__(self) -> int:
        return len(self._memories)


class SemanticMemory(BaseMemory):
    """
    Semantic memory with vector embeddings
    
    - Uses embeddings for similarity search
    - Supports various embedding backends
    - Optional integration with vector databases
    """
    
    def __init__(self, embedding_func=None, similarity_threshold: float = 0.7):
        """
        Args:
            embedding_func: Async function that takes text and returns embedding vector
            similarity_threshold: Minimum similarity for search results
        """
        self._memories: dict[str, MemoryItem] = {}
        self._embedding_func = embedding_func
        self.similarity_threshold = similarity_threshold
    
    async def add_async(self, content: str, metadata: dict = None, importance: float = 0.5) -> str:
        """Add with embedding (async)"""
        item = MemoryItem(
            content=content,
            metadata=metadata or {},
            importance=importance,
        )
        
        if self._embedding_func:
            item.embedding = await self._embedding_func(content)
        
        self._memories[item.id] = item
        return item.id
    
    def add(self, content: str, metadata: dict = None, importance: float = 0.5) -> str:
        """Add without embedding (sync)"""
        item = MemoryItem(
            content=content,
            metadata=metadata or {},
            importance=importance,
        )
        self._memories[item.id] = item
        return item.id
    
    def get(self, item_id: str) -> Optional[MemoryItem]:
        item = self._memories.get(item_id)
        if item:
            item.access()
        return item
    
    def search(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Fallback text search (use search_semantic for vector search)"""
        query_lower = query.lower()
        results = []
        
        for item in self._memories.values():
            if query_lower in item.content.lower():
                item.access()
                results.append(item)
        
        results.sort(key=lambda x: x.importance, reverse=True)
        return results[:limit]
    
    async def search_semantic(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Semantic search using embeddings"""
        if not self._embedding_func:
            return self.search(query, limit)
        
        query_embedding = await self._embedding_func(query)
        
        scored_items = []
        for item in self._memories.values():
            if item.embedding:
                similarity = self._cosine_similarity(query_embedding, item.embedding)
                if similarity >= self.similarity_threshold:
                    scored_items.append((similarity, item))
        
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for _, item in scored_items[:limit]:
            item.access()
            results.append(item)
        
        return results
    
    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(a) != len(b):
            return 0.0
        
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def clear(self) -> None:
        self._memories.clear()
    
    def to_list(self) -> list[MemoryItem]:
        return list(self._memories.values())
    
    def __len__(self) -> int:
        return len(self._memories)


class AgentMemory:
    """
    Unified memory system for an Agent
    
    Combines:
    - Short-term memory (recent conversation)
    - Working memory (current task)
    - Long-term memory (persistent knowledge)
    - Semantic memory (optional, for retrieval)
    """
    
    def __init__(
        self,
        short_term_size: int = 20,
        long_term_size: int = 1000,
        enable_semantic: bool = False,
        embedding_func=None,
    ):
        self.short_term = ShortTermMemory(max_size=short_term_size)
        self.working = WorkingMemory()
        self.long_term = LongTermMemory(max_size=long_term_size)
        
        if enable_semantic:
            self.semantic = SemanticMemory(embedding_func=embedding_func)
        else:
            self.semantic = None
    
    def remember(self, content: str, memory_type: str = "short", 
                 metadata: dict = None, importance: float = 0.5) -> str:
        """
        Add a memory
        
        Args:
            content: Memory content
            memory_type: "short", "long", or "semantic"
            metadata: Additional metadata
            importance: Importance score (0.0 - 1.0)
            
        Returns:
            Memory item ID
        """
        if memory_type == "short":
            return self.short_term.add(content, metadata, importance)
        elif memory_type == "long":
            return self.long_term.add(content, metadata, importance)
        elif memory_type == "semantic" and self.semantic:
            return self.semantic.add(content, metadata, importance)
        else:
            return self.short_term.add(content, metadata, importance)
    
    def recall(self, query: str, sources: list[str] = None, limit: int = 5) -> list[MemoryItem]:
        """
        Search across memory systems
        
        Args:
            query: Search query
            sources: List of sources to search ("short", "long", "semantic")
            limit: Maximum results per source
            
        Returns:
            Combined search results
        """
        sources = sources or ["short", "long"]
        results = []
        
        if "short" in sources:
            results.extend(self.short_term.search(query, limit))
        
        if "long" in sources:
            results.extend(self.long_term.search(query, limit))
        
        # Note: semantic search is async, use recall_semantic for that
        
        # Deduplicate and sort
        seen_ids = set()
        unique_results = []
        for item in results:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                unique_results.append(item)
        
        unique_results.sort(key=lambda x: (x.importance, x.timestamp), reverse=True)
        return unique_results[:limit * len(sources)]
    
    async def recall_semantic(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Semantic search (async)"""
        if self.semantic:
            return await self.semantic.search_semantic(query, limit)
        return []
    
    def get_context_string(self, max_items: int = 10) -> str:
        """
        Get formatted context string for prompt inclusion
        
        Returns:
            Formatted string with recent memories and working context
        """
        lines = []
        
        # Working memory context
        if self.working._storage:
            lines.append("## Current Task Context")
            for key, value in self.working._storage.items():
                if key not in ["_internal"]:  # Skip internal keys
                    lines.append(f"- {key}: {value}")
            lines.append("")
        
        # Recent history
        recent = self.short_term.get_recent(max_items)
        if recent:
            lines.append("## Recent Conversation")
            for item in recent:
                role = item.metadata.get("role", "memory")
                lines.append(f"[{role}] {item.content}")
            lines.append("")
        
        return "\n".join(lines)
    
    def save(self, filepath: str) -> None:
        """Save long-term memory to file"""
        self.long_term.save(filepath)
    
    def load(self, filepath: str) -> None:
        """Load long-term memory from file"""
        self.long_term.load(filepath)
    
    def clear_all(self) -> None:
        """Clear all memories"""
        self.short_term.clear()
        self.working.clear()
        self.long_term.clear()
        if self.semantic:
            self.semantic.clear()
    
    def stats(self) -> dict:
        """Get memory statistics"""
        return {
            "short_term_count": len(self.short_term),
            "long_term_count": len(self.long_term),
            "semantic_count": len(self.semantic) if self.semantic else 0,
            "working_memory_keys": list(self.working._storage.keys()),
            "history_steps": len(self.working.get_history()),
        }

