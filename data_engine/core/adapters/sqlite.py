"""SQLite database adapter."""

import json
import logging
import os
import sqlite3
from typing import Dict, Any, List, Optional

from data_engine.core.adapters.base import DatabaseAdapter

logger = logging.getLogger(__name__)


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter for data loading."""

    # Default e-commerce schema
    DEFAULT_ECOMMERCE_SCHEMA = """
    -- Categories table
    CREATE TABLE IF NOT EXISTS categories (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        parent_id TEXT,
        FOREIGN KEY (parent_id) REFERENCES categories(id)
    );

    -- Products table
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        sku TEXT NOT NULL,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        rating REAL,
        review_count INTEGER DEFAULT 0,
        image TEXT,
        short_description TEXT,
        description TEXT,
        features TEXT,
        details TEXT,
        category_slug TEXT,
        sub_category TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- Product-Categories junction table
    CREATE TABLE IF NOT EXISTS product_categories (
        product_id TEXT,
        category_slug TEXT,
        PRIMARY KEY (product_id, category_slug),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_slug);
    CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
    CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating);
    CREATE INDEX IF NOT EXISTS idx_products_review_count ON products(review_count);
    CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
    CREATE INDEX IF NOT EXISTS idx_product_categories_slug ON product_categories(category_slug);

    -- FTS virtual table for text search
    CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
        id,
        name,
        sku,
        short_description,
        description,
        content='products',
        content_rowid='rowid'
    );
    """

    def __init__(
        self,
        db_path: str,
        create_schema: bool = True,
        schema_type: str = "e-commerce"
    ):
        """
        Initialize SQLite adapter.

        Args:
            db_path: Path to SQLite database file
            create_schema: Whether to create schema on connect
            schema_type: Type of schema to create
        """
        self.db_path = db_path
        self.create_schema_on_connect = create_schema
        self.schema_type = schema_type
        self.conn: Optional[sqlite3.Connection] = None
        self._batch_buffer: List[Dict[str, Any]] = []
        self._batch_size = 1000

    def connect(self) -> None:
        """Establish database connection."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Remove existing database if it exists
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            logger.info(f"Removed existing database: {self.db_path}")

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to SQLite database: {self.db_path}")

        if self.create_schema_on_connect:
            self._create_default_schema()

    def _create_default_schema(self) -> None:
        """Create default schema based on schema_type."""
        if self.schema_type == "e-commerce":
            self.conn.executescript(self.DEFAULT_ECOMMERCE_SCHEMA)
            self.conn.commit()
            logger.info("Created e-commerce schema")

    def close(self) -> None:
        """Close database connection."""
        if self._batch_buffer:
            self._flush_batch()

        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Closed SQLite connection")

    def create_schema(self, schema: Dict[str, Dict[str, str]]) -> None:
        """Create database schema from specification."""
        for table_name, columns in schema.items():
            col_defs = []
            for col_name, col_type in columns.items():
                col_defs.append(f"{col_name} {col_type}")

            sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})"
            self.conn.execute(sql)

        self.conn.commit()

    def insert(self, record: Dict[str, Any], table: str = "products") -> None:
        """Insert a single record (buffered)."""
        self._batch_buffer.append((table, record))

        if len(self._batch_buffer) >= self._batch_size:
            self._flush_batch()

    def _flush_batch(self) -> None:
        """Flush buffered records to database."""
        if not self._batch_buffer:
            return

        # Group by table
        by_table: Dict[str, List[Dict]] = {}
        for table, record in self._batch_buffer:
            if table not in by_table:
                by_table[table] = []
            by_table[table].append(record)

        for table, records in by_table.items():
            self._insert_many(records, table)

        self._batch_buffer.clear()

    def _insert_many(self, records: List[Dict[str, Any]], table: str) -> None:
        """Insert multiple records into a table."""
        if not records:
            return

        # Get column names from first record
        columns = list(records[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        col_names = ", ".join(columns)

        sql = f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"

        # Prepare values
        values = []
        for record in records:
            row = []
            for col in columns:
                val = record.get(col)
                # Convert lists/dicts to JSON
                if isinstance(val, (list, dict)):
                    val = json.dumps(val)
                row.append(val)
            values.append(tuple(row))

        try:
            self.conn.executemany(sql, values)
        except sqlite3.Error as e:
            logger.error(f"Batch insert error: {e}")
            # Try inserting one by one to identify problem records
            for row in values:
                try:
                    self.conn.execute(sql, row)
                except sqlite3.Error as e2:
                    logger.debug(f"Record insert error: {e2}")

    def insert_batch(self, records: List[Dict[str, Any]], table: str = "products") -> int:
        """Insert multiple records."""
        self._insert_many(records, table)
        return len(records)

    def commit(self) -> None:
        """Commit pending transactions."""
        self._flush_batch()
        if self.conn:
            # Rebuild FTS index
            try:
                self.conn.execute("""
                    INSERT INTO products_fts (id, name, sku, short_description, description)
                    SELECT id, name, sku, short_description, description FROM products
                """)
            except sqlite3.Error:
                pass  # FTS table might not exist

            self.conn.commit()

    def rollback(self) -> None:
        """Rollback pending transactions."""
        self._batch_buffer.clear()
        if self.conn:
            self.conn.rollback()

    def execute(self, sql: str, params: Optional[tuple] = None) -> Any:
        """Execute raw SQL."""
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    def get_table_count(self, table: str) -> int:
        """Get row count for a table."""
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]

    def insert_categories(self, categories: Dict[str, Dict[str, str]]) -> None:
        """
        Insert categories from mapping.

        Args:
            categories: Dict of category_key -> {slug, name}
        """
        seen_slugs = set()
        records = []

        for cat_key, cat_info in categories.items():
            slug = cat_info.get("slug")
            name = cat_info.get("name")

            if slug and slug not in seen_slugs:
                records.append({
                    "id": slug,
                    "name": name,
                    "slug": slug
                })
                seen_slugs.add(slug)

        if records:
            self._insert_many(records, "categories")
            logger.info(f"Inserted {len(records)} categories")

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {
            "file_size_mb": os.path.getsize(self.db_path) / (1024 * 1024),
            "tables": {}
        }

        # Get table counts
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        for row in cursor:
            table = row[0]
            try:
                count = self.get_table_count(table)
                stats["tables"][table] = count
            except sqlite3.Error:
                pass

        return stats
