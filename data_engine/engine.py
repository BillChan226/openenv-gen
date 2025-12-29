"""
Main Data Engine class - orchestrates discovery, validation, and loading.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml

from data_engine.core.discovery import DatasetDiscovery, DataRequirements, DatasetCandidate
from data_engine.core.validator import SchemaValidator, FieldMapping
from data_engine.core.loader import DatasetLoader, LoadConfig, DataFilter, LoadResult
from data_engine.core.adapters import SQLiteAdapter, PostgreSQLAdapter, DatabaseAdapter

logger = logging.getLogger(__name__)


class DataEngine:
    """
    Main data engine orchestrator.

    Handles end-to-end workflow:
    1. Discover datasets based on requirements
    2. Validate schema compatibility
    3. Load data into database
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize data engine.

        Args:
            config_path: Path to domain configuration YAML
        """
        self.discovery = DatasetDiscovery()
        self.validator = SchemaValidator()
        self.loader = DatasetLoader()

        # Load domain config
        if config_path is None:
            config_path = Path(__file__).parent / "configs" / "domains.yaml"

        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load domain configuration."""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")
            return {}

    def discover(
        self,
        instruction: str,
        entities: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[DatasetCandidate]:
        """
        Discover datasets matching requirements.

        Args:
            instruction: Natural language description
            entities: Entity definitions from spec
            limit: Max candidates to return

        Returns:
            List of DatasetCandidate objects
        """
        return self.discovery.discover(instruction, entities, limit)

    def load(
        self,
        dataset_id: str,
        output_path: str,
        domain: str = "e-commerce",
        db_type: str = "sqlite",
        max_per_category: int = 1000,
        max_total: Optional[int] = None,
        category_mapping: Optional[Dict[str, Dict[str, str]]] = None
    ) -> LoadResult:
        """
        Load a dataset into database.

        Args:
            dataset_id: HuggingFace dataset ID
            output_path: Output database path
            domain: Domain type for default config
            db_type: Database type ("sqlite" or "postgres")
            max_per_category: Max records per category
            max_total: Max total records
            category_mapping: Category slug mapping

        Returns:
            LoadResult with statistics
        """
        # Get domain config
        domain_config = self.config.get(domain, {})

        # Use provided category mapping or get from config
        if category_mapping is None:
            category_mapping = domain_config.get("category_mapping", {})

        # Create load config
        load_config = self._create_load_config(
            dataset_id=dataset_id,
            domain=domain,
            domain_config=domain_config,
            category_mapping=category_mapping,
            max_per_category=max_per_category,
            max_total=max_total
        )

        # Create database adapter
        if db_type == "sqlite":
            adapter = SQLiteAdapter(output_path, schema_type=domain)
        elif db_type == "postgres":
            adapter = PostgreSQLAdapter(connection_string=output_path, schema_type=domain)
        else:
            raise ValueError(f"Unknown db_type: {db_type}")

        # Load data
        with adapter:
            # Insert categories first
            if category_mapping:
                adapter.insert_categories(category_mapping)

            # Load products
            result = self.loader.load(load_config, adapter)

            # Get final stats
            stats = adapter.get_stats()
            logger.info(f"Database stats: {stats}")

        return result

    def _create_load_config(
        self,
        dataset_id: str,
        domain: str,
        domain_config: Dict[str, Any],
        category_mapping: Dict[str, Dict[str, str]],
        max_per_category: int,
        max_total: Optional[int]
    ) -> LoadConfig:
        """Create LoadConfig from domain configuration."""

        # Build field mappings
        mappings = []
        field_mapping_config = domain_config.get("field_mappings", {})

        if domain == "e-commerce":
            # Default e-commerce mappings for Amazon-style datasets
            default_mappings = [
                ("parent_asin", "id"),
                ("parent_asin", "sku"),
                ("title", "name"),
                ("price", "price"),
                ("average_rating", "rating"),
                ("rating_number", "review_count"),
                ("image", "image"),
                ("description", "description"),
                ("description", "short_description"),
                ("features", "features"),
                ("details", "details"),
                ("categories", "sub_category"),
            ]

            for source, target in default_mappings:
                transform = None
                if target == "id":
                    transform = "prefix:amz-"
                elif target == "price":
                    transform = "float"
                elif target == "rating":
                    transform = "float:1"
                elif target == "review_count":
                    transform = "int"
                elif target == "name":
                    transform = "truncate:200"
                elif target == "description":
                    transform = "truncate:2000"
                elif target == "short_description":
                    transform = "truncate:300"
                elif target in ["features", "details"]:
                    transform = "json"

                mappings.append(FieldMapping(
                    source_field=source,
                    target_column=target,
                    transform=transform
                ))

        # Build filters
        filters = []
        filter_config = domain_config.get("filters", {})

        if domain == "e-commerce":
            filters = [
                DataFilter("price", "min", 0.01),
                DataFilter("price", "max", 50000),
                DataFilter("average_rating", "min", 0),
                DataFilter("image", "not_empty", True),
                DataFilter("title", "min_length", 5),
            ]

        # Override with config
        for field, conditions in filter_config.items():
            for cond, value in conditions.items():
                filters.append(DataFilter(field, cond, value))

        return LoadConfig(
            dataset_id=dataset_id,
            mappings=mappings,
            filters=filters,
            category_field="filename" if domain == "e-commerce" else None,
            category_mapping=category_mapping,
            max_per_category=max_per_category,
            max_total=max_total
        )

    def run(
        self,
        instruction: str,
        output_path: str,
        entities: Optional[Dict[str, Any]] = None,
        db_type: str = "sqlite",
        max_per_category: int = 1000,
        max_total: Optional[int] = None,
        dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full end-to-end pipeline: discover and load.

        Args:
            instruction: Natural language description
            output_path: Output database path
            entities: Entity definitions
            db_type: Database type
            max_per_category: Max records per category
            max_total: Max total records
            dataset_id: Optional specific dataset to use (skips discovery)

        Returns:
            Dict with discovery and load results
        """
        result = {
            "instruction": instruction,
            "output_path": output_path,
            "discovery": None,
            "load": None,
            "success": False,
            "error": None
        }

        try:
            # Infer domain
            domain = self.discovery.infer_domain(instruction)
            result["domain"] = domain

            # Discover dataset if not provided
            if dataset_id is None:
                candidates = self.discover(instruction, entities, limit=5)
                if not candidates:
                    result["error"] = "No suitable datasets found"
                    return result

                result["discovery"] = {
                    "candidates": [
                        {"id": c.dataset_id, "score": c.score, "downloads": c.downloads}
                        for c in candidates[:3]
                    ]
                }

                # Use top candidate
                dataset_id = candidates[0].dataset_id

            result["dataset_id"] = dataset_id

            # Load dataset
            load_result = self.load(
                dataset_id=dataset_id,
                output_path=output_path,
                domain=domain,
                db_type=db_type,
                max_per_category=max_per_category,
                max_total=max_total
            )

            result["load"] = {
                "total_processed": load_result.total_processed,
                "total_loaded": load_result.total_loaded,
                "categories": load_result.categories_loaded,
                "errors": len(load_result.errors)
            }

            result["success"] = load_result.total_loaded > 0

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            result["error"] = str(e)

        return result


def create_adapter(
    db_type: str,
    output_path: str,
    schema_type: str = "e-commerce"
) -> DatabaseAdapter:
    """
    Factory function to create database adapter.

    Args:
        db_type: "sqlite" or "postgres"
        output_path: Database path or connection string
        schema_type: Schema type to create

    Returns:
        DatabaseAdapter instance
    """
    if db_type == "sqlite":
        return SQLiteAdapter(output_path, schema_type=schema_type)
    elif db_type == "postgres":
        return PostgreSQLAdapter(connection_string=output_path, schema_type=schema_type)
    else:
        raise ValueError(f"Unknown db_type: {db_type}")
