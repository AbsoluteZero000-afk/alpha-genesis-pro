"""Pytest configuration and fixtures."""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.portfolio.manager import PortfolioManager
from src.execution.paper_broker import PaperBroker
from src.risk.risk_manager import RiskManager, RiskLimits
from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.mean_reversion import MeanReversionStrategy


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    n_days = len(dates)
    
    # Generate realistic price data
    price = 100.0
    prices = []
    
    for i in range(n_days):
        # Random walk with slight upward bias
        change = np.random.normal(0.001, 0.02)  # 0.1% drift, 2% volatility
        price *= (1 + change)
        prices.append(price)
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': [np.random.randint(100000, 1000000) for _ in range(n_days)]
    }, index=dates)
    
    return df


@pytest.fixture
def portfolio_manager():
    """Create a test portfolio manager."""
    return PortfolioManager(initial_cash=100_000.0)


@pytest.fixture
def paper_broker():
    """Create a test paper broker."""
    return PaperBroker(cash=100_000.0, commission=0.001, slippage_bps=2.0)


@pytest.fixture
def risk_manager():
    """Create a test risk manager."""
    limits = RiskLimits(
        max_risk_per_trade=0.02,
        max_daily_drawdown=0.05,
        max_position_fraction=0.10
    )
    return RiskManager(limits)


@pytest.fixture
def trend_strategy():
    """Create a trend following strategy."""
    return TrendFollowingStrategy(fast=10, slow=20)


@pytest.fixture
def mean_reversion_strategy():
    """Create a mean reversion strategy."""
    return MeanReversionStrategy(rsi_length=14, low=30, high=70)


# Add numpy import for fixtures
import numpy as np