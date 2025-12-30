"""PostgreSQL database adapter."""

import json
import logging
import os
from typing import Dict, Any, List, Optional

from data_engine.core.adapters.base import DatabaseAdapter

logger = logging.getLogger(__name__)


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL database adapter for data loading."""

    # Default e-commerce schema
    DEFAULT_ECOMMERCE_SCHEMA = """
    -- Enable extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    -- Categories table
    CREATE TABLE IF NOT EXISTS categories (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        parent_id TEXT REFERENCES categories(id),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Products table
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        sku TEXT NOT NULL,
        name TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        rating DECIMAL(2,1),
        review_count INTEGER DEFAULT 0,
        image TEXT,
        short_description TEXT,
        description TEXT,
        features JSONB DEFAULT '[]'::jsonb,
        details JSONB DEFAULT '{}'::jsonb,
        category_slug TEXT REFERENCES categories(slug),
        sub_category TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Product-Categories junction table
    CREATE TABLE IF NOT EXISTS product_categories (
        product_id TEXT REFERENCES products(id) ON DELETE CASCADE,
        category_slug TEXT REFERENCES categories(slug) ON DELETE CASCADE,
        PRIMARY KEY (product_id, category_slug)
    );

    -- Indexes for efficient querying
    CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_slug);
    CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
    CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating);
    CREATE INDEX IF NOT EXISTS idx_products_review_count ON products(review_count);
    CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON products USING GIN (name gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS idx_products_description_trgm ON products USING GIN (description gin_trgm_ops);
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        host: str = "localhost",
        port: int = 5432,
        database: str = "app",
        user: str = "app",
        password: str = "app",
        create_schema: bool = True,
        schema_type: str = "e-commerce"
    ):
        """
        Initialize PostgreSQL adapter.

        Args:
            connection_string: Full connection string (overrides other params)
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            create_schema: Whether to create schema on connect
            schema_type: Type of schema to create
        """
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        if not self.connection_string:
            self.connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"

        self.create_schema_on_connect = create_schema
        self.schema_type = schema_type
        self.conn = None
        self._batch_buffer: List[Dict[str, Any]] = []
        self._batch_size = 1000

    def connect(self) -> None:
        """Establish database connection."""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError:
            raise ImportError("psycopg2 is required for PostgreSQL. Install with: pip install psycopg2-binary")

        self.conn = psycopg2.connect(self.connection_string)
        self.conn.autocommit = False
        logger.info(f"Connected to PostgreSQL database")

        if self.create_schema_on_connect:
            self._create_default_schema()

    def _create_default_schema(self) -> None:
        """Create default schema based on schema_type."""
        if self.schema_type == "e-commerce":
            with self.conn.cursor() as cur:
                cur.execute(self.DEFAULT_ECOMMERCE_SCHEMA)
            self.conn.commit()
            logger.info("Created e-commerce schema")

    def close(self) -> None:
        """Close database connection."""
        if self._batch_buffer:
            self._flush_batch()

        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Closed PostgreSQL connection")

    def create_schema(self, schema: Dict[str, Dict[str, str]]) -> None:
        """Create database schema from specification."""
        with self.conn.cursor() as cur:
            for table_name, columns in schema.items():
                col_defs = []
                for col_name, col_type in columns.items():
                    col_defs.append(f"{col_name} {col_type}")

                sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})"
                cur.execute(sql)

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

        try:
            from psycopg2.extras import execute_values
        except ImportError:
            # Fallback to individual inserts
            for record in records:
                self._insert_single(record, table)
            return

        # Get column names from first record
        columns = list(records[0].keys())
        col_names = ", ".join(columns)

        # Prepare values
        values = []
        for record in records:
            row = []
            for col in columns:
                val = record.get(col)
                # Convert lists/dicts to JSON string for JSONB columns
                if isinstance(val, (list, dict)):
                    val = json.dumps(val)
                row.append(val)
            values.append(tuple(row))

        sql = f"""
            INSERT INTO {table} ({col_names})
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """

        try:
            with self.conn.cursor() as cur:
                execute_values(cur, sql, values)
        except Exception as e:
            logger.error(f"Batch insert error: {e}")
            # Try inserting one by one
            for record in records:
                try:
                    self._insert_single(record, table)
                except Exception as e2:
                    logger.debug(f"Record insert error: {e2}")

    def _insert_single(self, record: Dict[str, Any], table: str) -> None:
        """Insert a single record."""
        columns = list(record.keys())
        placeholders = ", ".join(["%s" for _ in columns])
        col_names = ", ".join(columns)

        values = []
        for col in columns:
            val = record.get(col)
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            values.append(val)

        sql = f"""
            INSERT INTO {table} ({col_names})
            VALUES ({placeholders})
            ON CONFLICT (id) DO NOTHING
        """

        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(values))

    def insert_batch(self, records: List[Dict[str, Any]], table: str = "products") -> int:
        """Insert multiple records."""
        self._insert_many(records, table)
        return len(records)

    def commit(self) -> None:
        """Commit pending transactions."""
        self._flush_batch()
        if self.conn:
            self.conn.commit()

    def rollback(self) -> None:
        """Rollback pending transactions."""
        self._batch_buffer.clear()
        if self.conn:
            self.conn.rollback()

    def execute(self, sql: str, params: Optional[tuple] = None) -> Any:
        """Execute raw SQL."""
        with self.conn.cursor() as cur:
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            try:
                return cur.fetchall()
            except Exception:
                return None

    def get_table_count(self, table: str) -> int:
        """Get row count for a table."""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]

    def insert_categories(self, categories: Dict[str, Dict[str, str]]) -> None:
        """Insert categories from mapping."""
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
        stats = {"tables": {}}

        with self.conn.cursor() as cur:
            # Get table counts
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            for row in cur.fetchall():
                table = row[0]
                try:
                    stats["tables"][table] = self.get_table_count(table)
                except Exception:
                    pass

        return stats
