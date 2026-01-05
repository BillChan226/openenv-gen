"""
Dataset Loader Module

Downloads HuggingFace datasets, transforms data, and loads into database.
"""

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator, Callable
from datasets import load_dataset, Dataset

from data_engine.core.validator import FieldMapping

logger = logging.getLogger(__name__)


@dataclass
class DataFilter:
    """Filter configuration for data loading."""
    field: str
    condition: str  # "min", "max", "not_empty", "min_length", "regex"
    value: Any


@dataclass
class LoadConfig:
    """Configuration for dataset loading."""
    dataset_id: str
    split: str = "train"
    mappings: List[FieldMapping] = field(default_factory=list)
    filters: List[DataFilter] = field(default_factory=list)
    category_field: Optional[str] = None
    category_mapping: Optional[Dict[str, Dict[str, str]]] = None
    max_per_category: int = 1000
    max_total: Optional[int] = None
    transforms: Dict[str, str] = field(default_factory=dict)


@dataclass
class LoadResult:
    """Result of dataset loading."""
    total_processed: int
    total_loaded: int
    total_filtered: int
    categories_loaded: Dict[str, int]
    errors: List[str]


class DatasetLoader:
    """Downloads and transforms HuggingFace datasets."""

    def __init__(self):
        self._transform_funcs: Dict[str, Callable] = {
            "float": self._transform_float,
            "int": self._transform_int,
            "truncate": self._transform_truncate,
            "json": self._transform_json,
            "slugify": self._transform_slugify,
            "clean_html": self._transform_clean_html,
            "prefix": self._transform_prefix,
            "first": self._transform_first,
        }

    def download(
        self,
        dataset_id: str,
        split: str = "train",
        streaming: bool = True
    ) -> Iterator[Dict[str, Any]]:
        """
        Download dataset from HuggingFace.

        Args:
            dataset_id: HuggingFace dataset ID
            split: Dataset split to use
            streaming: Whether to stream (memory efficient)

        Yields:
            Dataset records as dictionaries
        """
        logger.info(f"Downloading dataset: {dataset_id} (split={split})")

        try:
            ds = load_dataset(dataset_id, split=split, streaming=streaming)

            for record in ds:
                yield dict(record)

        except Exception as e:
            logger.error(f"Failed to download dataset {dataset_id}: {e}")
            raise

    def transform_record(
        self,
        record: Dict[str, Any],
        mappings: List[FieldMapping],
        transforms: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Transform a single record according to mappings.

        Args:
            record: Raw record from dataset
            mappings: Field mappings to apply
            transforms: Transform specifications

        Returns:
            Transformed record or None if invalid
        """
        result = {}

        for mapping in mappings:
            source = mapping.source_field
            target = mapping.target_column

            # Get source value
            value = record.get(source)

            # Apply transform if specified
            transform_spec = mapping.transform or transforms.get(target)
            if transform_spec and value is not None:
                value = self._apply_transform(value, transform_spec)

            result[target] = value

        return result

    def _apply_transform(self, value: Any, spec: str) -> Any:
        """Apply a transformation to a value."""
        # Parse spec like "truncate:200" or "float:1"
        parts = spec.split(":")
        func_name = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        if func_name in self._transform_funcs:
            return self._transform_funcs[func_name](value, *args)

        logger.warning(f"Unknown transform: {func_name}")
        return value

    def _transform_float(self, value: Any, decimals: str = None) -> Optional[float]:
        """Convert to float, optionally round."""
        try:
            if isinstance(value, str):
                # Remove currency symbols and commas
                value = re.sub(r'[^\d.\-]', '', value)
            f = float(value)
            if decimals:
                f = round(f, int(decimals))
            return f
        except (ValueError, TypeError):
            return None

    def _transform_int(self, value: Any) -> Optional[int]:
        """Convert to integer."""
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def _transform_truncate(self, value: Any, max_len: str) -> str:
        """Truncate string to max length."""
        s = str(value) if value else ""
        max_length = int(max_len)
        if len(s) > max_length:
            return s[:max_length - 3] + "..."
        return s

    def _transform_json(self, value: Any) -> str:
        """Convert to JSON string."""
        if isinstance(value, str):
            return value
        return json.dumps(value) if value else "[]"

    def _transform_slugify(self, value: Any) -> str:
        """Convert to URL-friendly slug."""
        if not value:
            return ""
        s = str(value).lower()
        s = re.sub(r'[^a-z0-9\s-]', '', s)
        s = re.sub(r'[\s_]+', '-', s)
        s = re.sub(r'-+', '-', s)
        return s.strip('-')

    def _transform_clean_html(self, value: Any) -> str:
        """Remove HTML tags."""
        if not value:
            return ""
        return re.sub(r'<[^>]+>', '', str(value))

    def _transform_prefix(self, value: Any, prefix: str) -> str:
        """Add prefix to value."""
        return f"{prefix}{value}" if value else ""

    def _transform_first(self, value: Any) -> str:
        """Get first element if list, else convert to string."""
        if isinstance(value, list) and value:
            return str(value[0])
        return str(value) if value else ""

    def filter_record(
        self,
        record: Dict[str, Any],
        filters: List[DataFilter]
    ) -> bool:
        """
        Check if record passes all filters.

        Args:
            record: Record to check
            filters: List of filters to apply

        Returns:
            True if record passes all filters
        """
        for f in filters:
            value = record.get(f.field)

            if f.condition == "min":
                if value is None or value < f.value:
                    return False

            elif f.condition == "max":
                if value is not None and value > f.value:
                    return False

            elif f.condition == "not_empty":
                if not value:
                    return False
                if isinstance(value, str) and not value.strip():
                    return False
                if isinstance(value, str) and not value.startswith("http"):
                    # For URLs, check if it's a valid URL
                    if f.field in ["image", "image_url", "thumbnail"]:
                        return False

            elif f.condition == "min_length":
                if not value or len(str(value)) < f.value:
                    return False

            elif f.condition == "regex":
                if not value or not re.match(f.value, str(value)):
                    return False

        return True

    def load(
        self,
        config: LoadConfig,
        adapter: "DatabaseAdapter"
    ) -> LoadResult:
        """
        Load dataset into database.

        Args:
            config: Load configuration
            adapter: Database adapter to use

        Returns:
            LoadResult with statistics
        """
        logger.info(f"Loading dataset {config.dataset_id} into database")

        # Track statistics
        total_processed = 0
        total_loaded = 0
        total_filtered = 0
        categories_loaded = defaultdict(int)
        errors = []

        # Track per-category limits
        category_counts = defaultdict(int)

        try:
            # Stream dataset
            for record in self.download(config.dataset_id, config.split):
                total_processed += 1

                if total_processed % 10000 == 0:
                    logger.info(f"Processed {total_processed} records, loaded {total_loaded}")

                # Check total limit
                if config.max_total and total_loaded >= config.max_total:
                    logger.info(f"Reached max_total limit: {config.max_total}")
                    break

                # Get category for per-category limiting
                category = None
                if config.category_field:
                    category = record.get(config.category_field)

                    # Map category if mapping provided
                    if config.category_mapping and category:
                        cat_info = config.category_mapping.get(category)
                        if not cat_info:
                            total_filtered += 1
                            continue
                        category = cat_info.get("slug", category)

                    # Check per-category limit
                    if category and category_counts[category] >= config.max_per_category:
                        continue

                # Transform record
                transformed = self.transform_record(
                    record,
                    config.mappings,
                    config.transforms
                )

                if not transformed:
                    total_filtered += 1
                    continue

                # Apply filters
                if not self.filter_record(transformed, config.filters):
                    total_filtered += 1
                    continue

                # Add category info
                if category:
                    transformed["category_slug"] = category

                # Insert into database
                try:
                    adapter.insert(transformed)
                    total_loaded += 1
                    if category:
                        category_counts[category] += 1
                        categories_loaded[category] += 1
                except Exception as e:
                    errors.append(f"Insert error: {e}")
                    if len(errors) > 100:
                        logger.error("Too many errors, aborting")
                        break

        except Exception as e:
            logger.error(f"Load failed: {e}")
            errors.append(f"Load failed: {e}")

        # Commit and finalize
        try:
            adapter.commit()
        except Exception as e:
            errors.append(f"Commit failed: {e}")

        logger.info(f"Load complete: {total_loaded} records loaded, "
                   f"{total_filtered} filtered, {len(errors)} errors")

        return LoadResult(
            total_processed=total_processed,
            total_loaded=total_loaded,
            total_filtered=total_filtered,
            categories_loaded=dict(categories_loaded),
            errors=errors
        )

    def create_load_config(
        self,
        dataset_id: str,
        domain: str = "e-commerce",
        category_mapping: Optional[Dict[str, Dict[str, str]]] = None,
        max_per_category: int = 1000
    ) -> LoadConfig:
        """
        Create a LoadConfig for common use cases.

        Args:
            dataset_id: HuggingFace dataset ID
            domain: Domain type
            category_mapping: Optional category slug mapping
            max_per_category: Max records per category

        Returns:
            LoadConfig object
        """
        if domain == "e-commerce":
            return self._create_ecommerce_config(
                dataset_id, category_mapping, max_per_category
            )

        # Default generic config
        return LoadConfig(
            dataset_id=dataset_id,
            max_per_category=max_per_category
        )

    def _create_ecommerce_config(
        self,
        dataset_id: str,
        category_mapping: Optional[Dict[str, Dict[str, str]]],
        max_per_category: int
    ) -> LoadConfig:
        """Create config for e-commerce datasets."""

        # Default mappings for Amazon-style datasets
        mappings = [
            FieldMapping("parent_asin", "id", transform="prefix:amz-"),
            FieldMapping("parent_asin", "sku"),
            FieldMapping("title", "name", transform="truncate:200"),
            FieldMapping("price", "price", transform="float"),
            FieldMapping("average_rating", "rating", transform="float:1"),
            FieldMapping("rating_number", "review_count", transform="int"),
            FieldMapping("image", "image"),
            FieldMapping("description", "description", transform="truncate:2000"),
            FieldMapping("description", "short_description", transform="truncate:300"),
            FieldMapping("features", "features", transform="json"),
            FieldMapping("details", "details", transform="json"),
            FieldMapping("categories", "sub_category", transform="first"),
        ]

        filters = [
            DataFilter("price", "min", 0.01),
            DataFilter("price", "max", 50000),
            DataFilter("average_rating", "min", 0),
            DataFilter("image", "not_empty", True),
            DataFilter("title", "min_length", 5),
        ]

        return LoadConfig(
            dataset_id=dataset_id,
            mappings=mappings,
            filters=filters,
            category_field="filename",  # Amazon dataset uses filename for category
            category_mapping=category_mapping,
            max_per_category=max_per_category,
            transforms={
                "id": "prefix:amz-",
                "price": "float",
                "rating": "float:1",
                "review_count": "int",
            }
        )


