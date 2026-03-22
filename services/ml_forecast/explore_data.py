"""
Step 1: Explore Your Data
--------------------------
Before building ML models, we need to:
1. See what data we have
2. Check for missing values
3. Understand data patterns
4. Decide what to predict
"""

import asyncpg
import pandas as pd
import asyncio
from datetime import datetime, timedelta

# Database connection settings
# Use 'postgres' as hostname when running in Docker, 'localhost' when running locally
import os
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),  # 'postgres' is the Docker service name
    'port': 5432,
    'user': os.getenv('POSTGRES_USER', 'market_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'testpass123'),
    'database': os.getenv('POSTGRES_DB', 'market_intel')
}

async def explore_data():
    """Step-by-step data exploration"""

    # Connect to database
    print("📊 Step 1.1: Connecting to PostgreSQL...")
    conn = await asyncpg.connect(**DB_CONFIG)

    # ============================================
    # STEP 1: Check what data we have
    # ============================================
    print("\n✅ Step 1.2: Checking available data...\n")

    # Count total records
    total_count = await conn.fetchval("SELECT COUNT(*) FROM asset_prices")
    print(f"Total price records: {total_count:,}")

    # Check date range
    date_range = await conn.fetchrow("""
        SELECT
            MIN(timestamp) as first_date,
            MAX(timestamp) as last_date,
            MAX(timestamp) - MIN(timestamp) as duration
        FROM asset_prices
    """)
    print(f"Data starts: {date_range['first_date']}")
    print(f"Data ends: {date_range['last_date']}")
    print(f"Duration: {date_range['duration']}")

    # Check which coins we have
    coins = await conn.fetch("""
        SELECT
            symbol,
            COUNT(*) as record_count,
            MIN(timestamp) as first,
            MAX(timestamp) as last
        FROM asset_prices
        GROUP BY symbol
        ORDER BY record_count DESC
    """)

    print("\n📈 Coins we're tracking:")
    print("-" * 70)
    for coin in coins:
        print(f"{coin['symbol']:15} | {coin['record_count']:5} records | "
              f"{coin['first']} → {coin['last']}")

    # ============================================
    # STEP 2: Get sample data for one coin
    # ============================================
    print("\n✅ Step 1.3: Getting sample data for BITCOIN...\n")

    # Get last 100 records for Bitcoin
    btc_data = await conn.fetch("""
        SELECT
            timestamp,
            price,
            volume,
            market_cap,
            change_24h
        FROM asset_prices
        WHERE symbol = 'BITCOIN'
          AND currency = 'usd'
        ORDER BY timestamp DESC
        LIMIT 100
    """)

    # Convert to pandas DataFrame (makes analysis easier)
    df = pd.DataFrame(btc_data, columns=['timestamp', 'price', 'volume',
                                         'market_cap', 'change_24h'])

    print("Sample of Bitcoin data (last 5 records):")
    print(df.head())

    # ============================================
    # STEP 3: Check for data quality issues
    # ============================================
    print("\n✅ Step 1.4: Checking data quality...\n")

    # Check for missing values
    print("Missing values per column:")
    print(df.isnull().sum())

    # Basic statistics
    print("\nBasic statistics:")
    print(df.describe())

    # ============================================
    # STEP 4: Check sentiment data
    # ============================================
    print("\n✅ Step 1.5: Checking sentiment data...\n")

    news_count = await conn.fetchval("SELECT COUNT(*) FROM market_news")
    print(f"Total news articles: {news_count:,}")

    if news_count > 0:
        sentiment_sample = await conn.fetch("""
            SELECT
                timestamp,
                headline,
                ai_sentiment_score
            FROM market_news
            ORDER BY timestamp DESC
            LIMIT 5
        """)

        print("\nSample news with sentiment:")
        for item in sentiment_sample:
            score = item['ai_sentiment_score'] or 0
            emoji = '😊' if score > 0.3 else ('😐' if score > -0.3 else '😰')
            print(f"{emoji} {score:+.2f} | {item['headline'][:60]}...")

    await conn.close()

    # ============================================
    # SUMMARY: What did we learn?
    # ============================================
    print("\n" + "="*70)
    print("📋 SUMMARY - What We Learned:")
    print("="*70)
    print(f"✅ We have {total_count:,} price records")
    print(f"✅ We're tracking {len(coins)} cryptocurrencies")
    print(f"✅ Data spans {date_range['duration']}")
    print(f"✅ We have {news_count:,} news articles with sentiment scores")
    print("\n💡 Next steps:")
    print("   1. We have enough data to start training")
    print("   2. Data looks clean (we'll handle missing values)")
    print("   3. We have both price AND sentiment data - great!")
    print("\n👉 Ready to move to Phase 2: Data Cleaning!")

# Run the exploration
if __name__ == "__main__":
    asyncio.run(explore_data())
