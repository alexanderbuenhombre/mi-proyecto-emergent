# XAU/USD Real-Time Signals Dashboard — PRD

## Original Problem Statement
> "quiero un sistema de señales en tiempo real para XAUUSD"

## User Choices (locked in)
- **Price sources**: TradingView (OANDA) + Gold-API.com (no credentials)
- **Signal types**: Scalping (1M, 5M, 15M) + Multi-timeframe completo (30M, 1H, 4H, 1D)
- **Indicators**: RSI + MACD + CCI + Bollinger Bands + Volumen + Momentum + ATR
- **Persistence**: In-memory only (no MongoDB writes)
- **Auth**: Public (none)

## Architecture
- **Backend** (FastAPI): `/app/backend/server.py` — public price fetchers (httpx), `yfinance` for OHLC indicators on `GC=F` (Gold Futures), pandas/numpy indicator math, in-memory STATE dict for active signal + history + stats.
- **Frontend** (React + Tailwind): `/app/frontend/src/pages/Dashboard.jsx` — 3-column Control Room layout, JetBrains Mono numbers, Manrope text. Polling via `usePolling` hook (4s price → 30s multi-tf).

## API Endpoints (all under `/api`)
- `GET /price?source=tradingview|goldapi` — live spot
- `GET /sessions` — market session activity (UTC)
- `GET /multi-timeframe` — analysis for 1m..1d
- `GET /strength` — combined trend/momentum/volatility/volume/confidence bars
- `GET /signal/active?timeframe=5m` — current BUY/SELL with TP1-3 + SL + analysis
- `GET /signal/history` — recent signals (in-memory)
- `GET /binary/next-candle` — 1m/5m CALL/PUT prediction
- `GET /stats` — active count, win rate, avg confidence

## Implemented (2026-02-05)
- Live price ticker with tick-up/tick-down animations
- Bulls&Bears half-donut gauge (Recharts)
- Active signal card (BUY/SELL with confidence, entry, TP1/TP2/TP3, SL, P&L live)
- Multi-timeframe panel (7 TFs with directional badges, click to switch)
- Strength indicators (5 progress bars)
- Market sessions panel (Sydney/Tokyo/London/NY with overlap detection)
- Signal history list (with status: active/won/lost/expired)
- Next candle binary prediction (1m + 5m countdown)
- System stats card (win rate, total, active)
- Source selector (TradingView OANDA / Gold-API toggle)
- Spanish UI throughout
- All `data-testid` attributes for testing

## Backlog (P1)
- Persistir historial en MongoDB (toggle opcional para análisis histórico)
- Sound/desktop notifications cuando aparece señal con confianza ≥75%
- Backtest playback (replay últimas 24h con tiempo acelerado)
- Cuenta de usuario + watchlist con alertas vía Telegram/email
- TradingView lightweight chart embebido con TPs/SL marcados
- Risk calculator (lot size por % de cuenta)
- Webhook outbound (TradingView, Discord) cuando se emite señal

## Backlog (P2)
- Más pares (EURUSD, GBPUSD, BTC) usando misma arquitectura
- Mobile-first PWA
- Modo "agresivo / conservador" con thresholds de confianza diferentes

## Notes / Caveats
- Yahoo `XAUUSD=X` está delisted → usamos `GC=F` para indicadores. El precio spot mostrado y los niveles de entry/TP/SL siguen el feed real de TradingView/Gold-API.
- Sin asesoría financiera (disclaimer en footer).
