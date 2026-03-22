# 🎓 ML Forecasting Tutorial - Learn by Doing

Welcome! You're about to learn how to build a **real crypto price forecaster** from scratch.

## 🎯 What You'll Learn

By the end of this tutorial, you'll understand:
- ✅ How to get data from a database
- ✅ How to clean and prepare data for ML
- ✅ What features are and how to create them
- ✅ How to train a LightGBM model
- ✅ How to make predictions
- ✅ How to evaluate model performance

---

## 🚀 Quick Start

All scripts run through Docker for consistent environment:

```powershell
# From the project root directory
cd "c:\Users\youss\OneDrive\Bureau\My Projects\autonomous-market"

# Build the ML container (first time only)
docker-compose build ml-forecast

# Run any phase
docker-compose run --rm ml-forecast python <script_name>.py
```

---

## 📚 The 3 Phases

### **Phase 1: Explore Data** (`explore_data.py`)
**What you learn:** How to connect to a database, load data, and check its quality

**Run it:**
```powershell
docker-compose run --rm ml-forecast python explore_data.py
```

**What you'll see:**
- Total number of price records
- Which coins you're tracking (Bitcoin, Ethereum, etc.)
- Sample data
- Data quality report
- News sentiment data

---

### **Phase 2: Clean Data & Feature Engineering** (`phase2_cleaning.py`)
**What you learn:** How to handle missing values and create ML features

**Key concepts:**
- **Missing values:** Fill gaps using forward-fill (previous value)
- **Lag features:** Past prices (1, 3, 5, 10 periods ago)
- **Rolling averages:** Smooth out noise, show trends
- **Price changes:** Percentage movements
- **Target variable:** What we're predicting (UP or DOWN)

**Run it:**
```powershell
docker-compose run --rm ml-forecast python phase2_cleaning.py
```

**Features created:**
| Feature | Description |
|---------|-------------|
| `price_lag_1` | Price 1 period ago |
| `price_lag_3` | Price 3 periods ago |
| `price_rolling_mean_5` | Average of last 5 prices |
| `price_pct_change_1` | % change from last period |
| `price_vs_ma5` | Price relative to 5-period average |
| `target` | 1 = price went UP, 0 = price went DOWN |

---

### **Phase 3: Train the Model** (`phase3_training.py`)
**What you learn:** How ML actually learns patterns from data

**Run it:**
```powershell
docker-compose run --rm ml-forecast python phase3_training.py
```

**Key concepts:**
- **Train/Test Split:** 80% to learn, 20% to evaluate
- **LightGBM:** Fast gradient boosting classifier
- **Accuracy:** How often predictions are correct
- **Feature Importance:** Which inputs matter most

**What you'll see:**
- Model training progress
- Accuracy, Precision, Recall metrics
- Confusion matrix (predictions vs actual)
- Top 10 most important features
- Sample predictions with confidence scores

---

## 🧠 Key ML Concepts

### What is Machine Learning?
Instead of writing rules like "if price goes up, predict up", we show the model **examples**:
```
Example 1: price_lag_1=68000, volume_up, sentiment_positive → price went UP
Example 2: price_lag_1=69000, volume_down, sentiment_negative → price went DOWN
... hundreds more examples ...
```
The model finds patterns and learns rules automatically!

### What is LightGBM?
A gradient boosting model that:
- Works great with tabular data (like price data)
- Trains very fast
- Handles missing values automatically
- Shows which features are most important

It builds many decision trees that work together:
```
Tree 1: Is price_pct_change > 0.1%? → likely UP
Tree 2: Is volume_lag > volume? → confirms momentum
Tree 3: Is price_vs_ma5 < 0? → below trend, might reverse
... 100 trees vote together for final prediction
```

---

## 📊 Understanding the Results

### Accuracy Metrics
| Metric | What it means |
|--------|---------------|
| **Accuracy** | % of all predictions that were correct |
| **Precision** | When we predict UP, how often is it actually UP? |
| **Recall** | Of all actual UPs, how many did we catch? |

### Confusion Matrix
```
              PREDICTED
              DOWN    UP
ACTUAL DOWN    TN     FP   (True Negative, False Positive)
ACTUAL UP      FN     TP   (False Negative, True Positive)
```

### Feature Importance
Higher score = more useful for predictions. Common important features:
- `price_pct_change_1` - Recent momentum matters
- `price_vs_ma5` - Position relative to trend
- `volume` - Trading activity signals

---

## ⚠️ Important Notes

This is a **learning exercise**! Real trading requires:
- Much more data (months/years, not hours)
- Rigorous backtesting
- Risk management
- Transaction costs consideration
- **Never invest more than you can afford to lose!**

---

## 🎯 Next Steps

After completing these phases, you can:
1. Add more features (sentiment scores, more coins)
2. Try different models (XGBoost, RandomForest)
3. Tune hyperparameters
4. Backtest on longer time periods
5. Build a real-time prediction API

---

## 📁 File Structure

```
services/ml_forecast/
├── Dockerfile           # Container configuration
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── explore_data.py     # Phase 1: Data exploration
├── phase2_cleaning.py  # Phase 2: Cleaning & features
└── phase3_training.py  # Phase 3: Model training
```
