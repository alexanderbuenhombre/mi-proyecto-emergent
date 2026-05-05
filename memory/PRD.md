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
- Live price ticker with tick-up/tick-down animations + freshness indicator
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

## Implemented (Iteration 3 - 2026-02-05)
- **High-probability strategy** with multi-TF confluence:
  - `compute_confluence()` checks 3 surrounding TFs and counts how many agree on direction
  - `compute_probability()` returns ULTRA/ALTA/MEDIA/BAJA based on score + confluence + session liquidity bonus
  - **STRICT FILTER**: signals only generated when probability is ALTA or ULTRA AND confluence direction matches analysis direction → no more low-probability noise
- **Explicit "Recomendable" recommendation** in every alert:
  - New fields in `/api/recommendation` and `/api/signal/active`: `take` (bool), `take_label` (RECOMENDABLE/NO RECOMENDABLE/CERRAR AHORA/TOMAR PARCIAL), `take_reason` (justificación clara)
  - RecommendationBanner shows probability badge (ULTRA/ALTA/MEDIA/BAJA) + dedicated take-recommendation strip with check/X icon
  - Voice alerts now include "Es recomendable tomar la señal" / "No es recomendable tomar la señal"
- **Bulls & Bears gauge** rediseñado con SVG inline (matches reference image):
  - Semicírculo con gradiente continuo rojo→ámbar→verde
  - 5 etiquetas curvadas: Venta Fuerte, Venta, Neutral, Compra, Compra Fuerte
  - Aguja animada (transition cubic-bezier 900ms)
  - Histograma de barras de tendencia (36 barras coloreadas por dirección)
  - RSI / CCI / Trends en grid de 3 columnas
  - Etiqueta inferior "Venta Fuerte (5m)" según score actual
- **ConfluencePanel** nuevo: muestra los 3 TFs analizados con dirección y veredicto consolidado

- **Real-time data 100%**: Eliminated Yahoo Finance / `GC=F` (descuadraba con MT4). All indicators (RSI/MACD/CCI/BB/Mom/ATR) now come from TradingView Technical Analysis API on OANDA:XAUUSD spot — same feed as displayed price → matches Exness/XM/IC Markets MT4 perfectly.
- **Tick freshness**: backend ring-buffer of last 600 ticks; `fresh_seconds` field shows seconds since real price change. Frontend price polling 2s.
- **Dynamic recommendations** (`/api/recommendation`): 6 actions — TOMAR, ESPERAR, MANTENER, TOMAR_GANANCIAS (TP1/2/3), CERRAR_REVERSO (sudden adverse move > ATR/30 in 45s window), STOP_LOSS_HIT.
- **RecommendationBanner**: prominent banner above active signal with urgency indicator and tone-coded styling.
- **Voice alerts** (Web Speech API, no API keys, no costs):
  - Toggle ON/OFF, voice selector (lists all browser voices, prefers Spanish), rate slider, volume slider, test button.
  - Alert types: nueva señal, TOMAR AHORA, TP alcanzado, Stop Loss, reverso, esperar (cada uno on/off).
  - Settings persisted to localStorage.
  - Auto-triggers when signal.id changes or recommendation.label changes.

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
