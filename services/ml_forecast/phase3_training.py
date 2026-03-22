"""
Phase 3: Model Training with LightGBM
=====================================
Now the exciting part - training an actual ML model!

What you'll learn:
1. Split data into TRAINING and TESTING sets
2. Train a LightGBM classifier
3. Evaluate model performance (accuracy, precision, recall)
4. Understand FEATURE IMPORTANCE (which features matter most)
5. Make predictions!

WHY LIGHTGBM?
- Fast to train (even on large datasets)
- Works well with tabular data (like our price data)
- Handles missing values automatically
- Shows which features are most important
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix, classification_report
import joblib
import asyncpg
import asyncio
import os

# Database config (same as before)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': 5432,
    'user': os.getenv('POSTGRES_USER', 'market_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'testpass123'),
    'database': os.getenv('POSTGRES_DB', 'market_intel')
}


async def load_and_prepare_data():
    """Load data from database and prepare features (combines Phase 2)"""

    print("\n📊 Loading and preparing data from database...")
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

    # Create lag features
    df['price_lag_1'] = df['price'].shift(1)
    df['price_lag_3'] = df['price'].shift(3)
    df['price_lag_5'] = df['price'].shift(5)
    df['price_lag_10'] = df['price'].shift(10)
    df['volume_lag_1'] = df['volume'].shift(1)
    df['volume_lag_3'] = df['volume'].shift(3)

    # Create rolling features
    df['price_rolling_mean_5'] = df['price'].rolling(window=5).mean()
    df['price_rolling_mean_10'] = df['price'].rolling(window=10).mean()
    df['volume_rolling_mean_5'] = df['volume'].rolling(window=5).mean()
    df['price_rolling_std_5'] = df['price'].rolling(window=5).std()

    # Create price change features
    df['price_pct_change_1'] = df['price'].pct_change(1) * 100
    df['price_pct_change_3'] = df['price'].pct_change(3) * 100
    df['price_pct_change_5'] = df['price'].pct_change(5) * 100
    df['price_vs_ma5'] = (df['price'] / df['price_rolling_mean_5'] - 1) * 100

    # Create target
    df['future_price'] = df['price'].shift(-1)
    df['target'] = (df['future_price'] > df['price']).astype(int)

    # Drop NaN rows
    df = df.dropna()

    print(f"✅ Prepared {len(df)} samples with features")
    return df


def train_model():
    """Step-by-step model training"""

    print("=" * 70)
    print("🤖 PHASE 3: Model Training with LightGBM")
    print("=" * 70)

    # ============================================
    # STEP 3.1: Load and prepare the data
    # ============================================
    print("\n📊 Step 3.1: Loading and preparing data...")

    # Load directly from database (includes Phase 2 cleaning)
    df = asyncio.run(load_and_prepare_data())

    # ============================================
    # STEP 3.2: Prepare Features (X) and Target (y)
    # ============================================
    print("\n" + "=" * 70)
    print("🎯 Step 3.2: Preparing Features and Target")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   X = FEATURES (inputs) - what the model sees")
    print("   y = TARGET (output) - what the model predicts")
    print("   ")
    print("   We exclude 'timestamp', 'future_price', and 'target' from features")
    print("   because the model shouldn't 'cheat' by seeing the answer!")

    # Define which columns are features
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

    print(f"\n✅ Features (X): {X.shape[0]} samples × {X.shape[1]} features")
    print(f"✅ Target (y): {y.shape[0]} samples")
    print(f"\n📋 Feature columns:")
    for i, col in enumerate(feature_columns, 1):
        print(f"   {i:2}. {col}")

    # ============================================
    # STEP 3.3: Split into Training and Testing
    # ============================================
    print("\n" + "=" * 70)
    print("✂️  Step 3.3: Splitting Data into Train/Test Sets")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   We split data into TWO parts:")
    print("   - TRAINING SET (80%): Model learns from this")
    print("   - TESTING SET (20%): We evaluate on this (model never sees it during training)")
    print("   ")
    print("   Why? To check if model can predict NEW data it hasn't seen!")
    print("   If we test on training data, model might just 'memorize' answers.")

    # Split the data (80% train, 20% test)
    # random_state=42 makes it reproducible (same split every time)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        shuffle=False  # Don't shuffle - keep time order for time series!
    )

    print(f"\n✅ Training set: {len(X_train)} samples ({100*len(X_train)/len(X):.0f}%)")
    print(f"✅ Testing set:  {len(X_test)} samples ({100*len(X_test)/len(X):.0f}%)")

    print(f"\n📊 Target distribution in training set:")
    print(f"   UP (1):   {y_train.sum()} ({100*y_train.sum()/len(y_train):.1f}%)")
    print(f"   DOWN (0): {len(y_train) - y_train.sum()} ({100*(len(y_train)-y_train.sum())/len(y_train):.1f}%)")

    # ============================================
    # STEP 3.4: Train the LightGBM Model
    # ============================================
    print("\n" + "=" * 70)
    print("🚀 Step 3.4: Training LightGBM Model")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   LightGBM builds many 'decision trees' that work together")
    print("   Each tree learns from the mistakes of previous trees")
    print("   ")
    print("   Key parameters:")
    print("   - n_estimators: How many trees to build (100)")
    print("   - max_depth: How deep each tree can be (5)")
    print("   - learning_rate: How fast to learn (0.1)")
    print("   - num_leaves: Complexity of each tree (31)")

    # Create the model
    model = lgb.LGBMClassifier(
        n_estimators=100,      # Number of trees
        max_depth=5,           # Prevent overfitting
        learning_rate=0.1,     # Step size
        num_leaves=31,         # Tree complexity
        random_state=42,
        verbose=-1             # Suppress warnings
    )

    print("\n⏳ Training in progress...")

    # Train the model
    model.fit(X_train, y_train)

    print("✅ Model trained successfully!")

    # ============================================
    # STEP 3.5: Evaluate the Model
    # ============================================
    print("\n" + "=" * 70)
    print("📊 Step 3.5: Evaluating Model Performance")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   We evaluate on the TEST set (data model never saw)")
    print("   ")
    print("   Metrics we'll look at:")
    print("   - ACCURACY: % of predictions that were correct")
    print("   - PRECISION: When we predict UP, how often is it actually UP?")
    print("   - RECALL: Of all actual UPs, how many did we catch?")

    # Make predictions on test set
    y_pred = model.predict(X_test)

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)

    print(f"\n🎯 Model Performance on Test Set:")
    print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   ACCURACY:  {accuracy:.1%}")
    print(f"   PRECISION: {precision:.1%}")
    print(f"   RECALL:    {recall:.1%}")
    print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Confusion Matrix
    print("\n📊 Confusion Matrix:")
    print("   (Shows what model predicted vs actual)")
    cm = confusion_matrix(y_test, y_pred)

    print(f"\n                  PREDICTED")
    print(f"                  DOWN    UP")
    print(f"   ACTUAL DOWN    {cm[0][0]:3}    {cm[0][1]:3}")
    print(f"   ACTUAL UP      {cm[1][0]:3}    {cm[1][1]:3}")

    print("\n   Reading: ")
    print(f"   - {cm[0][0]} times: Predicted DOWN, was actually DOWN ✅")
    print(f"   - {cm[0][1]} times: Predicted UP, was actually DOWN ❌")
    print(f"   - {cm[1][0]} times: Predicted DOWN, was actually UP ❌")
    print(f"   - {cm[1][1]} times: Predicted UP, was actually UP ✅")

    # ============================================
    # STEP 3.6: Feature Importance
    # ============================================
    print("\n" + "=" * 70)
    print("🔍 Step 3.6: Feature Importance")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   Feature importance shows WHICH features the model relies on most")
    print("   Higher score = more important for predictions")
    print("   This helps us understand what drives price movements!")

    # Get feature importance
    importance = pd.DataFrame({
        'feature': feature_columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\n📊 Top 10 Most Important Features:")
    print("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for i, row in importance.head(10).iterrows():
        bar = "█" * int(row['importance'] / importance['importance'].max() * 20)
        print(f"   {row['feature']:25} {bar} ({row['importance']:.0f})")

    # ============================================
    # STEP 3.7: Make a Sample Prediction
    # ============================================
    print("\n" + "=" * 70)
    print("🔮 Step 3.7: Making Predictions")
    print("=" * 70)

    print("\n📝 EXPLANATION:")
    print("   Now we can use the model to predict!")
    print("   We'll show predictions for the last 5 test samples")

    # Get predictions with probabilities
    y_proba = model.predict_proba(X_test)

    print("\n📊 Last 5 Predictions vs Actual:")
    print("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("   #  | Predicted | Actual | Confidence | Result")
    print("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for i in range(-5, 0):
        pred = "UP  " if y_pred[i] == 1 else "DOWN"
        actual = "UP  " if y_test.iloc[i] == 1 else "DOWN"
        conf = max(y_proba[i]) * 100
        result = "✅" if y_pred[i] == y_test.iloc[i] else "❌"
        print(f"   {i+6}  |   {pred}   |  {actual}  |   {conf:.0f}%      |  {result}")

    # ============================================
    # STEP 3.8: Save the Model
    # ============================================
    print("\n" + "=" * 70)
    print("💾 Step 3.8: Saving the Model")
    print("=" * 70)

    # Save the model
    model_path = '/app/bitcoin_predictor.pkl'
    joblib.dump(model, model_path)
    print(f"\n✅ Model saved to: {model_path}")
    print("   You can load it later with: model = joblib.load('bitcoin_predictor.pkl')")

    # ============================================
    # SUMMARY
    # ============================================
    print("\n" + "=" * 70)
    print("📋 PHASE 3 COMPLETE - Summary")
    print("=" * 70)

    print(f"\n✅ Trained LightGBM classifier")
    print(f"✅ Model accuracy: {accuracy:.1%}")
    print(f"✅ Top feature: {importance.iloc[0]['feature']}")
    print(f"✅ Model saved for future use")

    print("\n💡 What's Next?")
    print("   - Phase 4: Use the model for real-time predictions")
    print("   - Add more features (sentiment, more coins)")
    print("   - Try different models (XGBoost, Neural Networks)")
    print("   - Backtest on historical data")

    print("\n⚠️  IMPORTANT NOTE:")
    print("   This is a LEARNING exercise! Real trading requires:")
    print("   - Much more data (months/years, not hours)")
    print("   - Rigorous backtesting")
    print("   - Risk management")
    print("   - Never invest more than you can afford to lose!")

    return model, accuracy


if __name__ == "__main__":
    model, accuracy = train_model()
