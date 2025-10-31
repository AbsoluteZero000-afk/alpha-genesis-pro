from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any


class Broker(ABC):
    @abstractmethod
    def get_portfolio(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def submit_order(self, symbol: str, side: str, qty: float, price: float | None = None) -> Dict[str, Any]:
        ...
