"""Prometheus-compatible metrics collection."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from loguru import logger


@dataclass
class TradingMetrics:
    """Trading performance metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_volume: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    last_updated: float = field(default_factory=time.time)
    
    @property
    def win_rate(self) -> float:
        return self.winning_trades / max(1, self.total_trades)
        
    @property
    def average_pnl_per_trade(self) -> float:
        return self.total_pnl / max(1, self.total_trades)


class MetricsCollector:
    """Collects and exposes trading metrics for Prometheus."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None) -> None:
        self.registry = registry or CollectorRegistry()
        self.trading_metrics = TradingMetrics()
        
        # Prometheus metrics
        self.trade_counter = Counter(
            'trading_trades_total',
            'Total number of trades executed',
            ['strategy', 'symbol', 'side', 'status'],
            registry=self.registry
        )
        
        self.pnl_histogram = Histogram(
            'trading_pnl_dollars',
            'Profit and loss per trade in dollars',
            ['strategy', 'symbol'],
            registry=self.registry
        )
        
        self.execution_latency = Histogram(
            'trading_execution_latency_seconds',
            'Time from signal to execution',
            ['strategy', 'symbol'],
            registry=self.registry
        )
        
        self.portfolio_value = Gauge(
            'trading_portfolio_value_dollars',
            'Current portfolio value in dollars',
            registry=self.registry
        )
        
        self.open_positions = Gauge(
            'trading_open_positions',
            'Number of open positions',
            ['symbol'],
            registry=self.registry
        )
        
        self.drawdown_gauge = Gauge(
            'trading_drawdown_percent',
            'Current drawdown as percentage',
            registry=self.registry
        )
        
        self.system_health = Gauge(
            'trading_system_health',
            'System health status (1=healthy, 0=unhealthy)',
            ['component'],
            registry=self.registry
        )
        
    def record_trade(
        self,
        strategy: str,
        symbol: str,
        side: str,
        pnl: float,
        execution_time: float
    ) -> None:
        """Record a completed trade."""
        status = 'win' if pnl > 0 else 'loss'
        
        # Update Prometheus metrics
        self.trade_counter.labels(
            strategy=strategy,
            symbol=symbol,
            side=side,
            status=status
        ).inc()
        
        self.pnl_histogram.labels(
            strategy=strategy,
            symbol=symbol
        ).observe(pnl)
        
        self.execution_latency.labels(
            strategy=strategy,
            symbol=symbol
        ).observe(execution_time)
        
        # Update internal metrics
        self.trading_metrics.total_trades += 1
        self.trading_metrics.total_pnl += pnl
        
        if pnl > 0:
            self.trading_metrics.winning_trades += 1
        else:
            self.trading_metrics.losing_trades += 1
            
        self.trading_metrics.last_updated = time.time()
        
        logger.info(
            f"Trade recorded: {strategy} {side} {symbol} PnL=${pnl:.2f} "
            f"in {execution_time:.3f}s"
        )
        
    def update_portfolio_value(self, value: float) -> None:
        """Update current portfolio value."""
        self.portfolio_value.set(value)
        
    def update_positions(self, positions: Dict[str, float]) -> None:
        """Update open positions."""
        # Clear existing position metrics
        self.open_positions.clear()
        
        # Set current positions
        for symbol, quantity in positions.items():
            if quantity != 0:
                self.open_positions.labels(symbol=symbol).set(abs(quantity))
                
    def update_drawdown(self, drawdown_pct: float) -> None:
        """Update current drawdown percentage."""
        self.drawdown_gauge.set(drawdown_pct)
        self.trading_metrics.max_drawdown = max(
            self.trading_metrics.max_drawdown, drawdown_pct
        )
        
    def update_system_health(self, component: str, is_healthy: bool) -> None:
        """Update system health status."""
        self.system_health.labels(component=component).set(1 if is_healthy else 0)
        
    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format."""
        return generate_latest(self.registry).decode('utf-8')
        
    def get_trading_summary(self) -> Dict[str, Any]:
        """Get human-readable trading summary."""
        return {
            "total_trades": self.trading_metrics.total_trades,
            "win_rate": round(self.trading_metrics.win_rate * 100, 2),
            "total_pnl": round(self.trading_metrics.total_pnl, 2),
            "average_pnl_per_trade": round(self.trading_metrics.average_pnl_per_trade, 2),
            "max_drawdown": round(self.trading_metrics.max_drawdown, 2),
            "last_updated": self.trading_metrics.last_updated
        }