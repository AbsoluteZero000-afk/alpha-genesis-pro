"""Alpaca data and trading provider."""
from __future__ import annotations
import asyncio
from typing import AsyncIterator, Dict, Any, Optional
import pandas as pd
from loguru import logger
import aiohttp
import json
from datetime import datetime
from .base import BaseDataProvider
from ...config import get_settings


class AlpacaProvider(BaseDataProvider):
    """Alpaca data provider with WebSocket support."""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_session: Optional[aiohttp.ClientSession] = None
        self.base_url = self.settings.ALPACA_BASE_URL or "https://paper-api.alpaca.markets"
        self.data_url = "https://data.alpaca.markets"
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            headers = {
                "APCA-API-KEY-ID": self.settings.ALPACA_API_KEY or "",
                "APCA-API-SECRET-KEY": self.settings.ALPACA_SECRET_KEY or ""
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
        
    async def get_historical_data(
        self, symbol: str, start: str, end: str, interval: str = "1Day"
    ) -> pd.DataFrame:
        """Get historical bars from Alpaca."""
        try:
            session = await self._get_session()
            url = f"{self.data_url}/v2/stocks/{symbol}/bars"
            params = {
                "start": start,
                "end": end,
                "timeframe": interval,
                "asof": None,
                "feed": "iex",
                "page_token": None,
                "limit": 10000
            }
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Alpaca API error: {response.status}")
                    return pd.DataFrame()
                    
                data = await response.json()
                bars = data.get("bars", [])
                
                if not bars:
                    logger.warning(f"No bars returned for {symbol}")
                    return pd.DataFrame()
                
                # Convert to DataFrame
                df = pd.DataFrame(bars)
                df['timestamp'] = pd.to_datetime(df['t'])
                df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
                df = df.set_index('timestamp')
                df = df[['open', 'high', 'low', 'close', 'volume']]
                
                logger.info(f"Retrieved {len(df)} bars for {symbol} from Alpaca")
                return df
                
        except Exception as e:
            logger.error(f"Failed to get Alpaca historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_realtime_data(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream real-time data from Alpaca WebSocket."""
        import websockets
        import ssl
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        uri = "wss://stream.data.alpaca.markets/v2/iex"
        
        try:
            async with websockets.connect(uri, ssl=ssl_context) as websocket:
                # Authenticate
                auth_msg = {
                    "action": "auth",
                    "key": self.settings.ALPACA_API_KEY,
                    "secret": self.settings.ALPACA_SECRET_KEY
                }
                await websocket.send(json.dumps(auth_msg))
                
                # Subscribe to trades
                sub_msg = {
                    "action": "subscribe",
                    "trades": [symbol]
                }
                await websocket.send(json.dumps(sub_msg))
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        for trade in data.get("trades", []):
                            yield {
                                "symbol": trade["S"],
                                "price": float(trade["p"]),
                                "size": int(trade["s"]),
                                "timestamp": pd.to_datetime(trade["t"]),
                                "exchange": trade.get("x", "")
                            }
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Alpaca WebSocket error: {e}")
            
    async def close(self) -> None:
        """Close HTTP sessions."""
        if self.session and not self.session.closed:
            await self.session.close()
        if self.ws_session and not self.ws_session.closed:
            await self.ws_session.close()