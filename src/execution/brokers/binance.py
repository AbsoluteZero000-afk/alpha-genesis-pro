"""Binance live trading broker implementation."""
from __future__ import annotations
from typing import Dict, Any, Optional
import ccxt.pro as ccxt
from loguru import logger
from .base import BaseBroker
from ...config import get_settings


class BinanceBroker(BaseBroker):
    """Binance live trading broker using CCXT."""
    
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
        
    async def get_portfolio(self) -> Dict[str, Any]:
        """Get account balance and positions."""
        try:
            exchange = await self._get_exchange()
            balance = await exchange.fetch_balance()
            
            positions = {}
            for symbol, amount in balance.get('total', {}).items():
                if amount > 0:
                    positions[symbol] = float(amount)
                    
            return {
                "cash": float(balance.get('USDT', {}).get('free', 0)),
                "positions": positions,
                "total_balance": float(balance.get('info', {}).get('totalWalletBalance', 0))
            }
            
        except Exception as e:
            logger.error(f"Error getting Binance portfolio: {e}")
            return {"cash": 0.0, "positions": {}}
            
    async def submit_order(
        self, symbol: str, side: str, qty: float, price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Submit order to Binance."""
        try:
            exchange = await self._get_exchange()
            
            order_type = 'market' if price is None else 'limit'
            order = await exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side.lower(),
                amount=qty,
                price=price
            )
            
            logger.info(f"Submitted {side} {order_type} order for {qty} {symbol}")
            return order
            
        except Exception as e:
            logger.error(f"Error submitting Binance order: {e}")
            return {"error": str(e)}
            
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        try:
            exchange = await self._get_exchange()
            await exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled order {order_id} for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
            
    async def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order status."""
        try:
            exchange = await self._get_exchange()
            order = await exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {}
            
    async def close(self) -> None:
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()