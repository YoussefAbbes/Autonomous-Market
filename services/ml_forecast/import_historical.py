"""
Import Historical Data from CoinGecko
=====================================
Fetches 90 days of historical crypto price data
and imports it into your database for ML training.

HOURLY granularity = ~2,160 samples per coin
Total: ~21,600 data points for 10 coins!
"""

import asyncpg
import asyncio
import aiohttp
import os
from datetime import datetime, timedelta

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': 5432,
    'user': os.getenv('POSTGRES_USER', 'market_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'testpass123'),
    'database': os.getenv('POSTGRES_DB', 'market_intel')
}

# Coins to import (same as your n8n workflow)
COINS = [
    'bitcoin',
    'ethereum',
    'binancecoin',
    'ripple',
    'cardano',
    'solana',
    'polkadot',
    'dogecoin',
    'avalanche-2',
    'chainlink'
]


async def fetch_historical_data(session, coin_id, days=90):
    """Fetch historical data from CoinGecko API"""

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': days,
        'interval': 'hourly' if days <= 90 else 'daily'
    }

    try:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data
            elif response.status == 429:
                print(f"   ⚠️ Rate limited, waiting 60 seconds...")
                await asyncio.sleep(60)
                return await fetch_historical_data(session, coin_id, days)
            else:
                print(f"   ❌ Error fetching {coin_id}: {response.status}")
                return None
    except Exception as e:
        print(f"   ❌ Exception fetching {coin_id}: {e}")
        return None


async def import_historical_data():
    """Main function to import historical data"""

    print("=" * 70)
    print("📥 Importing 90 Days of HOURLY Historical Data from CoinGecko")
    print("=" * 70)
    print("\n⏰ Note: 90 days with hourly prices = ~2,160 samples per coin")
    print("   Total: ~21,600 records for all 10 coins!")

    # Connect to database
    print("\n📊 Connecting to database...")
    conn = await asyncpg.connect(**DB_CONFIG)

    # Check current data count
    current_count = await conn.fetchval("SELECT COUNT(*) FROM asset_prices")
    print(f"   Current records in database: {current_count}")

    total_imported = 0

    async with aiohttp.ClientSession() as session:
        for coin_id in COINS:
            print(f"\n🪙 Fetching {coin_id.upper()}...")

            # Fetch historical data (90 days = hourly granularity)
            data = await fetch_historical_data(session, coin_id, days=90)

            if not data:
                continue

            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            market_caps = data.get('market_caps', [])

            print(f"   📈 Got {len(prices)} price points")

            # Prepare records for insertion
            records = []
            for i, (timestamp_ms, price) in enumerate(prices):
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
                volume = volumes[i][1] if i < len(volumes) else None
                market_cap = market_caps[i][1] if i < len(market_caps) else None

                records.append((
                    coin_id.upper().replace('-', '_'),  # symbol
                    price,                              # price
                    volume,                             # volume
                    market_cap,                         # market_cap
                    None,                               # change_24h (not available in historical)
                    None,                               # price_eur
                    None,                               # price_gbp
                    None,                               # price_jpy
                    'usd',                              # currency
                    timestamp,                          # timestamp
                    'coingecko_historical'              # source
                ))

            # Insert records (skip duplicates)
            inserted = 0
            for record in records:
                try:
                    await conn.execute("""
                        INSERT INTO asset_prices
                        (symbol, price, volume, market_cap, change_24h,
                         price_eur, price_gbp, price_jpy, currency, timestamp, source)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT DO NOTHING
                    """, *record)
                    inserted += 1
                except Exception as e:
                    pass  # Skip duplicates silently

            print(f"   ✅ Imported {inserted} records for {coin_id.upper()}")
            total_imported += inserted

            # Rate limiting - CoinGecko free tier allows ~10-30 calls/minute
            await asyncio.sleep(6)  # Wait 6 seconds between coins

    # Final count
    final_count = await conn.fetchval("SELECT COUNT(*) FROM asset_prices")
    await conn.close()

    print("\n" + "=" * 70)
    print("📋 IMPORT COMPLETE")
    print("=" * 70)
    print(f"\n✅ Total records imported: {total_imported}")
    print(f"✅ Database now has: {final_count} records")
    print(f"✅ Growth: {final_count - current_count} new records")

    # Show breakdown by coin
    conn = await asyncpg.connect(**DB_CONFIG)
    breakdown = await conn.fetch("""
        SELECT symbol, COUNT(*) as count, MIN(timestamp) as first, MAX(timestamp) as last
        FROM asset_prices
        GROUP BY symbol
        ORDER BY count DESC
    """)
    await conn.close()

    print("\n📊 Records by coin:")
    print("-" * 70)
    for row in breakdown:
        print(f"   {row['symbol']:15} | {row['count']:6} records | {row['first'].date()} → {row['last'].date()}")

    print("\n🎉 Now retrain your model with more data!")
    print("   Run: docker-compose run --rm ml-forecast python phase3_training.py")


if __name__ == "__main__":
    asyncio.run(import_historical_data())
