from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskLimits:
    max_risk_per_trade: float = 0.02
    max_daily_drawdown: float = 0.05
    max_position_fraction: float = 0.10


class RiskManager:
    def __init__(self, limits: Optional[RiskLimits] = None) -> None:
        self.limits = limits or RiskLimits()
        self.daily_peak_value: Optional[float] = None

    def approve(self, signal: str, price: float, portfolio_value: float) -> bool:
        if self.daily_peak_value is None:
            self.daily_peak_value = portfolio_value
        self.daily_peak_value = max(self.daily_peak_value, portfolio_value)
        drawdown = 1 - (portfolio_value / self.daily_peak_value)
        if drawdown >= self.limits.max_daily_drawdown:
            return False
        if signal == "HOLD":
            return False
        # Additional checks could be added here (exposure, VaR, correlation, etc.)
        return True

    def position_size(self, price: float, portfolio_value: float) -> float:
        risk_amount = portfolio_value * self.limits.max_risk_per_trade
        qty = max(risk_amount / price, 0.0)
        return qty
