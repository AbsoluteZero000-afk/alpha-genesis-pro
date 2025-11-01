from __future__ import annotations
import os
import argparse
import pandas as pd
import yfinance as yf
from config import get_settings
from utils.logger import configure_logging
from backtesting.engine import BacktestEngine
from execution.paper_broker import PaperBroker
from risk.risk_manager import RiskManager

TECH_LIB = os.getenv("TECH_LIB", "ta-lib").lower()

if TECH_LIB == "ta-lib":
    from strategies.trend_following_talib import TrendFollowingStrategy
    from strategies.mean_reversion_talib import MeanReversionStrategy
else:
    from strategies.trend_following import TrendFollowingStrategy
    from strategies.mean_reversion import MeanReversionStrategy


def run_backtest() -> None:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    data = yf.download("SPY", period="2y", interval="1d").rename(columns=str.lower)
    data = data[["open", "high", "low", "close", "volume"]].dropna()

    strategies = [TrendFollowingStrategy(fast=20, slow=50), MeanReversionStrategy(rsi_length=14, low=30, high=70)]
    broker = PaperBroker(cash=100_000)
    risk = RiskManager()
    engine = BacktestEngine(data=data, strategies=strategies, broker=broker, risk=risk, symbol="SPY")
    report = engine.run()
    from loguru import logger
    logger.info(f"Backtest report: {report}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["backtest", "live"], default="backtest")
    args = parser.parse_args()

    if args.mode == "backtest":
        run_backtest()
    else:
        run_backtest()


if __name__ == "__main__":
    main()
