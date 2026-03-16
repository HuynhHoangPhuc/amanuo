"""Shared ARQ Redis connection pool — initialized once in app lifespan."""

import logging
from arq.connections import ArqRedis, RedisSettings, create_pool

logger = logging.getLogger(__name__)

_pool: ArqRedis | None = None


async def init_redis(redis_url: str) -> ArqRedis:
    """Initialize the Redis connection pool. Raises on connection failure."""
    global _pool
    _pool = await create_pool(RedisSettings.from_dsn(redis_url))
    return _pool


async def get_redis() -> ArqRedis | None:
    """Return the current Redis pool, or None if not initialized."""
    return _pool


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
        logger.info("Redis connection closed")
