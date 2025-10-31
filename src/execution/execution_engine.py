"""High-performance execution engine with smart routing."""
from __future__ import annotations
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
from .order_manager import OrderManager, Order, OrderType
from .brokers.base import BaseBroker
from ..core.events import Event, EventType
from ..core.event_bus import EventBus


@dataclass
class ExecutionRequest:
    """Request for order execution."""
    symbol: str
    side: str
    quantity: float
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    max_slippage_bps: float = 10.0  # Max 10 bps slippage
    time_limit_seconds: float = 300.0  # 5 minute time limit
    

class ExecutionEngine:
    """Advanced execution engine with smart routing and slippage control."""
    
    def __init__(self, broker: BaseBroker, event_bus: EventBus) -> None:
        self.broker = broker
        self.event_bus = event_bus
        self.order_manager = OrderManager(broker)
        self.active_executions: Dict[str, ExecutionRequest] = {}
        
    async def execute_order(self, request: ExecutionRequest) -> Optional[Order]:
        """Execute order with smart routing and slippage control."""
        logger.info(f"Executing {request.side} {request.quantity} {request.symbol}")
        
        try:
            # For market orders, get current price to check slippage
            if request.order_type == OrderType.MARKET:
                current_price = await self._get_current_price(request.symbol)
                if current_price and request.price:
                    slippage_bps = abs(current_price - request.price) / request.price * 10000
                    if slippage_bps > request.max_slippage_bps:
                        logger.warning(
                            f"Slippage {slippage_bps:.1f}bps exceeds limit {request.max_slippage_bps}bps"
                        )
                        # Convert to limit order at acceptable price
                        acceptable_price = self._calculate_acceptable_price(
                            request.price, request.side, request.max_slippage_bps
                        )
                        request.order_type = OrderType.LIMIT
                        request.price = acceptable_price
                        
            # Submit order through order manager
            order = await self.order_manager.submit_order(
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                order_type=request.order_type,
                price=request.price
            )
            
            # Publish execution event
            await self._publish_execution_event(order)
            
            # Start monitoring if needed
            if not order.is_complete:
                self.active_executions[order.order_id] = request
                asyncio.create_task(self._monitor_execution(order, request))
                
            return order
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return None
            
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol."""
        try:
            portfolio = await self.broker.get_portfolio()
            # This is a simplified implementation
            # In practice, you'd fetch current bid/ask from market data
            return None  # Placeholder
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None
            
    def _calculate_acceptable_price(
        self, reference_price: float, side: str, max_slippage_bps: float
    ) -> float:
        """Calculate acceptable execution price within slippage limits."""
        slippage_amount = reference_price * (max_slippage_bps / 10000)
        
        if side.upper() == "BUY":
            return reference_price + slippage_amount  # Pay up to slippage more
        else:
            return reference_price - slippage_amount  # Accept slippage less
            
    async def _monitor_execution(self, order: Order, request: ExecutionRequest) -> None:
        """Monitor order execution and handle timeouts."""
        start_time = asyncio.get_event_loop().time()
        
        while not order.is_complete:
            await asyncio.sleep(1.0)
            
            # Update order status
            await self.order_manager.update_order_status(order.order_id)
            
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > request.time_limit_seconds:
                logger.warning(f"Order {order.order_id} timed out, attempting cancel")
                await self.order_manager.cancel_order(order.order_id)
                break
                
        # Clean up
        self.active_executions.pop(order.order_id, None)
        await self._publish_execution_event(order)
        
    async def _publish_execution_event(self, order: Order) -> None:
        """Publish execution event to event bus."""
        try:
            event = Event(
                type=EventType.FILL if order.is_complete else EventType.ORDER,
                data={
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": order.quantity,
                    "filled_quantity": order.filled_quantity,
                    "status": order.status,
                    "average_price": order.average_fill_price
                }
            )
            self.event_bus.publish(event)
        except Exception as e:
            logger.error(f"Failed to publish execution event: {e}")
            
    async def cancel_all_orders(self) -> List[str]:
        """Cancel all active orders."""
        cancelled_orders = []
        open_orders = await self.order_manager.get_open_orders()
        
        for order in open_orders:
            success = await self.order_manager.cancel_order(order.order_id)
            if success:
                cancelled_orders.append(order.order_id)
                
        logger.info(f"Cancelled {len(cancelled_orders)} orders")
        return cancelled_orders
        
    async def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution performance statistics."""
        open_orders = await self.order_manager.get_open_orders()
        all_orders = list(self.order_manager.orders.values())
        
        filled_orders = [o for o in all_orders if o.status == "filled"]
        avg_fill_time = 0.0  # Would calculate based on timestamps
        
        return {
            "total_orders": len(all_orders),
            "open_orders": len(open_orders),
            "filled_orders": len(filled_orders),
            "fill_rate": len(filled_orders) / max(1, len(all_orders)),
            "average_fill_time_seconds": avg_fill_time
        }
        
    async def close(self) -> None:
        """Clean up resources."""
        await self.broker.close()