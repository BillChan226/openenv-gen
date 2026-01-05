"""
Data Engine - HuggingFace Dataset Discovery and Loading for Web Environments

This module provides tools to:
1. Discover relevant datasets on HuggingFace Hub based on requirements
2. Validate dataset schema compatibility with target database
3. Download, transform, and load datasets into SQLite/PostgreSQL

Usage:
    # CLI
    python -m data_engine search --domain e-commerce
    python -m data_engine load --dataset milistu/AMAZON-Products-2023 --output products.db

    # Python API
    from data_engine import DataEngine
    engine = DataEngine()
    dataset = engine.discover(instruction="e-commerce website", entities=spec)
    engine.load(dataset, output_path="products.db")
"""

from data_engine.core.discovery import DatasetDiscovery, DataRequirements, DatasetCandidate
from data_engine.core.validator import SchemaValidator, FieldMapping
from data_engine.core.loader import DatasetLoader
from data_engine.engine import DataEngine

__version__ = "0.1.0"
__all__ = [
    "DataEngine",
    "DatasetDiscovery",
    "DataRequirements",
    "DatasetCandidate",
    "SchemaValidator",
    "FieldMapping",
    "DatasetLoader",
]
