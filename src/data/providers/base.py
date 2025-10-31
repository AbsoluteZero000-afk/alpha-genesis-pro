"""Base data provider interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any
import pandas as pd


class BaseDataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @abstractmethod
    async def get_historical_data(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data."""
        
    @abstractmethod
    async def get_realtime_data(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream realtime price updates."""
        
    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""