"""Unified data feed for historical and live data."""
from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, AsyncIterator
import pandas as pd
from loguru import logger
from .providers.base import BaseDataProvider
from .providers import YahooFinanceProvider, AlpacaProvider, BinanceProvider
from .cache import DataCache


class DataFeed:
    """Unified interface for market data from multiple providers."""
    
    def __init__(self, provider_name: str = "yahoo", cache: Optional[DataCache] = None) -> None:
        self.provider_name = provider_name
        self.cache = cache or DataCache()
        self.provider: Optional[BaseDataProvider] = None
        self._initialize_provider()
        
    def _initialize_provider(self) -> None:
        """Initialize the data provider."""
        providers = {
            "yahoo": YahooFinanceProvider,
            "alpaca": AlpacaProvider,
            "binance": BinanceProvider
        }
        
        provider_class = providers.get(self.provider_name)
        if provider_class is None:
            raise ValueError(f"Unknown provider: {self.provider_name}")
            
        self.provider = provider_class()
        logger.info(f"Initialized {self.provider_name} data provider")
        
    async def get_historical_data(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical data with caching."""
        if self.provider is None:
            raise RuntimeError("Provider not initialized")
            
        # Check cache first
        cache_key = f"{symbol}_{start}_{end}_{interval}"
        cached_data = await self.cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Retrieved {symbol} from cache")
            return cached_data
            
        # Fetch from provider
        data = await self.provider.get_historical_data(symbol, start, end, interval)
        
        # Cache the result
        if not data.empty:
            await self.cache.set(cache_key, data, ttl=3600)  # 1 hour TTL
            
        return data
        
    async def get_realtime_data(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream real-time data."""
        if self.provider is None:
            raise RuntimeError("Provider not initialized")
            
        async for data in self.provider.get_realtime_data(symbol):
            yield data
            
    async def close(self) -> None:
        """Clean up resources."""
        if self.provider:
            await self.provider.close()
        await self.cache.close()