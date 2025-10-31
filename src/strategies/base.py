from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd


class BaseStrategy(ABC):
    name: str

    def __init__(self, params: Dict[str, Any] | None = None) -> None:
        self.params = params or {}

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add required indicators to df and return a copy."""

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> str:
        """Return 'BUY', 'SELL', or 'HOLD' based on latest bar."""

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return the current strategy parameters."""
