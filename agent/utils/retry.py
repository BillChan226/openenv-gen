"""
Retry Module - Robust retry mechanism with exponential backoff

Inspired by OpenHands RetryMixin, this module provides:
- Exponential backoff retry decorator
- Customizable retry conditions
- Automatic temperature adjustment on LLM failures
- Comprehensive logging
"""

import asyncio
import logging
import random
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, Union

# Try to import tenacity, fall back to simple retry if not available
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        before_sleep_log,
        RetryError,
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    RetryError = Exception

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 60.0,
        multiplier: float = 2.0,
        retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        jitter: bool = True,
    ):
        """
        Args:
            max_retries: Maximum number of retry attempts
            min_wait: Minimum wait time between retries (seconds)
            max_wait: Maximum wait time between retries (seconds)
            multiplier: Exponential backoff multiplier
            retry_exceptions: Tuple of exception types to retry on
            jitter: Add random jitter to wait times
        """
        self.max_retries = max_retries
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.multiplier = multiplier
        self.retry_exceptions = retry_exceptions
        self.jitter = jitter


# Default configs for different scenarios
DEFAULT_CONFIG = RetryConfig()

LLM_CONFIG = RetryConfig(
    max_retries=5,
    min_wait=2.0,
    max_wait=120.0,
    multiplier=2.0,
    jitter=True,
)

API_CONFIG = RetryConfig(
    max_retries=3,
    min_wait=1.0,
    max_wait=30.0,
    multiplier=2.0,
    jitter=True,
)


class LLMNoResponseError(Exception):
    """Error when LLM returns no response or empty response."""
    pass


class LLMRateLimitError(Exception):
    """Error when LLM rate limit is hit."""
    pass


class LLMContextWindowError(Exception):
    """Error when LLM context window is exceeded."""
    pass


def calculate_wait_time(
    attempt: int,
    min_wait: float,
    max_wait: float,
    multiplier: float,
    jitter: bool = True,
) -> float:
    """
    Calculate wait time for a retry attempt using exponential backoff.
    
    Args:
        attempt: Current attempt number (1-indexed)
        min_wait: Minimum wait time
        max_wait: Maximum wait time
        multiplier: Backoff multiplier
        jitter: Whether to add random jitter
        
    Returns:
        Wait time in seconds
    """
    wait = min(max_wait, min_wait * (multiplier ** (attempt - 1)))
    
    if jitter:
        # Add up to 25% random jitter
        jitter_range = wait * 0.25
        wait += random.uniform(-jitter_range, jitter_range)
    
    return max(0, wait)


if TENACITY_AVAILABLE:
    def create_retry_decorator(
        config: RetryConfig = None,
        on_retry: Callable[[int, Exception], None] = None,
    ) -> Callable:
        """
        Create a tenacity-based retry decorator.
        
        Args:
            config: Retry configuration
            on_retry: Callback function called on each retry
            
        Returns:
            Decorator function
        """
        config = config or DEFAULT_CONFIG
        
        def before_sleep(retry_state):
            """Called before each retry sleep."""
            exception = retry_state.outcome.exception()
            attempt = retry_state.attempt_number
            
            logger.warning(
                f"Retry attempt {attempt}/{config.max_retries} after error: {exception}"
            )
            
            if on_retry:
                on_retry(attempt, exception)
            
            # Handle LLMNoResponseError - increase temperature
            if isinstance(exception, LLMNoResponseError):
                if hasattr(retry_state, 'kwargs'):
                    current_temp = retry_state.kwargs.get('temperature', 0)
                    if current_temp == 0:
                        retry_state.kwargs['temperature'] = 1.0
                        logger.info("Increased temperature to 1.0 due to empty response")
        
        return retry(
            stop=stop_after_attempt(config.max_retries),
            wait=wait_exponential(
                multiplier=config.multiplier,
                min=config.min_wait,
                max=config.max_wait,
            ),
            retry=retry_if_exception_type(config.retry_exceptions),
            before_sleep=before_sleep,
            reraise=True,
        )
    
else:
    # Fallback simple retry implementation
    def create_retry_decorator(
        config: RetryConfig = None,
        on_retry: Callable[[int, Exception], None] = None,
    ) -> Callable:
        """
        Create a simple retry decorator (fallback when tenacity not available).
        """
        config = config or DEFAULT_CONFIG
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(1, config.max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except config.retry_exceptions as e:
                        last_exception = e
                        
                        if attempt < config.max_retries:
                            wait_time = calculate_wait_time(
                                attempt,
                                config.min_wait,
                                config.max_wait,
                                config.multiplier,
                                config.jitter,
                            )
                            
                            logger.warning(
                                f"Retry attempt {attempt}/{config.max_retries} "
                                f"after error: {e}. Waiting {wait_time:.1f}s"
                            )
                            
                            if on_retry:
                                on_retry(attempt, e)
                            
                            await asyncio.sleep(wait_time)
                
                raise last_exception
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                import time
                last_exception = None
                
                for attempt in range(1, config.max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except config.retry_exceptions as e:
                        last_exception = e
                        
                        if attempt < config.max_retries:
                            wait_time = calculate_wait_time(
                                attempt,
                                config.min_wait,
                                config.max_wait,
                                config.multiplier,
                                config.jitter,
                            )
                            
                            logger.warning(
                                f"Retry attempt {attempt}/{config.max_retries} "
                                f"after error: {e}. Waiting {wait_time:.1f}s"
                            )
                            
                            if on_retry:
                                on_retry(attempt, e)
                            
                            time.sleep(wait_time)
                
                raise last_exception
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator


def retry_on_exception(
    max_retries: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    min_wait: float = 1.0,
    max_wait: float = 60.0,
) -> Callable:
    """
    Convenience decorator for retrying on specific exceptions.
    
    Usage:
        @retry_on_exception(max_retries=3, exceptions=(ValueError, IOError))
        async def my_function():
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        min_wait=min_wait,
        max_wait=max_wait,
        retry_exceptions=exceptions,
    )
    return create_retry_decorator(config)


def retry_llm_call(
    max_retries: int = 5,
    on_retry: Callable[[int, Exception], None] = None,
) -> Callable:
    """
    Decorator specifically for LLM API calls.
    
    Handles common LLM errors:
    - Rate limiting
    - Empty responses
    - Timeout errors
    
    Usage:
        @retry_llm_call(max_retries=5)
        async def call_llm(prompt: str) -> str:
            ...
    """
    config = RetryConfig(
        max_retries=max_retries,
        min_wait=2.0,
        max_wait=120.0,
        multiplier=2.0,
        retry_exceptions=(
            LLMNoResponseError,
            LLMRateLimitError,
            TimeoutError,
            ConnectionError,
        ),
        jitter=True,
    )
    return create_retry_decorator(config, on_retry)


class RetryMixin:
    """
    Mixin class that adds retry capabilities to a class.
    
    Usage:
        class MyLLM(RetryMixin):
            async def completion(self, prompt):
                retry_decorator = self.create_retry()
                
                @retry_decorator
                async def _call():
                    return await self._raw_completion(prompt)
                
                return await _call()
    """
    
    def __init__(self, retry_config: RetryConfig = None):
        self._retry_config = retry_config or LLM_CONFIG
        self._retry_count = 0
        self._last_error: Optional[Exception] = None
    
    def create_retry(
        self,
        config: RetryConfig = None,
        on_retry: Callable[[int, Exception], None] = None,
    ) -> Callable:
        """Create a retry decorator with this instance's config."""
        config = config or self._retry_config
        
        def track_retry(attempt: int, error: Exception):
            self._retry_count += 1
            self._last_error = error
            if on_retry:
                on_retry(attempt, error)
        
        return create_retry_decorator(config, track_retry)
    
    @property
    def retry_count(self) -> int:
        """Get total retry count."""
        return self._retry_count
    
    @property
    def last_error(self) -> Optional[Exception]:
        """Get last error that triggered a retry."""
        return self._last_error
    
    def reset_retry_stats(self) -> None:
        """Reset retry statistics."""
        self._retry_count = 0
        self._last_error = None

