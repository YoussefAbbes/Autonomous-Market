# n8n Workflows for Autonomous Market Intelligence

This directory contains exportable n8n workflow JSON files for the market data ingestion pipeline.

## Workflows

| File | Description | Schedule |
|------|-------------|----------|
| `workflows/market_data_ingestion.json` | Main hourly pipeline: fetches prices, news, runs sentiment analysis, stores to PostgreSQL | Every hour |
| `workflows/dead_letter_handler.json` | Error notification workflow triggered on failures | On error |
| `workflows/daily_quality_check.json` | Data quality monitoring with threshold alerts | Daily at 6:00 UTC |

## Import Instructions

### Step 1: Start the Stack
```bash
docker compose up -d
```

### Step 2: Access n8n
Open `http://localhost:5678` in your browser. Log in with the credentials from your `.env` file.

### Step 3: Import Workflows
1. Go to **Workflows** in the left sidebar
2. Click the **...** menu → **Import from File**
3. Select `workflows/market_data_ingestion.json`
4. Repeat for the other workflow files

### Step 4: Create Credentials

#### PostgreSQL Credential
1. Go to **Credentials** in the left sidebar
2. Click **Add Credential** → Search for **Postgres**
3. Configure:
   - **Name:** `PostgreSQL Market DB`
   - **Host:** `postgres` (Docker service name)
   - **Port:** `5432`
   - **Database:** `market_intel` (or your `POSTGRES_DB` value)
   - **User:** `market_user` (or your `POSTGRES_USER` value)
   - **Password:** Your `POSTGRES_PASSWORD` value
4. Click **Save**

### Step 5: Set n8n Variables
1. Go to **Settings** (gear icon) → **Variables**
2. Add the following variables:

| Variable | Example Value | Description |
|----------|---------------|-------------|
| `TRACKED_ASSETS` | `bitcoin,ethereum,solana` | CoinGecko coin IDs to track |
| `NEWS_FEED_URL` | `https://cryptopanic.com/api/v1/posts/` | News API endpoint |
| `NEWS_API_KEY` | `your-api-key` | API key for news service (if required) |
| `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/...` | Slack webhook for alerts (optional) |

### Step 6: Link Credentials to Workflows
1. Open each imported workflow
2. Click on any **Postgres** node (e.g., "Insert Prices")
3. Select your `PostgreSQL Market DB` credential from the dropdown
4. Save the workflow

### Step 7: Link Error Workflow
1. Open `Market Data Ingestion - Hourly`
2. Click **Settings** (gear icon in the workflow)
3. Under **Error Workflow**, select `Dead Letter Handler - Error Notifications`
4. Repeat for `Daily Quality Check`

### Step 8: Activate Workflows
1. Toggle the **Active** switch on each workflow
2. Or click **Execute Workflow** to run manually first

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 Market Data Ingestion (Hourly)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Schedule] ─┬─▶ [CoinGecko] ─▶ [Normalize] ─▶ [Insert Prices] │
│              │                                        │         │
│              │                                        ▼         │
│              └─▶ [News API] ─▶ [Extract] ─▶ [ML API] ─▶        │
│                               [Headlines]   [Sentiment]         │
│                                                │                │
│                                                ▼                │
│                                        [Insert News]            │
│                                                │                │
│  On Error ──────────────────────────────────▶ [Dead Letter]    │
└─────────────────────────────────────────────────────────────────┘
```

## Verification

After setup, verify the pipeline works:

1. **Manual Execution:**
   - Open `Market Data Ingestion - Hourly`
   - Click **Execute Workflow**
   - Check execution panel for success/errors

2. **Check Database:**
   ```sql
   -- Connect to PostgreSQL and run:
   SELECT * FROM asset_prices ORDER BY created_at DESC LIMIT 5;
   SELECT * FROM market_news ORDER BY created_at DESC LIMIT 5;
   ```

3. **Test MCP Server:**
   - Access `http://localhost:8080/mcp`
   - The `latest_market_data` resource should return your ingested data

## Troubleshooting

### "Cannot connect to postgres"
- Ensure the Docker network name matches (`market_net`)
- Use `postgres` as the host (Docker service name, not `localhost`)

### "ML API timeout"
- Check that `ml-api` container is running: `docker compose ps`
- First run downloads the model (~250MB) - be patient

### "News API returns empty"
- Verify your `NEWS_API_KEY` is set correctly
- Check API rate limits on your news provider

### "No data in database after execution"
- Check the execution logs in n8n for errors
- Verify unique constraints aren't rejecting duplicate data
- Try running with different timestamps

## File Structure
```
n8n/
├── README.md                              # This file
└── workflows/
    ├── market_data_ingestion.json         # Main hourly pipeline
    ├── dead_letter_handler.json           # Error notifications
    └── daily_quality_check.json           # Data quality monitoring
```
