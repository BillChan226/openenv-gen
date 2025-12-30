"""Base database adapter interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters."""

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def create_schema(self, schema: Dict[str, Dict[str, str]]) -> None:
        """
        Create database schema.

        Args:
            schema: Dict of table_name -> {column_name: column_type}
        """
        pass

    @abstractmethod
    def insert(self, record: Dict[str, Any], table: str = "products") -> None:
        """
        Insert a single record.

        Args:
            record: Record data
            table: Target table name
        """
        pass

    @abstractmethod
    def insert_batch(self, records: List[Dict[str, Any]], table: str = "products") -> int:
        """
        Insert multiple records.

        Args:
            records: List of record data
            table: Target table name

        Returns:
            Number of records inserted
        """
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit pending transactions."""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rollback pending transactions."""
        pass

    @abstractmethod
    def execute(self, sql: str, params: Optional[tuple] = None) -> Any:
        """
        Execute raw SQL.

        Args:
            sql: SQL statement
            params: Query parameters

        Returns:
            Query result
        """
        pass

    @abstractmethod
    def get_table_count(self, table: str) -> int:
        """Get row count for a table."""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
