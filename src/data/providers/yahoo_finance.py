"""Yahoo Finance data provider."""
from __future__ import annotations
import asyncio
from typing import AsyncIterator, Dict, Any
import pandas as pd
import yfinance as yf
from loguru import logger
from .base import BaseDataProvider


class YahooFinanceProvider(BaseDataProvider):
    """Yahoo Finance data provider for historical data."""
    
    def __init__(self) -> None:
        self.session = None
        
    async def get_historical_data(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical data from Yahoo Finance."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, lambda: yf.download(symbol, start=start, end=end, interval=interval)
            )
            
            # Normalize column names
            data.columns = [col.lower().replace(' ', '_') for col in data.columns]
            if 'adj_close' in data.columns:
                data = data.drop('adj_close', axis=1)
                
            logger.info(f"Retrieved {len(data)} bars for {symbol} from Yahoo Finance")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_realtime_data(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        """Yahoo Finance doesn't provide real-time streaming. Simulate with periodic polling."""
        while True:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info
                yield {
                    "symbol": symbol,
                    "price": float(info.last_price),
                    "timestamp": pd.Timestamp.now(),
                    "volume": float(info.last_volume or 0)
                }
                await asyncio.sleep(60)  # Poll every minute
            except Exception as e:
                logger.error(f"Error getting realtime data for {symbol}: {e}")
                await asyncio.sleep(5)
                
    async def close(self) -> None:
        """No cleanup needed for Yahoo Finance."""
        pass