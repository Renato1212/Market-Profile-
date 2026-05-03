# ATLAS — ES Futures Intraday Intelligence Platform

Institutional-grade ES Futures analytics combining Gap Fill Statistics, A Period Market Profile, Dealer Gamma Exposure (GEX), and an AI Trading Copilot powered by Claude.

## Architecture

```
atlas/
  backend/    Python FastAPI — data pipelines, statistical engines, AI copilot
  frontend/   React 18 + TypeScript + Tailwind CSS — mobile-first PWA
  shared/     Shared TypeScript types
```

## Quick Start

### Backend

```bash
cd atlas/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Fill in your API keys
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd atlas/frontend
npm install
npm run dev
```

App runs at `http://localhost:3000`. Backend proxy configured in `vite.config.ts`.

## Required API Keys (all free)

| Key | Where | Required For |
|-----|-------|-------------|
| `ANTHROPIC_API_KEY` | console.anthropic.com | AI Copilot (all 3 modes) |
| `FRED_API_KEY` | fred.stlouisfed.org/docs/api | Macro data (yields, VIX, stress) |
| `TRADIER_SANDBOX_TOKEN` | developer.tradier.com | Options backup source |
| `BLS_API_KEY` | bls.gov/developers | NFP/CPI releases (optional) |
| `EIA_API_KEY` | eia.gov/opendata | Oil inventory (optional) |

Yahoo Finance, CBOE, and CFTC require no keys.

## First Run — Populate Historical Data

After starting the backend, trigger the initial DB population:

```bash
curl -X POST http://localhost:8000/api/live/refresh
```

This fetches 10+ years of ES daily data and 60 days of 5-min intraday bars, computes all gap and A Period statistics, and stores them in SQLite (`atlas.db`). Takes ~2 minutes on first run.

## Data Sources

- **Price data**: Yahoo Finance v8 (ES=F, SPY, VIX family)
- **Options/GEX**: Yahoo Finance options endpoint + Tradier sandbox
- **P/C Ratio**: CBOE public CSV archive
- **COT**: CFTC public reporting API
- **Macro**: FRED (Federal Reserve Economic Data)
- **Crypto proxy**: Binance public API (BTC overnight)

## Key Technical Decisions

- **Gap fill definition**: Gap Up filled iff Day Low ≤ Prior Close. No approximations.
- **A Period timing**: Precisely 09:30:00–10:00:00 ET, six 5-min bars.
- **GEX sign convention**: Calls +positive (dealers suppress), Puts −negative (dealers amplify). Net GEX > 0 = Long Gamma.
- **SPY→ES conversion**: Live computed multiplier, never hardcoded ×10.
- **AI hallucination guard**: Claude only receives real computed numbers. Never generates statistics.
- **Caching**: In-memory TTL cache + SQLite persistence. Options chains: 15 min. Daily OHLCV: 24h.

## Deployment

- **Frontend**: Vercel (`vercel.json` included). Set `VITE_API_URL` to your backend URL.
- **Backend**: Railway (`railway.toml` included). Set all env vars in Railway dashboard.
- **Database**: SQLite for development. Switch `DATABASE_URL` to PostgreSQL for production.

## Cost Estimate (per active user/day)

- Pre-market briefing (claude-opus-4-7, ~2000 tokens): ~$0.30
- Live alerts (claude-haiku-4-5, ~350 tokens × max 20/day): ~$0.04
- Chat queries (claude-haiku-4-5, ~500 tokens × 10 queries): ~$0.05
- **Total: ~$0.39/active user/day** — profitable at $99/mo subscription

## License

Proprietary. © 2026 ATLAS Intelligence.
