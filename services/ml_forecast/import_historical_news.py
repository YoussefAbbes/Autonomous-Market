"""
Import Historical News Data
============================
Fetches crypto news from RSS feeds and imports into database.

Uses RSS feeds from multiple reliable crypto news sources.
No API keys or tokens needed!

Strategy: Parse RSS feeds which typically contain 20-100 recent articles each.
"""

import asyncpg
import asyncio
import aiohttp
import os
from datetime import datetime
import xml.etree.ElementTree as ET
from html import unescape

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': 5432,
    'user': os.getenv('POSTGRES_USER', 'market_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'testpass123'),
    'database': os.getenv('POSTGRES_DB', 'market_intel')
}

# RSS feeds from major crypto news sites
RSS_FEEDS = [
    'https://cointelegraph.com/rss',
    'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'https://decrypt.co/feed',
    'https://www.theblockcrypto.com/rss.xml',
    'https://bitcoinmagazine.com/.rss/full/',
    'https://cryptopotato.com/feed/',
    'https://cryptoslate.com/feed/',
    'https://cryptonews.com/news/feed/',
]


async def fetch_rss_feed(session, feed_url):
    """Fetch and parse RSS feed"""

    try:
        async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                content = await response.text()
                return parse_rss(content)
            else:
                print(f"   ⚠️ Error fetching {feed_url}: {response.status}")
                return []
    except Exception as e:
        print(f"   ⚠️ Exception fetching {feed_url}: {str(e)[:50]}")
        return []


def parse_rss(xml_content):
    """Parse RSS XML and extract articles"""

    articles = []

    try:
        root = ET.fromstring(xml_content)

        # Try RSS 2.0 format
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            link_elem = item.find('link')
            pubdate_elem = item.find('pubDate')

            if title_elem is not None and title_elem.text:
                title = unescape(title_elem.text.strip())
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ''
                pubdate = pubdate_elem.text.strip() if pubdate_elem is not None and pubdate_elem.text else None

                # Parse date (RSS format: "Wed, 22 Mar 2026 10:30:00 GMT")
                timestamp = None
                if pubdate:
                    try:
                        # Try multiple date formats
                        for fmt in ['%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S %z']:
                            try:
                                timestamp = datetime.strptime(pubdate, fmt)
                                break
                            except:
                                continue
                    except:
                        pass

                if not timestamp:
                    timestamp = datetime.utcnow()

                articles.append({
                    'headline': title,
                    'source': link,
                    'timestamp': timestamp
                })

        # Try Atom format
        if len(articles) == 0:
            for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
                updated_elem = entry.find('{http://www.w3.org/2005/Atom}updated')

                if title_elem is not None and title_elem.text:
                    title = unescape(title_elem.text.strip())
                    link = link_elem.get('href', '') if link_elem is not None else ''
                    updated = updated_elem.text.strip() if updated_elem is not None and updated_elem.text else None

                    timestamp = None
                    if updated:
                        try:
                            timestamp = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        except:
                            timestamp = datetime.utcnow()
                    else:
                        timestamp = datetime.utcnow()

                    articles.append({
                        'headline': title,
                        'source': link,
                        'timestamp': timestamp
                    })

    except Exception as e:
        print(f"   ⚠️ Error parsing RSS: {str(e)[:50]}")

    return articles


async def get_ml_sentiment(session, headline):
    """Get sentiment score from ML API"""

    url = "http://ml-api:8000/v1/sentiment/headline"

    try:
        async with session.post(url, json={'headline': headline}, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('sentiment_score', 0.0)
            else:
                return 0.0  # Neutral fallback
    except Exception:
        return 0.0  # Neutral fallback


async def import_historical_news():
    """Main function to import news from RSS feeds"""

    print("=" * 70)
    print("📰 Importing News from RSS Feeds")
    print("=" * 70)
    print(f"\nℹ️  Fetching from {len(RSS_FEEDS)} crypto news RSS feeds")

    # Connect to database
    print("\n📊 Connecting to database...")
    conn = await asyncpg.connect(**DB_CONFIG)

    # Check current news count
    current_count = await conn.fetchval("SELECT COUNT(*) FROM market_news")
    print(f"   Current news records: {current_count}")

    total_imported = 0
    total_fetched = 0

    async with aiohttp.ClientSession() as session:

        print(f"\n📥 Fetching RSS feeds...\n")

        for i, feed_url in enumerate(RSS_FEEDS, 1):
            feed_name = feed_url.split('/')[2]  # Extract domain
            print(f"🔄 [{i}/{len(RSS_FEEDS)}] Fetching {feed_name}...")

            articles = await fetch_rss_feed(session, feed_url)

            if not articles:
                print(f"   ⚠️ No articles found")
                continue

            print(f"   📰 Found {len(articles)} articles")
            total_fetched += len(articles)

            # Get sentiment and insert
            imported_this_feed = 0
            for article in articles:
                # Get sentiment score from ML API
                sentiment_score = await get_ml_sentiment(session, article['headline'])

                # Insert into database (skip duplicates)
                try:
                    result = await conn.execute("""
                        INSERT INTO market_news
                        (headline, source, timestamp, ai_sentiment_score, created_at)
                        VALUES ($1, $2, $3, $4, NOW())
                        ON CONFLICT (headline) DO NOTHING
                    """, article['headline'], article['source'], article['timestamp'], sentiment_score)

                    # asyncpg returns "INSERT 0 1" for successful insert
                    if "INSERT" in result:
                        imported_this_feed += 1
                        total_imported += 1
                except Exception as e:
                    pass  # Skip errors silently

                # Small delay to avoid overwhelming ML API
                await asyncio.sleep(0.05)

            print(f"   ✅ Imported {imported_this_feed} new articles\n")

            # Delay between feeds
            if i < len(RSS_FEEDS):
                await asyncio.sleep(2)

    # Final count
    final_count = await conn.fetchval("SELECT COUNT(*) FROM market_news")

    # Get date range
    date_range = await conn.fetchrow("""
        SELECT MIN(timestamp) as first, MAX(timestamp) as last
        FROM market_news
    """)

    await conn.close()

    print("=" * 70)
    print("📋 IMPORT COMPLETE")
    print("=" * 70)
    print(f"\n✅ Articles fetched: {total_fetched}")
    print(f"✅ Articles imported (new): {total_imported}")
    print(f"✅ Database now has: {final_count} news records")
    print(f"✅ Growth: {final_count - current_count} new records")

    if date_range['first']:
        print(f"\n📅 Date range: {date_range['first'].date()} → {date_range['last'].date()}")
        days_span = (date_range['last'] - date_range['first']).days
        print(f"   Span: {days_span} days")

    print(f"\n📊 Current data balance:")

    # Check price vs news balance
    conn = await asyncpg.connect(**DB_CONFIG)
    price_count = await conn.fetchval("SELECT COUNT(*) FROM asset_prices WHERE symbol = 'BITCOIN'")
    await conn.close()

    print(f"   Price records (Bitcoin): {price_count}")
    print(f"   News records (all): {final_count}")

    ratio = final_count / price_count if price_count > 0 else 0

    if final_count < price_count / 2:
        print(f"\n⚠️  News data is still less than half of price data")
        print(f"   💡 Tips:")
        print(f"      - Run this script daily to continuously collect news")
        print(f"      - RSS feeds update regularly with new articles")
        print(f"      - Each run adds ~50-200 new articles")
    else:
        print(f"\n✅ Good balance! Ready to retrain with sentiment features")

    print("\n🎉 Next steps:")
    print("   1. Run this script daily to collect more news over time")
    print("   2. Retrain Phase 5: docker-compose run --rm ml-forecast python phase5_sentiment.py")


if __name__ == "__main__":
    asyncio.run(import_historical_news())
