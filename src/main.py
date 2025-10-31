from __future__ import annotations
import argparse
import asyncio
import pandas as pd
import yfinance as yf
from config import get_settings
from utils.logger import configure_logging
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from backtesting.engine import BacktestEngine
from execution.paper_broker import PaperBroker
from risk.risk_manager import RiskManager


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
        # Placeholder for live trading entrypoint (would reuse same components with live data and real broker)
        run_backtest()


if __name__ == "__main__":
    main()
