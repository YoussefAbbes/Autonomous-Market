# Autonomous Market Intelligence & Time-Series Engine

Phase 1 delivers a production-minded foundation for:
- Data ingestion/orchestration via n8n
- Time-series storage in PostgreSQL
- NLP sentiment scoring via FastAPI + Hugging Face
- LLM tool/resource access via an MCP server

## Architecture
- **n8n**: ingestion workflows, scheduling, ETL routing
- **PostgreSQL**: source of truth for prices/news and analytics queries
- **Redis**: queue backend for n8n execution mode
- **ML API**: sentiment microservice (`/v1/sentiment/headlines`)
- **MCP Server**: tool/resource interface over live DB data

## Project Layout
```text
.
├── docker-compose.yml
├── .env.example
├── db/
│   └── init.sql
├── docs/
│   └── n8n_strategy.md
└── services/
    ├── ml_api/
    │   ├── Dockerfile
    │   ├── main.py
    │   └── requirements.txt
    └── mcp_server/
        ├── Dockerfile
        ├── main.py
        └── requirements.txt
```

## Quick Start
1. Copy env file:
   - `cp .env.example .env` (Linux/macOS)
   - `Copy-Item .env.example .env` (PowerShell)
2. Set secure passwords/secrets in `.env`.
3. Start stack:
   - `docker compose up --build -d`
4. Validate services:
   - n8n: `http://localhost:5678`
   - ML API health: `http://localhost:8000/health`
   - MCP endpoint: `http://localhost:8080/mcp`

## Important Notes
- `get_market_forecast` is intentionally baseline logic in Phase 1 (simple trend extrapolation).
- Replace with ARIMA/LSTM service outputs in Phase 2.
- Full n8n workflow guidance is in `docs/n8n_strategy.md`.
