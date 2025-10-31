"""Binance data provider using CCXT."""
from __future__ import annotations
import asyncio
from typing import AsyncIterator, Dict, Any, Optional
import pandas as pd
from loguru import logger
import ccxt.pro as ccxt
from .base import BaseDataProvider
from ...config import get_settings


class BinanceProvider(BaseDataProvider):
    """Binance data provider using CCXT Pro."""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self.exchange: Optional[ccxt.binance] = None
        
    async def _get_exchange(self) -> ccxt.binance:
        """Get or create exchange instance."""
        if self.exchange is None:
            self.exchange = ccxt.binance({
                'apiKey': self.settings.BINANCE_API_KEY,
                'secret': self.settings.BINANCE_SECRET_KEY,
                'sandbox': self.settings.BINANCE_TESTNET,
                'enableRateLimit': True,
            })
            await self.exchange.load_markets()
        return self.exchange
        
    async def get_historical_data(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical OHLCV data from Binance."""
        try:
            exchange = await self._get_exchange()
            
            # Convert timeframe
            timeframe_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", 
                "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w"
            }
            tf = timeframe_map.get(interval, "1d")
            
            # Convert dates to timestamps
            since = int(pd.to_datetime(start).timestamp() * 1000)
            until = int(pd.to_datetime(end).timestamp() * 1000)
            
            ohlcv = await exchange.fetch_ohlcv(symbol, tf, since, limit=1000)
            
            if not ohlcv:
                logger.warning(f"No OHLCV data returned for {symbol}")
                return pd.DataFrame()
                
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            # Filter by end date
            df = df[df.index <= pd.to_datetime(end)]
            
            logger.info(f"Retrieved {len(df)} bars for {symbol} from Binance")
            return df
            
        except Exception as e:
            logger.error(f"Failed to get Binance historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_realtime_data(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream real-time ticker data from Binance."""
        try:
            exchange = await self._get_exchange()
            
            while True:
                ticker = await exchange.watch_ticker(symbol)
                yield {
                    "symbol": ticker['symbol'],
                    "price": float(ticker['last']),
                    "bid": float(ticker['bid']) if ticker['bid'] else None,
                    "ask": float(ticker['ask']) if ticker['ask'] else None,
                    "volume": float(ticker['baseVolume']),
                    "timestamp": pd.to_datetime(ticker['timestamp'], unit='ms')
                }
                
        except Exception as e:
            logger.error(f"Binance WebSocket error: {e}")
            
    async def close(self) -> None:
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()