"""
ML Forecast API Service
========================
Provides real-time price direction predictions using trained LightGBM model.

Endpoints:
- POST /predict/bitcoin - Get next 24h price direction predictions
- GET /model/info - Get model metadata
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncpg
import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

app = FastAPI(title="ML Forecast API")

# CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': 5432,
    'user': os.getenv('POSTGRES_USER', 'market_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'testpass123'),
    'database': os.getenv('POSTGRES_DB', 'market_intel')
}

MODEL_PATH = "/app/models/bitcoin_predictor.pkl"
model_cache = {}


def create_features(df):
    """Create same features as training"""
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

    return df


async def get_recent_data(symbol='BITCOIN', hours=48):
    """Fetch recent price data for prediction"""
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        rows = await conn.fetch("""
            SELECT price::float AS price,
                   volume::float AS volume,
                   timestamp
            FROM asset_prices
            WHERE symbol = $1
              AND timestamp >= NOW() - INTERVAL '1 day' * 2
            ORDER BY timestamp DESC
            LIMIT $2
        """, symbol, hours * 2)  # Get extra for feature creation

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=['price', 'volume', 'timestamp'])
        return df
    finally:
        await conn.close()


def load_model():
    """Load trained model from disk"""
    if 'model' not in model_cache:
        try:
            with open(MODEL_PATH, 'rb') as f:
                model_cache['model'] = pickle.load(f)
                model_cache['loaded_at'] = datetime.now()
        except FileNotFoundError:
            return None
    return model_cache.get('model')


class PredictionRequest(BaseModel):
    symbol: str = "bitcoin"
    horizon_hours: int = 24


class PredictionResponse(BaseModel):
    symbol: str
    predictions: list
    confidence: float
    horizon_hours: int
    model_accuracy: float
    generated_at: str


@app.post("/predict/{symbol}", response_model=PredictionResponse)
async def predict(symbol: str, horizon_hours: int = 24):
    """
    Generate price direction predictions for next N hours.

    Returns:
    - predictions: List of {timestamp, direction, probability, price_estimate}
    - direction: 'up' or 'down'
    - probability: 0.0-1.0 confidence
    """
    symbol_upper = symbol.upper()

    # Load model
    model = load_model()
    if model is None:
        raise HTTPException(status_code=503, detail="Model not trained yet. Run training first.")

    # Fetch recent data
    df = await get_recent_data(symbol_upper, hours=48)
    if df is None or len(df) < 20:
        raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}")

    # Create features
    df_features = create_features(df)
    df_features = df_features.dropna()

    if len(df_features) == 0:
        raise HTTPException(status_code=400, detail="Unable to create features from data")

    # Get latest point for prediction
    latest = df_features.iloc[-1]
    latest_price = latest['price']
    latest_ts = latest['timestamp']

    # Feature columns (same as training)
    feature_cols = [col for col in df_features.columns
                   if col not in ['timestamp', 'price_direction']]

    # Generate predictions for each hour
    predictions = []
    current_features = latest[feature_cols].values.reshape(1, -1)
    current_price = latest_price

    for i in range(1, horizon_hours + 1):
        # Predict
        prob = model.predict_proba(current_features)[0]
        direction_pred = 1 if prob[1] > 0.5 else 0
        confidence = max(prob)

        # Estimate price change (simple heuristic: ~1% per hour if confident)
        price_change_pct = (prob[1] - 0.5) * 0.02  # -1% to +1%
        estimated_price = current_price * (1 + price_change_pct)

        pred_timestamp = latest_ts + timedelta(hours=i)

        predictions.append({
            'timestamp': pred_timestamp.isoformat(),
            'hour': i,
            'direction': 'up' if direction_pred == 1 else 'down',
            'probability': float(confidence),
            'price_estimate': float(estimated_price),
            'confidence_level': 'high' if confidence > 0.65 else 'medium' if confidence > 0.55 else 'low'
        })

        # Update for next iteration
        current_price = estimated_price

    return PredictionResponse(
        symbol=symbol,
        predictions=predictions,
        confidence=float(np.mean([p['probability'] for p in predictions])),
        horizon_hours=horizon_hours,
        model_accuracy=0.558,  # From Phase 4 training
        generated_at=datetime.now().isoformat()
    )


@app.get("/model/info")
async def model_info():
    """Get model metadata"""
    model = load_model()

    if model is None:
        return {
            "status": "not_trained",
            "message": "Model not available. Run training pipeline first."
        }

    return {
        "status": "ready",
        "model_type": "LightGBM Classifier",
        "accuracy": 0.558,
        "features": 25,
        "training_phase": "Phase 4 - Hyperparameter Tuned",
        "loaded_at": model_cache.get('loaded_at').isoformat(),
        "model_path": MODEL_PATH
    }


@app.get("/health")
async def health():
    """Health check"""
    model = load_model()
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
