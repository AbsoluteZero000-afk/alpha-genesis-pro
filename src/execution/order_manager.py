"""Advanced order management system."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
from .brokers.base import BaseBroker


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


@dataclass
class Order:
    """Order representation."""
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    order_id: Optional[str] = None
    broker_order_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    fees: float = 0.0
    
    @property
    def is_complete(self) -> bool:
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]
        
    @property
    def remaining_quantity(self) -> float:
        return max(0.0, self.quantity - self.filled_quantity)


class OrderManager:
    """Manages order lifecycle and execution."""
    
    def __init__(self, broker: BaseBroker) -> None:
        self.broker = broker
        self.orders: Dict[str, Order] = {}
        self._order_counter = 0
        self._running = False
        
    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        self._order_counter += 1
        return f"order_{self._order_counter}_{int(datetime.now().timestamp())}"
        
    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Order:
        """Submit new order."""
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            order_id=self._generate_order_id()
        )
        
        try:
            # Submit to broker
            result = await self.broker.submit_order(
                symbol=symbol,
                side=side,
                qty=quantity,
                price=price
            )
            
            if "error" in result:
                order.status = OrderStatus.REJECTED
                logger.error(f"Order rejected: {result['error']}")
            else:
                order.status = OrderStatus.SUBMITTED
                order.broker_order_id = result.get("id", result.get("clientOrderId"))
                logger.info(f"Order submitted: {order.order_id}")
                
        except Exception as e:
            order.status = OrderStatus.REJECTED
            logger.error(f"Failed to submit order: {e}")
            
        self.orders[order.order_id] = order
        return order
        
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        order = self.orders.get(order_id)
        if not order or order.is_complete:
            return False
            
        try:
            if hasattr(self.broker, 'cancel_order'):
                success = await self.broker.cancel_order(order.broker_order_id or order_id)
                if success:
                    order.status = OrderStatus.CANCELLED
                    logger.info(f"Order cancelled: {order_id}")
                return success
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            
        return False
        
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)
        
    async def get_open_orders(self) -> List[Order]:
        """Get all open orders."""
        return [order for order in self.orders.values() if not order.is_complete]
        
    async def update_order_status(self, order_id: str) -> bool:
        """Update order status from broker."""
        order = self.orders.get(order_id)
        if not order or not order.broker_order_id:
            return False
            
        try:
            if hasattr(self.broker, 'get_order_status'):
                broker_order = await self.broker.get_order_status(order.broker_order_id)
                if broker_order:
                    # Update order status based on broker response
                    status_map = {
                        "new": OrderStatus.SUBMITTED,
                        "partially_filled": OrderStatus.PARTIALLY_FILLED,
                        "filled": OrderStatus.FILLED,
                        "cancelled": OrderStatus.CANCELLED,
                        "rejected": OrderStatus.REJECTED
                    }
                    order.status = status_map.get(
                        broker_order.get("status", "unknown").lower(),
                        order.status
                    )
                    
                    # Update fill information
                    order.filled_quantity = float(broker_order.get("filled_qty", 0))
                    order.average_fill_price = float(broker_order.get("filled_avg_price", 0))
                    
                return True
        except Exception as e:
            logger.error(f"Failed to update order status for {order_id}: {e}")
            
        return False
        
    async def start_monitoring(self, interval: float = 1.0) -> None:
        """Start monitoring order status updates."""
        self._running = True
        while self._running:
            open_orders = await self.get_open_orders()
            for order in open_orders:
                await self.update_order_status(order.order_id)
            await asyncio.sleep(interval)
            
    def stop_monitoring(self) -> None:
        """Stop order monitoring."""
        self._running = False