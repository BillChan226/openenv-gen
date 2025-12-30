"""
Workspace Manager - File Access Control for Multi-Agent System

Each agent has:
- A write directory (can create/modify files)
- Read access to other directories
- No cross-write access
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set


class WorkspaceManager:
    """
    Manages file access for multi-agent system.
    
    Directory structure:
    - design/       -> DesignAgent writes
    - app/database/ -> DatabaseAgent writes
    - app/backend/  -> BackendAgent writes
    - app/frontend/ -> FrontendAgent writes
    - docker/       -> Orchestrator writes
    
    All agents can read all directories.
    """
    
    # Agent to directory mapping
    AGENT_WRITE_DIRS = {
        "design": "design",
        "database": "app/database",
        "backend": "app/backend",
        "frontend": "app/frontend",
        "user": None,  # UserAgent doesn't write code
        "orchestrator": "docker",
    }
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self._logger = logging.getLogger("WorkspaceManager")
        
        # Create all directories
        self._init_directories()
    
    def _init_directories(self):
        """Create all workspace directories."""
        dirs = [
            "design",
            "app/database",
            "app/backend/routes",
            "app/backend/middleware",
            "app/frontend/src/pages",
            "app/frontend/src/components",
            "app/frontend/src/services",
            "docker",
        ]
        
        for d in dirs:
            (self.base_dir / d).mkdir(parents=True, exist_ok=True)
    
    # ==================== File Operations ====================
    
    def read_file(self, path: str, agent_id: str = None) -> Optional[str]:
        """
        Read a file. All agents can read all files.
        
        Args:
            path: Relative path from base_dir
            agent_id: Agent ID (for logging)
            
        Returns:
            File content or None if not found
        """
        full_path = self.base_dir / path
        
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self._logger.error(f"Failed to read {path}: {e}")
            return None
    
    def write_file(self, path: str, content: str, agent_id: str) -> bool:
        """
        Write a file. Only allowed in agent's write directory.
        
        Args:
            path: Relative path from base_dir
            content: File content
            agent_id: Agent ID (for permission check)
            
        Returns:
            True if written, False if not allowed
        """
        # Check permission
        if not self._can_write(path, agent_id):
            self._logger.warning(
                f"Agent '{agent_id}' cannot write to '{path}'. "
                f"Allowed: {self.AGENT_WRITE_DIRS.get(agent_id)}"
            )
            return False
        
        full_path = self.base_dir / path
        
        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._logger.debug(f"[{agent_id}] Wrote: {path}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to write {path}: {e}")
            return False
    
    def list_files(self, directory: str = "", agent_id: str = None) -> List[str]:
        """
        List files in a directory. All agents can list all directories.
        
        Args:
            directory: Relative path from base_dir (empty = all)
            agent_id: Agent ID (for logging)
            
        Returns:
            List of relative file paths
        """
        target = self.base_dir / directory if directory else self.base_dir
        
        if not target.exists():
            return []
        
        files = []
        for item in target.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(self.base_dir)
                files.append(str(rel_path))
        
        return sorted(files)
    
    def _can_write(self, path: str, agent_id: str) -> bool:
        """Check if agent can write to path."""
        allowed_dir = self.AGENT_WRITE_DIRS.get(agent_id)
        
        if allowed_dir is None:
            return False
        
        # Normalize paths
        path_norm = path.replace("\\", "/")
        allowed_norm = allowed_dir.replace("\\", "/")
        
        return path_norm.startswith(allowed_norm)
    
    # ==================== Agent Helpers ====================
    
    def get_agent_write_dir(self, agent_id: str) -> Optional[Path]:
        """Get the write directory for an agent."""
        dir_name = self.AGENT_WRITE_DIRS.get(agent_id)
        if dir_name:
            return self.base_dir / dir_name
        return None
    
    def get_all_design_docs(self) -> Dict[str, str]:
        """Read all design documents."""
        design_files = self.list_files("design")
        docs = {}
        
        for f in design_files:
            content = self.read_file(f)
            if content:
                docs[f] = content
        
        return docs
    
    # ==================== Status ====================
    
    def get_stats(self) -> Dict:
        """Get workspace statistics."""
        stats = {
            "base_dir": str(self.base_dir),
            "directories": {},
        }
        
        for agent_id, dir_name in self.AGENT_WRITE_DIRS.items():
            if dir_name:
                files = self.list_files(dir_name)
                stats["directories"][dir_name] = {
                    "agent": agent_id,
                    "file_count": len(files),
                    "files": files[:10],  # First 10 files
                }
        
        return stats
