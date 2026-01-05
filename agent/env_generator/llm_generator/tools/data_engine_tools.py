"""
Data Engine Tools - Dataset discovery and loading from HuggingFace

Tools for:
- Discovering relevant datasets based on project requirements
- Previewing dataset structure (columns/fields)
- Loading datasets with custom field mappings
- Generating SQL INSERT statements from datasets
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from utils.tool import BaseTool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


class DiscoverDatasetsTool(BaseTool):
    """
    Discover relevant datasets from HuggingFace based on project requirements.
    """
    
    NAME = "discover_datasets"
    DESCRIPTION = """Discover relevant datasets from HuggingFace based on project requirements.

Use this to find real-world datasets that match your project domain.

Examples:
- discover_datasets(instruction="e-commerce website selling electronics")
- discover_datasets(instruction="travel booking platform with flights and hotels")
- discover_datasets(instruction="social media app with posts and comments")

Returns a list of dataset candidates with dataset_id, score, downloads.
After finding a dataset, use `preview_dataset()` to see its structure before loading.
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
    
    def get_tool_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {
                            "type": "string",
                            "description": "Natural language description of the project/domain"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of candidates to return (default: 5)"
                        }
                    },
                    "required": ["instruction"]
                }
            }
        }
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def execute(self, instruction: str, limit: int = 5) -> ToolResult:
        """Execute dataset discovery."""
        try:
            from data_engine.core.discovery import DatasetDiscovery
            discovery = DatasetDiscovery()
            candidates = discovery.discover(instruction, entities=None, limit=limit)
            
            if not candidates:
                return ToolResult(
                    success=True,
                    data={
                        "candidates": [],
                        "message": "No suitable datasets found. Use manual seed data instead."
                    }
                )
            
            results = []
            for c in candidates:
                results.append({
                    "dataset_id": c.dataset_id,
                    "score": round(c.score, 2),
                    "downloads": c.downloads,
                    "description": c.description[:200] if c.description else ""
                })
            
            return ToolResult(
                success=True,
                data={
                    "candidates": results,
                    "recommended": results[0]["dataset_id"] if results else None,
                    "next_step": "Use preview_dataset(dataset_id) to see columns and sample data"
                }
            )
            
        except ImportError:
            return ToolResult(
                success=False,
                error_message="DataEngine not available. Install: pip install datasets huggingface_hub"
            )
        except Exception as e:
            logger.exception(f"Dataset discovery failed: {e}")
            return ToolResult(success=False, error_message=f"Discovery failed: {str(e)}")


class PreviewDatasetTool(BaseTool):
    """
    Preview a HuggingFace dataset's structure and sample data.
    
    Use this after discover_datasets() to see what columns are available
    so you can create proper field mappings for your schema.
    """
    
    NAME = "preview_dataset"
    DESCRIPTION = """Preview a HuggingFace dataset's columns and sample data.

Use this BEFORE loading to understand the dataset structure and plan your field mappings.

Example:
```python
preview_dataset(dataset_id="milistu/AMAZON-Products-2023", sample_size=3)
```

Returns:
- columns: List of available columns with types
- sample_data: Sample rows to understand data format
- total_rows: Approximate dataset size

After preview, use `generate_seed_sql()` with your custom field_mapping.
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
    
    def get_tool_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "HuggingFace dataset ID (e.g., 'milistu/AMAZON-Products-2023')"
                        },
                        "subset": {
                            "type": "string",
                            "description": "Dataset subset/config name (optional, some datasets have multiple)"
                        },
                        "split": {
                            "type": "string",
                            "description": "Dataset split to preview (default: 'train')"
                        },
                        "sample_size": {
                            "type": "integer",
                            "description": "Number of sample rows to return (default: 5)"
                        }
                    },
                    "required": ["dataset_id"]
                }
            }
        }
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def execute(
        self,
        dataset_id: str,
        subset: str = None,
        split: str = "train",
        sample_size: int = 5
    ) -> ToolResult:
        """Preview dataset structure."""
        try:
            from datasets import load_dataset
            
            # Load a small sample
            logger.info(f"Loading preview for {dataset_id}")
            
            load_args = {"path": dataset_id, "split": f"{split}[:100]", "streaming": False}
            if subset:
                load_args["name"] = subset
            
            try:
                ds = load_dataset(**load_args)
            except Exception as e:
                # Try without split specification
                load_args = {"path": dataset_id, "streaming": True}
                if subset:
                    load_args["name"] = subset
                ds = load_dataset(**load_args)
                ds = list(ds[split].take(100))
            
            # Get columns info
            if hasattr(ds, 'features'):
                columns = {col: str(dtype) for col, dtype in ds.features.items()}
            elif hasattr(ds, 'column_names'):
                columns = {col: "unknown" for col in ds.column_names}
            elif isinstance(ds, list) and ds:
                columns = {k: type(v).__name__ for k, v in ds[0].items()}
            else:
                columns = {}
            
            # Get sample data
            if hasattr(ds, 'select'):
                sample = ds.select(range(min(sample_size, len(ds)))).to_dict()
                # Convert to list of dicts
                sample_rows = []
                keys = list(sample.keys())
                for i in range(len(sample[keys[0]])):
                    row = {k: sample[k][i] for k in keys}
                    # Truncate long values for display
                    for k, v in row.items():
                        if isinstance(v, str) and len(v) > 200:
                            row[k] = v[:200] + "..."
                        elif isinstance(v, list) and len(v) > 5:
                            row[k] = v[:5] + ["..."]
                    sample_rows.append(row)
            elif isinstance(ds, list):
                sample_rows = ds[:sample_size]
            else:
                sample_rows = []
            
            total_rows = len(ds) if hasattr(ds, '__len__') else "unknown (streaming)"
            
            return ToolResult(
                success=True,
                data={
                    "dataset_id": dataset_id,
                    "columns": columns,
                    "sample_data": sample_rows,
                    "total_rows": total_rows,
                    "next_step": "Use generate_seed_sql() with field_mapping to create INSERT statements"
                }
            )
            
        except ImportError:
            return ToolResult(
                success=False,
                error_message="datasets library not available. Install: pip install datasets"
            )
        except Exception as e:
            logger.exception(f"Dataset preview failed: {e}")
            return ToolResult(success=False, error_message=f"Preview failed: {str(e)}")


class GenerateSeedSQLTool(BaseTool):
    """
    Generate SQL INSERT statements from a HuggingFace dataset with custom field mapping.
    
    The agent defines the mapping from dataset columns to database columns.
    """
    
    NAME = "generate_seed_sql"
    DESCRIPTION = """Generate SQL INSERT statements from a HuggingFace dataset with YOUR custom field mapping.

YOU define how dataset columns map to your database schema. This gives you full control.

Example:
```python
generate_seed_sql(
    dataset_id="milistu/AMAZON-Products-2023",
    table_name="products",
    field_mapping={
        "title": "name",           # dataset.title -> products.name
        "price": "price_cents",    # will auto-convert to cents
        "average_rating": "rating",
        "image": "image_url",
        "description": "description"
    },
    transforms={
        "price_cents": "multiply:100",  # Convert dollars to cents
        "name": "truncate:200"          # Limit length
    },
    filters={
        "price": {"min": 0.01, "max": 1000},  # Only products in price range
        "title": {"min_length": 5}             # Skip items without title
    },
    output_file="app/database/init/02_seed.sql",
    limit=500
)
```

This generates SQL like:
```sql
INSERT INTO products (name, price_cents, rating, image_url, description) VALUES
('Product Name', 1999, 4.5, 'http://...', 'Description...');
```
"""
    
    def __init__(self, workspace=None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
        self.workspace = workspace
    
    def get_tool_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "HuggingFace dataset ID"
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Target database table name"
                        },
                        "field_mapping": {
                            "type": "object",
                            "description": "Mapping from dataset columns to table columns: {dataset_col: table_col}",
                            "additionalProperties": {"type": "string"}
                        },
                        "transforms": {
                            "type": "object",
                            "description": "Optional transforms: {table_col: 'transform_type:arg'}. Types: multiply, truncate, lowercase, uppercase, default",
                            "additionalProperties": {"type": "string"}
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional filters: {dataset_col: {condition: value}}. Conditions: min, max, min_length, not_empty",
                            "additionalProperties": {"type": "object"}
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Output SQL file path (e.g., 'app/database/init/02_seed.sql')"
                        },
                        "subset": {
                            "type": "string",
                            "description": "Dataset subset/config name (optional)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of records to generate (default: 100)"
                        },
                        "append": {
                            "type": "boolean",
                            "description": "Append to existing file instead of overwrite (default: false)"
                        }
                    },
                    "required": ["dataset_id", "table_name", "field_mapping", "output_file"]
                }
            }
        }
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def execute(
        self,
        dataset_id: str,
        table_name: str,
        field_mapping: Dict[str, str],
        output_file: str,
        transforms: Dict[str, str] = None,
        filters: Dict[str, Dict] = None,
        subset: str = None,
        limit: int = 100,
        append: bool = False
    ) -> ToolResult:
        """Generate SQL INSERT statements."""
        try:
            from datasets import load_dataset
            
            # Resolve output path
            if self.workspace and not Path(output_file).is_absolute():
                output_file = str(self.workspace.root / output_file)
            
            # Ensure parent directory exists
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Generating seed SQL from {dataset_id} for table {table_name}")
            
            # Load dataset
            load_args = {"path": dataset_id, "split": f"train[:{limit * 2}]"}
            if subset:
                load_args["name"] = subset
            
            try:
                ds = load_dataset(**load_args)
            except:
                # Fallback to streaming
                load_args = {"path": dataset_id, "streaming": True}
                if subset:
                    load_args["name"] = subset
                ds = load_dataset(**load_args)
                ds = list(ds["train"].take(limit * 2))
            
            transforms = transforms or {}
            filters = filters or {}
            
            # Process records
            sql_statements = []
            table_columns = list(set(field_mapping.values()))
            
            processed = 0
            skipped = 0
            
            iterator = ds if isinstance(ds, list) else ds
            for row in iterator:
                if isinstance(row, dict):
                    record = row
                else:
                    record = dict(row)
                
                # Apply filters
                skip = False
                for col, conditions in filters.items():
                    val = record.get(col)
                    if val is None:
                        skip = True
                        break
                    for cond, threshold in conditions.items():
                        if cond == "min" and (not isinstance(val, (int, float)) or val < threshold):
                            skip = True
                        elif cond == "max" and (not isinstance(val, (int, float)) or val > threshold):
                            skip = True
                        elif cond == "min_length" and (not isinstance(val, str) or len(val) < threshold):
                            skip = True
                        elif cond == "not_empty" and not val:
                            skip = True
                        if skip:
                            break
                    if skip:
                        break
                
                if skip:
                    skipped += 1
                    continue
                
                # Map and transform values
                values = {}
                for src_col, tgt_col in field_mapping.items():
                    val = record.get(src_col)
                    
                    # Apply transform
                    if tgt_col in transforms:
                        transform = transforms[tgt_col]
                        if transform.startswith("multiply:"):
                            factor = float(transform.split(":")[1])
                            val = int(float(val or 0) * factor) if val else 0
                        elif transform.startswith("truncate:"):
                            max_len = int(transform.split(":")[1])
                            val = str(val)[:max_len] if val else ""
                        elif transform == "lowercase":
                            val = str(val).lower() if val else ""
                        elif transform == "uppercase":
                            val = str(val).upper() if val else ""
                        elif transform.startswith("default:"):
                            default_val = transform.split(":", 1)[1]
                            val = val if val else default_val
                    
                    values[tgt_col] = val
                
                # Generate SQL value
                sql_values = []
                for col in table_columns:
                    val = values.get(col)
                    if val is None:
                        sql_values.append("NULL")
                    elif isinstance(val, (int, float)):
                        sql_values.append(str(val))
                    elif isinstance(val, bool):
                        sql_values.append("TRUE" if val else "FALSE")
                    elif isinstance(val, (list, dict)):
                        import json
                        escaped = json.dumps(val).replace("'", "''")
                        sql_values.append(f"'{escaped}'")
                    else:
                        escaped = str(val).replace("'", "''")
                        sql_values.append(f"'{escaped}'")
                
                sql_statements.append(f"({', '.join(sql_values)})")
                processed += 1
                
                if processed >= limit:
                    break
            
            if not sql_statements:
                return ToolResult(
                    success=False,
                    error_message=f"No records passed filters. Skipped {skipped} records."
                )
            
            # Generate SQL
            columns_str = ", ".join(table_columns)
            sql = f"-- Auto-generated seed data from HuggingFace: {dataset_id}\n"
            sql += f"-- Records: {len(sql_statements)}\n\n"
            sql += f"INSERT INTO {table_name} ({columns_str}) VALUES\n"
            sql += ",\n".join(sql_statements)
            sql += ";\n"
            
            # Write to file
            mode = "a" if append else "w"
            with open(output_file, mode) as f:
                if append:
                    f.write("\n\n")
                f.write(sql)
            
            return ToolResult(
                success=True,
                data={
                    "output_file": output_file,
                    "table_name": table_name,
                    "records_generated": len(sql_statements),
                    "records_skipped": skipped,
                    "columns": table_columns,
                    "message": f"Generated {len(sql_statements)} INSERT statements in {output_file}"
                }
            )
            
        except ImportError:
            return ToolResult(
                success=False,
                error_message="datasets library not available. Install: pip install datasets"
            )
        except Exception as e:
            logger.exception(f"SQL generation failed: {e}")
            return ToolResult(success=False, error_message=f"Generation failed: {str(e)}")


def create_data_engine_tools(workspace=None) -> List[BaseTool]:
    """Create all data engine tools."""
    return [
        DiscoverDatasetsTool(),
        PreviewDatasetTool(),
        GenerateSeedSQLTool(workspace=workspace),
    ]


__all__ = [
    "DiscoverDatasetsTool",
    "PreviewDatasetTool",
    "GenerateSeedSQLTool",
    "create_data_engine_tools",
]

