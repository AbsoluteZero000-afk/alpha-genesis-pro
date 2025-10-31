"""Advanced portfolio management with P&L tracking."""
from __future__ import annotations
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger


@dataclass
class Position:
    """Individual position tracking."""
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    entry_time: datetime = field(default_factory=datetime.now)
    realized_pnl: float = 0.0
    fees: float = 0.0
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
        
    @property
    def cost_basis(self) -> float:
        return abs(self.quantity) * self.average_price
        
    @property
    def unrealized_pnl(self) -> float:
        if self.quantity == 0:
            return 0.0
        return (self.current_price - self.average_price) * self.quantity
        
    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl
        
    @property
    def pnl_percent(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.total_pnl / self.cost_basis) * 100
        
    def update_price(self, new_price: float) -> None:
        """Update current market price."""
        self.current_price = new_price
        
    def add_shares(self, quantity: float, price: float, fee: float = 0.0) -> None:
        """Add shares to position (buy)."""
        if self.quantity == 0:
            self.average_price = price
            self.quantity = quantity
        else:
            total_cost = (self.quantity * self.average_price) + (quantity * price)
            self.quantity += quantity
            if self.quantity != 0:
                self.average_price = total_cost / abs(self.quantity)
                
        self.fees += fee
        
    def reduce_shares(self, quantity: float, price: float, fee: float = 0.0) -> float:
        """Reduce shares from position (sell). Returns realized P&L."""
        if abs(quantity) > abs(self.quantity):
            raise ValueError("Cannot sell more shares than owned")
            
        # Calculate realized P&L
        pnl = (price - self.average_price) * quantity
        self.realized_pnl += pnl
        
        # Update position
        self.quantity -= quantity
        self.fees += fee
        
        if abs(self.quantity) < 1e-6:  # Close position if near zero
            self.quantity = 0.0
            
        return pnl


class PortfolioManager:
    """Comprehensive portfolio management and tracking."""
    
    def __init__(self, initial_cash: float = 100_000.0) -> None:
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self._last_update = datetime.now()
        
    def execute_trade(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        quantity: float,
        price: float,
        fee: float = 0.0,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Execute a trade and update portfolio."""
        timestamp = timestamp or datetime.now()
        trade_value = quantity * price
        
        # Record trade
        trade_record = {
            "timestamp": timestamp,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "value": trade_value,
            "fee": fee,
            "cash_before": self.cash
        }
        
        if side.upper() == "BUY":
            # Check if we have enough cash
            total_cost = trade_value + fee
            if total_cost > self.cash:
                raise ValueError(f"Insufficient cash: need ${total_cost:.2f}, have ${self.cash:.2f}")
                
            self.cash -= total_cost
            
            # Add to position
            if symbol not in self.positions:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=0,
                    average_price=0,
                    current_price=price,
                    entry_time=timestamp
                )
                
            self.positions[symbol].add_shares(quantity, price, fee)
            
        elif side.upper() == "SELL":
            if symbol not in self.positions or self.positions[symbol].quantity < quantity:
                raise ValueError(f"Insufficient shares to sell: {symbol}")
                
            # Reduce position and get realized P&L
            realized_pnl = self.positions[symbol].reduce_shares(quantity, price, fee)
            self.cash += trade_value - fee
            
            trade_record["realized_pnl"] = realized_pnl
            
            # Remove position if closed
            if self.positions[symbol].quantity == 0:
                del self.positions[symbol]
                
        trade_record["cash_after"] = self.cash
        self.trade_history.append(trade_record)
        
        logger.info(
            f"Trade executed: {side} {quantity} {symbol} @ ${price:.2f} "
            f"(fee: ${fee:.2f}, cash: ${self.cash:.2f})"
        )
        
        return trade_record
        
    def update_prices(self, prices: Dict[str, float]) -> None:
        """Update current market prices for all positions."""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)
                
        # Record equity snapshot
        self._record_equity_snapshot()
        
    def _record_equity_snapshot(self) -> None:
        """Record current portfolio equity for curve tracking."""
        snapshot = {
            "timestamp": datetime.now(),
            "cash": self.cash,
            "positions_value": sum(pos.market_value for pos in self.positions.values()),
            "total_equity": self.get_total_value(),
            "unrealized_pnl": self.get_unrealized_pnl(),
            "realized_pnl": self.get_realized_pnl()
        }
        self.equity_curve.append(snapshot)
        
    def get_total_value(self) -> float:
        """Get total portfolio value."""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value
        
    def get_unrealized_pnl(self) -> float:
        """Get total unrealized P&L."""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
        
    def get_realized_pnl(self) -> float:
        """Get total realized P&L from all trades."""
        return sum(pos.realized_pnl for pos in self.positions.values())
        
    def get_total_pnl(self) -> float:
        """Get total P&L (realized + unrealized)."""
        return self.get_realized_pnl() + self.get_unrealized_pnl()
        
    def get_total_return_percent(self) -> float:
        """Get total return as percentage of initial capital."""
        return (self.get_total_pnl() / self.initial_cash) * 100
        
    def get_positions_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all positions."""
        summary = {}
        total_value = self.get_total_value()
        
        for symbol, position in self.positions.items():
            weight = (position.market_value / total_value) * 100 if total_value > 0 else 0
            
            summary[symbol] = {
                "quantity": position.quantity,
                "avg_price": round(position.average_price, 2),
                "current_price": round(position.current_price, 2),
                "market_value": round(position.market_value, 2),
                "unrealized_pnl": round(position.unrealized_pnl, 2),
                "pnl_percent": round(position.pnl_percent, 2),
                "weight_percent": round(weight, 2),
                "entry_time": position.entry_time.isoformat()
            }
            
        return summary
        
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        return {
            "cash": round(self.cash, 2),
            "positions_value": round(sum(pos.market_value for pos in self.positions.values()), 2),
            "total_value": round(self.get_total_value(), 2),
            "unrealized_pnl": round(self.get_unrealized_pnl(), 2),
            "realized_pnl": round(self.get_realized_pnl(), 2),
            "total_pnl": round(self.get_total_pnl(), 2),
            "total_return_percent": round(self.get_total_return_percent(), 2),
            "number_of_positions": len(self.positions),
            "total_trades": len(self.trade_history),
            "initial_cash": self.initial_cash
        }
        
    def get_equity_curve_df(self) -> pd.DataFrame:
        """Get equity curve as pandas DataFrame."""
        if not self.equity_curve:
            return pd.DataFrame()
            
        df = pd.DataFrame(self.equity_curve)
        df.set_index('timestamp', inplace=True)
        return df
        
    def get_trades_df(self) -> pd.DataFrame:
        """Get trade history as pandas DataFrame."""
        if not self.trade_history:
            return pd.DataFrame()
            
        df = pd.DataFrame(self.trade_history)
        df.set_index('timestamp', inplace=True)
        return df
        
    def export_portfolio_data(self) -> Dict[str, Any]:
        """Export all portfolio data for persistence or analysis."""
        return {
            "initial_cash": self.initial_cash,
            "current_cash": self.cash,
            "positions": {symbol: {
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "average_price": pos.average_price,
                "current_price": pos.current_price,
                "entry_time": pos.entry_time.isoformat(),
                "realized_pnl": pos.realized_pnl,
                "fees": pos.fees
            } for symbol, pos in self.positions.items()},
            "trade_history": self.trade_history,
            "equity_curve": self.equity_curve
        }