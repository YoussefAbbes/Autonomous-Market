"""
Dashboard Backend API - Exposes market data for the React frontend.
Supports multi-currency, market cap, 24h changes, and more.
"""
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Database connection pool
db_pool = None

# Supported currencies
SUPPORTED_CURRENCIES = ["usd", "eur", "gbp", "jpy"]

# Currency symbols for display
CURRENCY_SYMBOLS = {
    "usd": "$",
    "eur": "€",
    "gbp": "£",
    "jpy": "¥"
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connection pool lifecycle."""
    global db_pool
    db_pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER", "market_user"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        database=os.getenv("POSTGRES_DB", "market_intel"),
        min_size=2,
        max_size=10
    )
    yield
    await db_pool.close()


app = FastAPI(
    title="Market Intelligence Dashboard API",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def safe_float(value, default=0):
    """Safely convert to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/currencies")
async def get_currencies():
    """Get list of supported currencies."""
    return {
        "currencies": SUPPORTED_CURRENCIES,
        "symbols": CURRENCY_SYMBOLS,
        "default": "usd"
    }


@app.get("/api/summary")
async def get_summary(currency: str = "usd"):
    """Get dashboard summary with multi-currency support."""
    if currency not in SUPPORTED_CURRENCIES:
        currency = "usd"

    async with db_pool.acquire() as conn:
        # Check if new columns exist
        has_new_columns = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'asset_prices' AND column_name = 'market_cap'
            )
        """)

        if has_new_columns:
            # Use new schema with multi-currency
            price_col = "price" if currency == "usd" else f"price_{currency}"
            prices = await conn.fetch(f"""
                SELECT DISTINCT ON (symbol)
                    symbol,
                    price as price_usd,
                    COALESCE(price_eur, price * 0.92) as price_eur,
                    COALESCE(price_gbp, price * 0.79) as price_gbp,
                    COALESCE(price_jpy, price * 150) as price_jpy,
                    volume,
                    COALESCE(market_cap, 0) as market_cap,
                    COALESCE(change_24h, 0) as change_24h,
                    timestamp
                FROM asset_prices
                ORDER BY symbol, timestamp DESC
            """)
        else:
            # Fall back to old schema
            prices = await conn.fetch("""
                SELECT DISTINCT ON (symbol)
                    symbol,
                    price as price_usd,
                    price * 0.92 as price_eur,
                    price * 0.79 as price_gbp,
                    price * 150 as price_jpy,
                    volume,
                    0 as market_cap,
                    0 as change_24h,
                    timestamp
                FROM asset_prices
                ORDER BY symbol, timestamp DESC
            """)

        # Get 24h sentiment average
        sentiment = await conn.fetchrow("""
            SELECT
                AVG(ai_sentiment_score) as avg_sentiment,
                COUNT(*) as article_count
            FROM market_news
            WHERE timestamp >= NOW() - INTERVAL '24 hours'
        """)

        # Get data freshness
        freshness = await conn.fetchrow("""
            SELECT
                EXTRACT(EPOCH FROM (NOW() - MAX(timestamp)))/60 as minutes_since_price,
                (SELECT EXTRACT(EPOCH FROM (NOW() - MAX(timestamp)))/60 FROM market_news) as minutes_since_news
            FROM asset_prices
        """)

        # Get 24h price changes (calculated)
        price_changes = await conn.fetch("""
            WITH latest AS (
                SELECT DISTINCT ON (symbol) symbol, price, timestamp
                FROM asset_prices
                ORDER BY symbol, timestamp DESC
            ),
            day_ago AS (
                SELECT DISTINCT ON (symbol) symbol, price
                FROM asset_prices
                WHERE timestamp <= NOW() - INTERVAL '24 hours'
                ORDER BY symbol, timestamp DESC
            )
            SELECT
                l.symbol,
                l.price as current_price,
                d.price as prev_price,
                CASE WHEN d.price > 0
                    THEN ((l.price - d.price) / d.price * 100)
                    ELSE 0
                END as change_pct
            FROM latest l
            LEFT JOIN day_ago d ON l.symbol = d.symbol
        """)

        # Format prices based on currency
        price_key = f"price_{currency}"
        formatted_prices = []
        for p in prices:
            formatted_prices.append({
                "symbol": p["symbol"],
                "price": safe_float(p[price_key] if price_key in p.keys() else p["price_usd"]),
                "price_usd": safe_float(p["price_usd"]),
                "price_eur": safe_float(p["price_eur"]),
                "price_gbp": safe_float(p["price_gbp"]),
                "price_jpy": safe_float(p["price_jpy"]),
                "volume": safe_float(p["volume"]),
                "market_cap": safe_float(p["market_cap"]),
                "change_24h": safe_float(p["change_24h"]),
                "timestamp": p["timestamp"].isoformat() if p["timestamp"] else None
            })

        return {
            "currency": currency,
            "currency_symbol": CURRENCY_SYMBOLS.get(currency, "$"),
            "latest_prices": formatted_prices,
            "price_changes": [
                {
                    "symbol": p["symbol"],
                    "current_price": safe_float(p["current_price"]),
                    "prev_price": safe_float(p["prev_price"]),
                    "change_pct": safe_float(p["change_pct"])
                }
                for p in price_changes
            ],
            "sentiment": {
                "average": safe_float(sentiment["avg_sentiment"]),
                "article_count": sentiment["article_count"] or 0
            },
            "freshness": {
                "minutes_since_price": safe_float(freshness["minutes_since_price"]) if freshness["minutes_since_price"] else None,
                "minutes_since_news": safe_float(freshness["minutes_since_news"]) if freshness["minutes_since_news"] else None
            },
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/api/coins")
async def get_coins():
    """Get list of all tracked coins with latest data."""
    async with db_pool.acquire() as conn:
        # Check if new columns exist
        has_new_columns = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'asset_prices' AND column_name = 'market_cap'
            )
        """)

        if has_new_columns:
            rows = await conn.fetch("""
                SELECT DISTINCT ON (symbol)
                    symbol,
                    price,
                    volume,
                    COALESCE(market_cap, 0) as market_cap,
                    COALESCE(change_24h, 0) as change_24h,
                    timestamp
                FROM asset_prices
                ORDER BY symbol, timestamp DESC
            """)
        else:
            rows = await conn.fetch("""
                SELECT DISTINCT ON (symbol)
                    symbol,
                    price,
                    volume,
                    0 as market_cap,
                    0 as change_24h,
                    timestamp
                FROM asset_prices
                ORDER BY symbol, timestamp DESC
            """)

        return {
            "count": len(rows),
            "coins": [
                {
                    "symbol": r["symbol"],
                    "name": r["symbol"].replace("-", " ").title(),
                    "price": safe_float(r["price"]),
                    "volume": safe_float(r["volume"]),
                    "market_cap": safe_float(r["market_cap"]),
                    "change_24h": safe_float(r["change_24h"]),
                    "last_updated": r["timestamp"].isoformat() if r["timestamp"] else None
                }
                for r in rows
            ]
        }


@app.get("/api/prices/{symbol}")
async def get_price_history(
    symbol: str,
    hours: int = 24,
    currency: str = "usd"
):
    """Get price history for a specific symbol with multi-currency support."""
    if currency not in SUPPORTED_CURRENCIES:
        currency = "usd"

    async with db_pool.acquire() as conn:
        # Check if multi-currency columns exist
        has_multi_currency = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'asset_prices' AND column_name = 'price_eur'
            )
        """)

        if has_multi_currency and currency != "usd":
            price_col = f"COALESCE(price_{currency}, price * {get_rate(currency)}) as price"
        else:
            price_col = "price"

        rows = await conn.fetch(f"""
            SELECT {price_col}, volume, timestamp
            FROM asset_prices
            WHERE UPPER(symbol) = UPPER($1)
              AND timestamp >= NOW() - INTERVAL '{hours} hours'
            ORDER BY timestamp ASC
        """, symbol)

        if not rows:
            raise HTTPException(status_code=404, detail=f"No data for symbol: {symbol}")

        return {
            "symbol": symbol.upper(),
            "currency": currency,
            "hours": hours,
            "data": [
                {
                    "price": safe_float(r["price"]),
                    "volume": safe_float(r["volume"]),
                    "timestamp": r["timestamp"].isoformat()
                }
                for r in rows
            ]
        }


def get_rate(currency):
    """Get approximate exchange rate from USD."""
    rates = {"eur": 0.92, "gbp": 0.79, "jpy": 150}
    return rates.get(currency, 1)


@app.get("/api/prices")
async def get_all_prices(
    hours: int = 24,
    currency: str = "usd",
    symbols: Optional[str] = None
):
    """Get price history for all or selected symbols."""
    if currency not in SUPPORTED_CURRENCIES:
        currency = "usd"

    async with db_pool.acquire() as conn:
        # Build query with optional symbol filter
        symbol_filter = ""
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            symbol_filter = f"AND UPPER(symbol) IN ({','.join(repr(s) for s in symbol_list)})"

        rows = await conn.fetch(f"""
            SELECT symbol, price, volume, timestamp
            FROM asset_prices
            WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
            {symbol_filter}
            ORDER BY timestamp ASC
        """)

        # Group by symbol
        by_symbol = {}
        rate = get_rate(currency) if currency != "usd" else 1

        for r in rows:
            sym = r["symbol"].upper()
            if sym not in by_symbol:
                by_symbol[sym] = []
            by_symbol[sym].append({
                "price": safe_float(r["price"]) * rate,
                "volume": safe_float(r["volume"]),
                "timestamp": r["timestamp"].isoformat()
            })

        return {
            "hours": hours,
            "currency": currency,
            "symbols": by_symbol
        }


@app.get("/api/news")
async def get_news(
    limit: int = 20,
    search: Optional[str] = None,
    sentiment_filter: Optional[str] = None
):
    """Get recent news with optional search and sentiment filter."""
    async with db_pool.acquire() as conn:
        # Build query with filters
        conditions = []
        params = []
        param_idx = 1

        if search:
            conditions.append(f"LOWER(headline) LIKE LOWER(${param_idx})")
            params.append(f"%{search}%")
            param_idx += 1

        if sentiment_filter == "positive":
            conditions.append("ai_sentiment_score > 0.3")
        elif sentiment_filter == "negative":
            conditions.append("ai_sentiment_score < -0.3")
        elif sentiment_filter == "neutral":
            conditions.append("ai_sentiment_score BETWEEN -0.3 AND 0.3")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT headline, source, url, ai_sentiment_score, timestamp
            FROM market_news
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit}
        """

        rows = await conn.fetch(query, *params)

        return {
            "count": len(rows),
            "search": search,
            "sentiment_filter": sentiment_filter,
            "articles": [
                {
                    "headline": r["headline"],
                    "source": r["source"],
                    "url": r["url"],
                    "sentiment": safe_float(r["ai_sentiment_score"]),
                    "timestamp": r["timestamp"].isoformat()
                }
                for r in rows
            ]
        }


@app.get("/api/sentiment/history")
async def get_sentiment_history(hours: int = 24):
    """Get sentiment score history aggregated by hour."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT
                DATE_TRUNC('hour', timestamp) as hour,
                AVG(ai_sentiment_score) as avg_sentiment,
                COUNT(*) as article_count
            FROM market_news
            WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
            GROUP BY DATE_TRUNC('hour', timestamp)
            ORDER BY hour ASC
        """)

        return {
            "hours": hours,
            "data": [
                {
                    "hour": r["hour"].isoformat(),
                    "sentiment": safe_float(r["avg_sentiment"]),
                    "count": r["article_count"]
                }
                for r in rows
            ]
        }


@app.get("/api/alerts")
async def get_alerts(
    limit: int = 20,
    severity: Optional[str] = None
):
    """Get recent alerts with optional severity filter."""
    async with db_pool.acquire() as conn:
        # Check if alerts table exists
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'alerts'
            )
        """)

        if not exists:
            return {"count": 0, "alerts": [], "message": "Alerts table not created yet"}

        # Build query with optional severity filter
        severity_filter = ""
        params = [limit]
        if severity:
            severity_filter = "WHERE severity = $2"
            params.append(severity)

        rows = await conn.fetch(f"""
            SELECT type, symbol, message, severity, metadata, created_at
            FROM alerts
            {severity_filter}
            ORDER BY created_at DESC
            LIMIT $1
        """, *params)

        return {
            "count": len(rows),
            "alerts": [
                {
                    "type": r["type"],
                    "symbol": r["symbol"],
                    "message": r["message"],
                    "severity": r["severity"],
                    "metadata": dict(r["metadata"]) if r["metadata"] else {},
                    "created_at": r["created_at"].isoformat()
                }
                for r in rows
            ]
        }


@app.get("/api/stats")
async def get_stats():
    """Get overall statistics for the dashboard."""
    async with db_pool.acquire() as conn:
        # Total coins tracked
        coin_count = await conn.fetchval("""
            SELECT COUNT(DISTINCT symbol) FROM asset_prices
        """)

        # Total price records
        price_count = await conn.fetchval("""
            SELECT COUNT(*) FROM asset_prices
        """)

        # Total news articles
        news_count = await conn.fetchval("""
            SELECT COUNT(*) FROM market_news
        """)

        # Date range
        date_range = await conn.fetchrow("""
            SELECT MIN(timestamp) as first_record, MAX(timestamp) as last_record
            FROM asset_prices
        """)

        return {
            "coins_tracked": coin_count or 0,
            "total_price_records": price_count or 0,
            "total_news_articles": news_count or 0,
            "first_record": date_range["first_record"].isoformat() if date_range["first_record"] else None,
            "last_record": date_range["last_record"].isoformat() if date_range["last_record"] else None
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
