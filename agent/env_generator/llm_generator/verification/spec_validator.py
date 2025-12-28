"""
Spec Validator - Validates design specification files

Ensures spec.api.json, spec.project.json, and spec.ui.json are:
1. Valid JSON
2. Have required sections
3. Are cross-referenced correctly
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set


@dataclass
class ValidationIssue:
    """A validation issue found in specs."""
    file: str
    path: str
    severity: str  # "error" or "warning"
    message: str


@dataclass
class ValidationResult:
    """Result of spec validation."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    api_endpoints: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    
    def add_error(self, file: str, path: str, message: str):
        self.issues.append(ValidationIssue(file, path, "error", message))
        self.valid = False
    
    def add_warning(self, file: str, path: str, message: str):
        self.issues.append(ValidationIssue(file, path, "warning", message))


class SpecValidator:
    """Validates design specification files."""
    
    REQUIRED_API_SECTIONS = ["conventions", "schemas", "endpoints"]
    # "entities" can be top-level or within permissions_matrix
    REQUIRED_PROJECT_SECTIONS = ["user_roles_and_personas"]
    REQUIRED_UI_SECTIONS = ["design_tokens", "components"]
    
    REQUIRED_AUTH_ENDPOINTS = [
        ("POST", "/auth/register"),
        ("POST", "/auth/login"),
        ("GET", "/auth/me"),
    ]
    
    def __init__(self, workspace_root: Path):
        self.root = Path(workspace_root)
        self.design_dir = self.root / "design"
    
    def validate_all(self) -> ValidationResult:
        """Validate all spec files."""
        result = ValidationResult(valid=True)
        
        # Check design directory exists
        if not self.design_dir.exists():
            result.add_error("design/", "", "Design directory not found")
            return result
        
        # Validate each spec file
        api_result = self._validate_api_spec()
        project_result = self._validate_project_spec()
        ui_result = self._validate_ui_spec()
        
        # Merge results
        for r in [api_result, project_result, ui_result]:
            result.issues.extend(r.issues)
            if not r.valid:
                result.valid = False
        
        result.api_endpoints = api_result.api_endpoints
        result.entities = project_result.entities
        result.components = ui_result.components
        
        # Cross-reference validation
        self._validate_cross_references(result, api_result, project_result, ui_result)
        
        return result
    
    def _load_json(self, filename: str) -> tuple[Optional[Dict], Optional[str]]:
        """Load and parse a JSON file."""
        path = self.design_dir / filename
        if not path.exists():
            return None, f"File not found: {filename}"
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f), None
        except json.JSONDecodeError as e:
            return None, f"Invalid JSON: {e}"
    
    def _validate_api_spec(self) -> ValidationResult:
        """Validate spec.api.json."""
        result = ValidationResult(valid=True)
        filename = "spec.api.json"
        
        data, error = self._load_json(filename)
        if error:
            result.add_error(filename, "", error)
            return result
        
        # Check required sections
        for section in self.REQUIRED_API_SECTIONS:
            if section not in data:
                result.add_error(filename, section, f"Missing required section: {section}")
        
        # Validate conventions
        if "conventions" in data:
            conv = data["conventions"]
            if "base_url" not in conv:
                result.add_warning(filename, "conventions.base_url", "Missing base_url")
            if "auth" not in conv:
                result.add_warning(filename, "conventions.auth", "Missing auth convention")
            if "error_format" not in conv:
                result.add_warning(filename, "conventions.error_format", "Missing error_format")
        
        # Validate endpoints
        if "endpoints" in data:
            endpoints = data["endpoints"]
            if not isinstance(endpoints, list):
                result.add_error(filename, "endpoints", "endpoints must be an array")
            else:
                # Collect endpoint paths for cross-reference
                endpoint_set: Set[tuple] = set()
                for i, ep in enumerate(endpoints):
                    if "path" not in ep or "method" not in ep:
                        result.add_error(filename, f"endpoints[{i}]", "Missing path or method")
                    else:
                        endpoint_set.add((ep["method"].upper(), ep["path"]))
                        result.api_endpoints.append(f"{ep['method'].upper()} {ep['path']}")
                    
                    if "auth_required" not in ep:
                        result.add_warning(filename, f"endpoints[{i}]", "Missing auth_required flag")
                
                # Check for required auth endpoints (allow various path formats)
                for method, path in self.REQUIRED_AUTH_ENDPOINTS:
                    found = False
                    # Check exact match, with /api prefix, or with {base_url} placeholder
                    for check_path in [path, f"/api{path}", f"{{base_url}}{path}"]:
                        if (method, check_path) in endpoint_set:
                            found = True
                            break
                    if not found:
                        # Warn instead of error if login exists (register might be optional)
                        if path == "/auth/register":
                            result.add_warning(filename, "endpoints", f"Missing auth endpoint: {method} {path}")
                        else:
                            result.add_error(filename, "endpoints", f"Missing required auth endpoint: {method} {path}")
        
        # Validate schemas
        if "schemas" in data:
            schemas = data["schemas"]
            if not isinstance(schemas, dict):
                result.add_error(filename, "schemas", "schemas must be an object")
            elif len(schemas) == 0:
                result.add_warning(filename, "schemas", "No schemas defined")
        
        return result
    
    def _validate_project_spec(self) -> ValidationResult:
        """Validate spec.project.json."""
        result = ValidationResult(valid=True)
        filename = "spec.project.json"
        
        data, error = self._load_json(filename)
        if error:
            result.add_error(filename, "", error)
            return result
        
        # Check required sections
        for section in self.REQUIRED_PROJECT_SECTIONS:
            if section not in data:
                result.add_error(filename, section, f"Missing required section: {section}")
        
        # Validate user roles
        if "user_roles_and_personas" in data:
            roles = data["user_roles_and_personas"]
            if "personas" not in roles:
                result.add_warning(filename, "user_roles_and_personas", "Missing personas")
        
        # Validate entities (can be top-level or within permissions_matrix)
        if "entities" in data:
            entities = data["entities"]
            if isinstance(entities, dict):
                result.entities = list(entities.keys())
                for name, entity in entities.items():
                    if "fields" not in entity:
                        result.add_warning(filename, f"entities.{name}", "Missing fields definition")
            elif isinstance(entities, list):
                result.entities = entities
        elif "permissions_matrix" in data:
            pm = data["permissions_matrix"]
            if isinstance(pm, dict) and "entities" in pm:
                if isinstance(pm["entities"], list):
                    result.entities = pm["entities"]
        
        # Validate workflows (optional but recommended)
        if "workflows" not in data:
            result.add_warning(filename, "workflows", "No workflows defined")
        
        return result
    
    def _validate_ui_spec(self) -> ValidationResult:
        """Validate spec.ui.json."""
        result = ValidationResult(valid=True)
        filename = "spec.ui.json"
        
        data, error = self._load_json(filename)
        if error:
            result.add_error(filename, "", error)
            return result
        
        # Check required sections
        for section in self.REQUIRED_UI_SECTIONS:
            if section not in data:
                result.add_error(filename, section, f"Missing required section: {section}")
        
        # Validate design tokens
        if "design_tokens" in data:
            tokens = data["design_tokens"]
            if "colors" not in tokens:
                result.add_warning(filename, "design_tokens.colors", "Missing colors")
            if "typography" not in tokens:
                result.add_warning(filename, "design_tokens.typography", "Missing typography")
            if "spacing" not in tokens:
                result.add_warning(filename, "design_tokens.spacing", "Missing spacing")
        
        # Validate components
        if "components" in data:
            components = data["components"]
            if isinstance(components, list):
                for i, comp in enumerate(components):
                    if "name" not in comp:
                        result.add_warning(filename, f"components[{i}]", "Missing component name")
                    else:
                        result.components.append(comp["name"])
            elif isinstance(components, dict):
                # Also support object format
                for category, comps in components.items():
                    if isinstance(comps, list):
                        for comp in comps:
                            if isinstance(comp, dict) and "name" in comp:
                                result.components.append(comp["name"])
        
        return result
    
    def _validate_cross_references(
        self,
        result: ValidationResult,
        api_result: ValidationResult,
        project_result: ValidationResult,
        ui_result: ValidationResult
    ):
        """Validate cross-references between spec files."""
        # Check if API endpoints cover all entities with CRUD operations
        entities = set(project_result.entities)
        
        # Simple heuristic: each entity should have at least GET and POST endpoints
        for entity in entities:
            entity_lower = entity.lower()
            has_get = any(entity_lower in ep.lower() for ep in api_result.api_endpoints if ep.startswith("GET"))
            has_post = any(entity_lower in ep.lower() for ep in api_result.api_endpoints if ep.startswith("POST"))
            
            if not has_get and not has_post:
                result.add_warning(
                    "cross-reference",
                    f"entity.{entity}",
                    f"Entity '{entity}' has no API endpoints defined"
                )


def validate_specs(workspace_root: str) -> ValidationResult:
    """Convenience function to validate specs."""
    validator = SpecValidator(Path(workspace_root))
    return validator.validate_all()


# Command line interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python spec_validator.py <workspace_root>")
        sys.exit(1)
    
    result = validate_specs(sys.argv[1])
    
    print(f"\n{'='*60}")
    print(f"Spec Validation: {'PASS' if result.valid else 'FAIL'}")
    print(f"{'='*60}")
    
    if result.issues:
        print("\nIssues found:")
        for issue in result.issues:
            icon = "ERROR" if issue.severity == "error" else "WARN"
            print(f"  [{icon}] {issue.file}:{issue.path} - {issue.message}")
    
    if result.api_endpoints:
        print(f"\nAPI Endpoints ({len(result.api_endpoints)}):")
        for ep in result.api_endpoints[:10]:
            print(f"  - {ep}")
        if len(result.api_endpoints) > 10:
            print(f"  ... and {len(result.api_endpoints) - 10} more")
    
    if result.entities:
        print(f"\nEntities ({len(result.entities)}): {', '.join(result.entities)}")
    
    if result.components:
        print(f"\nUI Components ({len(result.components)}): {', '.join(result.components[:10])}...")
    
    sys.exit(0 if result.valid else 1)

