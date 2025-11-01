from .base import BaseBroker
from ...paper_broker import PaperBroker

# Provide stubs that don't raise ImportError if not used directly
try:
    from .alpaca import AlpacaBroker
except Exception:
    class AlpacaBroker(BaseBroker):
        """Stub AlpacaBroker to avoid ImportError if actual implementation is not available."""
        def get_portfolio(self):
            raise NotImplementedError("AlpacaBroker not implemented. See implementation notes.")
        def submit_order(self, symbol, side, qty, price=None):
            raise NotImplementedError("AlpacaBroker not implemented. See implementation notes.")
try:
    from .binance import BinanceBroker
except Exception:
    class BinanceBroker(BaseBroker):
        """Stub BinanceBroker to avoid ImportError if actual implementation is not available."""
        def get_portfolio(self):
            raise NotImplementedError("BinanceBroker not implemented. See implementation notes.")
        def submit_order(self, symbol, side, qty, price=None):
            raise NotImplementedError("BinanceBroker not implemented. See implementation notes.")

__all__ = ["BaseBroker", "PaperBroker", "AlpacaBroker", "BinanceBroker"]
