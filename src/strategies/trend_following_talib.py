from __future__ import annotations
import pandas as pd
import talib as ta
from .base import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    name = "trend_following_sma_talib"

    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        super().__init__({"fast": fast, "slow": slow})

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        out = df.copy()
        out[f"sma_{p['fast']}"] = ta.SMA(out["close"].values, timeperiod=p["fast"])
        out[f"sma_{p['slow']}"] = ta.SMA(out["close"].values, timeperiod=p["slow"])
        cross = (out[f"sma_{p['fast']}"] > out[f"sma_{p['slow']}"]).astype(int)
        out["signal_cross"] = pd.Series(cross, index=out.index).diff().fillna(0)
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
