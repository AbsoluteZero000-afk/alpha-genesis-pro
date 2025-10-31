"""Integration tests for the full trading system."""
import pytest
import asyncio
from datetime import datetime
from src.core.event_bus import EventBus
from src.core.events import Event, EventType
from src.execution.paper_broker import PaperBroker
from src.strategies.trend_following import TrendFollowingStrategy
from src.portfolio.manager import PortfolioManager
from src.monitoring.metrics import MetricsCollector
from src.monitoring.alerts import AlertManager, AlertLevel


class TestFullSystemIntegration:
    """Integration tests for the complete trading system."""
    
    @pytest.mark.asyncio
    async def test_event_bus_integration(self):
        """Test event bus integration."""
        event_bus = EventBus()
        
        # Publish an event
        test_event = Event(
            type=EventType.MARKET,
            data={"symbol": "AAPL", "price": 150.0}
        )
        
        event_bus.publish(test_event)
        
        # Consume the event
        received_event = await event_bus.next_event(timeout=1.0)
        
        assert received_event is not None
        assert received_event.type == EventType.MARKET
        assert received_event.data["symbol"] == "AAPL"
        
    def test_portfolio_broker_integration(self):
        """Test portfolio manager with paper broker integration."""
        portfolio = PortfolioManager(initial_cash=100000.0)
        broker = PaperBroker(cash=100000.0)
        
        # Execute trades through both systems
        portfolio.execute_trade("AAPL", "BUY", 100, 150.0, 5.0)
        broker.submit_order("AAPL", "BUY", 100, 150.0)
        
        # Check consistency
        portfolio_cash = portfolio.cash
        broker_cash = broker.state.cash
        
        # Should be similar (broker might have different fees)
        assert abs(portfolio_cash - broker_cash) < 1000  # Allow for fee differences
        
    @pytest.mark.asyncio
    async def test_metrics_alerts_integration(self):
        """Test metrics and alerts integration."""
        metrics = MetricsCollector()
        alerts = AlertManager()
        
        # Record a losing trade
        metrics.record_trade(
            strategy="test_strategy",
            symbol="AAPL",
            side="SELL",
            pnl=-500.0,
            execution_time=0.1
        )
        
        # This would trigger an alert in a real system
        await alerts.alert_trade_executed(
            symbol="AAPL",
            side="SELL",
            quantity=100,
            price=145.0,
            pnl=-500.0
        )
        
        # Check that alert was recorded
        recent_alerts = alerts.get_recent_alerts(hours=1)
        assert len(recent_alerts) > 0
        assert recent_alerts[-1].level == AlertLevel.WARNING  # Losing trade
        
    def test_strategy_portfolio_integration(self, sample_ohlcv_data):
        """Test strategy with portfolio integration."""
        portfolio = PortfolioManager(initial_cash=100000.0)
        strategy = TrendFollowingStrategy(fast=5, slow=10)
        
        # Process data and generate signals
        processed_data = strategy.calculate_indicators(sample_ohlcv_data.head(20))
        
        # Simulate trading based on signals
        for i in range(10, len(processed_data)):
            current_data = processed_data.iloc[:i+1]
            signal = strategy.generate_signal(current_data)
            price = float(processed_data.iloc[i]['close'])
            
            if signal == "BUY" and portfolio.cash > price * 100:
                try:
                    portfolio.execute_trade("TEST", "BUY", 100, price, 1.0)
                except ValueError:
                    pass  # Insufficient cash
                    
            elif signal == "SELL" and "TEST" in portfolio.positions:
                current_qty = portfolio.positions["TEST"].quantity
                if current_qty > 0:
                    try:
                        portfolio.execute_trade("TEST", "SELL", min(100, current_qty), price, 1.0)
                    except ValueError:
                        pass  # Insufficient shares
                        
        # Check that some trading occurred
        assert len(portfolio.trade_history) > 0
        
    @pytest.mark.asyncio
    async def test_complete_workflow(self, sample_ohlcv_data):
        """Test complete trading workflow integration."""
        # Initialize components
        event_bus = EventBus()
        portfolio = PortfolioManager(initial_cash=100000.0)
        broker = PaperBroker(cash=100000.0)
        strategy = TrendFollowingStrategy(fast=5, slow=15)
        metrics = MetricsCollector()
        
        # Process historical data
        data = sample_ohlcv_data.head(50)
        processed_data = strategy.calculate_indicators(data)
        
        trade_count = 0
        
        # Simulate live trading loop
        for i in range(20, len(processed_data)):
            current_data = processed_data.iloc[:i+1]
            signal = strategy.generate_signal(current_data)
            price = float(processed_data.iloc[i]['close'])
            
            # Publish market event
            market_event = Event(
                type=EventType.MARKET,
                data={"symbol": "TEST", "price": price, "timestamp": datetime.now()}
            )
            event_bus.publish(market_event)
            
            # Process signal
            if signal in ["BUY", "SELL"]:
                try:
                    if signal == "BUY" and portfolio.cash > price * 10:
                        trade = portfolio.execute_trade("TEST", "BUY", 10, price, 0.5)
                        broker_result = broker.submit_order("TEST", "BUY", 10, price)
                        trade_count += 1
                        
                        # Record metrics
                        metrics.record_trade(
                            strategy="trend_following",
                            symbol="TEST",
                            side="BUY",
                            pnl=0.0,  # No PnL on entry
                            execution_time=0.05
                        )
                        
                    elif signal == "SELL" and "TEST" in portfolio.positions:
                        position_qty = portfolio.positions["TEST"].quantity
                        if position_qty > 0:
                            sell_qty = min(10, position_qty)
                            trade = portfolio.execute_trade("TEST", "SELL", sell_qty, price, 0.5)
                            broker_result = broker.submit_order("TEST", "SELL", sell_qty, price)
                            trade_count += 1
                            
                            # Record metrics with PnL
                            pnl = trade.get("realized_pnl", 0.0)
                            metrics.record_trade(
                                strategy="trend_following",
                                symbol="TEST",
                                side="SELL",
                                pnl=pnl,
                                execution_time=0.05
                            )
                            
                except ValueError:
                    pass  # Insufficient funds/shares
                    
            # Update portfolio with current prices
            portfolio.update_prices({"TEST": price})
            metrics.update_portfolio_value(portfolio.get_total_value())
            
            # Consume and check events
            event = await event_bus.next_event(timeout=0.1)
            if event:
                assert event.type == EventType.MARKET
                assert event.data["symbol"] == "TEST"
                
        # Verify integration worked
        assert trade_count > 0, "No trades were executed"
        assert len(portfolio.trade_history) > 0
        assert metrics.trading_metrics.total_trades > 0
        
        # Check final portfolio state
        final_summary = portfolio.get_portfolio_summary()
        assert "total_value" in final_summary
        assert "total_pnl" in final_summary
        
        # Check metrics summary
        metrics_summary = metrics.get_trading_summary()
        assert metrics_summary["total_trades"] > 0