from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from ..strategies.base import BaseStrategy
from ..execution.paper_broker import PaperBroker
from ..risk.risk_manager import RiskManager


def performance_report(equity_curve: pd.Series) -> Dict[str, Any]:
    returns = equity_curve.pct_change().dropna()
    sharpe = np.sqrt(252) * returns.mean() / (returns.std() + 1e-12)
    cumulative = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    roll_max = equity_curve.cummax()
    dd = (equity_curve / roll_max - 1)
    max_dd = dd.min()
    return {"sharpe": float(sharpe), "total_return": float(cumulative), "max_drawdown": float(max_dd)}


class BacktestEngine:
    def __init__(self, data: pd.DataFrame, strategies: List[BaseStrategy], broker: PaperBroker, risk: RiskManager, symbol: str = "SPY") -> None:
        self.data = data.copy()
        self.strategies = strategies
        self.broker = broker
        self.risk = risk
        self.symbol = symbol
        self.equity_curve: List[float] = []

    def run(self) -> Dict[str, Any]:
        df = self.data.copy()
        for strat in self.strategies:
            df = strat.calculate_indicators(df)

        cash = self.broker.state.cash
        pos = 0.0
        equity = cash
        self.equity_curve.append(equity)

        for idx in range(1, len(df)):
            price = float(df.iloc[idx]["close"])
            # Aggregate signals (simple majority)
            signals = [s.generate_signal(df.iloc[: idx + 1]) for s in self.strategies]
            action = max(set(signals), key=signals.count)

            portfolio_value = self.broker.state.cash + pos * price
            if self.risk.approve(action, price, portfolio_value):
                if action == "BUY":
                    qty = self.risk.position_size(price, portfolio_value)
                    fill = self.broker.submit_order(self.symbol, "BUY", qty, price)
                    pos += qty
                elif action == "SELL" and pos > 0:
                    fill = self.broker.submit_order(self.symbol, "SELL", pos, price)
                    pos = 0.0

            equity = self.broker.state.cash + pos * price
            self.equity_curve.append(equity)

        eq_series = pd.Series(self.equity_curve, index=df.index[: len(self.equity_curve)])
        report = performance_report(eq_series)
        report["final_equity"] = float(eq_series.iloc[-1])
        return report
