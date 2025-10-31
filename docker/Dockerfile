FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app

# Minimal runtime image
FROM base AS runtime
ENV ENVIRONMENT=production
EXPOSE 8000
CMD ["python", "src/main.py", "--mode", "backtest"]
