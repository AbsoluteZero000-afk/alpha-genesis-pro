"""Data caching using Redis."""
from __future__ import annotations
import pickle
from typing import Any, Optional
import pandas as pd
from loguru import logger
import redis.asyncio as redis
from ..config import get_settings


class DataCache:
    """Redis-based cache for market data."""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        
    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                self.settings.REDIS_URL,
                decode_responses=False  # We need bytes for pickle
            )
        return self.redis_client
        
    async def get(self, key: str) -> Optional[pd.DataFrame]:
        """Get cached DataFrame."""
        try:
            client = await self._get_client()
            data = await client.get(key)
            if data is not None:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
        return None
        
    async def set(self, key: str, data: pd.DataFrame, ttl: int = 3600) -> None:
        """Cache DataFrame with TTL."""
        try:
            client = await self._get_client()
            serialized = pickle.dumps(data)
            await client.setex(key, ttl, serialized)
            logger.debug(f"Cached {key} for {ttl}s")
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()