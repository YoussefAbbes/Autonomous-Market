"""
MCP server for Autonomous Market Intelligence.

Phase 1 responsibilities:
- Expose a Resource: latest_market_data
- Expose a Tool: get_market_forecast
- Query PostgreSQL as the source of truth
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any

import asyncpg
from mcp.server.fastmcp import FastMCP


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://market_user:change-me@postgres:5432/market_intel",
)
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8080"))
MCP_PATH = os.getenv("MCP_PATH", "/mcp")


mcp = FastMCP(
    "Autonomous Market MCP",
    instructions=(
        "Use tools and resources to retrieve market prices, sentiment, and "
        "simple forecasts derived from live PostgreSQL time-series data."
    ),
    json_response=True,
)


_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    """
    Create/reuse a shared asyncpg connection pool.

    A shared pool is the standard pattern for async microservices because it
    avoids connection churn and improves latency under concurrent MCP calls.
    """
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await asyncpg.create_pool(
                    dsn=DATABASE_URL,
                    min_size=1,
                    max_size=10,
                    command_timeout=30,
                )
    return _pool


def _to_iso(value: Any) -> str | None:
    """Normalize datetime values into ISO8601 strings for JSON outputs."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


@mcp.resource("market://latest_market_data")
async def latest_market_data() -> str:
    """
    Resource: latest_market_data

    Returns:
    - latest known price row per symbol
    - simple sentiment rollup for the current UTC date
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        latest_rows = await conn.fetch(
            """
            SELECT symbol, price::float8 AS price, volume::float8 AS volume, "timestamp", source
            FROM latest_asset_prices
            ORDER BY "timestamp" DESC
            LIMIT 200
            """
        )

        sentiment_row = await conn.fetchrow(
            """
            SELECT
                COALESCE(AVG(ai_sentiment_score), 0.0)::float8 AS avg_sentiment,
                COUNT(*)::int AS article_count
            FROM market_news
            WHERE "timestamp" >= date_trunc('day', NOW() AT TIME ZONE 'UTC')
            """
        )

    prices = [
        {
            "symbol": row["symbol"],
            "price": row["price"],
            "volume": row["volume"],
            "timestamp": _to_iso(row["timestamp"]),
            "source": row["source"],
        }
        for row in latest_rows
    ]

    payload = {
        "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "latest_prices": prices,
        "today_news_sentiment": {
            "avg_sentiment": sentiment_row["avg_sentiment"] if sentiment_row else 0.0,
            "article_count": sentiment_row["article_count"] if sentiment_row else 0,
        },
    }
    return json.dumps(payload, indent=2)


@mcp.tool()
async def get_market_forecast(symbol: str, horizon_hours: int = 24) -> dict[str, Any]:
    """
    Tool: get_market_forecast

    This Phase 1 baseline uses a simple trend extrapolation from the latest two
    price points. It is intentionally transparent and deterministic until your
    ARIMA/LSTM model is deployed in a later phase.
    """
    if not symbol or not symbol.strip():
        raise ValueError("symbol is required")
    if horizon_hours < 1 or horizon_hours > 168:
        raise ValueError("horizon_hours must be between 1 and 168")

    normalized_symbol = symbol.strip().upper()

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT price::float8 AS price, "timestamp"
            FROM asset_prices
            WHERE symbol = $1
            ORDER BY "timestamp" DESC
            LIMIT 2
            """,
            normalized_symbol,
        )

    if not rows:
        return {
            "symbol": normalized_symbol,
            "status": "no_data",
            "message": "No price data found for the requested symbol.",
        }

    latest_price = float(rows[0]["price"])
    latest_ts = rows[0]["timestamp"]

    if len(rows) == 1:
        # If we have only one point, forecast == latest price as a safe fallback.
        forecast_price = latest_price
        method = "last_value_carry_forward"
    else:
        prev_price = float(rows[1]["price"])
        prev_ts = rows[1]["timestamp"]
        elapsed_hours = max((latest_ts - prev_ts).total_seconds() / 3600.0, 1e-6)
        hourly_slope = (latest_price - prev_price) / elapsed_hours
        forecast_price = latest_price + (hourly_slope * horizon_hours)
        method = "linear_extrapolation_last_two_points"

    return {
        "symbol": normalized_symbol,
        "horizon_hours": horizon_hours,
        "latest_price": latest_price,
        "forecast_price": forecast_price,
        "latest_timestamp": _to_iso(latest_ts),
        "method": method,
        "disclaimer": "Baseline forecast for Phase 1; replace with ARIMA/LSTM in Phase 2.",
    }


if __name__ == "__main__":
    # Streamable HTTP path defaults to /mcp; configurable for reverse proxies.
    mcp.settings.streamable_http_path = MCP_PATH
    mcp.settings.host = MCP_HOST
    mcp.settings.port = MCP_PORT
    mcp.run(transport=MCP_TRANSPORT)
