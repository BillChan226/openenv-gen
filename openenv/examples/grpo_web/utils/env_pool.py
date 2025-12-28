"""
Environment Pool for Managing Multiple BrowserGym Servers

This module provides a centralized pool for managing environment server
connections, ensuring no conflicts between training rollouts and evaluation.

The pool uses a semaphore-based approach to limit concurrent connections
to the number of available servers, preventing "Server at capacity" errors.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional


class EnvironmentPool:
    """
    Shared pool of environment servers for both training and evaluation.

    This pool ensures that:
    - With 1 server: tasks run sequentially (no conflicts)
    - With N servers: up to N tasks run concurrently
    - Both training rollouts and evaluation share the same pool

    Example usage:
        pool = EnvironmentPool(["http://localhost:8005", "http://localhost:8006"])

        async with pool.acquire() as server_url:
            # Use server_url for a task
            result = await play_web_task(server_url=server_url, ...)
    """

    def __init__(self, server_urls: List[str]):
        """
        Initialize the environment pool.

        Args:
            server_urls: List of BrowserGym server URLs
        """
        if not server_urls:
            raise ValueError("server_urls must contain at least one URL")

        self.server_urls = list(server_urls)
        self._num_servers = len(server_urls)

        # Semaphore limits concurrent usage to number of servers
        self._semaphore = asyncio.Semaphore(self._num_servers)

        # Queue of available server URLs
        self._available: asyncio.Queue[str] = asyncio.Queue()
        for url in server_urls:
            self._available.put_nowait(url)

        # Track active connections for debugging
        self._active_count = 0
        self._lock = asyncio.Lock()

    @property
    def capacity(self) -> int:
        """Total number of servers in the pool."""
        return self._num_servers

    @property
    def active_count(self) -> int:
        """Number of currently active connections."""
        return self._active_count

    @property
    def available_count(self) -> int:
        """Number of currently available servers."""
        return self._num_servers - self._active_count

    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None):
        """
        Acquire a server from the pool.

        This is a context manager that automatically releases the server
        when the context exits.

        Args:
            timeout: Maximum time to wait for an available server (seconds).
                     Default is None (wait indefinitely). With a single server
                     and many tasks, waiting indefinitely is usually correct
                     since tasks are queued and will eventually be served.

        Yields:
            str: The acquired server URL

        Raises:
            asyncio.TimeoutError: If no server becomes available within timeout

        Example:
            async with pool.acquire() as server_url:
                env = BrowserGymEnv(base_url=server_url)
                # ... use env ...
        """
        # Wait for a slot in the semaphore
        if timeout is not None:
            try:
                await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError(
                    f"No environment server available after {timeout}s. "
                    f"Pool has {self._num_servers} servers, {self._active_count} active."
                )
        else:
            # Wait indefinitely - this is the normal case for queued tasks
            await self._semaphore.acquire()

        # Get an available server URL
        server_url = await self._available.get()

        async with self._lock:
            self._active_count += 1

        try:
            yield server_url
        finally:
            # Return server to the pool
            async with self._lock:
                self._active_count -= 1
            await self._available.put(server_url)
            self._semaphore.release()

    async def acquire_batch(
        self,
        count: int,
        timeout: Optional[float] = None
    ) -> List[str]:
        """
        Acquire multiple servers for batch processing.

        This method acquires up to `count` servers, but will only acquire
        as many as are available (up to pool capacity).

        Args:
            count: Number of servers to acquire
            timeout: Maximum time to wait for servers (None = wait indefinitely)

        Returns:
            List of acquired server URLs

        Note:
            Caller MUST call release_batch() when done with the servers.
        """
        # Can only acquire up to pool capacity
        actual_count = min(count, self._num_servers)
        servers = []

        for _ in range(actual_count):
            try:
                if timeout is not None:
                    await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
                else:
                    await self._semaphore.acquire()
                server_url = await self._available.get()
                async with self._lock:
                    self._active_count += 1
                servers.append(server_url)
            except asyncio.TimeoutError:
                # Release any servers we already acquired
                await self.release_batch(servers)
                raise asyncio.TimeoutError(
                    f"Could not acquire {actual_count} servers within {timeout}s"
                )

        return servers

    async def release_batch(self, servers: List[str]) -> None:
        """
        Release a batch of servers back to the pool.

        Args:
            servers: List of server URLs to release
        """
        for server_url in servers:
            async with self._lock:
                self._active_count -= 1
            await self._available.put(server_url)
            self._semaphore.release()

    def __repr__(self) -> str:
        return (
            f"EnvironmentPool(servers={self._num_servers}, "
            f"active={self._active_count}, "
            f"available={self.available_count})"
        )


def create_pool_from_config(web_env_cfg: dict) -> EnvironmentPool:
    """
    Create an EnvironmentPool from web_env configuration.

    Supports both single server_url and multiple server_urls.

    Args:
        web_env_cfg: The web_env section of the config

    Returns:
        EnvironmentPool instance

    Example config (single server):
        web_env:
          server_url: "http://localhost:8005"

    Example config (multiple servers):
        web_env:
          server_urls:
            - "http://localhost:8005"
            - "http://localhost:8006"
            - "http://localhost:8007"
    """
    # Check for server_urls list first (preferred)
    server_urls = web_env_cfg.get("server_urls", None)

    if server_urls is not None:
        # Convert OmegaConf list to Python list if needed
        if hasattr(server_urls, '__iter__') and not isinstance(server_urls, str):
            server_urls = list(server_urls)
        else:
            raise ValueError("server_urls must be a list of URLs")
    else:
        # Fall back to single server_url
        server_url = web_env_cfg.get("server_url", "http://localhost:8005")
        server_urls = [server_url]

    return EnvironmentPool(server_urls)
