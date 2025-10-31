"""Advanced performance and risk analytics."""
from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from .manager import PortfolioManager


@dataclass
class RiskMetrics:
    """Risk measurement results."""
    value_at_risk_95: float
    value_at_risk_99: float
    expected_shortfall_95: float
    expected_shortfall_99: float
    max_drawdown: float
    max_drawdown_duration: int
    volatility_annual: float
    beta: Optional[float] = None
    correlation_with_market: Optional[float] = None
    

class PerformanceAnalytics:
    """Comprehensive performance and risk analytics."""
    
    def __init__(self, portfolio: PortfolioManager) -> None:
        self.portfolio = portfolio
        
    def calculate_returns(self, period: str = "daily") -> pd.Series:
        """Calculate portfolio returns over time."""
        equity_df = self.portfolio.get_equity_curve_df()
        
        if equity_df.empty:
            return pd.Series()
            
        # Resample based on period
        if period == "daily":
            equity_resampled = equity_df['total_equity'].resample('D').last().dropna()
        elif period == "hourly":
            equity_resampled = equity_df['total_equity'].resample('H').last().dropna()
        else:
            equity_resampled = equity_df['total_equity']
            
        returns = equity_resampled.pct_change().dropna()
        return returns
        
    def calculate_sharpe_ratio(
        self, risk_free_rate: float = 0.02, period: str = "daily"
    ) -> float:
        """Calculate Sharpe ratio."""
        returns = self.calculate_returns(period)
        
        if returns.empty or returns.std() == 0:
            return 0.0
            
        # Adjust risk-free rate for period
        periods_per_year = {"daily": 252, "hourly": 252 * 24}[period]
        rf_period = risk_free_rate / periods_per_year
        
        excess_returns = returns - rf_period
        sharpe = excess_returns.mean() / returns.std()
        
        # Annualize
        return sharpe * np.sqrt(periods_per_year)
        
    def calculate_sortino_ratio(
        self, risk_free_rate: float = 0.02, period: str = "daily"
    ) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        returns = self.calculate_returns(period)
        
        if returns.empty:
            return 0.0
            
        periods_per_year = {"daily": 252, "hourly": 252 * 24}[period]
        rf_period = risk_free_rate / periods_per_year
        
        excess_returns = returns - rf_period
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return float('inf') if excess_returns.mean() > 0 else 0.0
            
        sortino = excess_returns.mean() / downside_returns.std()
        return sortino * np.sqrt(periods_per_year)
        
    def calculate_calmar_ratio(self) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)."""
        total_return = self.portfolio.get_total_return_percent() / 100
        equity_df = self.portfolio.get_equity_curve_df()
        
        if equity_df.empty:
            return 0.0
            
        # Annualize return
        days_elapsed = (datetime.now() - equity_df.index[0]).days
        if days_elapsed < 1:
            return 0.0
            
        annual_return = (1 + total_return) ** (365.25 / days_elapsed) - 1
        
        # Calculate max drawdown
        equity_series = equity_df['total_equity']
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak
        max_drawdown = abs(drawdown.min())
        
        if max_drawdown == 0:
            return float('inf') if annual_return > 0 else 0.0
            
        return annual_return / max_drawdown
        
    def calculate_maximum_drawdown(self) -> Tuple[float, int, datetime, datetime]:
        """Calculate maximum drawdown and its duration."""
        equity_df = self.portfolio.get_equity_curve_df()
        
        if equity_df.empty:
            return 0.0, 0, datetime.now(), datetime.now()
            
        equity_series = equity_df['total_equity']
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak
        
        # Find maximum drawdown
        max_dd_idx = drawdown.idxmin()
        max_dd_value = abs(drawdown.min())
        
        # Find drawdown period
        peak_before_dd = peak.loc[:max_dd_idx].idxmax()
        
        # Find recovery (if any)
        recovery_idx = None
        for idx in equity_series.loc[max_dd_idx:].index:
            if equity_series.loc[idx] >= peak.loc[peak_before_dd]:
                recovery_idx = idx
                break
                
        if recovery_idx is None:
            recovery_idx = equity_series.index[-1]
            
        dd_duration = (recovery_idx - peak_before_dd).days
        
        return max_dd_value, dd_duration, peak_before_dd, recovery_idx
        
    def calculate_risk_metrics(
        self, confidence_levels: Tuple[float, float] = (0.95, 0.99)
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics."""
        returns = self.calculate_returns()
        
        if returns.empty:
            return RiskMetrics(
                value_at_risk_95=0.0,
                value_at_risk_99=0.0,
                expected_shortfall_95=0.0,
                expected_shortfall_99=0.0,
                max_drawdown=0.0,
                max_drawdown_duration=0,
                volatility_annual=0.0
            )
            
        # Value at Risk
        var_95 = np.percentile(returns, (1 - confidence_levels[0]) * 100)
        var_99 = np.percentile(returns, (1 - confidence_levels[1]) * 100)
        
        # Expected Shortfall (Conditional VaR)
        es_95 = returns[returns <= var_95].mean()
        es_99 = returns[returns <= var_99].mean()
        
        # Maximum Drawdown
        max_dd, dd_duration, _, _ = self.calculate_maximum_drawdown()
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252)
        
        return RiskMetrics(
            value_at_risk_95=abs(var_95),
            value_at_risk_99=abs(var_99),
            expected_shortfall_95=abs(es_95) if not np.isnan(es_95) else 0.0,
            expected_shortfall_99=abs(es_99) if not np.isnan(es_99) else 0.0,
            max_drawdown=max_dd,
            max_drawdown_duration=dd_duration,
            volatility_annual=volatility
        )
        
    def calculate_win_rate(self) -> Dict[str, Any]:
        """Calculate win rate and trade statistics."""
        trades_df = self.portfolio.get_trades_df()
        
        if trades_df.empty:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "profit_factor": 0.0
            }
            
        # Only consider trades with realized P&L (sells)
        completed_trades = trades_df[trades_df['realized_pnl'].notna()]
        
        if completed_trades.empty:
            return {"total_trades": 0, "win_rate": 0.0}
            
        total_trades = len(completed_trades)
        winning_trades = len(completed_trades[completed_trades['realized_pnl'] > 0])
        losing_trades = len(completed_trades[completed_trades['realized_pnl'] < 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        wins = completed_trades[completed_trades['realized_pnl'] > 0]['realized_pnl']
        losses = completed_trades[completed_trades['realized_pnl'] < 0]['realized_pnl']
        
        avg_win = wins.mean() if not wins.empty else 0.0
        avg_loss = abs(losses.mean()) if not losses.empty else 0.0
        
        # Profit factor = gross profits / gross losses
        gross_profits = wins.sum() if not wins.empty else 0.0
        gross_losses = abs(losses.sum()) if not losses.empty else 0.0
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf')
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate * 100, 2),
            "average_win": round(avg_win, 2),
            "average_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2)
        }
        
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        portfolio_summary = self.portfolio.get_portfolio_summary()
        risk_metrics = self.calculate_risk_metrics()
        win_rate_stats = self.calculate_win_rate()
        
        return {
            "portfolio_summary": portfolio_summary,
            "performance_ratios": {
                "sharpe_ratio": round(self.calculate_sharpe_ratio(), 3),
                "sortino_ratio": round(self.calculate_sortino_ratio(), 3),
                "calmar_ratio": round(self.calculate_calmar_ratio(), 3)
            },
            "risk_metrics": {
                "max_drawdown_percent": round(risk_metrics.max_drawdown * 100, 2),
                "max_drawdown_duration_days": risk_metrics.max_drawdown_duration,
                "annual_volatility_percent": round(risk_metrics.volatility_annual * 100, 2),
                "var_95_percent": round(risk_metrics.value_at_risk_95 * 100, 2),
                "var_99_percent": round(risk_metrics.value_at_risk_99 * 100, 2),
                "expected_shortfall_95": round(risk_metrics.expected_shortfall_95 * 100, 2),
                "expected_shortfall_99": round(risk_metrics.expected_shortfall_99 * 100, 2)
            },
            "trade_statistics": win_rate_stats,
            "report_timestamp": datetime.now().isoformat()
        }
        
    def export_detailed_analysis(self, filename: Optional[str] = None) -> str:
        """Export detailed analysis to file."""
        report = self.generate_performance_report()
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"portfolio_analysis_{timestamp}.json"
            
        import json
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Performance analysis exported to {filename}")
        return filename