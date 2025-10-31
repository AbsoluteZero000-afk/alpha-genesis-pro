"""Unit tests for backtesting engine."""
import pytest
import pandas as pd
from src.backtesting.engine import BacktestEngine, performance_report
from src.strategies.trend_following import TrendFollowingStrategy
from src.execution.paper_broker import PaperBroker
from src.risk.risk_manager import RiskManager


class TestBacktestEngine:
    """Test suite for BacktestEngine."""
    
    def test_engine_initialization(self, sample_ohlcv_data, trend_strategy, paper_broker, risk_manager):
        """Test backtesting engine initialization."""
        engine = BacktestEngine(
            data=sample_ohlcv_data,
            strategies=[trend_strategy],
            broker=paper_broker,
            risk=risk_manager,
            symbol="TEST"
        )
        
        assert len(engine.strategies) == 1
        assert engine.symbol == "TEST"
        assert engine.broker == paper_broker
        assert engine.risk == risk_manager
        
    def test_backtest_run(self, sample_ohlcv_data, trend_strategy, paper_broker, risk_manager):
        """Test running a backtest."""
        # Use smaller dataset for faster testing
        small_data = sample_ohlcv_data.head(50)
        
        engine = BacktestEngine(
            data=small_data,
            strategies=[trend_strategy],
            broker=paper_broker,
            risk=risk_manager,
            symbol="TEST"
        )
        
        report = engine.run()
        
        # Check report structure
        assert "sharpe" in report
        assert "total_return" in report
        assert "max_drawdown" in report
        assert "final_equity" in report
        
        # Check that equity curve was recorded
        assert len(engine.equity_curve) > 0
        
    def test_performance_report_function(self):
        """Test the performance_report function."""
        # Create a simple equity curve
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        equity_values = [100000 + i * 100 for i in range(100)]  # Steady growth
        equity_series = pd.Series(equity_values, index=dates)
        
        report = performance_report(equity_series)
        
        assert "sharpe" in report
        assert "total_return" in report
        assert "max_drawdown" in report
        assert report["total_return"] > 0  # Should show positive return
        
    def test_multiple_strategies(self, sample_ohlcv_data, trend_strategy, mean_reversion_strategy, paper_broker, risk_manager):
        """Test backtesting with multiple strategies."""
        small_data = sample_ohlcv_data.head(30)
        
        engine = BacktestEngine(
            data=small_data,
            strategies=[trend_strategy, mean_reversion_strategy],
            broker=paper_broker,
            risk=risk_manager,
            symbol="TEST"
        )
        
        report = engine.run()
        assert isinstance(report, dict)
        assert "final_equity" in report