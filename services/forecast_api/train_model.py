"""
Train and Save Model for Production API
========================================
This script trains the LightGBM model and saves it for the forecast API.
Based on Phase 4 hyperparameter tuning results.
"""
import asyncpg
import asyncio
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
import pickle
import os
from datetime import datetime

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': 5432,
    'user': os.getenv('POSTGRES_USER', 'market_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'testpass123'),
    'database': os.getenv('POSTGRES_DB', 'market_intel')
}

MODEL_OUTPUT_PATH = '/app/models/bitcoin_predictor.pkl'


def create_features(df):
    """Create same features as prediction API"""
    df = df.sort_values('timestamp').copy()

    # Lag features
    for lag in [1, 3, 5, 10]:
        df[f'price_lag_{lag}'] = df['price'].shift(lag)
        df[f'volume_lag_{lag}'] = df['volume'].shift(lag)

    # Rolling features
    df['price_rolling_mean_5'] = df['price'].rolling(window=5).mean()
    df['price_rolling_mean_10'] = df['price'].rolling(window=10).mean()
    df['price_rolling_std_5'] = df['price'].rolling(window=5).std()
    df['volume_rolling_mean_5'] = df['volume'].rolling(window=5).mean()

    # Price changes
    df['price_pct_change_1'] = df['price'].pct_change(1)
    df['price_pct_change_3'] = df['price'].pct_change(3)
    df['price_pct_change_5'] = df['price'].pct_change(5)

    # Price vs moving average
    df['price_vs_ma5'] = df['price'] / df['price_rolling_mean_5']
    df['price_vs_ma10'] = df['price'] / df['price_rolling_mean_10']

    # Target: Did price go up next hour?
    df['price_direction'] = (df['price'].shift(-1) > df['price']).astype(int)

    return df


async def train_and_save_model():
    """Train model and save for API"""
    print("=" * 70)
    print("🤖 Training Production Model")
    print("=" * 70)

    # Connect to database
    conn = await asyncpg.connect(**DB_CONFIG)

    # Fetch data
    print("\n📊 Fetching training data...")
    rows = await conn.fetch("""
        SELECT price::float AS price,
               volume::float AS volume,
               timestamp
        FROM asset_prices
        WHERE symbol = 'BITCOIN'
        ORDER BY timestamp
    """)

    await conn.close()

    df = pd.DataFrame(rows, columns=['price', 'volume', 'timestamp'])
    print(f"   ✅ Loaded {len(df)} records")

    # Create features
    print("\n🔧 Creating features...")
    df = create_features(df)
    df = df.dropna()
    print(f"   ✅ {len(df)} samples after feature creation")

    # Split features and target
    feature_cols = [col for col in df.columns
                   if col not in ['timestamp', 'price_direction']]

    X = df[feature_cols]
    y = df['price_direction']

    # Train/test split (preserve time order)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"\n📚 Training set: {len(X_train)} samples")
    print(f"   Test set: {len(X_test)} samples")

    # Train with best config from Phase 4 (More Trees)
    print("\n⏳ Training LightGBM model (More Trees config)...")
    model = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        num_leaves=31,
        random_state=42,
        verbose=-1
    )

    model.fit(X_train, y_train)

    # Evaluate
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)

    print(f"\n✅ Training complete!")
    print(f"   Train accuracy: {train_acc * 100:.1f}%")
    print(f"   Test accuracy: {test_acc * 100:.1f}%")

    # Save model
    print(f"\n💾 Saving model to {MODEL_OUTPUT_PATH}...")
    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)

    with open(MODEL_OUTPUT_PATH, 'wb') as f:
        pickle.dump(model, f)

    print(f"   ✅ Model saved successfully")

    # Save metadata
    metadata = {
        'trained_at': datetime.now().isoformat(),
        'train_accuracy': train_acc,
        'test_accuracy': test_acc,
        'n_features': len(feature_cols),
        'n_samples': len(df),
        'model_type': 'LightGBM',
        'hyperparameters': {
            'n_estimators': 200,
            'max_depth': 5,
            'learning_rate': 0.1
        }
    }

    print("\n📋 Model Metadata:")
    for key, value in metadata.items():
        print(f"   {key}: {value}")

    print("\n🎉 Model ready for production API!")
    print(f"   Use POST /predict/bitcoin to get predictions")


if __name__ == "__main__":
    asyncio.run(train_and_save_model())
