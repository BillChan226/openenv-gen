"""
Data Engine CLI

Usage:
    python -m data_engine search --instruction "e-commerce website"
    python -m data_engine load --dataset milistu/AMAZON-Products-2023 --output products.db
    python -m data_engine run --instruction "e-commerce website like eBay" --output products.db
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from data_engine.engine import DataEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_search(args):
    """Search for datasets matching requirements."""
    engine = DataEngine()

    # Load entities if provided
    entities = None
    if args.entities:
        with open(args.entities, "r") as f:
            entities = json.load(f)

    candidates = engine.discover(
        instruction=args.instruction,
        entities=entities,
        limit=args.limit
    )

    print(f"\nFound {len(candidates)} candidate datasets:\n")
    for i, c in enumerate(candidates, 1):
        print(f"{i}. {c.dataset_id}")
        print(f"   Score: {c.score:.1f}")
        print(f"   Downloads: {c.downloads:,}")
        print(f"   URL: {c.url}")
        if c.description:
            desc = c.description[:100] + "..." if len(c.description) > 100 else c.description
            print(f"   Description: {desc}")
        print()


def cmd_load(args):
    """Load a specific dataset into database."""
    engine = DataEngine()

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading dataset: {args.dataset}")
    print(f"Output: {args.output}")
    print(f"Max per category: {args.max_per_category}")
    print()

    result = engine.load(
        dataset_id=args.dataset,
        output_path=str(output_path),
        domain=args.domain,
        db_type=args.db_type,
        max_per_category=args.max_per_category,
        max_total=args.max_total
    )

    print(f"\nLoad complete!")
    print(f"  Processed: {result.total_processed:,}")
    print(f"  Loaded: {result.total_loaded:,}")
    print(f"  Filtered: {result.total_filtered:,}")
    print(f"  Errors: {len(result.errors)}")
    print(f"\nCategories:")
    for cat, count in sorted(result.categories_loaded.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count:,}")


def cmd_run(args):
    """Run full pipeline: discover and load."""
    engine = DataEngine()

    # Load entities if provided
    entities = None
    if args.entities:
        with open(args.entities, "r") as f:
            entities = json.load(f)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Running data engine pipeline")
    print(f"  Instruction: {args.instruction}")
    print(f"  Output: {args.output}")
    print()

    result = engine.run(
        instruction=args.instruction,
        output_path=str(output_path),
        entities=entities,
        db_type=args.db_type,
        max_per_category=args.max_per_category,
        max_total=args.max_total,
        dataset_id=args.dataset
    )

    print(f"\nPipeline complete!")
    print(f"  Success: {result['success']}")
    print(f"  Domain: {result.get('domain', 'unknown')}")
    print(f"  Dataset: {result.get('dataset_id', 'none')}")

    if result.get("discovery"):
        print(f"\nDiscovery results:")
        for c in result["discovery"]["candidates"]:
            print(f"  - {c['id']} (score: {c['score']:.1f})")

    if result.get("load"):
        load = result["load"]
        print(f"\nLoad results:")
        print(f"  Processed: {load['total_processed']:,}")
        print(f"  Loaded: {load['total_loaded']:,}")
        print(f"  Errors: {load['errors']}")

    if result.get("error"):
        print(f"\nError: {result['error']}")
        sys.exit(1)


def cmd_schema(args):
    """Show schema for a dataset."""
    from data_engine.core.discovery import DatasetDiscovery

    discovery = DatasetDiscovery()
    schema = discovery.get_dataset_schema(args.dataset)

    print(f"\nSchema for {args.dataset}:\n")
    for field, info in schema.items():
        print(f"  {field}:")
        print(f"    Type: {info['type']}")
        if info.get('sample'):
            sample = info['sample'][:50] + "..." if len(info['sample']) > 50 else info['sample']
            print(f"    Sample: {sample}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Data Engine - HuggingFace dataset discovery and loading"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for datasets")
    search_parser.add_argument(
        "--instruction", "-i",
        required=True,
        help="Natural language description of what you need"
    )
    search_parser.add_argument(
        "--entities", "-e",
        help="Path to entities JSON file"
    )
    search_parser.add_argument(
        "--limit", "-n",
        type=int,
        default=5,
        help="Max number of results"
    )

    # Load command
    load_parser = subparsers.add_parser("load", help="Load a dataset")
    load_parser.add_argument(
        "--dataset", "-d",
        required=True,
        help="HuggingFace dataset ID"
    )
    load_parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output database path"
    )
    load_parser.add_argument(
        "--domain",
        default="e-commerce",
        help="Domain type"
    )
    load_parser.add_argument(
        "--db-type",
        choices=["sqlite", "postgres"],
        default="sqlite",
        help="Database type"
    )
    load_parser.add_argument(
        "--max-per-category",
        type=int,
        default=1000,
        help="Max records per category"
    )
    load_parser.add_argument(
        "--max-total",
        type=int,
        default=None,
        help="Max total records"
    )

    # Run command (full pipeline)
    run_parser = subparsers.add_parser("run", help="Run full pipeline")
    run_parser.add_argument(
        "--instruction", "-i",
        required=True,
        help="Natural language description"
    )
    run_parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output database path"
    )
    run_parser.add_argument(
        "--entities", "-e",
        help="Path to entities JSON file"
    )
    run_parser.add_argument(
        "--dataset", "-d",
        help="Specific dataset to use (skips discovery)"
    )
    run_parser.add_argument(
        "--db-type",
        choices=["sqlite", "postgres"],
        default="sqlite",
        help="Database type"
    )
    run_parser.add_argument(
        "--max-per-category",
        type=int,
        default=1000,
        help="Max records per category"
    )
    run_parser.add_argument(
        "--max-total",
        type=int,
        default=None,
        help="Max total records"
    )

    # Schema command
    schema_parser = subparsers.add_parser("schema", help="Show dataset schema")
    schema_parser.add_argument(
        "--dataset", "-d",
        required=True,
        help="HuggingFace dataset ID"
    )

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "load":
        cmd_load(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "schema":
        cmd_schema(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
