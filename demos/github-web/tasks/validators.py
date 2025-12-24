"""Validation helpers for task definitions.

Provides reusable validators for common success conditions.
"""

from typing import Any, Callable, Dict, List, Optional


class PageValidator:
    """Validators for page state."""

    @staticmethod
    def url_contains(page: Any, substring: str) -> bool:
        """Check if current URL contains substring."""
        return substring in page.url

    @staticmethod
    def url_matches(page: Any, pattern: str) -> bool:
        """Check if current URL matches regex pattern."""
        import re
        return bool(re.match(pattern, page.url))

    @staticmethod
    def element_exists(page: Any, selector: str) -> bool:
        """Check if element exists on page."""
        try:
            return page.query_selector(selector) is not None
        except Exception:
            return False

    @staticmethod
    def element_visible(page: Any, selector: str) -> bool:
        """Check if element is visible on page."""
        try:
            element = page.query_selector(selector)
            return element is not None and element.is_visible()
        except Exception:
            return False

    @staticmethod
    def element_text_contains(page: Any, selector: str, text: str) -> bool:
        """Check if element contains specific text."""
        try:
            element = page.query_selector(selector)
            if element:
                return text in element.text_content()
        except Exception:
            pass
        return False

    @staticmethod
    def has_success_message(page: Any, messages: List[str] = None) -> bool:
        """Check for success message on page."""
        default_messages = ["success", "completed", "done", "thank you"]
        messages = messages or default_messages

        try:
            content = page.content().lower()
            return any(msg.lower() in content for msg in messages)
        except Exception:
            return False


class DBValidator:
    """Validators for database state."""

    @staticmethod
    def record_exists(
        db_state: Dict[str, Any],
        table: str,
        conditions: Dict[str, Any],
    ) -> bool:
        """Check if a record matching conditions exists."""
        records = db_state.get(table, [])
        for record in records:
            if all(record.get(k) == v for k, v in conditions.items()):
                return True
        return False

    @staticmethod
    def record_count(
        db_state: Dict[str, Any],
        table: str,
        expected: int,
    ) -> bool:
        """Check if table has expected number of records."""
        records = db_state.get(table, [])
        return len(records) == expected

    @staticmethod
    def field_value(
        db_state: Dict[str, Any],
        table: str,
        record_id: str,
        field: str,
        expected: Any,
    ) -> bool:
        """Check if a specific field has expected value."""
        records = db_state.get(table, [])
        for record in records:
            if record.get("id") == record_id:
                return record.get(field) == expected
        return False


class CompositeValidator:
    """Combine multiple validators."""

    def __init__(self):
        self._validators: List[Callable[[], bool]] = []

    def add(self, validator: Callable[[], bool]) -> "CompositeValidator":
        """Add a validator function."""
        self._validators.append(validator)
        return self

    def all_pass(self) -> bool:
        """Check if all validators pass."""
        return all(v() for v in self._validators)

    def any_pass(self) -> bool:
        """Check if any validator passes."""
        return any(v() for v in self._validators)

    def count_passed(self) -> int:
        """Count how many validators pass."""
        return sum(1 for v in self._validators if v())
