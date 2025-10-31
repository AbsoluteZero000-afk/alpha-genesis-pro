"""Unit tests for portfolio management."""
import pytest
from datetime import datetime
from src.portfolio.manager import PortfolioManager, Position
from src.portfolio.analytics import PerformanceAnalytics


class TestPosition:
    """Test suite for Position class."""
    
    def test_position_initialization(self):
        """Test position initialization."""
        pos = Position(
            symbol="AAPL",
            quantity=100,
            average_price=150.0,
            current_price=155.0
        )
        
        assert pos.symbol == "AAPL"
        assert pos.quantity == 100
        assert pos.average_price == 150.0
        assert pos.current_price == 155.0
        
    def test_position_market_value(self):
        """Test market value calculation."""
        pos = Position("AAPL", 100, 150.0, 155.0)
        assert pos.market_value == 15500.0  # 100 * 155.0
        
    def test_position_unrealized_pnl(self):
        """Test unrealized P&L calculation."""
        pos = Position("AAPL", 100, 150.0, 155.0)
        assert pos.unrealized_pnl == 500.0  # (155 - 150) * 100
        
    def test_position_add_shares(self):
        """Test adding shares to position."""
        pos = Position("AAPL", 100, 150.0, 155.0)
        pos.add_shares(50, 160.0, 5.0)
        
        assert pos.quantity == 150
        # Average price should be weighted: (100*150 + 50*160) / 150 = 153.33
        assert abs(pos.average_price - 153.33) < 0.01
        assert pos.fees == 5.0
        
    def test_position_reduce_shares(self):
        """Test reducing shares from position."""
        pos = Position("AAPL", 100, 150.0, 160.0)
        realized_pnl = pos.reduce_shares(50, 160.0, 2.0)
        
        assert pos.quantity == 50
        assert realized_pnl == 500.0  # (160 - 150) * 50
        assert pos.realized_pnl == 500.0
        assert pos.fees == 2.0


class TestPortfolioManager:
    """Test suite for PortfolioManager."""
    
    def test_portfolio_initialization(self):
        """Test portfolio initialization."""
        portfolio = PortfolioManager(initial_cash=50000.0)
        assert portfolio.initial_cash == 50000.0
        assert portfolio.cash == 50000.0
        assert len(portfolio.positions) == 0
        assert len(portfolio.trade_history) == 0
        
    def test_execute_buy_trade(self, portfolio_manager):
        """Test executing a buy trade."""
        trade = portfolio_manager.execute_trade(
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0,
            fee=10.0
        )
        
        assert trade["symbol"] == "AAPL"
        assert trade["side"] == "BUY"
        assert trade["quantity"] == 100
        assert trade["price"] == 150.0
        assert trade["fee"] == 10.0
        
        # Check portfolio state
        assert portfolio_manager.cash == 100000 - 15000 - 10  # Initial - cost - fee
        assert "AAPL" in portfolio_manager.positions
        assert portfolio_manager.positions["AAPL"].quantity == 100
        
    def test_execute_sell_trade(self, portfolio_manager):
        """Test executing a sell trade."""
        # First buy some shares
        portfolio_manager.execute_trade("AAPL", "BUY", 100, 150.0, 5.0)
        
        # Then sell half
        trade = portfolio_manager.execute_trade(
            symbol="AAPL",
            side="SELL",
            quantity=50,
            price=160.0,
            fee=5.0
        )
        
        assert "realized_pnl" in trade
        assert trade["realized_pnl"] == 500.0  # (160 - 150) * 50
        
        # Check position
        assert portfolio_manager.positions["AAPL"].quantity == 50
        
    def test_insufficient_cash_error(self, portfolio_manager):
        """Test error when insufficient cash for trade."""
        with pytest.raises(ValueError, match="Insufficient cash"):
            portfolio_manager.execute_trade("AAPL", "BUY", 1000, 150.0, 0.0)
            
    def test_insufficient_shares_error(self, portfolio_manager):
        """Test error when insufficient shares for sale."""
        with pytest.raises(ValueError, match="Insufficient shares"):
            portfolio_manager.execute_trade("AAPL", "SELL", 100, 150.0, 0.0)
            
    def test_get_total_value(self, portfolio_manager):
        """Test total portfolio value calculation."""
        # Buy some shares
        portfolio_manager.execute_trade("AAPL", "BUY", 100, 150.0, 10.0)
        
        # Update prices
        portfolio_manager.update_prices({"AAPL": 160.0})
        
        expected_value = portfolio_manager.cash + (100 * 160.0)
        assert abs(portfolio_manager.get_total_value() - expected_value) < 0.01
        
    def test_portfolio_summary(self, portfolio_manager):
        """Test portfolio summary generation."""
        # Execute some trades
        portfolio_manager.execute_trade("AAPL", "BUY", 100, 150.0, 10.0)
        portfolio_manager.execute_trade("GOOGL", "BUY", 50, 2000.0, 20.0)
        
        summary = portfolio_manager.get_portfolio_summary()
        
        assert "cash" in summary
        assert "total_value" in summary
        assert "number_of_positions" in summary
        assert summary["number_of_positions"] == 2
        assert summary["total_trades"] == 2


class TestPerformanceAnalytics:
    """Test suite for PerformanceAnalytics."""
    
    def test_analytics_initialization(self, portfolio_manager):
        """Test analytics initialization."""
        analytics = PerformanceAnalytics(portfolio_manager)
        assert analytics.portfolio == portfolio_manager
        
    def test_sharpe_ratio_calculation(self, portfolio_manager):
        """Test Sharpe ratio calculation."""
        analytics = PerformanceAnalytics(portfolio_manager)
        
        # With empty portfolio, should return 0
        sharpe = analytics.calculate_sharpe_ratio()
        assert sharpe == 0.0
        
    def test_performance_report_generation(self, portfolio_manager):
        """Test performance report generation."""
        analytics = PerformanceAnalytics(portfolio_manager)
        report = analytics.generate_performance_report()
        
        assert "portfolio_summary" in report
        assert "performance_ratios" in report
        assert "risk_metrics" in report
        assert "trade_statistics" in report
        assert "report_timestamp" in report