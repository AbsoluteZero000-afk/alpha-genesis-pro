"""Unit tests for trading strategies."""
import pytest
import pandas as pd
import numpy as np
from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.mean_reversion import MeanReversionStrategy


class TestTrendFollowingStrategy:
    """Test suite for trend following strategy."""
    
    def test_strategy_initialization(self):
        """Test strategy initialization with parameters."""
        strategy = TrendFollowingStrategy(fast=5, slow=20)
        assert strategy.params['fast'] == 5
        assert strategy.params['slow'] == 20
        assert strategy.name == 'trend_following_sma'
        
    def test_calculate_indicators(self, sample_ohlcv_data):
        """Test indicator calculation."""
        strategy = TrendFollowingStrategy(fast=10, slow=20)
        result = strategy.calculate_indicators(sample_ohlcv_data)
        
        # Check that indicators are added
        assert 'sma_10' in result.columns
        assert 'sma_20' in result.columns
        assert 'signal_cross' in result.columns
        
        # Check that SMAs are calculated correctly
        expected_sma_10 = sample_ohlcv_data['close'].rolling(10).mean()
        pd.testing.assert_series_equal(result['sma_10'], expected_sma_10, check_names=False)
        
    def test_generate_signal_buy(self):
        """Test BUY signal generation."""
        strategy = TrendFollowingStrategy(fast=2, slow=5)
        
        # Create data where fast SMA crosses above slow SMA
        data = pd.DataFrame({
            'close': [10, 11, 12, 13, 14, 15, 16],
            'sma_2': [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16],
            'sma_5': [10, 10.5, 11, 11.5, 12, 12.5, 13],
            'signal_cross': [0, 0, 0, 0, 0, 1, 0]  # Cross up on index 5
        })
        
        signal = strategy.generate_signal(data)
        assert signal == "BUY"
        
    def test_generate_signal_sell(self):
        """Test SELL signal generation."""
        strategy = TrendFollowingStrategy(fast=2, slow=5)
        
        data = pd.DataFrame({
            'close': [16, 15, 14, 13, 12, 11, 10],
            'sma_2': [15.5, 14.5, 13.5, 12.5, 11.5, 10.5, 9.5],
            'sma_5': [15, 14.5, 14, 13.5, 13, 12.5, 12],
            'signal_cross': [0, 0, 0, 0, 0, -1, 0]  # Cross down on index 5
        })
        
        signal = strategy.generate_signal(data)
        assert signal == "SELL"
        
    def test_generate_signal_hold(self):
        """Test HOLD signal generation."""
        strategy = TrendFollowingStrategy(fast=2, slow=5)
        
        data = pd.DataFrame({
            'close': [10, 10, 10, 10, 10],
            'sma_2': [10, 10, 10, 10, 10],
            'sma_5': [10, 10, 10, 10, 10],
            'signal_cross': [0, 0, 0, 0, 0]  # No cross
        })
        
        signal = strategy.generate_signal(data)
        assert signal == "HOLD"


class TestMeanReversionStrategy:
    """Test suite for mean reversion strategy."""
    
    def test_strategy_initialization(self):
        """Test strategy initialization."""
        strategy = MeanReversionStrategy(rsi_length=10, low=25, high=75)
        assert strategy.params['rsi_length'] == 10
        assert strategy.params['low'] == 25
        assert strategy.params['high'] == 75
        assert strategy.name == 'mean_reversion_rsi'
        
    def test_calculate_indicators(self, sample_ohlcv_data):
        """Test RSI calculation."""
        strategy = MeanReversionStrategy(rsi_length=14, low=30, high=70)
        result = strategy.calculate_indicators(sample_ohlcv_data)
        
        assert 'rsi' in result.columns
        assert not result['rsi'].isna().all()  # RSI should have valid values
        
    def test_generate_signal_buy_oversold(self):
        """Test BUY signal when RSI is oversold."""
        strategy = MeanReversionStrategy(rsi_length=14, low=30, high=70)
        
        data = pd.DataFrame({
            'close': [100],
            'rsi': [25]  # Oversold
        })
        
        signal = strategy.generate_signal(data)
        assert signal == "BUY"
        
    def test_generate_signal_sell_overbought(self):
        """Test SELL signal when RSI is overbought."""
        strategy = MeanReversionStrategy(rsi_length=14, low=30, high=70)
        
        data = pd.DataFrame({
            'close': [100],
            'rsi': [75]  # Overbought
        })
        
        signal = strategy.generate_signal(data)
        assert signal == "SELL"
        
    def test_generate_signal_hold_neutral(self):
        """Test HOLD signal when RSI is neutral."""
        strategy = MeanReversionStrategy(rsi_length=14, low=30, high=70)
        
        data = pd.DataFrame({
            'close': [100],
            'rsi': [50]  # Neutral
        })
        
        signal = strategy.generate_signal(data)
        assert signal == "HOLD"