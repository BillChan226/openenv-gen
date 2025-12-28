"""
Dependency Analysis Tools

Tools for analyzing and managing dependencies:
- check_imports: Check imports in a file
- missing_dependencies: Find missing npm/pip packages
"""

import ast
import json
import re
import sys
from pathlib import Path
from typing import List, Set, Dict, Any, Optional, Union

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tool import BaseTool, ToolResult, ToolCategory, create_tool_param
from workspace import Workspace


class CheckImportsTool(BaseTool):
    """Check what a file imports."""
    
    NAME = "check_imports"
    DESCRIPTION = """List all imports in a file.

Shows what packages and modules a file depends on.
Works with Python and JavaScript/TypeScript.

Example:
  check_imports(file="app/backend/src/app.js")
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.CODE)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
    
    @property
    def tool_definition(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "Path to the file to analyze"
                    },
                },
                "required": ["file"],
            },
        )
    
    async def execute(self, file: str) -> ToolResult:
        file_path = self.workspace.resolve(file)
        
        if not file_path.exists():
            return ToolResult.fail(f"File not found: {file}")
        
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return ToolResult.fail(f"Error reading file: {e}")
        
        suffix = file_path.suffix.lower()
        
        if suffix == ".py":
            imports = self._analyze_python_imports(content)
        elif suffix in [".js", ".jsx", ".ts", ".tsx"]:
            imports = self._analyze_js_imports(content)
        else:
            return ToolResult.fail(f"Unsupported file type: {suffix}")
        
        return ToolResult.ok(data={
            "file": file,
            "imports": imports,
            "packages": list(set(i["package"] for i in imports if i.get("package"))),
            "local": [i for i in imports if i.get("local")],
        })
    
    def _analyze_python_imports(self, content: str) -> List[Dict]:
        imports = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            "type": "import",
                            "module": alias.name,
                            "package": alias.name.split(".")[0],
                            "local": False,
                            "line": node.lineno,
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    is_local = module.startswith(".")
                    imports.append({
                        "type": "from",
                        "module": module,
                        "names": [a.name for a in node.names],
                        "package": None if is_local else module.split(".")[0],
                        "local": is_local,
                        "line": node.lineno,
                    })
        except SyntaxError:
            # Fallback to regex
            for match in re.finditer(r"^import\s+(\S+)", content, re.MULTILINE):
                imports.append({"module": match.group(1), "package": match.group(1).split(".")[0]})
            for match in re.finditer(r"^from\s+(\S+)\s+import", content, re.MULTILINE):
                imports.append({"module": match.group(1), "local": match.group(1).startswith(".")})
        
        return imports
    
    def _analyze_js_imports(self, content: str) -> List[Dict]:
        imports = []
        
        # ES6 imports
        # import X from 'package'
        # import { X } from 'package'
        # import * as X from 'package'
        for match in re.finditer(
            r"import\s+(?:(?:\{[^}]+\}|\*\s+as\s+\w+|\w+)(?:\s*,\s*(?:\{[^}]+\}|\*\s+as\s+\w+|\w+))*\s+from\s+)?['\"]([^'\"]+)['\"]",
            content
        ):
            module = match.group(1)
            is_local = module.startswith(".") or module.startswith("/")
            imports.append({
                "type": "import",
                "module": module,
                "package": None if is_local else module.split("/")[0],
                "local": is_local,
            })
        
        # CommonJS require
        for match in re.finditer(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
            module = match.group(1)
            is_local = module.startswith(".") or module.startswith("/")
            imports.append({
                "type": "require",
                "module": module,
                "package": None if is_local else module.split("/")[0],
                "local": is_local,
            })
        
        return imports


class MissingDependenciesTool(BaseTool):
    """Find missing dependencies in a project."""
    
    NAME = "missing_dependencies"
    DESCRIPTION = """Analyze project to find missing dependencies.

Compares imports in code against declared dependencies in package.json/requirements.txt.

Example:
  missing_dependencies(path="app/backend")
  missing_dependencies(path="app/frontend")
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.CODE)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
    
    @property
    def tool_definition(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to analyze (default: entire project)"
                    },
                },
                "required": [],
            },
        )
    
    async def execute(self, path: str = "") -> ToolResult:
        search_path = self.workspace.resolve(path)
        
        if not search_path.exists():
            return ToolResult.fail(f"Path not found: {search_path}")
        
        results = {
            "npm": self._check_npm_dependencies(search_path),
            "python": self._check_python_dependencies(search_path),
        }
        
        all_missing = []
        if results["npm"]["missing"]:
            all_missing.extend([f"npm: {p}" for p in results["npm"]["missing"]])
        if results["python"]["missing"]:
            all_missing.extend([f"pip: {p}" for p in results["python"]["missing"]])
        
        return ToolResult.ok(data={
            "path": path or "(project root)",
            "npm": results["npm"],
            "python": results["python"],
            "missing_count": len(all_missing),
            "summary": all_missing[:20] if all_missing else "No missing dependencies found",
        })
    
    def _check_npm_dependencies(self, search_path: Path) -> Dict:
        # Find package.json
        package_json = None
        for p in [search_path / "package.json", search_path.parent / "package.json"]:
            if p.exists():
                package_json = p
                break
        
        if not package_json:
            return {"declared": [], "used": [], "missing": [], "error": "No package.json found"}
        
        # Get declared dependencies
        try:
            with open(package_json) as f:
                pkg = json.load(f)
            declared = set(pkg.get("dependencies", {}).keys())
            declared.update(pkg.get("devDependencies", {}).keys())
        except Exception:
            return {"declared": [], "used": [], "missing": [], "error": "Failed to parse package.json"}
        
        # Built-in Node modules
        builtins = {
            "path", "fs", "http", "https", "url", "util", "os", "crypto",
            "stream", "buffer", "events", "child_process", "assert", "net",
            "dns", "tls", "zlib", "querystring", "process",
        }
        
        # Find used packages
        used = set()
        for ext in ["*.js", "*.jsx", "*.ts", "*.tsx"]:
            for file_path in search_path.rglob(ext):
                if "node_modules" in str(file_path):
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8")
                    
                    # ES6 imports
                    for match in re.finditer(r"from\s+['\"]([^'\"./][^'\"]*)['\"]", content):
                        pkg = match.group(1).split("/")[0]
                        if not pkg.startswith("@"):
                            used.add(pkg)
                        else:
                            # Scoped package like @types/node
                            parts = match.group(1).split("/")
                            if len(parts) >= 2:
                                used.add(f"{parts[0]}/{parts[1]}")
                    
                    # require()
                    for match in re.finditer(r"require\(['\"]([^'\"./][^'\"]*)['\"]", content):
                        pkg = match.group(1).split("/")[0]
                        used.add(pkg)
                except Exception:
                    continue
        
        # Remove builtins
        used -= builtins
        
        # Find missing
        missing = used - declared
        
        return {
            "declared": sorted(declared),
            "used": sorted(used),
            "missing": sorted(missing),
        }
    
    def _check_python_dependencies(self, search_path: Path) -> Dict:
        # Find requirements.txt or pyproject.toml
        requirements = None
        for p in [
            search_path / "requirements.txt",
            search_path / "pyproject.toml",
            search_path.parent / "requirements.txt",
        ]:
            if p.exists():
                requirements = p
                break
        
        if not requirements:
            return {"declared": [], "used": [], "missing": [], "error": "No requirements.txt found"}
        
        # Get declared dependencies
        declared = set()
        try:
            content = requirements.read_text(encoding="utf-8")
            if requirements.name == "requirements.txt":
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Remove version specifiers
                        pkg = re.split(r"[<>=!~\[]", line)[0].strip().lower()
                        declared.add(pkg)
            elif requirements.name == "pyproject.toml":
                # Simple parsing for dependencies
                for match in re.finditer(r'"([^"]+)"', content):
                    pkg = re.split(r"[<>=!~\[]", match.group(1))[0].strip().lower()
                    if pkg and not pkg.startswith("python"):
                        declared.add(pkg)
        except Exception:
            return {"declared": [], "used": [], "missing": [], "error": "Failed to parse requirements"}
        
        # Python stdlib (simplified)
        stdlib = {
            "os", "sys", "re", "json", "time", "datetime", "logging", "pathlib",
            "typing", "collections", "itertools", "functools", "dataclasses",
            "abc", "asyncio", "subprocess", "threading", "multiprocessing",
            "unittest", "io", "contextlib", "copy", "enum", "hashlib", "uuid",
            "random", "math", "statistics", "pickle", "base64", "urllib",
            "http", "email", "html", "xml", "csv", "sqlite3", "socket",
        }
        
        # Find used packages
        used = set()
        for file_path in search_path.rglob("*.py"):
            if "__pycache__" in str(file_path) or "venv" in str(file_path):
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            pkg = alias.name.split(".")[0].lower()
                            used.add(pkg)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and not node.module.startswith("."):
                            pkg = node.module.split(".")[0].lower()
                            used.add(pkg)
            except Exception:
                continue
        
        # Remove stdlib
        used -= stdlib
        
        # Find missing
        missing = used - declared
        
        return {
            "declared": sorted(declared),
            "used": sorted(used),
            "missing": sorted(missing),
        }


def create_dependency_tools(output_dir: str = None, workspace: Workspace = None) -> List[BaseTool]:
    """Create all dependency analysis tools."""
    return [
        CheckImportsTool(output_dir=output_dir, workspace=workspace),
        MissingDependenciesTool(output_dir=output_dir, workspace=workspace),
    ]

