"""
Phase 2: Data Cleaning & Feature Engineering
=============================================
This is where the REAL magic happens in ML!

What you'll learn:
1. Handle missing values (fill or remove)
2. Create LAG FEATURES (past prices to predict future)
3. Create ROLLING AVERAGES (smoothed trends)
4. Create the TARGET variable (what we're predicting)

WHY THIS MATTERS:
- ML models can't use raw data directly
- We need to give the model "hints" about patterns
- Example: "If price went UP the last 3 hours, it might keep going up"
"""

import asyncpg
import pandas as pd
import numpy as np
import asyncio
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': 5432,
    'user': os.getenv('POSTGRES_USER', 'market_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'testpass123'),
    'database': os.getenv('POSTGRES_DB', 'market_intel')
}


async def clean_and_engineer_features():
    """Step-by-step data cleaning and feature engineering"""

    print("=" * 70)
    print("🧹 PHASE 2: Data Cleaning & Feature Engineering")
    print("=" * 70)

    # Connect to database
    print("\n📊 Step 2.1: Loading Bitcoin price data...")
    conn = await asyncpg.connect(**DB_CONFIG)

    # Get Bitcoin data ordered by time
    rows = await conn.fetch("""
        SELECT
            timestamp,
            price,
            volume,
            market_cap,
            change_24h
        FROM asset_prices
        WHERE symbol = 'BITCOIN'
          AND currency = 'usd'
        ORDER BY timestamp ASC
    """)
    await conn.close()

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=['timestamp', 'price', 'volume', 'market_cap', 'change_24h'])

    # Convert Decimal to float for ML
    for col in ['price', 'volume', 'market_cap', 'change_24h']:
        df[col] = df[col].astype(float)

    print(f"✅ Loaded {len(df)} Bitcoin price records")
    print(f"   Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")

    # ============================================
    # STEP 2.1b: Remove Duplicates
    # ============================================
    print("\n" + "=" * 70)
    print("🔄 Step 2.1b: Removing Duplicates")
    print("=" * 70)

    duplicates_count = df.duplicated(subset=['timestamp']).sum()
    print(f"\n📝 EXPLANATION:")
    print(f"   Duplicates can occur when data is collected multiple times")
    print(f"   We keep only one record per timestamp")

    print(f"\nDuplicate rows found: {duplicates_count}")

    if duplicates_count > 0:
        df = df.drop_duplicates(subset=['timestamp'], keep='last')
        print(f"✅ Removed {duplicates_count} duplicate rows")
        print(f"   Remaining records: {len(df)}")
    else:
        print("✅ No duplicates found - data is clean!")

    # ============================================
    # STEP 2.2: Handle Missing Values
    # ============================================
    print("\n" + "=" * 70)
    print("🔧 Step 2.2: Handling Missing Values")
    print("=" * 70)

    print("\nBEFORE cleaning - Missing values:")
    print(df.isnull().sum())

    # Strategy: Forward fill (use previous value)
    # This makes sense for time series - if we don't have today's market cap,
    # yesterday's is a good approximation
    print("\n📝 EXPLANATION:")
    print("   We use 'forward fill' - replace missing with the previous value")
    print("   Why? In time series, yesterday's value is usually close to today's")

    df['market_cap'] = df['market_cap'].ffill()
    df['change_24h'] = df['change_24h'].ffill()

    # If first row is missing, backfill
    df['market_cap'] = df['market_cap'].bfill()
    df['change_24h'] = df['change_24h'].bfill()

    print("\nAFTER cleaning - Missing values:")
    print(df.isnull().sum())
    print("✅ No more missing values!")

    # ============================================
    # STEP 2.3: Create LAG FEATURES
    # ============================================
    print("\n" + "=" * 70)
    print("⏮️  Step 2.3: Creating LAG FEATURES")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   LAG FEATURES = past values that might predict the future")
    print("   Example: price_lag_1 = price from 1 time period ago")
    print("   ")
    print("   Why? If price went UP the last few periods, pattern might continue")
    print("   The model learns: 'When price was X, Y, Z... next price was W'")

    # Create lag features for price
    # lag_1 = previous record, lag_3 = 3 records ago, etc.
    df['price_lag_1'] = df['price'].shift(1)   # 1 period ago
    df['price_lag_3'] = df['price'].shift(3)   # 3 periods ago
    df['price_lag_5'] = df['price'].shift(5)   # 5 periods ago
    df['price_lag_10'] = df['price'].shift(10) # 10 periods ago

    # Also create lag for volume (trading activity)
    df['volume_lag_1'] = df['volume'].shift(1)
    df['volume_lag_3'] = df['volume'].shift(3)

    print("\n✅ Created lag features:")
    print("   - price_lag_1  (price 1 period ago)")
    print("   - price_lag_3  (price 3 periods ago)")
    print("   - price_lag_5  (price 5 periods ago)")
    print("   - price_lag_10 (price 10 periods ago)")
    print("   - volume_lag_1 (volume 1 period ago)")
    print("   - volume_lag_3 (volume 3 periods ago)")

    # Show example
    print("\n📊 Example of lag features (first 5 rows with data):")
    print(df[['timestamp', 'price', 'price_lag_1', 'price_lag_3']].iloc[10:15].to_string())

    # ============================================
    # STEP 2.4: Create ROLLING AVERAGES
    # ============================================
    print("\n" + "=" * 70)
    print("📈 Step 2.4: Creating ROLLING AVERAGES")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   ROLLING AVERAGE = average of the last N values")
    print("   Example: rolling_mean_5 = average of last 5 prices")
    print("   ")
    print("   Why? Smooths out noise and shows the TREND")
    print("   If current price > rolling average → price is ABOVE trend (bullish)")
    print("   If current price < rolling average → price is BELOW trend (bearish)")

    # Create rolling averages
    df['price_rolling_mean_5'] = df['price'].rolling(window=5).mean()
    df['price_rolling_mean_10'] = df['price'].rolling(window=10).mean()
    df['volume_rolling_mean_5'] = df['volume'].rolling(window=5).mean()

    # Create rolling standard deviation (measures volatility)
    df['price_rolling_std_5'] = df['price'].rolling(window=5).std()

    print("\n✅ Created rolling features:")
    print("   - price_rolling_mean_5   (average of last 5 prices)")
    print("   - price_rolling_mean_10  (average of last 10 prices)")
    print("   - volume_rolling_mean_5  (average of last 5 volumes)")
    print("   - price_rolling_std_5    (volatility - how much price varies)")

    # ============================================
    # STEP 2.5: Create PRICE CHANGE features
    # ============================================
    print("\n" + "=" * 70)
    print("📉 Step 2.5: Creating PRICE CHANGE Features")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   Instead of absolute price, we calculate % CHANGE")
    print("   Why? A $100 move means different things at $10 vs $70,000")
    print("   Percentage change normalizes this")

    # Price change from previous period (percentage)
    df['price_pct_change_1'] = df['price'].pct_change(1) * 100
    df['price_pct_change_3'] = df['price'].pct_change(3) * 100
    df['price_pct_change_5'] = df['price'].pct_change(5) * 100

    # Price relative to rolling average (is it above or below trend?)
    df['price_vs_ma5'] = (df['price'] / df['price_rolling_mean_5'] - 1) * 100

    print("\n✅ Created price change features:")
    print("   - price_pct_change_1  (% change from 1 period ago)")
    print("   - price_pct_change_3  (% change from 3 periods ago)")
    print("   - price_pct_change_5  (% change from 5 periods ago)")
    print("   - price_vs_ma5        (% difference from 5-period average)")

    # ============================================
    # STEP 2.6: Create the TARGET variable
    # ============================================
    print("\n" + "=" * 70)
    print("🎯 Step 2.6: Creating the TARGET Variable")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   TARGET = what we want to PREDICT")
    print("   We'll predict: 'Will price go UP or DOWN in the next period?'")
    print("   ")
    print("   target = 1 if next price > current price (UP)")
    print("   target = 0 if next price <= current price (DOWN)")

    # The target is the FUTURE price direction
    # shift(-1) looks at the NEXT row
    df['future_price'] = df['price'].shift(-1)
    df['target'] = (df['future_price'] > df['price']).astype(int)

    print("\n✅ Created target variable:")
    print("   - target = 1 → Price went UP")
    print("   - target = 0 → Price went DOWN or stayed same")

    # ============================================
    # STEP 2.7: Clean up - Remove rows with NaN
    # ============================================
    print("\n" + "=" * 70)
    print("🧽 Step 2.7: Final Cleanup")
    print("=" * 70)

    print(f"\nBefore cleanup: {len(df)} rows")

    # The first rows have NaN because we can't calculate lag/rolling for them
    # The last row has NaN target (we don't know future price)
    df_clean = df.dropna()

    print(f"After cleanup: {len(df_clean)} rows")
    print(f"   (Removed {len(df) - len(df_clean)} rows with incomplete data)")

    # ============================================
    # SUMMARY
    # ============================================
    print("\n" + "=" * 70)
    print("📋 PHASE 2 COMPLETE - Summary")
    print("=" * 70)

    print("\n✅ Features we created for ML:")
    feature_cols = [col for col in df_clean.columns if col not in ['timestamp', 'future_price', 'target']]
    for i, col in enumerate(feature_cols, 1):
        print(f"   {i:2}. {col}")

    print(f"\n✅ Total features: {len(feature_cols)}")
    print(f"✅ Total samples: {len(df_clean)}")

    # Target distribution
    up_count = df_clean['target'].sum()
    down_count = len(df_clean) - up_count
    print(f"\n📊 Target distribution:")
    print(f"   UP (1):   {up_count} ({100*up_count/len(df_clean):.1f}%)")
    print(f"   DOWN (0): {down_count} ({100*down_count/len(df_clean):.1f}%)")

    # Save the cleaned data for Phase 3
    df_clean.to_csv('/app/cleaned_data.csv', index=False)
    print("\n💾 Saved cleaned data to: cleaned_data.csv")

    print("\n" + "=" * 70)
    print("👉 Ready for Phase 3: Model Training!")
    print("=" * 70)

    # Show sample of final data
    print("\n📊 Sample of final cleaned data (features + target):")
    display_cols = ['timestamp', 'price', 'price_lag_1', 'price_pct_change_1',
                    'price_rolling_mean_5', 'price_vs_ma5', 'target']
    print(df_clean[display_cols].tail(5).to_string())

    return df_clean


if __name__ == "__main__":
    asyncio.run(clean_and_engineer_features())
