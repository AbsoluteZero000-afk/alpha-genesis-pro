from __future__ import annotations
import pandas as pd
import talib as ta
from .base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    name = "mean_reversion_rsi_talib"

    def __init__(self, rsi_length: int = 14, low: int = 30, high: int = 70) -> None:
        super().__init__({"rsi_length": rsi_length, "low": low, "high": high})

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        out = df.copy()
        out["rsi"] = ta.RSI(out["close"].values, timeperiod=p["rsi_length"])
        return out

    def generate_signal(self, df: pd.DataFrame) -> str:
        rsi = df.iloc[-1]["rsi"]
        if rsi < self.params["low"]:
            return "BUY"
        if rsi > self.params["high"]:
            return "SELL"
        return "HOLD"

    def get_parameters(self):
        return self.params
