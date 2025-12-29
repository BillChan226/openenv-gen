"""
Data Engine Tools

LLM-powered tools for discovering and loading HuggingFace datasets into databases.
Uses LLM for intelligent domain inference, search query generation, and dataset evaluation.
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# Setup paths
_TOOLS_DIR = Path(__file__).parent.resolve()
_LLM_GEN_DIR = _TOOLS_DIR.parent
_AGENTS_DIR = _LLM_GEN_DIR.parent.parent
_ENV_GEN_DIR = _AGENTS_DIR.parent.parent  # /scratch/czr/env-gen

for _path in [str(_LLM_GEN_DIR), str(_AGENTS_DIR), str(_ENV_GEN_DIR)]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from utils.tool import BaseTool, ToolResult, ToolCategory, create_tool_param
from workspace import Workspace

# Import data_engine library
from data_engine import DataEngine
from data_engine.core.discovery import DatasetDiscovery, DatasetCandidate
from data_engine.core.loader import LoadResult

DATA_ENGINE_AVAILABLE = True


class DiscoverDatasetTool(BaseTool):
    """
    LLM-powered dataset discovery.

    Uses LLM to intelligently:
    - Infer domain from instruction
    - Generate optimized search queries
    - Evaluate dataset quality and relevance
    """

    NAME = "discover_dataset"

    DESCRIPTION = """Discover HuggingFace datasets matching project requirements.

This tool uses an LLM to:
1. Infer the domain from your instruction (e-commerce, social-media, news, etc.)
2. Generate optimized HuggingFace search queries
3. Evaluate each candidate for quality and relevance
4. Provide detailed analysis and recommendations

Parameters:
- instruction: Natural language description of the project
- entities: Optional entity definitions from spec.project.json
- limit: Maximum candidates to return (default: 5)

Example:
  instruction: "Build a marketplace for handmade crafts like Etsy"
  -> LLM infers "e-commerce" domain, generates queries like "handmade products",
     "craft marketplace", evaluates datasets for craft/artisan product coverage
"""

    def __init__(self, workspace: Workspace = None, llm_client=None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace or Workspace(Path.cwd())
        self.llm_client = llm_client
        self._llm_engine = None
        self._rule_engine = DataEngine()  # For fallback and loading

    def _get_llm_engine(self):
        """Lazy load LLM engine."""
        if self._llm_engine is None and self.llm_client is not None:
            from tools.llm_data_engine import LLMDataEngine
            self._llm_engine = LLMDataEngine(self.llm_client)
        return self._llm_engine

    @property
    def tool_definition(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "Natural language description of the project"
                    },
                    "entities": {
                        "type": "object",
                        "description": "Entity definitions from spec.project.json (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum candidates to return (default: 5)"
                    }
                },
                "required": ["instruction"]
            }
        )

    async def execute_async(
        self,
        instruction: str,
        entities: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> ToolResult:
        """Async execution with LLM."""
        llm_engine = self._get_llm_engine()

        if llm_engine is None:
            # Fallback to rule-based
            return self._execute_rule_based(instruction, entities, limit)

        try:
            # Step 1: LLM domain inference
            domain_result = await llm_engine.infer_domain(instruction, entities)

            # Step 2: Use LLM-generated queries to search
            from huggingface_hub import HfApi
            api = HfApi()

            candidates = []
            seen_ids = set()

            # Search with LLM-generated queries
            for query in domain_result.search_queries[:5]:
                try:
                    results = api.list_datasets(search=query, sort="downloads", direction=-1, limit=10)
                    for info in results:
                        if info.id not in seen_ids:
                            seen_ids.add(info.id)
                            candidates.append({
                                "dataset_id": info.id,
                                "description": getattr(info, 'description', '') or "",
                                "downloads": getattr(info, 'downloads', 0) or 0,
                                "likes": getattr(info, 'likes', 0) or 0,
                            })
                except Exception:
                    continue

            # Step 3: LLM evaluation of top candidates
            evaluated = []
            for candidate in candidates[:limit * 2]:  # Evaluate more than needed
                try:
                    # Get dataset schema for evaluation
                    schema = self._rule_engine.discovery.get_dataset_schema(candidate["dataset_id"])
                    if not schema:
                        continue

                    sample = {k: v.get("sample") for k, v in schema.items()}

                    eval_result = await llm_engine.evaluate_dataset(
                        requirement=instruction,
                        dataset_id=candidate["dataset_id"],
                        description=candidate["description"],
                        fields=list(schema.keys()),
                        sample=sample,
                        downloads=candidate["downloads"]
                    )

                    evaluated.append({
                        **candidate,
                        "score": eval_result.score,
                        "recommendation": eval_result.recommendation,
                        "strengths": eval_result.strengths,
                        "weaknesses": eval_result.weaknesses,
                        "reasoning": eval_result.reasoning
                    })
                except Exception:
                    continue

            # Sort by score and take top
            evaluated.sort(key=lambda x: x["score"], reverse=True)
            top_candidates = evaluated[:limit]

            # Format summary
            lines = [
                f"LLM-powered dataset discovery completed!\n",
                f"Domain: {domain_result.domain} (confidence: {domain_result.confidence:.0%})",
                f"Keywords: {', '.join(domain_result.keywords[:5])}",
                f"Reasoning: {domain_result.reasoning}\n",
                f"Found {len(top_candidates)} evaluated candidates:\n"
            ]

            for i, c in enumerate(top_candidates):
                lines.append(f"{i+1}. {c['dataset_id']} (score: {c['score']}, {c['downloads']:,} downloads)")
                lines.append(f"   Recommendation: {c['recommendation']}")
                if c.get('strengths'):
                    lines.append(f"   Strengths: {', '.join(c['strengths'][:2])}")
                lines.append("")

            return ToolResult(
                success=True,
                data={
                    "candidates": top_candidates,
                    "summary": "\n".join(lines),
                    "domain_inference": {
                        "domain": domain_result.domain,
                        "confidence": domain_result.confidence,
                        "keywords": domain_result.keywords,
                        "entities": domain_result.entities,
                        "search_queries": domain_result.search_queries,
                        "reasoning": domain_result.reasoning
                    },
                    "top_recommendation": top_candidates[0] if top_candidates else None
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"LLM dataset discovery failed: {str(e)}"
            )

    def _execute_rule_based(
        self,
        instruction: str,
        entities: Optional[Dict[str, Any]],
        limit: int
    ) -> ToolResult:
        """Fallback to rule-based discovery."""
        candidates = self._rule_engine.discover(instruction, entities, limit)

        if not candidates:
            return ToolResult(
                success=True,
                data={"candidates": [], "message": "No datasets found"}
            )

        results = []
        for i, c in enumerate(candidates):
            results.append({
                "rank": i + 1,
                "dataset_id": c.dataset_id,
                "description": c.description[:200] if c.description else "",
                "downloads": c.downloads,
                "score": round(c.score, 1),
                "url": c.url,
            })

        lines = [f"Found {len(results)} candidate datasets:\n"]
        for r in results:
            lines.append(f"{r['rank']}. {r['dataset_id']} (score: {r['score']}, {r['downloads']:,} downloads)")

        return ToolResult(
            success=True,
            data={
                "candidates": results,
                "summary": "\n".join(lines),
                "domain": self._rule_engine.discovery.infer_domain(instruction),
                "top_recommendation": results[0] if results else None
            }
        )

    def execute(
        self,
        instruction: str,
        entities: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> ToolResult:
        """Sync execution - uses rule-based fallback."""
        return self._execute_rule_based(instruction, entities, limit)


class LoadDatasetTool(BaseTool):
    """
    Load a HuggingFace dataset into the database.
    """

    NAME = "load_dataset"

    DESCRIPTION = """Load a HuggingFace dataset into the project database.

Use this tool after discover_dataset to:
- Download dataset from HuggingFace Hub
- Transform data to match database schema
- Populate SQLite or PostgreSQL database

Parameters:
- dataset_id: HuggingFace dataset ID (e.g., "milistu/AMAZON-Products-2023")
- output_path: Path to output database file (relative to workspace)
- domain: Domain type (e-commerce, social-media, news, etc.)
- db_type: Database type ("sqlite" or "postgres")
- max_per_category: Maximum records per category (default: 1000)
- max_total: Maximum total records (optional)

Example:
  dataset_id: "milistu/AMAZON-Products-2023"
  output_path: "app/database/data/products.db"
  domain: "e-commerce"
  -> Loads Amazon products into SQLite database
"""

    def __init__(self, workspace: Workspace = None, llm_client=None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace or Workspace(Path.cwd())
        self.llm_client = llm_client
        self.engine = DataEngine()

    @property
    def tool_definition(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "HuggingFace dataset ID"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to output database file"
                    },
                    "domain": {
                        "type": "string",
                        "enum": ["e-commerce", "social-media", "news", "real-estate", "restaurant", "travel"],
                        "description": "Domain type for schema and field mappings (default: e-commerce)"
                    },
                    "db_type": {
                        "type": "string",
                        "enum": ["sqlite", "postgres"],
                        "description": "Database type (default: sqlite)"
                    },
                    "max_per_category": {
                        "type": "integer",
                        "description": "Maximum records per category (default: 1000)"
                    },
                    "max_total": {
                        "type": "integer",
                        "description": "Maximum total records (optional)"
                    }
                },
                "required": ["dataset_id", "output_path"]
            }
        )

    def execute(
        self,
        dataset_id: str,
        output_path: str,
        domain: str = "e-commerce",
        db_type: str = "sqlite",
        max_per_category: int = 1000,
        max_total: Optional[int] = None
    ) -> ToolResult:

        try:
            # Resolve output path
            full_output_path = self.workspace.resolve(output_path)

            # Ensure parent directory exists
            full_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Load dataset
            result = self.engine.load(
                dataset_id=dataset_id,
                output_path=str(full_output_path),
                domain=domain,
                db_type=db_type,
                max_per_category=max_per_category,
                max_total=max_total
            )

            return ToolResult(
                success=True,
                data={
                    "dataset_id": dataset_id,
                    "output_path": str(full_output_path),
                    "total_processed": result.total_processed,
                    "total_loaded": result.total_loaded,
                    "categories_loaded": result.categories_loaded,
                    "errors_count": len(result.errors),
                    "errors": result.errors[:10] if result.errors else [],
                    "summary": f"Loaded {result.total_loaded:,} records from {dataset_id} into {output_path}"
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Dataset loading failed: {str(e)}"
            )


class DataEnginePipelineTool(BaseTool):
    """
    Run the complete data engine pipeline: discover + load.
    """

    NAME = "data_engine_pipeline"

    DESCRIPTION = """Run complete data engine pipeline: discover and load dataset.

Use this tool to automatically:
1. Infer domain from project description (using LLM if available)
2. Search HuggingFace for matching datasets
3. Select the best candidate
4. Download and load into database

This is the recommended tool for automatic database population.

Parameters:
- instruction: Natural language description of the project
- output_path: Path to output database file
- db_type: Database type ("sqlite" or "postgres")
- max_per_category: Maximum records per category
- max_total: Maximum total records
- dataset_id: Optional specific dataset to use (skips discovery)

Example:
  instruction: "e-commerce website like eBay with electronics and fashion"
  output_path: "app/database/data/products.db"
  -> Discovers best dataset, downloads and loads it
"""

    def __init__(self, workspace: Workspace = None, llm_client=None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace or Workspace(Path.cwd())
        self.llm_client = llm_client
        self.engine = DataEngine()

    @property
    def tool_definition(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "Natural language description of the project"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to output database file"
                    },
                    "entities": {
                        "type": "object",
                        "description": "Entity definitions from spec.project.json (optional)"
                    },
                    "db_type": {
                        "type": "string",
                        "enum": ["sqlite", "postgres"],
                        "description": "Database type (default: sqlite)"
                    },
                    "max_per_category": {
                        "type": "integer",
                        "description": "Maximum records per category (default: 1000)"
                    },
                    "max_total": {
                        "type": "integer",
                        "description": "Maximum total records (optional)"
                    },
                    "dataset_id": {
                        "type": "string",
                        "description": "Specific dataset to use (skips discovery)"
                    }
                },
                "required": ["instruction", "output_path"]
            }
        )

    def execute(
        self,
        instruction: str,
        output_path: str,
        entities: Optional[Dict[str, Any]] = None,
        db_type: str = "sqlite",
        max_per_category: int = 1000,
        max_total: Optional[int] = None,
        dataset_id: Optional[str] = None
    ) -> ToolResult:

        try:
            # Resolve output path
            full_output_path = self.workspace.resolve(output_path)
            full_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Run full pipeline
            result = self.engine.run(
                instruction=instruction,
                output_path=str(full_output_path),
                entities=entities,
                db_type=db_type,
                max_per_category=max_per_category,
                max_total=max_total,
                dataset_id=dataset_id
            )

            if result["success"]:
                summary_lines = [
                    f"Data engine pipeline completed successfully!",
                    f"",
                    f"Domain: {result.get('domain', 'unknown')}",
                    f"Dataset: {result.get('dataset_id', 'unknown')}",
                    f"Output: {output_path}",
                    f"",
                    f"Load Results:",
                    f"  - Processed: {result['load']['total_processed']:,} records",
                    f"  - Loaded: {result['load']['total_loaded']:,} records",
                    f"  - Categories: {result['load']['categories']}",
                ]
            else:
                summary_lines = [
                    f"Data engine pipeline failed",
                    f"Error: {result.get('error', 'Unknown error')}"
                ]

            return ToolResult(
                success=result["success"],
                data={**result, "summary": "\n".join(summary_lines)},
                error_message=None if result["success"] else result.get("error")
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Data engine pipeline failed: {str(e)}"
            )


class GetDatasetSchemaTool(BaseTool):
    """
    Get the schema of a HuggingFace dataset.
    """

    NAME = "get_dataset_schema"

    DESCRIPTION = """Get the schema (columns and types) of a HuggingFace dataset.

Use this tool to:
- Inspect a dataset before loading
- Understand what fields are available
- Plan field mappings to database columns

Parameters:
- dataset_id: HuggingFace dataset ID

Returns column names, types, and sample values.
"""

    def __init__(self, workspace: Workspace = None, llm_client=None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace or Workspace(Path.cwd())
        self.llm_client = llm_client
        self.discovery = DatasetDiscovery()

    @property
    def tool_definition(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "HuggingFace dataset ID"
                    }
                },
                "required": ["dataset_id"]
            }
        )

    def execute(self, dataset_id: str) -> ToolResult:

        try:
            schema = self.discovery.get_dataset_schema(dataset_id)

            if not schema:
                return ToolResult(
                    success=False,
                    error_message=f"Could not retrieve schema for dataset: {dataset_id}"
                )

            # Format schema for display
            lines = [f"Schema for {dataset_id}:\n"]
            for field, info in schema.items():
                sample = info.get('sample', 'N/A')
                if sample and len(str(sample)) > 50:
                    sample = str(sample)[:50] + "..."
                lines.append(f"  {field}: {info['type']}")
                lines.append(f"    Sample: {sample}")

            return ToolResult(
                success=True,
                data={
                    "dataset_id": dataset_id,
                    "schema": schema,
                    "columns": list(schema.keys()),
                    "summary": "\n".join(lines)
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Failed to get schema: {str(e)}"
            )


class FieldMappingTool(BaseTool):
    """
    LLM-powered field mapping between dataset and database schema.
    """

    NAME = "generate_field_mapping"

    DESCRIPTION = """Generate field mappings using LLM analysis.

Use this tool to:
- Map HuggingFace dataset fields to database columns
- Get intelligent transform recommendations
- Handle complex nested structures

Parameters:
- dataset_id: HuggingFace dataset ID
- target_schema: Database schema (column: type pairs)

Returns detailed mappings with transforms.
"""

    def __init__(self, workspace: Workspace = None, llm_client=None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace or Workspace(Path.cwd())
        self.llm_client = llm_client
        self._llm_engine = None

    def _get_llm_engine(self):
        """Lazy load LLM engine."""
        if self._llm_engine is None and self.llm_client is not None:
            from tools.llm_data_engine import LLMDataEngine
            self._llm_engine = LLMDataEngine(self.llm_client)
        return self._llm_engine

    @property
    def tool_definition(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "HuggingFace dataset ID"
                    },
                    "target_schema": {
                        "type": "object",
                        "description": "Target database schema {column: type}"
                    }
                },
                "required": ["dataset_id", "target_schema"]
            }
        )

    async def execute_async(
        self,
        dataset_id: str,
        target_schema: Dict[str, str]
    ) -> ToolResult:
        """Async execution with LLM."""
        llm_engine = self._get_llm_engine()

        if llm_engine is None:
            return ToolResult(
                success=False,
                error_message="LLM client not available for field mapping"
            )

        try:
            # Get dataset schema
            discovery = DatasetDiscovery()
            dataset_schema = discovery.get_dataset_schema(dataset_id)

            if not dataset_schema:
                return ToolResult(
                    success=False,
                    error_message=f"Could not retrieve schema for {dataset_id}"
                )

            # Generate mappings with LLM
            result = await llm_engine.generate_field_mapping(target_schema, dataset_schema)

            # Format summary
            lines = [f"Field mapping for {dataset_id}:\n"]
            lines.append(f"Confidence: {result.confidence:.0%}")
            lines.append(f"Notes: {result.notes}\n")
            lines.append("Mappings:")
            for m in result.mappings:
                transform = m.get("transform") or "none"
                lines.append(f"  {m['source']} -> {m['target']} (transform: {transform})")

            if result.unmapped_target:
                lines.append(f"\nUnmapped target columns: {', '.join(result.unmapped_target)}")
            if result.unmapped_source:
                lines.append(f"Unmapped source fields: {', '.join(result.unmapped_source)}")

            return ToolResult(
                success=True,
                data={
                    "mappings": result.mappings,
                    "unmapped_target": result.unmapped_target,
                    "unmapped_source": result.unmapped_source,
                    "confidence": result.confidence,
                    "notes": result.notes,
                    "summary": "\n".join(lines)
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"Field mapping failed: {str(e)}"
            )

    def execute(
        self,
        dataset_id: str,
        target_schema: Dict[str, str]
    ) -> ToolResult:
        """Sync execution - requires LLM."""
        return ToolResult(
            success=False,
            error_message="Field mapping requires async execution with LLM"
        )


def create_data_engine_tools(workspace: Workspace = None, llm_client=None) -> List[BaseTool]:
    """Create all data engine tools.

    Args:
        workspace: Workspace instance
        llm_client: Optional LLM client for LLM-powered features

    Returns:
        List of data engine tools
    """
    return [
        DiscoverDatasetTool(workspace=workspace, llm_client=llm_client),
        LoadDatasetTool(workspace=workspace, llm_client=llm_client),
        DataEnginePipelineTool(workspace=workspace, llm_client=llm_client),
        GetDatasetSchemaTool(workspace=workspace, llm_client=llm_client),
        FieldMappingTool(workspace=workspace, llm_client=llm_client),
    ]


__all__ = [
    "DiscoverDatasetTool",
    "LoadDatasetTool",
    "DataEnginePipelineTool",
    "GetDatasetSchemaTool",
    "FieldMappingTool",
    "create_data_engine_tools",
    "DATA_ENGINE_AVAILABLE",
]
