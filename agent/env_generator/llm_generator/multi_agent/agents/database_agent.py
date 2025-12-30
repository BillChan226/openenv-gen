"""
Database Agent - Database Code Generation

Responsibilities:
1. Generate SQL schema from design spec
2. Create seed data with test users
3. Generate migrations
4. Fix database-related issues
5. Load real data from HuggingFace datasets (via DataEngine)

Uses prompts from: prompts/code_agents.j2
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.llm import Message

from .base import EnvGenAgent

# Try to import DataEngine for real data loading
try:
    from data_engine import DataEngine
    HAS_DATA_ENGINE = True
except ImportError:
    HAS_DATA_ENGINE = False


class DatabaseAgent(EnvGenAgent):
    """
    Database Agent - Handles all database code.
    
    Communicates with:
    - DesignAgent: Get schema details
    - BackendAgent: Coordinate data types
    
    Features:
    - SQL schema generation from design specs
    - Real data loading from HuggingFace datasets
    - Seed data generation with test users
    """
    
    agent_id = "database"
    agent_name = "DatabaseAgent"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._schema: Dict = {}
        self._files_created: List[str] = []
        self._data_engine: Optional["DataEngine"] = None
        
        # Initialize data engine if available
        if HAS_DATA_ENGINE:
            try:
                self._data_engine = DataEngine()
                self._logger.info("DataEngine initialized for real data loading")
            except Exception as e:
                self._logger.warning(f"Could not initialize DataEngine: {e}")
    
    # ==================== Main Interface ====================
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database tasks."""
        task_type = task.get("type", "")
        
        if task_type == "generate":
            return await self._generate()
        elif task_type == "fix":
            return await self._fix_issues(task.get("issues", []))
        else:
            return {"success": False, "error": f"Unknown task type: {task_type}"}
    
    # ==================== Generation ====================
    
    async def _generate(self) -> Dict[str, Any]:
        """Generate database code from design spec."""
        self._logger.info("Generating database code...")
        
        # Get schema from design docs or file
        schema = self._design_docs.get("design_schema") or self._design_docs.get("schema")
        
        if not schema:
            content = self.read_file("design/spec.database.json")
            if content:
                schema = json.loads(content)
        
        if not schema:
            # Schema not found - use LLM with tools to decide what to do
            # The LLM can use ask_agent tool to communicate with design agent
            return {
                "success": False, 
                "error": "No database schema found. Use ask_agent tool to request from design agent.",
                "suggestion": "ask_agent(agent_id='design', question='Please provide the database schema JSON.')"
            }
        
        self._schema = schema
        
        try:
            # 1. Generate init.sql
            init_sql = await self._generate_init_sql(schema)
            self.write_file("app/database/init.sql", init_sql)
            self._files_created.append("app/database/init.sql")
            
            # 2. Generate seed.sql
            seed_sql = await self._generate_seed_sql(schema)
            self.write_file("app/database/seed.sql", seed_sql)
            self._files_created.append("app/database/seed.sql")
            
            # 3. Generate Dockerfile
            dockerfile = self._generate_dockerfile()
            self.write_file("app/database/Dockerfile", dockerfile)
            self._files_created.append("app/database/Dockerfile")
            
            # 4. Try to load real data from HuggingFace
            real_data_loaded = await self._load_real_data(schema)
            
            # Return result - LLM can decide to notify others using tell_agent/broadcast tools
            return {
                "success": True,
                "files_created": self._files_created,
                "real_data_loaded": real_data_loaded,
                "tables": [t["name"] for t in schema.get("tables", [])],
                "notify_suggestion": "Consider using tell_agent or broadcast to notify other agents about database completion.",
            }
            
        except Exception as e:
            self._logger.error(f"Database generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_init_sql(self, schema: Dict) -> str:
        """Generate init.sql from schema using j2 template."""
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "database_generate_init",
                schema=schema
            )
        except Exception as e:
            self._logger.warning(f"Could not load j2 template: {e}")
            prompt = f"""Generate PostgreSQL init.sql for:
{json.dumps(schema, indent=2)}

Requirements:
- Start with CREATE EXTENSION IF NOT EXISTS "pgcrypto";
- Use UUIDs with gen_random_uuid()
- Add proper constraints and indexes
- Use TIMESTAMP WITH TIME ZONE

Output raw SQL only.
"""
        
        return await self.think(prompt)
    
    async def _generate_seed_sql(self, schema: Dict) -> str:
        """Generate seed.sql from schema using j2 template."""
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "database_generate_seed",
                schema=schema
            )
        except Exception as e:
            self._logger.warning(f"Could not load j2 template: {e}")
            # Get test credentials from context or use defaults
            test_users = self._get_test_credentials()
            prompt = f"""Generate PostgreSQL seed data for:
{json.dumps(schema, indent=2)}

Include:
- Test users: {test_users}
- Use bcrypt hashes
- 5-10 realistic records per table

Output raw SQL only.
"""
        
        return await self.think(prompt)
    
    def _get_test_credentials(self) -> str:
        """Get test credentials from context or return defaults."""
        if self.context and hasattr(self.context, 'test_users'):
            return self.context.test_users
        # Default test users - can be overridden via context
        return "admin@example.com (admin123), user@example.com (password123)"
    
    def _generate_dockerfile(self) -> str:
        """Generate database Dockerfile."""
        return '''FROM postgres:15-alpine

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
COPY seed.sql /docker-entrypoint-initdb.d/02-seed.sql

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \\
    CMD pg_isready -U postgres
'''
    
    # ==================== Real Data Loading ====================
    
    async def _load_real_data(self, schema: Dict) -> bool:
        """
        Load real data from HuggingFace using DataEngine.
        
        This enhances the generated environment with realistic data
        from public datasets.
        """
        if not self._data_engine:
            self._logger.info("DataEngine not available, using generated seed data")
            return False
        
        # Get project description for domain inference
        description = self._requirements.get("description", "")
        if not description and self.context:
            description = getattr(self.context, "description", "")
        
        if not description:
            self._logger.info("No project description for data discovery")
            return False
        
        try:
            # Infer domain from description
            domain = self._data_engine.discovery.infer_domain(description)
            self._logger.info(f"Inferred data domain: {domain}")
            
            # Prepare output path
            output_dir = self.workspace.base_dir / "app" / "data"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / "products.db")
            
            # Extract entities from schema for better matching
            entities = {}
            for table in schema.get("tables", []):
                table_name = table.get("name", "")
                columns = [col.get("name", "") for col in table.get("columns", [])]
                entities[table_name] = columns
            
            # Discover and load datasets
            self._logger.info(f"Discovering datasets for domain: {domain}")
            result = self._data_engine.run(
                instruction=description,
                output_path=output_path,
                entities=entities,
                db_type="sqlite",
                max_per_category=500,  # Reasonable default
                max_total=5000,
            )
            
            if result.get("success"):
                load_stats = result.get("load", {})
                self._logger.info(
                    f"Loaded {load_stats.get('total_loaded', 0)} records "
                    f"from {result.get('dataset_id', 'unknown dataset')}"
                )
                self._files_created.append("app/data/products.db")
                # LLM can use tell_agent to notify user if needed
                return True
            else:
                self._logger.warning(f"Data loading failed: {result.get('error')}")
                return False
                
        except Exception as e:
            self._logger.warning(f"Real data loading failed: {e}")
            return False
    
    async def load_dataset(
        self,
        dataset_id: str,
        output_path: str,
        domain: str = "e-commerce",
        max_records: int = 1000
    ) -> Dict[str, Any]:
        """
        Manually load a specific dataset.
        
        Can be called by other agents or directly.
        """
        if not self._data_engine:
            return {"success": False, "error": "DataEngine not available"}
        
        try:
            result = self._data_engine.load(
                dataset_id=dataset_id,
                output_path=output_path,
                domain=domain,
                db_type="sqlite",
                max_per_category=max_records // 10,
                max_total=max_records,
            )
            
            return {
                "success": True,
                "records_loaded": result.total_loaded,
                "categories": result.categories_loaded,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== Fix Issues ====================
    
    async def _fix_issues(self, issues: List[Dict]) -> Dict[str, Any]:
        """Fix database-related issues."""
        self._logger.info(f"Fixing {len(issues)} database issues...")
        fixed = 0
        
        for issue in issues:
            try:
                result = await self._fix_single_issue(issue)
                if result:
                    fixed += 1
            except Exception as e:
                self._logger.error(f"Failed to fix issue: {e}")
        
        return {
            "success": True,
            "fixed": fixed,
            "total": len(issues),
        }
    
    async def _fix_single_issue(self, issue: Dict) -> bool:
        """Fix a single database issue using j2 template."""
        init_sql = self.read_file("app/database/init.sql") or ""
        seed_sql = self.read_file("app/database/seed.sql") or ""
        
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "database_fix_issue",
                issue=issue,
                current_files={"init.sql": init_sql, "seed.sql": seed_sql}
            )
        except:
            prompt = f"""Fix this database issue:
Issue: {issue.get('title', '')}
Description: {issue.get('description', '')}

Current init.sql:
{init_sql[:2000]}

Provide fix as JSON: {{"file": "init.sql or seed.sql", "content": "full SQL"}}
"""
        
        response = await self.think(prompt)
        
        try:
            fix = json.loads(self._extract_json(response))
            target_file = fix.get("file", "")
            content = fix.get("content", "")
            
            if target_file and content:
                self.write_file(f"app/database/{target_file}", content)
                return True
            
        except Exception as e:
            self._logger.error(f"Failed to parse fix: {e}")
        
        return False
    
    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response."""
        if "```json" in response:
            return response.split("```json")[1].split("```")[0]
        elif "```" in response:
            return response.split("```")[1].split("```")[0]
        return response
    
    # ==================== Communication Handlers ====================
    
    async def _answer_question(self, message) -> str:
        """Answer questions about the database."""
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "answer_question",
                agent_type="Database",
                question=message.content,
                context={"schema": self._schema, "files": self._files_created}
            )
        except:
            prompt = f"""You are the Database agent. Another agent asks:
{message.content}

Schema: {json.dumps(self._schema, indent=2)[:1000] if self._schema else "Not generated"}
Files: {self._files_created}

Provide a helpful answer about database structure or queries.
"""
        return await self.think(prompt)
