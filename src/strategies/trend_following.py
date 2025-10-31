from __future__ import annotations
import pandas as pd
import pandas_ta as ta
from .base import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    name = "trend_following_sma"

    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        super().__init__({"fast": fast, "slow": slow})

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        fast = self.params["fast"]
        slow = self.params["slow"]
        out = df.copy()
        out[f"sma_{fast}"] = ta.sma(out["close"], length=fast)
        out[f"sma_{slow}"] = ta.sma(out["close"], length=slow)
        out["signal_cross"] = (out[f"sma_{fast}"] > out[f"sma_{slow}"]).astype(int).diff().fillna(0)
        return out

    def generate_signal(self, df: pd.DataFrame) -> str:
        row = df.iloc[-1]
        if row["signal_cross"] == 1:
            return "BUY"
        if row["signal_cross"] == -1:
            return "SELL"
        return "HOLD"

    def get_parameters(self):
        return self.params
