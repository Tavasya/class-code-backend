"""
Shared HTTP client module for connection pooling and concurrency control.

This module provides:
1. A shared aiohttp ClientSession for connection pooling
2. A semaphore to limit concurrent API requests and prevent bursts

References:
- https://docs.cloud.google.com/run/docs/configuring/networking-best-practices
- https://docs.aiohttp.org/en/stable/http_request_lifecycle.html
- https://cookbook.openai.com/examples/how_to_handle_rate_limits
"""

import asyncio
import aiohttp
import logging
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Module-level shared session
_shared_session: Optional[aiohttp.ClientSession] = None
_session_lock = asyncio.Lock()

# Module-level semaphore for concurrency control
_api_semaphore: Optional[asyncio.Semaphore] = None

# Configuration for the shared session
SESSION_CONFIG = {
    "total_timeout": 60,      # Total request timeout in seconds
    "connect_timeout": 10,    # Connection timeout in seconds
    "pool_limit": 100,        # Total connection pool limit
    "pool_limit_per_host": 50, # Per-host connection limit (e.g., OpenAI API)
    "dns_cache_ttl": 300,     # DNS cache TTL in seconds
    "keepalive_timeout": 30,  # Keep-alive timeout in seconds
}

# Concurrency control configuration
CONCURRENCY_CONFIG = {
    "max_concurrent_requests": 30,  # Max concurrent API requests per instance
}


async def get_shared_session() -> aiohttp.ClientSession:
    """
    Get or create a shared aiohttp ClientSession.

    This function is thread-safe and will create a new session if one doesn't
    exist or if the existing session is closed.

    Returns:
        aiohttp.ClientSession: A shared session for making HTTP requests
    """
    global _shared_session

    async with _session_lock:
        if _shared_session is None or _shared_session.closed:
            logger.info("Creating new shared aiohttp ClientSession")

            # Create connector with connection pooling
            connector = aiohttp.TCPConnector(
                limit=SESSION_CONFIG["pool_limit"],
                limit_per_host=SESSION_CONFIG["pool_limit_per_host"],
                ttl_dns_cache=SESSION_CONFIG["dns_cache_ttl"],
                use_dns_cache=True,
                keepalive_timeout=SESSION_CONFIG["keepalive_timeout"],
            )

            # Create timeout configuration
            timeout = aiohttp.ClientTimeout(
                total=SESSION_CONFIG["total_timeout"],
                connect=SESSION_CONFIG["connect_timeout"],
            )

            # Create the session
            _shared_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
            )

            logger.info(
                f"Shared session created with pool_limit={SESSION_CONFIG['pool_limit']}, "
                f"pool_limit_per_host={SESSION_CONFIG['pool_limit_per_host']}"
            )

    return _shared_session


async def close_shared_session() -> None:
    """
    Close the shared aiohttp ClientSession.

    This should be called during application shutdown to properly clean up
    resources and close all connections in the pool.
    """
    global _shared_session

    async with _session_lock:
        if _shared_session is not None and not _shared_session.closed:
            logger.info("Closing shared aiohttp ClientSession")
            await _shared_session.close()
            _shared_session = None
            logger.info("Shared session closed successfully")


async def reset_shared_session() -> None:
    """
    Reset the shared session by closing and recreating it.

    This can be useful if the session gets into a bad state or after
    encountering connection errors.
    """
    global _shared_session

    async with _session_lock:
        if _shared_session is not None and not _shared_session.closed:
            logger.info("Resetting shared aiohttp ClientSession")
            await _shared_session.close()
            _shared_session = None

    # Recreate the session
    await get_shared_session()
    logger.info("Shared session reset complete")


def get_api_semaphore() -> asyncio.Semaphore:
    """
    Get or create the API semaphore for concurrency control.

    The semaphore limits the number of concurrent API requests to prevent
    bursts that can overwhelm the API or cause connection errors.

    Returns:
        asyncio.Semaphore: A semaphore for rate limiting API requests
    """
    global _api_semaphore

    if _api_semaphore is None:
        max_concurrent = CONCURRENCY_CONFIG["max_concurrent_requests"]
        _api_semaphore = asyncio.Semaphore(max_concurrent)
        logger.info(f"Created API semaphore with max_concurrent_requests={max_concurrent}")

    return _api_semaphore


@asynccontextmanager
async def rate_limited_request():
    """
    Context manager for rate-limited API requests.

    Usage:
        async with rate_limited_request():
            session = await get_shared_session()
            async with session.post(url, ...) as response:
                ...

    This ensures that no more than max_concurrent_requests are in-flight
    at any time, preventing API bursts and connection errors.
    """
    semaphore = get_api_semaphore()
    async with semaphore:
        yield
