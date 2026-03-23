"""
Phase 5: Add Sentiment Features from News
=========================================
Enhance the model by incorporating news sentiment scores!

What you'll learn:
1. How to join price data with news sentiment
2. Create sentiment-based features
3. Compare model performance with vs without sentiment
4. See if news actually predicts price movements

News sentiment = How positive/negative news articles are
Theory: Positive news → prices might go UP
        Negative news → prices might go DOWN
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import asyncpg
import asyncio
import joblib
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': 5432,
    'user': os.getenv('POSTGRES_USER', 'market_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'testpass123'),
    'database': os.getenv('POSTGRES_DB', 'market_intel')
}


async def load_data_with_sentiment():
    """Load price data and join with news sentiment"""

    print("\n📊 Loading price and sentiment data...")
    conn = await asyncpg.connect(**DB_CONFIG)

    # Get Bitcoin price data
    price_rows = await conn.fetch("""
        SELECT timestamp, price, volume, market_cap, change_24h
        FROM asset_prices
        WHERE symbol = 'BITCOIN' AND currency = 'usd'
        ORDER BY timestamp ASC
    """)

    # Get news sentiment data
    news_rows = await conn.fetch("""
        SELECT timestamp, ai_sentiment_score
        FROM market_news
        WHERE ai_sentiment_score IS NOT NULL
        ORDER BY timestamp ASC
    """)

    await conn.close()

    # Convert to DataFrames
    df_price = pd.DataFrame(price_rows, columns=['timestamp', 'price', 'volume', 'market_cap', 'change_24h'])
    df_news = pd.DataFrame(news_rows, columns=['timestamp', 'ai_sentiment_score'])

    print(f"   Price records: {len(df_price)}")
    print(f"   News records: {len(df_news)}")

    # Convert to float
    for col in ['price', 'volume', 'market_cap', 'change_24h']:
        df_price[col] = df_price[col].astype(float)
    df_news['ai_sentiment_score'] = df_news['ai_sentiment_score'].astype(float)

    # Remove duplicates
    df_price = df_price.drop_duplicates(subset=['timestamp'], keep='last')
    df_news = df_news.drop_duplicates(subset=['timestamp'], keep='last')

    return df_price, df_news


def create_price_features(df):
    """Create price-based features (same as before)"""

    # Fill missing values
    df['market_cap'] = df['market_cap'].ffill().bfill()
    df['change_24h'] = df['change_24h'].ffill().bfill()

    # Lag features
    df['price_lag_1'] = df['price'].shift(1)
    df['price_lag_3'] = df['price'].shift(3)
    df['price_lag_5'] = df['price'].shift(5)
    df['price_lag_10'] = df['price'].shift(10)
    df['volume_lag_1'] = df['volume'].shift(1)
    df['volume_lag_3'] = df['volume'].shift(3)

    # Rolling features
    df['price_rolling_mean_5'] = df['price'].rolling(window=5).mean()
    df['price_rolling_mean_10'] = df['price'].rolling(window=10).mean()
    df['volume_rolling_mean_5'] = df['volume'].rolling(window=5).mean()
    df['price_rolling_std_5'] = df['price'].rolling(window=5).std()

    # Price change features
    df['price_pct_change_1'] = df['price'].pct_change(1) * 100
    df['price_pct_change_3'] = df['price'].pct_change(3) * 100
    df['price_pct_change_5'] = df['price'].pct_change(5) * 100
    df['price_vs_ma5'] = (df['price'] / df['price_rolling_mean_5'] - 1) * 100

    # Target
    df['future_price'] = df['price'].shift(-1)
    df['target'] = (df['future_price'] > df['price']).astype(int)

    return df


def create_sentiment_features(df_price, df_news):
    """Create sentiment-based features"""

    print("\n📰 Creating sentiment features...")

    # Set timestamp as index for both
    df_price = df_price.set_index('timestamp')
    df_news = df_news.set_index('timestamp')

    # Resample news to hourly (or whatever granularity price data is)
    # Use forward fill to carry sentiment until new news arrives
    df_news_resampled = df_news.resample('1h').mean().ffill()

    # Join price with sentiment
    df = df_price.join(df_news_resampled, how='left')

    # Reset index
    df = df.reset_index()

    # Fill missing sentiment with 0 (neutral)
    df['ai_sentiment_score'] = df['ai_sentiment_score'].fillna(0)

    print(f"   ✅ Merged data: {len(df)} records")

    # Create sentiment features
    print("\n📊 Sentiment features being created:")
    print("   1. sentiment_current - Current news sentiment")
    print("   2. sentiment_lag_1 - Sentiment 1 period ago")
    print("   3. sentiment_rolling_mean_5 - Average sentiment last 5 periods")
    print("   4. sentiment_change - Change in sentiment")
    print("   5. sentiment_positive - Is sentiment positive? (1/0)")
    print("   6. sentiment_negative - Is sentiment negative? (1/0)")

    # Raw sentiment
    df['sentiment_current'] = df['ai_sentiment_score']

    # Lagged sentiment
    df['sentiment_lag_1'] = df['ai_sentiment_score'].shift(1)

    # Rolling sentiment average
    df['sentiment_rolling_mean_5'] = df['ai_sentiment_score'].rolling(window=5).mean()

    # Sentiment change
    df['sentiment_change'] = df['ai_sentiment_score'].diff()

    # Binary sentiment flags
    df['sentiment_positive'] = (df['ai_sentiment_score'] > 0.1).astype(int)
    df['sentiment_negative'] = (df['ai_sentiment_score'] < -0.1).astype(int)

    return df


def train_with_sentiment():
    """Train models with and without sentiment to compare"""

    print("=" * 70)
    print("🤖 PHASE 5: Adding Sentiment Features")
    print("=" * 70)

    # Load data
    df_price, df_news = asyncio.run(load_data_with_sentiment())

    # Create price features
    df_price = create_price_features(df_price)

    # Create sentiment features
    df_full = create_sentiment_features(df_price, df_news)

    # Drop NaN rows
    df_full = df_full.dropna()

    print(f"\n✅ Final dataset: {len(df_full)} samples")

    # Define feature sets
    price_features = [
        'price', 'volume', 'market_cap', 'change_24h',
        'price_lag_1', 'price_lag_3', 'price_lag_5', 'price_lag_10',
        'volume_lag_1', 'volume_lag_3',
        'price_rolling_mean_5', 'price_rolling_mean_10',
        'volume_rolling_mean_5', 'price_rolling_std_5',
        'price_pct_change_1', 'price_pct_change_3', 'price_pct_change_5',
        'price_vs_ma5'
    ]

    sentiment_features = [
        'sentiment_current', 'sentiment_lag_1',
        'sentiment_rolling_mean_5', 'sentiment_change',
        'sentiment_positive', 'sentiment_negative'
    ]

    all_features = price_features + sentiment_features

    # Prepare target
    y = df_full['target']

    # Split data
    split_idx = int(len(df_full) * 0.8)
    train_idx = df_full.index[:split_idx]
    test_idx = df_full.index[split_idx:]

    # ============================================
    # Model 1: Price features only (baseline)
    # ============================================
    print("\n" + "=" * 70)
    print("🔹 Model 1: Price Features Only (Baseline)")
    print("=" * 70)

    X_price_train = df_full.loc[train_idx, price_features]
    X_price_test = df_full.loc[test_idx, price_features]
    y_train = y.loc[train_idx]
    y_test = y.loc[test_idx]

    model_price = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        num_leaves=31,
        random_state=42,
        verbose=-1
    )

    print("⏳ Training...")
    model_price.fit(X_price_train, y_train)

    y_pred_price = model_price.predict(X_price_test)
    acc_price = accuracy_score(y_test, y_pred_price)
    prec_price = precision_score(y_test, y_pred_price, zero_division=0)
    rec_price = recall_score(y_test, y_pred_price, zero_division=0)

    print(f"✅ Accuracy:  {acc_price:.1%}")
    print(f"✅ Precision: {prec_price:.1%}")
    print(f"✅ Recall:    {rec_price:.1%}")

    # ============================================
    # Model 2: Price + Sentiment features
    # ============================================
    print("\n" + "=" * 70)
    print("🔹 Model 2: Price + Sentiment Features")
    print("=" * 70)

    X_full_train = df_full.loc[train_idx, all_features]
    X_full_test = df_full.loc[test_idx, all_features]

    model_full = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        num_leaves=31,
        random_state=42,
        verbose=-1
    )

    print("⏳ Training...")
    model_full.fit(X_full_train, y_train)

    y_pred_full = model_full.predict(X_full_test)
    acc_full = accuracy_score(y_test, y_pred_full)
    prec_full = precision_score(y_test, y_pred_full, zero_division=0)
    rec_full = recall_score(y_test, y_pred_full, zero_division=0)

    print(f"✅ Accuracy:  {acc_full:.1%}")
    print(f"✅ Precision: {prec_full:.1%}")
    print(f"✅ Recall:    {rec_full:.1%}")

    # ============================================
    # Comparison
    # ============================================
    print("\n" + "=" * 70)
    print("📊 Comparison: Does Sentiment Help?")
    print("=" * 70)

    print(f"\n{'Metric':<15} {'Price Only':<15} {'+ Sentiment':<15} {'Improvement'}")
    print("━" * 70)
    print(f"{'Accuracy':<15} {acc_price:<15.1%} {acc_full:<15.1%} {(acc_full - acc_price)*100:+.1f}%")
    print(f"{'Precision':<15} {prec_price:<15.1%} {prec_full:<15.1%} {(prec_full - prec_price)*100:+.1f}%")
    print(f"{'Recall':<15} {rec_price:<15.1%} {rec_full:<15.1%} {(rec_full - rec_price)*100:+.1f}%")

    # Feature importance for sentiment model
    print("\n" + "=" * 70)
    print("🔍 Feature Importance (with Sentiment)")
    print("=" * 70)

    importance_df = pd.DataFrame({
        'feature': all_features,
        'importance': model_full.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\n📊 Top 15 Most Important Features:")
    for i, row in importance_df.head(15).iterrows():
        is_sentiment = row['feature'] in sentiment_features
        emoji = "📰" if is_sentiment else "💰"
        bar = "█" * int(row['importance'] / importance_df['importance'].max() * 20)
        print(f"   {emoji} {row['feature']:30} {bar} ({row['importance']:.0f})")

    # Count sentiment in top features
    top_10_features = importance_df.head(10)['feature'].tolist()
    sentiment_in_top10 = sum(1 for f in top_10_features if f in sentiment_features)

    print(f"\n📊 Sentiment features in top 10: {sentiment_in_top10}/10")

    # ============================================
    # Save best model
    # ============================================
    print("\n" + "=" * 70)
    print("💾 Saving Model")
    print("=" * 70)

    if acc_full > acc_price:
        model_to_save = model_full
        filename = '/app/bitcoin_predictor_with_sentiment.pkl'
        print("   Using model WITH sentiment (better accuracy)")
    else:
        model_to_save = model_price
        filename = '/app/bitcoin_predictor_price_only.pkl'
        print("   Using model WITHOUT sentiment (better accuracy)")

    joblib.dump(model_to_save, filename)
    print(f"✅ Model saved to: {filename}")

    # ============================================
    # Summary
    # ============================================
    print("\n" + "=" * 70)
    print("📋 PHASE 5 COMPLETE - Summary")
    print("=" * 70)

    print(f"\n✅ Added {len(sentiment_features)} sentiment features")
    print(f"✅ Price-only accuracy: {acc_price:.1%}")
    print(f"✅ With sentiment accuracy: {acc_full:.1%}")

    if acc_full > acc_price:
        print(f"✅ Sentiment HELPS! (+{(acc_full - acc_price)*100:.1f}%)")
    else:
        print(f"⚠️  Sentiment didn't improve accuracy (try collecting more news data)")

    print("\n💡 Key Insights:")
    if sentiment_in_top10 > 0:
        print(f"   - {sentiment_in_top10} sentiment features in top 10")
        print("   - News sentiment has predictive power!")
    else:
        print("   - Sentiment features not in top 10")
        print("   - Price momentum matters more than news")

    print("\n🎯 Next Steps:")
    print("   - Collect more news over time")
    print("   - Try sentiment from multiple sources")
    print("   - Experiment with different sentiment windows")

    return model_to_save, max(acc_price, acc_full)


if __name__ == "__main__":
    model, accuracy = train_with_sentiment()
