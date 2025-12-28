"""
File Tools Base - Shared utilities and FileHistory
"""
from typing import Optional


class FileHistory:
    """Singleton for file undo history."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._history = {}
            cls._instance.max_history = 10
        return cls._instance
    
    def save(self, path: str, content: str):
        if path not in self._history:
            self._history[path] = []
        self._history[path].append(content)
        if len(self._history[path]) > self.max_history:
            self._history[path] = self._history[path][-self.max_history:]
    
    def get_previous(self, path: str) -> Optional[str]:
        if path in self._history and self._history[path]:
            return self._history[path].pop()
        return None
    
    def clear(self, path: str = None):
        if path:
            self._history.pop(path, None)
        else:
            self._history.clear()


# Singleton instance
_file_history = FileHistory()

