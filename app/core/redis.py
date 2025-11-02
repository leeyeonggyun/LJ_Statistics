import redis.asyncio as redis
import json
import logging
from typing import Any, Optional
from app.core.settings import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await _redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None

    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    try:
        client = await get_redis()
        if client is None:
            return None

        value = await client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Cache get error for key {key}: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    try:
        client = await get_redis()
        if client is None:
            return False

        json_value = json.dumps(value, ensure_ascii=False, default=str)
        await client.setex(key, ttl, json_value)
        return True
    except Exception as e:
        logger.error(f"Cache set error for key {key}: {e}")
        return False


async def cache_delete(key: str) -> bool:
    try:
        client = await get_redis()
        if client is None:
            return False

        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error for key {key}: {e}")
        return False


async def cache_clear_pattern(pattern: str) -> int:
    try:
        client = await get_redis()
        if client is None:
            return 0

        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            return await client.delete(*keys)
        return 0
    except Exception as e:
        logger.error(f"Cache clear pattern error for {pattern}: {e}")
        return 0
