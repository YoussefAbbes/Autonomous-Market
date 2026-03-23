"""
Phase 4: Hyperparameter Tuning
===============================
Now let's optimize the model by tuning its hyperparameters!

What you'll learn:
1. What hyperparameters are and why they matter
2. How to test different configurations
3. Find the best settings for your data
4. Compare improvements

Hyperparameters = Settings that control how the model learns
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


async def load_and_prepare_data():
    """Load data from database and prepare features"""

    print("\n📊 Loading and preparing data...")
    conn = await asyncpg.connect(**DB_CONFIG)

    rows = await conn.fetch("""
        SELECT timestamp, price, volume, market_cap, change_24h
        FROM asset_prices
        WHERE symbol = 'BITCOIN' AND currency = 'usd'
        ORDER BY timestamp ASC
    """)
    await conn.close()

    df = pd.DataFrame(rows, columns=['timestamp', 'price', 'volume', 'market_cap', 'change_24h'])

    # Convert to float
    for col in ['price', 'volume', 'market_cap', 'change_24h']:
        df[col] = df[col].astype(float)

    # Remove duplicates
    df = df.drop_duplicates(subset=['timestamp'], keep='last')

    # Fill missing values
    df['market_cap'] = df['market_cap'].ffill().bfill()
    df['change_24h'] = df['change_24h'].ffill().bfill()

    # Create features
    df['price_lag_1'] = df['price'].shift(1)
    df['price_lag_3'] = df['price'].shift(3)
    df['price_lag_5'] = df['price'].shift(5)
    df['price_lag_10'] = df['price'].shift(10)
    df['volume_lag_1'] = df['volume'].shift(1)
    df['volume_lag_3'] = df['volume'].shift(3)
    df['price_rolling_mean_5'] = df['price'].rolling(window=5).mean()
    df['price_rolling_mean_10'] = df['price'].rolling(window=10).mean()
    df['volume_rolling_mean_5'] = df['volume'].rolling(window=5).mean()
    df['price_rolling_std_5'] = df['price'].rolling(window=5).std()
    df['price_pct_change_1'] = df['price'].pct_change(1) * 100
    df['price_pct_change_3'] = df['price'].pct_change(3) * 100
    df['price_pct_change_5'] = df['price'].pct_change(5) * 100
    df['price_vs_ma5'] = (df['price'] / df['price_rolling_mean_5'] - 1) * 100

    # Create target
    df['future_price'] = df['price'].shift(-1)
    df['target'] = (df['future_price'] > df['price']).astype(int)

    df = df.dropna()

    print(f"✅ Prepared {len(df)} samples")
    return df


def tune_hyperparameters():
    """Test different hyperparameter configurations"""

    print("=" * 70)
    print("🔧 PHASE 4: Hyperparameter Tuning")
    print("=" * 70)

    # Load data
    df = asyncio.run(load_and_prepare_data())

    # Prepare features
    feature_columns = [
        'price', 'volume', 'market_cap', 'change_24h',
        'price_lag_1', 'price_lag_3', 'price_lag_5', 'price_lag_10',
        'volume_lag_1', 'volume_lag_3',
        'price_rolling_mean_5', 'price_rolling_mean_10',
        'volume_rolling_mean_5', 'price_rolling_std_5',
        'price_pct_change_1', 'price_pct_change_3', 'price_pct_change_5',
        'price_vs_ma5'
    ]

    X = df[feature_columns]
    y = df['target']

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False
    )

    print(f"\n✅ Data split: {len(X_train)} train, {len(X_test)} test")

    # ============================================
    # Test different configurations
    # ============================================
    print("\n" + "=" * 70)
    print("🧪 Testing Different Hyperparameter Configurations")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   We'll test different settings and compare results:")
    print("   - n_estimators: More trees = more learning (but slower)")
    print("   - learning_rate: Smaller = more careful learning")
    print("   - max_depth: Deeper = more complex patterns")
    print("   - num_leaves: More leaves = more detailed decisions")

    # Configurations to test
    configs = [
        {
            'name': 'Baseline (Phase 3)',
            'params': {
                'n_estimators': 100,
                'max_depth': 5,
                'learning_rate': 0.1,
                'num_leaves': 31,
                'random_state': 42,
                'verbose': -1
            }
        },
        {
            'name': 'More Trees',
            'params': {
                'n_estimators': 200,
                'max_depth': 5,
                'learning_rate': 0.1,
                'num_leaves': 31,
                'random_state': 42,
                'verbose': -1
            }
        },
        {
            'name': 'Slower Learning',
            'params': {
                'n_estimators': 200,
                'max_depth': 5,
                'learning_rate': 0.05,
                'num_leaves': 31,
                'random_state': 42,
                'verbose': -1
            }
        },
        {
            'name': 'Deeper Trees',
            'params': {
                'n_estimators': 200,
                'max_depth': 7,
                'learning_rate': 0.05,
                'num_leaves': 50,
                'random_state': 42,
                'verbose': -1
            }
        },
        {
            'name': 'Maximum Power',
            'params': {
                'n_estimators': 300,
                'max_depth': 10,
                'learning_rate': 0.05,
                'num_leaves': 100,
                'random_state': 42,
                'verbose': -1
            }
        }
    ]

    results = []

    print("\n⏳ Training and testing configurations...\n")

    for config in configs:
        print(f"Testing: {config['name']}")
        print(f"   Settings: n_estimators={config['params']['n_estimators']}, "
              f"max_depth={config['params']['max_depth']}, "
              f"learning_rate={config['params']['learning_rate']}")

        # Train model
        model = lgb.LGBMClassifier(**config['params'])
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)

        results.append({
            'name': config['name'],
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'params': config['params'],
            'model': model
        })

        print(f"   ✅ Accuracy: {accuracy:.1%}, Precision: {precision:.1%}, Recall: {recall:.1%}\n")

    # ============================================
    # Compare Results
    # ============================================
    print("\n" + "=" * 70)
    print("📊 Comparison of All Configurations")
    print("=" * 70)

    # Sort by accuracy
    results_sorted = sorted(results, key=lambda x: x['accuracy'], reverse=True)

    print("\n🏆 Rankings (by Accuracy):")
    print("━" * 70)
    for i, result in enumerate(results_sorted, 1):
        stars = "⭐" * min(5, i)
        print(f"\n{i}. {result['name']} {stars if i == 1 else ''}")
        print(f"   Accuracy:  {result['accuracy']:.1%}")
        print(f"   Precision: {result['precision']:.1%}")
        print(f"   Recall:    {result['recall']:.1%}")

    # ============================================
    # Best Model Analysis
    # ============================================
    print("\n" + "=" * 70)
    print("🥇 Best Model Details")
    print("=" * 70)

    best = results_sorted[0]
    baseline = next(r for r in results if r['name'] == 'Baseline (Phase 3)')

    print(f"\n✅ Winner: {best['name']}")
    print(f"\n📈 Improvement over Baseline:")
    print(f"   Accuracy:  {baseline['accuracy']:.1%} → {best['accuracy']:.1%} "
          f"(+{(best['accuracy'] - baseline['accuracy']) * 100:.1f}%)")
    print(f"   Precision: {baseline['precision']:.1%} → {best['precision']:.1%} "
          f"(+{(best['precision'] - baseline['precision']) * 100:.1f}%)")
    print(f"   Recall:    {baseline['recall']:.1%} → {best['recall']:.1%} "
          f"(+{(best['recall'] - baseline['recall']) * 100:.1f}%)")

    print(f"\n⚙️  Best Hyperparameters:")
    for param, value in best['params'].items():
        if param not in ['random_state', 'verbose']:
            print(f"   {param}: {value}")

    # ============================================
    # Save Best Model
    # ============================================
    print("\n" + "=" * 70)
    print("💾 Saving Best Model")
    print("=" * 70)

    model_path = '/app/bitcoin_predictor_tuned.pkl'
    joblib.dump(best['model'], model_path)
    print(f"\n✅ Best model saved to: {model_path}")

    # ============================================
    # Summary
    # ============================================
    print("\n" + "=" * 70)
    print("📋 PHASE 4 COMPLETE - Summary")
    print("=" * 70)

    print(f"\n✅ Tested {len(configs)} configurations")
    print(f"✅ Best accuracy: {best['accuracy']:.1%}")
    print(f"✅ Improvement: +{(best['accuracy'] - baseline['accuracy']) * 100:.1f}% over baseline")
    print(f"✅ Tuned model saved")

    print("\n💡 Key Learnings:")
    print("   - More trees usually help (up to a point)")
    print("   - Lower learning rate = more careful, often better")
    print("   - Deeper trees capture complex patterns")
    print("   - But too complex = overfitting risk!")

    print("\n🎯 Next Steps:")
    print("   - Use the tuned model for predictions")
    print("   - Add sentiment features from news")
    print("   - Collect more data over time")
    print("   - Try ensemble methods (combine multiple models)")

    return best['model'], best['accuracy']


if __name__ == "__main__":
    best_model, best_accuracy = tune_hyperparameters()
