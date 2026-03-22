# Phase 2 & Beyond: Roadmap

This document outlines the next features and enhancements for the Autonomous Market Intelligence system.

---

## Table of Contents

- [B) Connect Claude Desktop via MCP](#b-connect-claude-desktop-via-mcp)
- [C) Phase 2: ML Forecasting Models](#c-phase-2-ml-forecasting-models)
  - [Option 1: ARIMA](#option-1-arima)
  - [Option 2: LSTM Neural Network](#option-2-lstm-neural-network)
- [D) Additional Features](#d-additional-features)
  - [1. More Coins](#1-more-coins)
  - [2. Dashboard](#2-dashboard)
  - [3. Alerts & Notifications](#3-alerts--notifications)
- [Implementation Priority](#implementation-priority)

---

## B) Connect Claude Desktop via MCP

### Overview
Enable Claude Desktop to query your live market data using the Model Context Protocol (MCP). This allows natural language queries against your database.

### What Is MCP?
The Model Context Protocol is Anthropic's standard for connecting AI assistants to external data sources. Your MCP server (running at port 8081) exposes:
- **Resource:** `latest_market_data` - Real-time prices and sentiment
- **Tool:** `get_market_forecast` - Price predictions

### Setup Steps

**1. Install Claude Desktop**
- Download: https://claude.ai/download
- Available for Windows, Mac, Linux

**2. Configure MCP Server**

Edit the config file:
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac/Linux:** `~/.config/Claude/claude_desktop_config.json`

Add this configuration:
```json
{
  "mcpServers": {
    "autonomous-market": {
      "command": "curl",
      "args": ["-X", "POST", "http://localhost:8081/mcp"],
      "transport": "streamable-http"
    }
  }
}
```

**3. Restart Claude Desktop**

### Usage Examples

Once configured, you can ask Claude:

> "What's the current Bitcoin price in my database?"

> "Show me the sentiment analysis for today's crypto news"

> "Forecast Ethereum price for the next 24 hours"

> "Which coin has the most positive sentiment today?"

### Expected Results

Claude will:
- ✅ Execute SQL queries against your PostgreSQL database
- ✅ Return formatted analysis of prices and sentiment
- ✅ Generate forecasts using your prediction tools
- ✅ Provide insights based on live data

### Time Estimate
**10 minutes** (configuration only)

### Difficulty
**Easy** - No coding required, just config file edits

---

## C) Phase 2: ML Forecasting Models

### Current State
The `get_market_forecast` tool currently uses **simple linear extrapolation** - it draws a line between the last 2 price points. This is a baseline placeholder.

### Goal
Replace linear extrapolation with real machine learning models trained on historical data.

---

## Option 1: ARIMA

### What is ARIMA?
**AutoRegressive Integrated Moving Average** - A statistical model for time-series forecasting.

**Characteristics:**
- Statistical approach (not neural network)
- Analyzes patterns, trends, seasonality
- Industry-standard for financial forecasting
- Fast training, interpretable results
- Works well with limited data (30+ days)

### Architecture

```
services/
├── forecast_api/
│   ├── Dockerfile
│   ├── main.py              # FastAPI endpoints
│   ├── models/
│   │   └── arima.py         # ARIMA training & inference
│   ├── training/
│   │   ├── train_arima.py   # Training script
│   │   └── datasets.py      # Data preprocessing
│   ├── model_cache/         # Saved model artifacts
│   └── requirements.txt     # statsmodels, pmdarima, etc.
```

### Implementation Plan

**1. Create Forecast API Service**

`services/forecast_api/main.py`:
```python
from fastapi import FastAPI, HTTPException
from pmdarima import auto_arima
import pandas as pd
import asyncpg

app = FastAPI()

@app.post("/train")
async def train_model(symbol: str, days: int = 30):
    """Train ARIMA model on historical data"""
    # Fetch historical prices
    df = await fetch_prices(symbol, days)

    # Auto-tune ARIMA parameters (p, d, q)
    model = auto_arima(
        df['price'],
        seasonal=False,
        stepwise=True,
        suppress_warnings=True,
        error_action='ignore'
    )

    # Save model
    model.save(f"model_cache/{symbol}_arima.pkl")

    return {
        "status": "trained",
        "symbol": symbol,
        "order": model.order,
        "aic": model.aic()
    }

@app.post("/forecast")
async def forecast(symbol: str, horizon_hours: int = 24):
    """Generate forecast for symbol"""
    # Load trained model
    model = load_model(f"model_cache/{symbol}_arima.pkl")

    # Generate forecast with confidence intervals
    forecast, conf_int = model.predict(
        n_periods=horizon_hours,
        return_conf_int=True
    )

    return {
        "symbol": symbol,
        "horizon_hours": horizon_hours,
        "forecast_prices": forecast.tolist(),
        "confidence_lower": conf_int[:, 0].tolist(),
        "confidence_upper": conf_int[:, 1].tolist(),
        "method": "ARIMA"
    }

@app.get("/model-info/{symbol}")
async def model_info(symbol: str):
    """Return model parameters and diagnostics"""
    model = load_model(f"model_cache/{symbol}_arima.pkl")
    return {
        "order": model.order,
        "aic": model.aic(),
        "bic": model.bic(),
        "trained_at": get_train_timestamp(symbol)
    }
```

**2. Add to Docker Compose**

`docker-compose.yml`:
```yaml
forecast-api:
  build: ./services/forecast_api
  container_name: market-forecast-api
  restart: unless-stopped
  depends_on:
    postgres:
      condition: service_healthy
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
  ports:
    - "8002:8002"
  networks:
    - market_net
  volumes:
    - forecast_models:/app/model_cache
```

**3. Create n8n Workflow: "Retrain ARIMA Models Daily"**

Schedule: Daily at 7:00 AM UTC (after quality check)

Flow:
```
[Schedule Trigger]
    │
    ├──▶ [HTTP: Train BTC] ──▶ POST http://forecast-api:8002/train {"symbol": "bitcoin"}
    │
    ├──▶ [HTTP: Train ETH] ──▶ POST http://forecast-api:8002/train {"symbol": "ethereum"}
    │
    └──▶ [HTTP: Train SOL] ──▶ POST http://forecast-api:8002/train {"symbol": "solana"}
```

**4. Update MCP Server**

`services/mcp_server/main.py`:
```python
@mcp.tool()
async def get_market_forecast(symbol, horizon_hours=24):
    """Get ARIMA-based forecast"""
    # Call forecast API instead of linear extrapolation
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://forecast-api:8002/forecast",
            json={"symbol": symbol, "horizon_hours": horizon_hours}
        )
        data = response.json()

    return {
        "symbol": data["symbol"],
        "horizon_hours": horizon_hours,
        "forecast_prices": data["forecast_prices"],
        "confidence_interval": {
            "lower": data["confidence_lower"],
            "upper": data["confidence_upper"]
        },
        "method": "ARIMA (AutoRegressive Integrated Moving Average)",
        "disclaimer": "Forecasts are probabilistic and not financial advice."
    }
```

### Key Features

- **Auto-tuning:** `auto_arima` finds optimal parameters
- **Confidence intervals:** 95% prediction bands
- **Daily retraining:** Models stay fresh with new data
- **Multi-step forecasts:** Predict next N hours, not just one point

### Time Estimate
**4-6 hours** (coding, testing, integration)

### Difficulty
**Medium** - Requires understanding of time-series concepts

---

## Option 2: LSTM Neural Network

### What is LSTM?
**Long Short-Term Memory** - A recurrent neural network designed for sequential data.

**Characteristics:**
- Deep learning approach
- Learns complex non-linear patterns
- Better for long-term dependencies
- Requires more data (60+ days) and compute
- Less interpretable ("black box")

### Architecture

Add to existing `forecast_api`:
```
services/forecast_api/
├── models/
│   ├── arima.py      # Existing
│   └── lstm.py       # NEW: Neural network model
├── training/
│   ├── train_lstm.py # Training script
│   └── datasets.py   # Preprocessing & feature engineering
└── model_cache/
    ├── btc_arima.pkl
    └── btc_lstm.pth  # PyTorch checkpoint
```

### Implementation Plan

**1. Define LSTM Model**

`services/forecast_api/models/lstm.py`:
```python
import torch
import torch.nn as nn

class CryptoLSTM(nn.Module):
    def __init__(self, input_size=5, hidden_size=64, num_layers=2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # LSTM layers
        self.lstm = nn.LSTM(
            input_size,
            hidden_size,
            num_layers,
            batch_first=True,
            dropout=0.2
        )

        # Fully connected output layer
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        # x shape: (batch, sequence_length, features)
        lstm_out, _ = self.lstm(x)

        # Use last hidden state
        prediction = self.fc(lstm_out[:, -1, :])
        return prediction
```

**2. Training Script**

`services/forecast_api/training/train_lstm.py`:
```python
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd

def create_sequences(df, lookback=24):
    """Create sequences for LSTM training"""
    X, y = [], []

    # Features: [price, volume, sentiment, hour_of_day, day_of_week]
    features = df[['price', 'volume', 'sentiment', 'hour', 'weekday']].values

    for i in range(len(df) - lookback):
        X.append(features[i:i+lookback])
        y.append(features[i+lookback, 0])  # Predict next price

    return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)

def train_lstm(symbol: str, epochs=100):
    # Fetch 60 days of data
    df = fetch_historical_data(symbol, days=60)

    # Add features
    df['hour'] = df['timestamp'].dt.hour / 24.0
    df['weekday'] = df['timestamp'].dt.dayofweek / 7.0
    df['sentiment'] = merge_sentiment_scores(df)

    # Normalize
    scaler = StandardScaler()
    df[['price', 'volume', 'sentiment']] = scaler.fit_transform(
        df[['price', 'volume', 'sentiment']]
    )

    # Create sequences
    X_train, y_train = create_sequences(df, lookback=24)

    # DataLoader
    dataset = TensorDataset(X_train, y_train)
    loader = DataLoader(dataset, batch_size=32, shuffle=True)

    # Initialize model
    model = CryptoLSTM(input_size=5, hidden_size=64, num_layers=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_fn = nn.MSELoss()

    # Training loop
    for epoch in range(epochs):
        total_loss = 0
        for X_batch, y_batch in loader:
            optimizer.zero_grad()
            predictions = model(X_batch)
            loss = loss_fn(predictions.squeeze(), y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(loader):.4f}")

    # Save model
    torch.save({
        'model_state_dict': model.state_dict(),
        'scaler': scaler
    }, f"model_cache/{symbol}_lstm.pth")

    return {"status": "trained", "epochs": epochs, "final_loss": total_loss/len(loader)}
```

**3. Add Endpoint**

`services/forecast_api/main.py`:
```python
@app.post("/train-lstm")
async def train_lstm_model(symbol: str, epochs: int = 100):
    """Train LSTM model (takes ~10 minutes)"""
    result = await asyncio.to_thread(train_lstm, symbol, epochs)
    return result

@app.post("/forecast-lstm")
async def forecast_lstm(symbol: str, horizon_hours: int = 24):
    """Generate LSTM forecast"""
    # Load model
    checkpoint = torch.load(f"model_cache/{symbol}_lstm.pth")
    model = CryptoLSTM()
    model.load_state_dict(checkpoint['model_state_dict'])
    scaler = checkpoint['scaler']

    # Get last 24 hours of data
    recent_data = fetch_recent_data(symbol, hours=24)

    # Predict next N hours
    predictions = []
    for i in range(horizon_hours):
        X = prepare_input(recent_data, scaler)
        pred = model(X).item()
        predictions.append(scaler.inverse_transform([[pred, 0, 0]])[0, 0])

    return {
        "symbol": symbol,
        "forecast_prices": predictions,
        "method": "LSTM (Neural Network)"
    }
```

**4. Create n8n Workflow: "Train LSTM Weekly"**

Schedule: Every Sunday at 2:00 AM

Flow:
```
[Schedule Trigger]
    │
    └──▶ [HTTP: Train LSTM] ──▶ POST http://forecast-api:8002/train-lstm
              (takes 10 minutes)      {"symbol": "bitcoin", "epochs": 100}
```

### Key Features

- **Multi-feature input:** Price, volume, sentiment, time-of-day
- **Sequence learning:** Uses last 24 hours to predict next hour
- **Non-linear patterns:** Captures complex market dynamics
- **GPU acceleration:** Optional, faster with CUDA

### Comparison: ARIMA vs LSTM

| Feature | ARIMA | LSTM |
|---------|-------|------|
| **Accuracy** | Good | Better |
| **Training Time** | 30 seconds | 10 minutes |
| **Data Needed** | 30+ days | 60+ days |
| **Interpretability** | High | Low |
| **Complexity** | Medium | High |
| **Maintenance** | Daily retrain | Weekly retrain |
| **Best For** | Short-term trends | Complex patterns |

### Time Estimate
**8-12 hours** (neural network setup, training pipeline, testing)

### Difficulty
**Hard** - Requires deep learning knowledge

---

## D) Additional Features

---

## 1. More Coins

### Goal
Track additional cryptocurrencies beyond BTC, ETH, SOL.

### Implementation

**Step 1:** Update n8n variable

In n8n: Settings → Variables → `TRACKED_ASSETS`

Change from:
```
bitcoin,ethereum,solana
```

To:
```
bitcoin,ethereum,solana,cardano,polkadot,avalanche-2,chainlink,polygon,algorand,cosmos
```

**Step 2:** Done! No code changes needed.

### CoinGecko API IDs

| Symbol | CoinGecko ID | Symbol | CoinGecko ID |
|--------|--------------|--------|--------------|
| BTC | `bitcoin` | ADA | `cardano` |
| ETH | `ethereum` | DOT | `polkadot` |
| SOL | `solana` | AVAX | `avalanche-2` |
| XRP | `ripple` | LINK | `chainlink` |
| BNB | `binancecoin` | MATIC | `polygon` |

### Benefits

- 📊 More data for comparison
- 🔍 Cross-asset correlation analysis
- 💡 Portfolio diversification insights
- 🎯 Better ML model training (more samples)

### Time Estimate
**2 minutes**

### Difficulty
**Trivial** - Configuration only

---

## 2. Dashboard

### Goal
Build a real-time web dashboard to visualize market data, sentiment, and forecasts.

### Technology Options

#### Option A: Streamlit (Recommended for Speed)

**Pros:**
- Python-native (no JavaScript)
- Built-in components (charts, metrics, tables)
- Auto-refresh support
- 1-file prototype possible

**Cons:**
- Less customizable than React
- Streamlit-specific UX patterns

**Example Implementation:**

`services/dashboard/app.py`:
```python
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import psycopg2

st.set_page_config(page_title="Market Intelligence", layout="wide")

# Database connection
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="postgres",
        database="market_intel",
        user="market_user",
        password=st.secrets["POSTGRES_PASSWORD"]
    )

# Header
st.title("🔮 Autonomous Market Intelligence")

# Metrics row
col1, col2, col3, col4 = st.columns(4)

conn = get_connection()

# Latest prices
prices = pd.read_sql("""
    SELECT symbol, price, timestamp
    FROM latest_asset_prices
    ORDER BY timestamp DESC
""", conn)

btc_price = prices[prices['symbol'] == 'BITCOIN']['price'].iloc[0]
col1.metric("Bitcoin", f"${btc_price:,.0f}", delta="+2.3%")

# Sentiment
sentiment = pd.read_sql("""
    SELECT AVG(ai_sentiment_score)::float as avg_sentiment
    FROM market_news
    WHERE timestamp >= NOW() - INTERVAL '24 hours'
""", conn)
avg_sent = sentiment['avg_sentiment'].iloc[0]
col2.metric("24h Sentiment", f"{avg_sent:.2f}", delta=f"{avg_sent:.2f}")

# Article count
articles = pd.read_sql("""
    SELECT COUNT(*) as count
    FROM market_news
    WHERE timestamp >= NOW() - INTERVAL '24 hours'
""", conn)
col3.metric("Articles Today", articles['count'].iloc[0])

# Data freshness
freshness = pd.read_sql("""
    SELECT EXTRACT(EPOCH FROM (NOW() - MAX(timestamp)))/60 as minutes_ago
    FROM asset_prices
""", conn)
col4.metric("Last Update", f"{freshness['minutes_ago'].iloc[0]:.0f} min ago")

# Price chart
st.subheader("📈 Price Trends (24h)")

price_history = pd.read_sql("""
    SELECT symbol, price, timestamp
    FROM asset_prices
    WHERE timestamp >= NOW() - INTERVAL '24 hours'
    ORDER BY timestamp
""", conn)

fig = go.Figure()
for symbol in price_history['symbol'].unique():
    data = price_history[price_history['symbol'] == symbol]
    fig.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['price'],
        name=symbol,
        mode='lines'
    ))

fig.update_layout(height=400, xaxis_title="Time", yaxis_title="Price (USD)")
st.plotly_chart(fig, use_container_width=True)

# News feed
st.subheader("📰 Latest News with Sentiment")

news = pd.read_sql("""
    SELECT headline, ai_sentiment_score, timestamp, url
    FROM market_news
    ORDER BY timestamp DESC
    LIMIT 10
""", conn)

for _, row in news.iterrows():
    sentiment_color = "🟢" if row['ai_sentiment_score'] > 0.3 else "🔴" if row['ai_sentiment_score'] < -0.3 else "⚪"
    st.markdown(f"{sentiment_color} **{row['headline']}** ({row['ai_sentiment_score']:.2f})")
    st.caption(f"{row['timestamp']} • [Read more]({row['url']})")

# Auto-refresh every 60 seconds
st_autorefresh(interval=60000, key="auto_refresh")

conn.close()
```

**Add to Docker Compose:**

```yaml
dashboard:
  build: ./services/dashboard
  container_name: market-dashboard
  restart: unless-stopped
  depends_on:
    - postgres
  environment:
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  ports:
    - "8501:8501"
  networks:
    - market_net
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Access:**
```
http://localhost:8501
```

#### Option B: React + FastAPI (Production Quality)

**Architecture:**
```
services/dashboard/
├── backend/
│   ├── main.py              # FastAPI aggregation API
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── PriceChart.tsx
    │   │   ├── SentimentGauge.tsx
    │   │   ├── NewsFeed.tsx
    │   │   └── ForecastViz.tsx
    │   ├── App.tsx
    │   └── index.tsx
    ├── package.json
    └── Dockerfile
```

**Backend API:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.get("/api/summary")
async def get_summary():
    return {
        "latest_prices": fetch_latest_prices(),
        "sentiment_today": fetch_sentiment_summary(),
        "article_count": fetch_article_count(),
        "last_update": fetch_last_update()
    }

@app.get("/api/price-history/{symbol}")
async def get_price_history(symbol: str, hours: int = 24):
    return fetch_price_history(symbol, hours)

@app.get("/api/news")
async def get_news(limit: int = 20):
    return fetch_recent_news(limit)
```

**Frontend (React + Recharts):**
```tsx
import { LineChart, Line, XAxis, YAxis } from 'recharts';

function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('http://localhost:8003/api/summary')
      .then(r => r.json())
      .then(setData);
  }, []);

  return (
    <div className="dashboard">
      <h1>Market Intelligence</h1>
      <div className="metrics">
        <MetricCard title="Bitcoin" value={data?.latest_prices.BTC} />
        <MetricCard title="Sentiment" value={data?.sentiment_today} />
      </div>
      <LineChart width={800} height={300} data={priceHistory}>
        <Line type="monotone" dataKey="price" stroke="#8884d8" />
        <XAxis dataKey="timestamp" />
        <YAxis />
      </LineChart>
    </div>
  );
}
```

### Dashboard Features

| Feature | Description |
|---------|-------------|
| **Live Metrics** | Current prices, sentiment, data freshness |
| **Price Charts** | Line/candlestick charts with Plotly/Recharts |
| **News Feed** | Latest headlines with sentiment color-coding |
| **Forecast Overlay** | Show predictions vs actual (if Phase 2 done) |
| **Multi-symbol View** | Compare BTC vs ETH vs SOL side-by-side |
| **Alert History** | Display recent alerts triggered |
| **Data Quality** | Show metrics from daily quality check |

### Time Estimate
- **Streamlit:** 3-4 hours
- **React:** 5-8 hours

### Difficulty
- **Streamlit:** Medium
- **React:** Medium-Hard

---

## 3. Alerts & Notifications

### Goal
Get real-time notifications when significant market events occur.

### Alert Types

| Alert | Trigger Condition | Example |
|-------|-------------------|---------|
| **Price Spike** | >5% change in 1 hour | "🚨 BTC spiked +7.2% to $75,500" |
| **Price Drop** | <-5% change in 1 hour | "⚠️ ETH dropped -6.1% to $2,890" |
| **Sentiment Crash** | Avg sentiment < -0.5 | "📉 High bearish sentiment: -0.67" |
| **Sentiment Surge** | Avg sentiment > 0.5 | "📈 High bullish sentiment: +0.73" |
| **Forecast Divergence** | Actual differs >10% from forecast | "🎯 BTC actual $68k vs predicted $75k" |
| **Data Stale** | No new data for 2+ hours | "⏰ Price data stale: 3.2h since update" (already have this!) |

### Implementation Options

#### Option A: n8n Alert Workflow (Easiest)

**Workflow: "Price Alert Monitor"**

Schedule: Every 15 minutes

```
[Schedule Trigger]
    │
    ▼
[Postgres: Query Latest & 1h Ago]
    │
    ▼
[Code: Calculate % Change]
    │
    ▼
[IF: price_change > 5% OR price_change < -5%]
    │
    ├──▶ TRUE: [Slack Webhook] → Send alert
    │
    └──▶ FALSE: [No Action]
```

**Code Node:**
```javascript
const latest = $('Query Latest').first().json;
const prev = $('Query 1h Ago').first().json;

const change_pct = ((latest.price - prev.price) / prev.price) * 100;

return [{
  json: {
    symbol: latest.symbol,
    current_price: latest.price,
    prev_price: prev.price,
    change_pct: change_pct,
    alert: Math.abs(change_pct) > 5
  }
}];
```

**Slack Webhook Node:**
```json
{
  "text": "🚨 {{ $json.symbol }} {{ $json.change_pct > 0 ? 'spiked' : 'dropped' }} {{ Math.abs($json.change_pct).toFixed(1) }}% to ${{ $json.current_price }}"
}
```

#### Option B: Python Alert Service (More Flexible)

**Architecture:**
```
services/alert_service/
├── Dockerfile
├── main.py           # Main monitoring loop
├── monitors/
│   ├── price_monitor.py
│   ├── sentiment_monitor.py
│   └── forecast_monitor.py
├── notifiers/
│   ├── slack.py
│   ├── discord.py
│   ├── email.py
│   └── telegram.py
└── requirements.txt
```

**Implementation:**

`services/alert_service/main.py`:
```python
import asyncio
from monitors import PriceMonitor, SentimentMonitor
from notifiers import SlackNotifier, DiscordNotifier

async def main():
    # Initialize monitors
    price_monitor = PriceMonitor(threshold=0.05)  # 5%
    sentiment_monitor = SentimentMonitor(threshold=0.5)

    # Initialize notifiers
    slack = SlackNotifier(webhook_url=os.getenv("SLACK_WEBHOOK_URL"))
    discord = DiscordNotifier(webhook_url=os.getenv("DISCORD_WEBHOOK_URL"))

    while True:
        # Check for price alerts
        price_alerts = await price_monitor.check()
        for alert in price_alerts:
            await slack.send(alert)
            await save_alert_to_db(alert)

        # Check for sentiment alerts
        sentiment_alerts = await sentiment_monitor.check()
        for alert in sentiment_alerts:
            await discord.send(alert)

        # Wait 15 minutes
        await asyncio.sleep(900)

if __name__ == "__main__":
    asyncio.run(main())
```

`services/alert_service/monitors/price_monitor.py`:
```python
class PriceMonitor:
    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold

    async def check(self):
        alerts = []

        # Get latest and 1h ago prices
        latest = await fetch_latest_prices()
        prev = await fetch_prices_1h_ago()

        for symbol in latest:
            change_pct = (latest[symbol] - prev[symbol]) / prev[symbol]

            if abs(change_pct) > self.threshold:
                severity = "critical" if abs(change_pct) > 0.1 else "warning"
                alerts.append({
                    "type": "price_spike" if change_pct > 0 else "price_drop",
                    "symbol": symbol,
                    "current_price": latest[symbol],
                    "change_pct": change_pct * 100,
                    "severity": severity,
                    "message": f"{'🚨' if severity == 'critical' else '⚠️'} {symbol} {'spiked' if change_pct > 0 else 'dropped'} {abs(change_pct)*100:.1f}% to ${latest[symbol]:,.2f}"
                })

        return alerts
```

`services/alert_service/notifiers/slack.py`:
```python
import aiohttp

class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, alert: dict):
        async with aiohttp.ClientSession() as session:
            await session.post(
                self.webhook_url,
                json={
                    "text": alert["message"],
                    "attachments": [{
                        "color": "danger" if alert["severity"] == "critical" else "warning",
                        "fields": [
                            {"title": "Symbol", "value": alert["symbol"], "short": True},
                            {"title": "Change", "value": f"{alert['change_pct']:+.2f}%", "short": True},
                            {"title": "Price", "value": f"${alert['current_price']:,.2f}", "short": True}
                        ]
                    }]
                }
            )
```

#### Option C: PostgreSQL Triggers (Database-Level)

**Create Alert Table:**
```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,           -- 'price_spike', 'sentiment_crash', etc.
    symbol VARCHAR(20),
    message TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'info', -- 'info', 'warning', 'critical'
    metadata JSONB,                      -- Additional context
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX idx_alerts_notified ON alerts(notified) WHERE notified = FALSE;
```

**Trigger Function:**
```sql
CREATE OR REPLACE FUNCTION check_price_spike()
RETURNS TRIGGER AS $$
DECLARE
    prev_price NUMERIC;
    change_pct NUMERIC;
BEGIN
    -- Get previous price for same symbol
    SELECT price INTO prev_price
    FROM asset_prices
    WHERE symbol = NEW.symbol
      AND timestamp < NEW.timestamp
    ORDER BY timestamp DESC
    LIMIT 1;

    IF prev_price IS NOT NULL THEN
        change_pct := ((NEW.price - prev_price) / prev_price) * 100;

        -- Check if spike exceeds threshold
        IF ABS(change_pct) > 5 THEN
            INSERT INTO alerts (type, symbol, message, severity, metadata)
            VALUES (
                CASE WHEN change_pct > 0 THEN 'price_spike' ELSE 'price_drop' END,
                NEW.symbol,
                format('%s %s %.1f%% to $%.2f',
                       NEW.symbol,
                       CASE WHEN change_pct > 0 THEN 'spiked' ELSE 'dropped' END,
                       ABS(change_pct),
                       NEW.price),
                CASE WHEN ABS(change_pct) > 10 THEN 'critical' ELSE 'warning' END,
                jsonb_build_object(
                    'current_price', NEW.price,
                    'prev_price', prev_price,
                    'change_pct', change_pct
                )
            );
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger
CREATE TRIGGER price_spike_trigger
AFTER INSERT ON asset_prices
FOR EACH ROW
EXECUTE FUNCTION check_price_spike();
```

**Notifier Process:**

`services/alert_service/db_notifier.py`:
```python
async def process_pending_alerts():
    """Poll alerts table and send notifications"""
    while True:
        alerts = await fetch_unnotified_alerts()

        for alert in alerts:
            # Send to appropriate channel based on severity
            if alert['severity'] == 'critical':
                await slack.send(alert)
                await discord.send(alert)
            elif alert['severity'] == 'warning':
                await slack.send(alert)

            # Mark as notified
            await mark_alert_notified(alert['id'])

        await asyncio.sleep(60)  # Check every minute
```

### Notification Channels

#### 1. Slack

**Setup:**
1. Create Slack app: https://api.slack.com/apps
2. Enable Incoming Webhooks
3. Add webhook URL to `.env`: `SLACK_WEBHOOK_URL=https://hooks.slack.com/...`

**Format:**
```python
import requests

requests.post(SLACK_WEBHOOK_URL, json={
    "text": "🚨 Bitcoin spiked +7.2% to $75,500!",
    "attachments": [{
        "color": "danger",
        "fields": [
            {"title": "Current Price", "value": "$75,500", "short": True},
            {"title": "Change", "value": "+7.2%", "short": True}
        ]
    }]
})
```

#### 2. Discord

**Setup:**
1. Create webhook in Discord server settings
2. Add to `.env`: `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`

**Format:**
```python
requests.post(DISCORD_WEBHOOK_URL, json={
    "content": "⚠️ High bearish sentiment detected: avg -0.67",
    "embeds": [{
        "title": "Sentiment Alert",
        "description": "20 articles analyzed",
        "color": 0xFF0000,  # Red
        "fields": [
            {"name": "Timeframe", "value": "Last 24 hours", "inline": True},
            {"name": "Article Count", "value": "20", "inline": True}
        ]
    }]
})
```

#### 3. Email (via SendGrid)

**Setup:**
```bash
pip install sendgrid
```

```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email='alerts@yourdomain.com',
    to_emails='you@example.com',
    subject='Market Alert: BTC Spike',
    html_content=f'<strong>Bitcoin spiked +7.2%</strong> to $75,500'
)

sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
sg.send(message)
```

#### 4. Telegram Bot

**Setup:**
1. Create bot via @BotFather
2. Get bot token and chat ID
3. Add to `.env`

```python
import telegram

bot = telegram.Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
bot.send_message(
    chat_id=os.getenv('TELEGRAM_CHAT_ID'),
    text="🔔 Ethereum dropped -6.1% to $2,890"
)
```

### Alert Dashboard Integration

Add alerts view to dashboard:

```python
# In Streamlit dashboard
st.subheader("🔔 Recent Alerts")

alerts = pd.read_sql("""
    SELECT type, symbol, message, severity, created_at
    FROM alerts
    ORDER BY created_at DESC
    LIMIT 10
""", conn)

for _, alert in alerts.iterrows():
    icon = "🚨" if alert['severity'] == 'critical' else "⚠️" if alert['severity'] == 'warning' else "ℹ️"
    st.markdown(f"{icon} **{alert['message']}**")
    st.caption(f"{alert['created_at']} • {alert['type']}")
```

### Time Estimate
- **n8n Workflow:** 2 hours
- **Python Service:** 4-6 hours
- **Database Triggers:** 3-4 hours

### Difficulty
- **n8n:** Easy
- **Python:** Medium
- **Triggers:** Medium

---

## Implementation Priority

### Immediate (Today)
1. ✅ **MCP Connection (B)** - 10 min
2. ✅ **More Coins (D.1)** - 2 min

### Short-term (This Week)
3. 📊 **Dashboard (D.2)** - 3-5 hours (Streamlit)
4. 🔔 **Basic Alerts (D.3)** - 2-3 hours (n8n workflow)

### Medium-term (1-2 Weeks)
5. 🧠 **ARIMA Model (C)** - 4-6 hours
6. 📱 **Advanced Alerts (D.3)** - 3-4 hours (Python service)

### Long-term (2-4 Weeks)
7. 🚀 **LSTM Model (C)** - 8-12 hours
8. 🎨 **React Dashboard (D.2)** - 5-8 hours (if upgrading from Streamlit)

---

## Summary Table

| Feature | Time | Difficulty | Impact | Status |
|---------|------|------------|--------|--------|
| **MCP Connection** | 10 min | Easy | High | ⏸️ Pending |
| **More Coins** | 2 min | Trivial | Medium | ⏸️ Pending |
| **ARIMA Model** | 4-6 hrs | Medium | High | ⏸️ Pending |
| **LSTM Model** | 8-12 hrs | Hard | Very High | ⏸️ Pending |
| **Streamlit Dashboard** | 3-4 hrs | Medium | High | ⏸️ Pending |
| **React Dashboard** | 5-8 hrs | Hard | Very High | ⏸️ Pending |
| **n8n Alerts** | 2 hrs | Easy | Medium | ⏸️ Pending |
| **Python Alert Service** | 4-6 hrs | Medium | High | ⏸️ Pending |
| **Database Triggers** | 3-4 hrs | Medium | Medium | ⏸️ Pending |

---

## Questions?

For questions or to choose which feature to implement next, refer back to this roadmap.

**Current Recommendation:** Start with MCP Connection (B) + More Coins (D.1) for immediate value, then build Dashboard (D.2) for visualization!
