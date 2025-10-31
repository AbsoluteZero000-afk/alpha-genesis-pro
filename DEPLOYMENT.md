# Deployment and Setup Guide

## 1) Clone and Environment Setup
- git clone https://github.com/AbsoluteZero000-afk/alpha-genesis-pro.git
- cd alpha-genesis-pro
- python -m venv .venv && source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
- pip install -r requirements.txt -r requirements-dev.txt
- cp .env.example .env
- Edit .env with your settings (at minimum: DATABASE_URL, REDIS_URL, ENCRYPTION_KEY)

## 2) Run a Quick Backtest (SPY daily)
- python src/main.py --mode backtest

## 3) Docker (optional)
- docker build -t alpha-genesis-pro -f docker/Dockerfile .
- docker compose -f docker/docker-compose.yml up --build

## 4) Production Notes
- Configure CI/CD in .github/workflows
- For live trading, plug in Alpaca/Binance credentials and implement live data feed & broker in src/data/providers and src/execution/brokers
