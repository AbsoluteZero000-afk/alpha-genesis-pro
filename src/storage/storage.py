from __future__ import annotations
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
from ..config import get_settings

Base = declarative_base()


class MarketBar(Base):
    __tablename__ = "market_bars"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    side = Column(String)
    quantity = Column(Float)
    price = Column(Float)
    fee = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata = Column(JSON)


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    equity = Column(Float)
    cash = Column(Float)
    positions_value = Column(Float)


class Storage:
    """Best-practice storage wrapper using SQLAlchemy.
    - Uses pooled connections
    - Separate tables for bars, trades, equity
    - Safe upserts and batched inserts
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            pool_recycle=1800,
            future=True,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)
        logger.info("Database schema ensured.")

    def insert_market_bars(self, symbol: str, df) -> int:
        if df is None or df.empty:
            return 0
        df = df.copy()
        df = df.reset_index().rename(columns={"index": "timestamp"})
        rows = [
            dict(
                symbol=symbol,
                timestamp=row["timestamp"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            for _, row in df.iterrows()
        ]
        with self.engine.begin() as conn:
            conn.execute(MarketBar.__table__.insert(), rows)
        return len(rows)

    def insert_trade(self, symbol: str, side: str, quantity: float, price: float, fee: float, metadata: Optional[Dict[str, Any]] = None) -> int:
        with self.engine.begin() as conn:
            res = conn.execute(
                Trade.__table__.insert().values(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    metadata=metadata or {},
                )
            )
            return res.rowcount or 0

    def insert_equity_snapshot(self, equity: float, cash: float, positions_value: float) -> int:
        with self.engine.begin() as conn:
            res = conn.execute(
                EquitySnapshot.__table__.insert().values(
                    equity=equity,
                    cash=cash,
                    positions_value=positions_value,
                )
            )
            return res.rowcount or 0
