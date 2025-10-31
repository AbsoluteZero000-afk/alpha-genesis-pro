from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class PortfolioState:
    cash: float
    positions: Dict[str, float]


class PaperBroker:
    """Simulated broker with slippage and commission."""

    def __init__(self, cash: float = 100_000.0, commission: float = 0.0005, slippage_bps: float = 1.0) -> None:
        self.state = PortfolioState(cash=cash, positions={})
        self.commission = commission
        self.slippage_bps = slippage_bps

    def get_portfolio(self) -> Dict[str, Any]:
        return {"cash": self.state.cash, "positions": self.state.positions.copy()}

    def submit_order(self, symbol: str, side: str, qty: float, price: float) -> Dict[str, Any]:
        slip = price * (self.slippage_bps / 10_000.0)
        fill_price = price + slip if side == "BUY" else price - slip
        cost = qty * fill_price
        fee = abs(cost) * self.commission
        if side == "BUY":
            self.state.cash -= cost + fee
            self.state.positions[symbol] = self.state.positions.get(symbol, 0.0) + qty
        else:
            self.state.cash += abs(cost) - fee
            self.state.positions[symbol] = self.state.positions.get(symbol, 0.0) - qty
        return {"symbol": symbol, "side": side, "qty": qty, "price": fill_price, "fee": fee}
