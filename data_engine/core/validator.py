"""
Schema Validator Module

Validates dataset schema compatibility with target database schema
and generates field mappings.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class FieldMapping:
    """Mapping from dataset field to database column."""
    source_field: str  # Field name in HuggingFace dataset
    target_column: str  # Column name in database
    transform: Optional[str] = None  # Optional transformation (e.g., "float", "truncate:200")
    required: bool = False


@dataclass
class ValidationResult:
    """Result of schema validation."""
    is_valid: bool
    mappings: List[FieldMapping]
    missing_required: List[str]  # Required fields not found in dataset
    unmapped_columns: List[str]  # DB columns without dataset mapping
    warnings: List[str] = field(default_factory=list)
    coverage_score: float = 0.0  # Percentage of DB columns mapped


class SchemaValidator:
    """Validates and maps dataset schemas to database schemas."""

    # Common field name synonyms
    FIELD_SYNONYMS = {
        # Product fields
        "name": ["title", "product_name", "item_name", "product_title"],
        "price": ["cost", "amount", "value", "unit_price"],
        "description": ["desc", "details", "description_text", "body", "content"],
        "short_description": ["summary", "brief", "excerpt", "short_desc"],
        "image": ["image_url", "img", "thumbnail", "picture", "photo", "imageUrl", "thumbnailUrl"],
        "rating": ["average_rating", "avg_rating", "score", "stars", "review_score"],
        "review_count": ["rating_number", "num_reviews", "reviews_count", "reviewsCount"],
        "sku": ["product_id", "item_id", "asin", "parent_asin", "upc", "ean"],
        "category": ["category_name", "category_slug", "cat", "type", "main_category"],

        # User fields
        "email": ["email_address", "user_email", "mail"],
        "username": ["user_name", "login", "handle", "screen_name"],
        "avatar": ["avatar_url", "profile_image", "picture"],

        # Common fields
        "created_at": ["created", "date_created", "timestamp", "created_date"],
        "updated_at": ["updated", "modified", "last_modified"],
        "id": ["_id", "uuid", "identifier"],
    }

    # Type compatibility mappings
    TYPE_COMPATIBILITY = {
        "str": ["TEXT", "VARCHAR", "CHAR", "STRING"],
        "int": ["INTEGER", "INT", "BIGINT", "SMALLINT"],
        "float": ["REAL", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC"],
        "bool": ["BOOLEAN", "BOOL"],
        "list": ["JSON", "JSONB", "TEXT"],  # Lists stored as JSON
        "dict": ["JSON", "JSONB", "TEXT"],  # Dicts stored as JSON
    }

    def __init__(self):
        # Build reverse synonym lookup
        self._reverse_synonyms = {}
        for canonical, synonyms in self.FIELD_SYNONYMS.items():
            for syn in synonyms:
                self._reverse_synonyms[syn.lower()] = canonical
            self._reverse_synonyms[canonical.lower()] = canonical

    def validate(
        self,
        dataset_schema: Dict[str, Any],
        db_schema: Dict[str, Dict[str, str]],
        required_mappings: Optional[Dict[str, str]] = None
    ) -> ValidationResult:
        """
        Validate dataset schema against database schema.

        Args:
            dataset_schema: Dict of field_name -> {type, sample}
            db_schema: Dict of table_name -> {column_name: column_type}
            required_mappings: Optional explicit mappings to enforce

        Returns:
            ValidationResult with mappings and validation status
        """
        mappings = []
        missing_required = []
        unmapped_columns = []
        warnings = []

        # Flatten DB schema for simpler matching
        all_columns = {}
        for table, columns in db_schema.items():
            for col_name, col_type in columns.items():
                all_columns[col_name] = {
                    "table": table,
                    "type": col_type,
                    "mapped": False
                }

        dataset_fields = set(dataset_schema.keys())
        required_mappings = required_mappings or {}

        # First, apply explicit mappings
        for source, target in required_mappings.items():
            if source in dataset_fields and target in all_columns:
                mappings.append(FieldMapping(
                    source_field=source,
                    target_column=target,
                    required=True
                ))
                all_columns[target]["mapped"] = True
                dataset_fields.discard(source)

        # Then, try automatic mapping
        for col_name, col_info in all_columns.items():
            if col_info["mapped"]:
                continue

            # Try to find matching dataset field
            match = self._find_matching_field(col_name, dataset_fields, dataset_schema)

            if match:
                source_field, transform = match
                mappings.append(FieldMapping(
                    source_field=source_field,
                    target_column=col_name,
                    transform=transform
                ))
                col_info["mapped"] = True
                dataset_fields.discard(source_field)
            else:
                unmapped_columns.append(col_name)

        # Check for critical missing fields
        critical_fields = ["name", "id", "price"]  # Fields that are typically required
        for critical in critical_fields:
            if critical in unmapped_columns:
                # Check if any synonym is available
                synonyms = self.FIELD_SYNONYMS.get(critical, [])
                found = False
                for syn in synonyms:
                    if syn in dataset_fields:
                        mappings.append(FieldMapping(
                            source_field=syn,
                            target_column=critical,
                            required=True
                        ))
                        all_columns[critical]["mapped"] = True
                        unmapped_columns.remove(critical)
                        found = True
                        break

                if not found:
                    missing_required.append(critical)

        # Calculate coverage
        total_columns = len(all_columns)
        mapped_columns = sum(1 for c in all_columns.values() if c["mapped"])
        coverage = mapped_columns / total_columns if total_columns > 0 else 0

        # Determine validity
        is_valid = len(missing_required) == 0 and coverage >= 0.5

        if not is_valid:
            if missing_required:
                warnings.append(f"Missing required fields: {missing_required}")
            if coverage < 0.5:
                warnings.append(f"Low coverage: {coverage:.1%} of columns mapped")

        return ValidationResult(
            is_valid=is_valid,
            mappings=mappings,
            missing_required=missing_required,
            unmapped_columns=unmapped_columns,
            warnings=warnings,
            coverage_score=coverage
        )

    def _find_matching_field(
        self,
        target_column: str,
        dataset_fields: set,
        dataset_schema: Dict[str, Any]
    ) -> Optional[Tuple[str, Optional[str]]]:
        """
        Find a dataset field that matches the target column.

        Returns:
            Tuple of (source_field, transform) or None
        """
        target_lower = target_column.lower()
        target_normalized = self._normalize_name(target_column)

        # 1. Exact match
        for field in dataset_fields:
            if field.lower() == target_lower:
                return (field, None)

        # 2. Synonym match
        canonical = self._reverse_synonyms.get(target_lower)
        if canonical:
            for field in dataset_fields:
                field_canonical = self._reverse_synonyms.get(field.lower())
                if field_canonical == canonical:
                    return (field, None)

        # 3. Normalized match (snake_case, camelCase, etc.)
        for field in dataset_fields:
            if self._normalize_name(field) == target_normalized:
                return (field, None)

        # 4. Fuzzy match (similarity > 0.8)
        best_match = None
        best_score = 0.8

        for field in dataset_fields:
            score = SequenceMatcher(None, target_lower, field.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = field

        if best_match:
            return (best_match, None)

        return None

    def _normalize_name(self, name: str) -> str:
        """Normalize field name (remove underscores, lowercase)."""
        # Convert camelCase to snake_case
        name = re.sub(r'([a-z])([A-Z])', r'\1_\2', name)
        # Remove all non-alphanumeric
        name = re.sub(r'[^a-z0-9]', '', name.lower())
        return name

    def generate_mapping_config(
        self,
        dataset_id: str,
        dataset_schema: Dict[str, Any],
        target_entity: str = "products"
    ) -> Dict[str, Any]:
        """
        Generate a mapping configuration for common use cases.

        Args:
            dataset_id: HuggingFace dataset ID
            dataset_schema: Dataset schema
            target_entity: Target entity type

        Returns:
            Mapping configuration dict
        """
        config = {
            "dataset_id": dataset_id,
            "entity": target_entity,
            "mappings": {},
            "filters": {},
            "transforms": {}
        }

        # Common product field mappings
        if target_entity == "products":
            product_mappings = {
                "id": ["id", "parent_asin", "asin", "product_id"],
                "sku": ["parent_asin", "asin", "sku", "product_id"],
                "name": ["title", "name", "product_name"],
                "price": ["price", "cost", "amount"],
                "description": ["description", "desc", "details"],
                "short_description": ["description", "summary"],
                "image": ["image", "images", "image_url", "main_image"],
                "rating": ["average_rating", "rating", "stars"],
                "review_count": ["rating_number", "review_count", "num_reviews"],
                "category_slug": ["main_category", "category", "categories"],
            }

            for target, sources in product_mappings.items():
                for source in sources:
                    if source in dataset_schema:
                        config["mappings"][target] = source
                        break

            # Add common filters
            config["filters"] = {
                "price": {"min": 0, "max": 50000},
                "rating": {"min": 0},
                "image": {"not_empty": True},
                "name": {"min_length": 5},
            }

            # Add transforms
            config["transforms"] = {
                "price": "float",
                "rating": "float:1",  # Round to 1 decimal
                "name": "truncate:200",
                "description": "truncate:2000",
            }

        return config

    def infer_db_schema_from_entities(
        self,
        entities: Dict[str, Any]
    ) -> Dict[str, Dict[str, str]]:
        """
        Infer database schema from entity definitions.

        Args:
            entities: Entity definitions from spec.project.json

        Returns:
            Database schema dict
        """
        schema = {}

        for entity_name, entity_def in entities.items():
            table_name = self._entity_to_table_name(entity_name)
            columns = {}

            # Add standard columns
            columns["id"] = "TEXT PRIMARY KEY"
            columns["created_at"] = "TIMESTAMP"

            # Add fields from entity definition
            if isinstance(entity_def, dict):
                fields = entity_def.get("fields", {})
                for field_name, field_def in fields.items():
                    col_type = self._infer_column_type(field_def)
                    columns[field_name] = col_type

            schema[table_name] = columns

        return schema

    def _entity_to_table_name(self, entity_name: str) -> str:
        """Convert entity name to table name."""
        # CamelCase to snake_case
        name = re.sub(r'([a-z])([A-Z])', r'\1_\2', entity_name)
        return name.lower()

    def _infer_column_type(self, field_def: Any) -> str:
        """Infer SQL column type from field definition."""
        if isinstance(field_def, dict):
            field_type = field_def.get("type", "string")
        elif isinstance(field_def, str):
            field_type = field_def
        else:
            field_type = "string"

        type_map = {
            "string": "TEXT",
            "text": "TEXT",
            "number": "REAL",
            "integer": "INTEGER",
            "float": "REAL",
            "boolean": "BOOLEAN",
            "date": "TIMESTAMP",
            "datetime": "TIMESTAMP",
            "array": "TEXT",  # JSON
            "object": "TEXT",  # JSON
        }

        return type_map.get(field_type.lower(), "TEXT")
