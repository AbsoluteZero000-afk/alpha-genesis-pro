"""Portfolio rebalancing engine."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from loguru import logger
from .manager import PortfolioManager


@dataclass
class RebalanceRule:
    """Portfolio rebalancing rule configuration."""
    name: str
    target_weights: Dict[str, float]  # symbol -> weight (0.0 to 1.0)
    tolerance: float = 0.05  # 5% tolerance before rebalancing
    min_trade_value: float = 100.0  # Minimum trade value to avoid dust
    frequency_hours: int = 24  # How often to check for rebalancing
    
    def __post_init__(self) -> None:
        """Validate rule configuration."""
        total_weight = sum(self.target_weights.values())
        if not 0.95 <= total_weight <= 1.05:  # Allow small rounding errors
            raise ValueError(f"Target weights sum to {total_weight:.3f}, should be ~1.0")
            

class PortfolioRebalancer:
    """Automated portfolio rebalancing system."""
    
    def __init__(self, portfolio: PortfolioManager) -> None:
        self.portfolio = portfolio
        self.rules: List[RebalanceRule] = []
        self.last_rebalance: Dict[str, datetime] = {}
        self.rebalance_history: List[Dict[str, Any]] = []
        
    def add_rule(self, rule: RebalanceRule) -> None:
        """Add a rebalancing rule."""
        self.rules.append(rule)
        self.last_rebalance[rule.name] = datetime.now()
        logger.info(f"Added rebalancing rule: {rule.name}")
        
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rebalancing rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                self.last_rebalance.pop(rule_name, None)
                logger.info(f"Removed rebalancing rule: {rule_name}")
                return True
        return False
        
    def check_rebalancing_needed(
        self, rule: RebalanceRule, current_prices: Dict[str, float]
    ) -> bool:
        """Check if rebalancing is needed for a given rule."""
        # Check frequency
        last_rebalance = self.last_rebalance.get(rule.name, datetime.min)
        time_since_last = datetime.now() - last_rebalance
        
        if time_since_last < timedelta(hours=rule.frequency_hours):
            return False
            
        # Update position prices
        self.portfolio.update_prices(current_prices)
        total_value = self.portfolio.get_total_value()
        
        if total_value <= 0:
            return False
            
        # Calculate current weights
        current_weights = {}
        for symbol in rule.target_weights.keys():
            if symbol in self.portfolio.positions:
                position_value = self.portfolio.positions[symbol].market_value
                current_weights[symbol] = position_value / total_value
            else:
                current_weights[symbol] = 0.0
                
        # Check if any weight deviates beyond tolerance
        for symbol, target_weight in rule.target_weights.items():
            current_weight = current_weights[symbol]
            deviation = abs(current_weight - target_weight)
            
            if deviation > rule.tolerance:
                logger.info(
                    f"Rebalancing needed for {rule.name}: {symbol} "
                    f"current={current_weight:.3f} target={target_weight:.3f} "
                    f"deviation={deviation:.3f}"
                )
                return True
                
        return False
        
    def calculate_rebalancing_trades(
        self, rule: RebalanceRule, current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Calculate trades needed for rebalancing."""
        trades = []
        total_value = self.portfolio.get_total_value()
        
        for symbol, target_weight in rule.target_weights.items():
            target_value = total_value * target_weight
            current_value = 0.0
            
            if symbol in self.portfolio.positions:
                current_value = self.portfolio.positions[symbol].market_value
                
            price = current_prices.get(symbol, 0.0)
            if price <= 0:
                logger.warning(f"No price available for {symbol}, skipping")
                continue
                
            value_diff = target_value - current_value
            
            # Only trade if difference is significant
            if abs(value_diff) < rule.min_trade_value:
                continue
                
            quantity = abs(value_diff) / price
            side = "BUY" if value_diff > 0 else "SELL"
            
            # Check if we can actually execute this trade
            if side == "SELL":
                current_quantity = self.portfolio.positions.get(symbol, type('', (), {'quantity': 0})).quantity
                if quantity > current_quantity:
                    quantity = current_quantity
                    
            if quantity > 0:
                trades.append({
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "value": quantity * price,
                    "reason": f"Rebalance {rule.name}"
                })
                
        return trades
        
    def execute_rebalancing(
        self,
        rule: RebalanceRule,
        current_prices: Dict[str, float],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute portfolio rebalancing for a given rule."""
        if not self.check_rebalancing_needed(rule, current_prices):
            return {"status": "no_rebalancing_needed", "rule": rule.name}
            
        trades = self.calculate_rebalancing_trades(rule, current_prices)
        
        if not trades:
            return {"status": "no_trades_needed", "rule": rule.name}
            
        executed_trades = []
        errors = []
        
        if dry_run:
            logger.info(f"DRY RUN: Would execute {len(trades)} trades for {rule.name}")
            for trade in trades:
                logger.info(f"  {trade['side']} {trade['quantity']:.3f} {trade['symbol']} @ ${trade['price']:.2f}")
        else:
            # Execute trades
            for trade in trades:
                try:
                    result = self.portfolio.execute_trade(
                        symbol=trade['symbol'],
                        side=trade['side'],
                        quantity=trade['quantity'],
                        price=trade['price'],
                        fee=0.0  # Fee would be calculated by broker
                    )
                    executed_trades.append(result)
                    logger.info(f"Rebalancing trade executed: {trade}")
                    
                except Exception as e:
                    error_msg = f"Failed to execute trade {trade}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    
            # Update last rebalance time
            self.last_rebalance[rule.name] = datetime.now()
            
        # Record rebalancing event
        rebalance_record = {
            "timestamp": datetime.now(),
            "rule_name": rule.name,
            "planned_trades": len(trades),
            "executed_trades": len(executed_trades),
            "errors": len(errors),
            "dry_run": dry_run,
            "trades": executed_trades if not dry_run else trades,
            "error_messages": errors
        }
        
        self.rebalance_history.append(rebalance_record)
        
        return {
            "status": "completed",
            "rule": rule.name,
            "executed_trades": len(executed_trades),
            "errors": len(errors),
            "trades": executed_trades
        }
        
    def run_all_rebalancing(
        self, current_prices: Dict[str, float], dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """Run rebalancing for all configured rules."""
        results = []
        
        for rule in self.rules:
            try:
                result = self.execute_rebalancing(rule, current_prices, dry_run)
                results.append(result)
            except Exception as e:
                logger.error(f"Rebalancing failed for rule {rule.name}: {e}")
                results.append({
                    "status": "error",
                    "rule": rule.name,
                    "error": str(e)
                })
                
        return results
        
    def get_rebalancing_summary(self) -> Dict[str, Any]:
        """Get summary of rebalancing activity."""
        return {
            "total_rules": len(self.rules),
            "rule_names": [rule.name for rule in self.rules],
            "total_rebalances": len(self.rebalance_history),
            "last_rebalances": self.last_rebalance.copy(),
            "recent_rebalances": self.rebalance_history[-5:] if self.rebalance_history else []
        }
        
    def create_equal_weight_rule(
        self, name: str, symbols: List[str], **kwargs
    ) -> RebalanceRule:
        """Create an equal-weight rebalancing rule."""
        weight = 1.0 / len(symbols)
        target_weights = {symbol: weight for symbol in symbols}
        
        return RebalanceRule(
            name=name,
            target_weights=target_weights,
            **kwargs
        )
        
    def create_custom_weight_rule(
        self, name: str, weights: Dict[str, float], **kwargs
    ) -> RebalanceRule:
        """Create a custom weight rebalancing rule."""
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        normalized_weights = {k: v / total_weight for k, v in weights.items()}
        
        return RebalanceRule(
            name=name,
            target_weights=normalized_weights,
            **kwargs
        )