"""Alpaca live trading broker implementation."""
from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional
import aiohttp
from loguru import logger
from .base import BaseBroker
from ...config import get_settings


class AlpacaBroker(BaseBroker):
    """Alpaca live trading broker."""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = self.settings.ALPACA_BASE_URL or "https://paper-api.alpaca.markets"
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with auth headers."""
        if self.session is None or self.session.closed:
            headers = {
                "APCA-API-KEY-ID": self.settings.ALPACA_API_KEY or "",
                "APCA-API-SECRET-KEY": self.settings.ALPACA_SECRET_KEY or "",
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
        
    async def get_portfolio(self) -> Dict[str, Any]:
        """Get account and positions from Alpaca."""
        try:
            session = await self._get_session()
            
            # Get account info
            async with session.get(f"{self.base_url}/v2/account") as response:
                if response.status != 200:
                    logger.error(f"Failed to get account: {response.status}")
                    return {"cash": 0.0, "positions": {}}
                account = await response.json()
                
            # Get positions
            async with session.get(f"{self.base_url}/v2/positions") as response:
                positions_data = await response.json() if response.status == 200 else []
                
            positions = {}
            for pos in positions_data:
                positions[pos["symbol"]] = float(pos["qty"])
                
            return {
                "cash": float(account["cash"]),
                "buying_power": float(account["buying_power"]),
                "portfolio_value": float(account["portfolio_value"]),
                "positions": positions
            }
            
        except Exception as e:
            logger.error(f"Error getting Alpaca portfolio: {e}")
            return {"cash": 0.0, "positions": {}}
            
    async def submit_order(
        self, symbol: str, side: str, qty: float, price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Submit order to Alpaca."""
        try:
            session = await self._get_session()
            
            order_data = {
                "symbol": symbol,
                "qty": str(qty),
                "side": side.lower(),
                "type": "market" if price is None else "limit",
                "time_in_force": "day"
            }
            
            if price is not None:
                order_data["limit_price"] = str(price)
                
            async with session.post(
                f"{self.base_url}/v2/orders", json=order_data
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    logger.error(f"Order submission failed: {response.status} - {error_text}")
                    return {"error": error_text}
                    
                order_response = await response.json()
                logger.info(f"Submitted {side} order for {qty} {symbol}")
                return order_response
                
        except Exception as e:
            logger.error(f"Error submitting Alpaca order: {e}")
            return {"error": str(e)}
            
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        try:
            session = await self._get_session()
            async with session.delete(f"{self.base_url}/v2/orders/{order_id}") as response:
                success = response.status == 204
                if success:
                    logger.info(f"Cancelled order {order_id}")
                else:
                    logger.error(f"Failed to cancel order {order_id}: {response.status}")
                return success
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
            
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/v2/orders/{order_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get order status: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {}
            
    async def close(self) -> None:
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()