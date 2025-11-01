# Storage & Persistence Best Practices

This project includes a Storage layer (SQLAlchemy) with the following principles:

- Pooled connections (pool_pre_ping, pool_recycle) for long-running services
- Separate tables for: market bars, trades, equity snapshots
- Batched inserts for market data ingestion
- JSON metadata column on trades for extensibility
- Alembic migrations recommended for schema evolution
- Redis used strictly for caching and ephemeral data

Run schema creation locally:

```bash
python -c "from src.storage import Storage; Storage().create_schema()"
```
