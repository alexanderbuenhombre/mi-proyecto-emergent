# 🔬 AUDITORÍA TÉCNICA TOTAL — Sistema de Señales XAU/USD

> Documento de ingeniería inversa exhaustivo. Cada fórmula, número y línea proviene del código fuente real en `/app`. No hay especulación ni invención.
>
> **Versión auditada**: post-iteración 5 (TPs sticky + recomendación inline + per-TF state)
> **Fecha**: 2026-02

---

## ÍNDICE

1. Resumen ejecutivo
2. Arquitectura completa
3. Estructura de carpetas y archivos
4. Dependencias exactas
5. Estrategia de detección de señales (lógica completa)
6. Indicadores técnicos y fórmulas
7. Cálculo de Entrada, SL y TPs
8. Manejo de tiempo real (precio y señales)
9. Estructura del backend — línea por línea
10. Estructura del frontend — componente por componente
11. APIs y contratos
12. Manejo de estado en memoria
13. Sistema de alertas de voz
14. Sesiones de mercado
15. Gestión de riesgo
16. Análisis de debilidades y fortalezas
17. ¿Hay IA / LLM? — Respuesta directa
18. Repainting, lag y otros riesgos técnicos
19. Cómo optimizar y escalar
20. Guía de migración a Claude / otro framework
21. Pseudocódigo maestro de toda la estrategia

---

## 1. RESUMEN EJECUTIVO

| Aspecto | Detalle |
|---|---|
| **Stack** | FastAPI (Python 3.11) + React 19 (CRA + Tailwind 3 + Recharts) |
| **Persistencia** | In-memory (dict + deque). MongoDB disponible pero no usado en lógica principal. |
| **Fuente de datos** | TradingView público (`scanner.tradingview.com`) + Gold-API.com como fallback |
| **Estrategia** | Confluencia multi-timeframe sobre indicadores TradingView pre-calculados |
| **Indicadores** | Recommend.All, RSI(14), MACD(12/26/9), CCI(20), Momentum(10), Bollinger(20,2σ), ATR(14) |
| **Comunicación real-time** | Polling HTTP (no WebSockets) — 2s para precio, 6s para señal |
| **IA / ML** | **NINGUNA**. Es lógica determinista basada en reglas matemáticas. |
| **Alertas** | Web Speech API del navegador (gratis) |
| **Autenticación** | Ninguna (público) |
| **Persistencia de historial** | Solo en memoria, se pierde al reiniciar backend |

---

## 2. ARQUITECTURA COMPLETA

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 19)                            │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  /app/frontend/src/pages/Dashboard.jsx                         │  │
│  │   • Estado: source, tf, voiceSettings                          │  │
│  │   • Hooks: usePolling × 8                                      │  │
│  │     ├─ price (2s)        ├─ binary/next-candle (4s)            │  │
│  │     ├─ signal/active (6s) ├─ strength (10s)                    │  │
│  │     ├─ multi-tf (15s)    ├─ history (15s)                      │  │
│  │     └─ stats (15s)        └─ sessions (30s)                    │  │
│  │   • useVoiceAlerts (composite key + cooldown 8s)               │  │
│  │   • Componentes (12):                                          │  │
│  │     PriceHeader · BullsBearsGauge · ConfluencePanel            │  │
│  │     ActiveSignalCard (con recomendación inline)                │  │
│  │     MultiTimeframe · StrengthBars · MarketSessions             │  │
│  │     NextCandleBinary · SignalHistory · SystemStats             │  │
│  │     SourceSelector · VoiceSettings                             │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                              │ HTTP fetch (axios)
                              │ REACT_APP_BACKEND_URL/api/*
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI / Uvicorn)                     │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  /app/backend/server.py (≈830 líneas, monolítico)              │  │
│  │                                                                  │  │
│  │  CAPA 1 — DATA FETCHERS (httpx async):                          │  │
│  │   ├─ fetch_tradingview_oanda()                                  │  │
│  │   ├─ fetch_gold_api()                                           │  │
│  │   ├─ get_price()                                                │  │
│  │   └─ fetch_tv_analysis()  ← cache 8s                            │  │
│  │                                                                  │  │
│  │  CAPA 2 — ANÁLISIS:                                              │  │
│  │   ├─ analyze_timeframe_tv(tv, tf, price) → score, dir, conf     │  │
│  │   ├─ compute_confluence(tv, p, tf) → 3 TFs alineados            │  │
│  │   ├─ compute_probability(...) → ULTRA/ALTA/MEDIA/BAJA           │  │
│  │   └─ detect_sudden_move(...) → análisis de ticks 45s            │  │
│  │                                                                  │  │
│  │  CAPA 3 — DECISIÓN:                                              │  │
│  │   ├─ _make_signal(...) → genera Signal con TP/SL desde ATR      │  │
│  │   └─ compute_recommendation(...) → 8 acciones priorizadas        │  │
│  │                                                                  │  │
│  │  CAPA 4 — API ROUTING (FastAPI @api_router):                    │  │
│  │   GET /api/price, /api/sessions, /api/multi-timeframe,          │  │
│  │   /api/strength, /api/signal/active, /api/signal/history,       │  │
│  │   /api/binary/next-candle, /api/stats, /api/recommendation      │  │
│  │                                                                  │  │
│  │  STATE GLOBAL (dict in-memory):                                  │  │
│  │   active_signals{tf}, signal_cooldown{tf}, ticks(deque600),     │  │
│  │   ta_cache, last_price, history[50], stats                      │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                  │                                  │
                  ▼                                  ▼
   ┌─────────────────────────────┐   ┌─────────────────────────────┐
   │  TradingView Scanner API    │   │      Gold-API.com           │
   │  scanner.tradingview.com    │   │      api.gold-api.com       │
   │  → Spot OANDA               │   │      → Spot LBMA            │
   │  → 26+ indicadores per-TF   │   │      → Fallback únicamente  │
   │  → Sin credenciales         │   │      → Sin credenciales     │
   └─────────────────────────────┘   └─────────────────────────────┘
```

---

## 3. ESTRUCTURA DE CARPETAS Y ARCHIVOS

```
/app
├── backend/
│   ├── server.py              # 833 líneas — TODO el backend en un archivo
│   ├── requirements.txt
│   └── .env                   # MONGO_URL, DB_NAME, CORS_ORIGINS
│
├── frontend/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── craco.config.js
│   ├── .env                   # REACT_APP_BACKEND_URL
│   └── src/
│       ├── App.js             # Solo monta el Router → Dashboard
│       ├── index.js, index.css
│       ├── lib/
│       │   ├── signalsApi.js  # axios wrappers de cada endpoint
│       │   ├── usePolling.js  # hook con generation counter
│       │   ├── voice.js       # Web Speech API helpers
│       │   └── useVoiceAlerts.js  # dedup + cooldown 8s
│       ├── pages/
│       │   └── Dashboard.jsx  # página única
│       └── components/dashboard/
│           ├── PriceHeader.jsx
│           ├── BullsBearsGauge.jsx
│           ├── ConfluencePanel.jsx
│           ├── ActiveSignalCard.jsx   # con recomendación inline
│           ├── MultiTimeframe.jsx
│           ├── StrengthBars.jsx
│           ├── MarketSessions.jsx
│           ├── NextCandleBinary.jsx
│           ├── SignalHistory.jsx
│           ├── SystemStats.jsx
│           ├── SourceSelector.jsx
│           └── VoiceSettings.jsx
│
├── memory/
│   └── PRD.md
└── test_reports/
    └── iteration_*.json
```

---

## 4. DEPENDENCIAS EXACTAS

### Backend (`requirements.txt`, las críticas)

```
fastapi
uvicorn
httpx               # cliente HTTP async para llamar TradingView/Gold-API
python-dotenv
pydantic
motor==3.3.1        # MongoDB async (preparado pero no usado en lógica principal)
pymongo==4.5.0
```

**Notable**: No usa `pandas`, `numpy`, `ta-lib`, `pandas-ta`, `yfinance`, ni librerías de análisis técnico. Todo viene pre-calculado de TradingView.

### Frontend (`package.json`)

```json
{
  "react": "^19.0.0",
  "react-dom": "^19.0.0",
  "react-router-dom": "^7.5.1",
  "axios": "^1.8.4",
  "recharts": "^3.6.0",        // (importado pero el gauge usa SVG inline)
  "lucide-react": "^0.507.0",  // iconos
  "tailwindcss": "^3.4.17",
  "sonner": "^2.0.3",
  // + radix-ui completo para shadcn components
}
```

---

## 5. ESTRATEGIA DE DETECCIÓN DE SEÑALES — LÓGICA COMPLETA

### 5.1 Pipeline de decisión

```
                            ┌─────────────────────┐
                            │ GET /signal/active  │
                            │   ?timeframe=5m     │
                            └──────────┬──────────┘
                                       ▼
        ┌──────────────────────────────────────────────────┐
        │ Paso 1: fetch_tv_analysis()  (cache 8s)          │
        │  → dict con ~250 campos (todos los indicadores   │
        │    × todos los TFs)                              │
        └──────────────────────────────────────────────────┘
                                       ▼
        ┌──────────────────────────────────────────────────┐
        │ Paso 2: get_price("tradingview")                 │
        │  → precio spot + actualiza tick buffer           │
        └──────────────────────────────────────────────────┘
                                       ▼
        ┌──────────────────────────────────────────────────┐
        │ Paso 3: analyze_timeframe_tv(tv, "5m", price)    │
        │  → calcula score con fórmula determinista        │
        │  → score → direction (BUY/SELL/NEUTRAL)          │
        └──────────────────────────────────────────────────┘
                                       ▼
        ┌──────────────────────────────────────────────────┐
        │ Paso 4: compute_confluence(tv, p, "5m")          │
        │  → analiza 5m + 15m + 1h                         │
        │  → aligned_count, direction (mayoría)            │
        └──────────────────────────────────────────────────┘
                                       ▼
        ┌──────────────────────────────────────────────────┐
        │ Paso 5: compute_probability(...)                 │
        │  → ULTRA / ALTA / MEDIA / BAJA + take(bool)      │
        └──────────────────────────────────────────────────┘
                                       ▼
        ┌──────────────────────────────────────────────────┐
        │ Paso 6: ¿active_signals["5m"] vigente?           │
        │  SÍ → actualiza pnl, MFE, tp_hits[sticky],       │
        │        sl_hit[sticky] → retorna mismo signal      │
        │  NO → continúa                                    │
        └──────────────────────────────────────────────────┘
                                       ▼
        ┌──────────────────────────────────────────────────┐
        │ Paso 7: ¿cooldown activo?                        │
        │  SÍ → signal = null                              │
        │  NO → _make_signal(...)                          │
        │      Filtros:                                     │
        │       • direction ≠ NEUTRAL                       │
        │       • probability ≠ BAJA                        │
        │       • confluence no contradictoria              │
        │      Si pasa → calcula TP/SL desde ATR            │
        │              → guarda en active_signals[tf]      │
        │              → set cooldown 50% expiración        │
        └──────────────────────────────────────────────────┘
                                       ▼
        ┌──────────────────────────────────────────────────┐
        │ Paso 8: compute_recommendation(signal, p, ...)   │
        │  Evalúa 8 reglas en orden de prioridad:          │
        │   1. STOP_LOSS_HIT     2. TP3                    │
        │   3. TP2               4. TP1                    │
        │   5. REVERSO_BRUSCO    6. TOMAR/NO_TOMAR         │
        │   7. ESPERAR           8. MANTENER               │
        └──────────────────────────────────────────────────┘
                                       ▼
                Response: signal + analysis + price +
                          recommendation + confluence + probability
```

### 5.2 ¿Cómo se decide BUY vs SELL?

Solo y exclusivamente por el **score numérico** calculado en `analyze_timeframe_tv()`:

```python
score = int(Recommend.All * 100)  # base [-100, +100]

# Refuerzos por extremos
if RSI < 30:    score += 8     # sobreventa
elif RSI > 70:  score -= 8     # sobrecompra

if MACD_line > MACD_signal: score += 5
else:                       score -= 5

if CCI > +100:   score += 5
elif CCI < -100: score -= 5

score = clamp(score, -100, +100)

# Decisión final
if score >= +25: direction = "BUY"
elif score <= -25: direction = "SELL"
else: direction = "NEUTRAL"
```

**El score puede sumar máximo +118 antes del clamp** (100 de Recommend + 8 RSI + 5 MACD + 5 CCI). El clamp limita a ±100.

---

## 6. INDICADORES TÉCNICOS Y FÓRMULAS

### 6.1 Tabla completa

| Indicador | Origen | Parámetros | Uso en estrategia |
|---|---|---|---|
| **Recommend.All** | TV (consenso ~26 indicadores) | n/a | Score base × 100 |
| **RSI** | TV | 14 | +8 si <30, −8 si >70 |
| **MACD line / signal** | TV | 12 / 26 / 9 | ±5 según cruce |
| **CCI20** | TV | 20 | ±5 si |CCI| > 100 |
| **Mom** (Momentum) | TV | 10 | Bar de "Momentum" en UI |
| **BB.upper / BB.lower** | TV | 20, 2σ | Calcula `bb_pos` (UI only) |
| **ATR** | TV | 14 (per-TF) | SL/TP calculation |
| **Volume** | TV (24h agregado) | n/a | Bar "Volumen" en UI |

### 6.2 Fórmulas usadas

**RSI** (calculado por TradingView):
```
RS = avgGain / avgLoss   (período 14)
RSI = 100 - (100 / (1 + RS))
```

**MACD** (calculado por TradingView):
```
EMA_fast = EMA(close, 12)
EMA_slow = EMA(close, 26)
MACD_line = EMA_fast - EMA_slow
MACD_signal = EMA(MACD_line, 9)
MACD_hist = MACD_line - MACD_signal
```

**CCI** (calculado por TradingView):
```
TP = (high + low + close) / 3
SMA_TP = SMA(TP, 20)
MD = mean(|TP - SMA_TP|, 20)
CCI = (TP - SMA_TP) / (0.015 × MD)
```

**ATR** (calculado por TradingView):
```
TR = max(high-low, |high-close_prev|, |low-close_prev|)
ATR = EMA(TR, 14)
```

**Bollinger Position** (calculado en backend):
```python
bb_pos = (current_price - BB.lower) / (BB.upper - BB.lower)
       → ∈ [0, 1]
```

**Probability** (heurística propia):
```python
prob = |score| × 0.6
     + (aligned_count / total) × 100 × 0.3   # si confluence match
     + 5                                       # si sesión líquida
```

---

## 7. CÁLCULO DE ENTRADA, SL y TPs

```python
# Factor por timeframe (multiplicador de ATR)
tf_atr_scale = {
    "1m":  0.15,    # scalping ultra-rápido — stops muy ajustados
    "5m":  0.25,
    "15m": 0.40,
    "30m": 0.60,
    "1h":  0.80,
    "4h":  1.00,
    "1d":  1.20,    # swing — stops amplios
}
eff_atr = ATR × tf_atr_scale[timeframe]

entry = precio_spot_actual

# BUY:
stop_loss = entry - eff_atr × 1.2     # riesgo
tp1       = entry + eff_atr × 1.0     # R:R ≈ 1:0.83
tp2       = entry + eff_atr × 2.0     # R:R ≈ 1:1.66
tp3       = entry + eff_atr × 3.5     # R:R ≈ 1:2.9

# SELL: inverso (entry +/- invertidos)
```

**Riesgo por trade** (mostrado en UI):
```python
risk_pct = |entry - stop_loss| / entry × 100
```

**Tiempo de expiración por TF**:
| TF | Minutos | Real |
|---|---|---|
| 1m | 3 | 3 min |
| 5m | 15 | 15 min |
| 15m | 45 | 45 min |
| 30m | 90 | 1h 30min |
| 1h | 240 | 4 horas |
| 4h | 960 | 16 horas |
| 1d | 1440 | 24 horas |

---

## 8. MANEJO DE TIEMPO REAL

### 8.1 Precio

- **Polling HTTP**, no WebSocket
- Backend: `httpx.AsyncClient(timeout=8.0)` por request
- Cache TA: 8s (`STATE["ta_cache"]`)
- Frontend: `/api/price` cada **2 segundos**

### 8.2 Tick Buffer

```python
STATE["ticks"] = deque(maxlen=600)   # ~20 min @ 2s
# Cada elemento: (unix_ts, price)
```

Se actualiza en CADA llamada a `get_price()` independiente de si el precio cambió.

### 8.3 Detección de "freshness" del precio

```python
# En get_price():
if STATE["last_price"] is None or p.price != STATE["last_price"]:
    STATE["last_price_change_at"] = now.timestamp()
# ...
p.fresh_seconds = int(now.timestamp() - STATE["last_price_change_at"])
```

Si el precio no cambia durante 20s, `fresh_seconds = 20`. UI lo colorea:
- ≤ 5s → verde
- ≤ 15s → ámbar
- > 15s → rojo

### 8.4 Detección de reverso brusco

```python
def detect_sudden_move(direction_against, atr_value):
    ticks = list(STATE["ticks"])
    # Ventana de últimos 45 segundos
    window = [t for t in ticks if now - t.ts <= 45]
    if len(window) < 3: return no_reversal
    delta = window[-1].price - window[0].price
    threshold = max(atr_value / 30.0, 0.4)
    # Si Δ contra la dirección de la señal supera threshold
    if direction_against == "BUY" and delta < -threshold:
        return reversal
    if direction_against == "SELL" and delta > threshold:
        return reversal
```

**Significado**: si en 45s el precio se mueve >ATR/30 EN CONTRA de tu posición, dispara `CERRAR_REVERSO`.

### 8.5 Manejo per-TF de señales

```python
STATE["active_signals"] = {
    "1m":  {...},
    "5m":  {...},
    ...
}
STATE["signal_cooldown"] = {
    "5m": unix_ts_until_can_regenerate,
    ...
}
```

Crítico: cada TF mantiene su señal independiente, evita el bug histórico de "loop infinito al cambiar TF".

### 8.6 TPs sticky con MFE

```python
# En cada poll:
prev_mfe = signal.max_favorable or entry
if is_buy:
    signal.max_favorable = max(prev_mfe, current_price)
else:
    signal.max_favorable = min(prev_mfe, current_price)

for tp in ["tp1", "tp2", "tp3"]:
    if signal.tp_hits[tp]: continue   # sticky — no se desmarca
    if is_buy:  reached = mfe >= signal[tp]
    else:       reached = mfe <= signal[tp]
    if reached: signal.tp_hits[tp] = True
```

---

## 9. ESTRUCTURA DEL BACKEND — LÍNEA POR LÍNEA

### 9.1 Imports y setup (líneas 1-30)

```python
from fastapi import FastAPI, APIRouter, Query
from starlette.middleware.cors import CORSMiddleware
from collections import deque
from pydantic import BaseModel, Field
import httpx
# ...

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="XAUUSD Signals API")
api_router = APIRouter(prefix="/api")
```

### 9.2 State global (líneas 32-54)

```python
STATE = {
    "history": [],                    # últimas 50 señales
    "active_signals": {},             # {tf: Signal}
    "signal_cooldown": {},            # {tf: unix_ts}
    "last_price": None,
    "last_price_at": None,
    "last_price_change_at": None,
    "ticks": deque(maxlen=600),
    "stats": {"total": 0, "wins": 0, "losses": 0},
    "ta_cache": {"ts": 0, "data": None},
}

TV_TIMEFRAMES = {
    "1m": "1", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "4h": "240", "1d": "1D", "1w": "1W"
}
```

### 9.3 Models Pydantic (líneas 57-88)

```python
class PriceData(BaseModel):
    price: float
    change: float
    change_pct: float
    spread: float
    source: str
    timestamp: str
    high: Optional[float] = None
    low: Optional[float] = None
    fresh_seconds: int = 0

class Signal(BaseModel):
    id: str                          # uuid4
    symbol: str = "XAUUSD"
    direction: Literal["BUY", "SELL"]
    timeframe: str
    confidence: float                # 0-99
    entry: float
    tp1: float; tp2: float; tp3: float
    stop_loss: float
    analysis: str                    # texto descriptivo
    created_at: str                  # ISO 8601 UTC
    expires_at: str
    status: Literal["active","won","lost","expired"] = "active"
    pnl_pct: Optional[float] = None
    tp_hits: Dict[str,bool]          # sticky markers
    sl_hit: bool = False
    max_favorable: Optional[float] = None   # MFE
```

### 9.4 Data fetchers (líneas 91-171)

`fetch_tradingview_oanda()`: GET a scanner.tradingview.com, parsea close/bid/ask, retorna PriceData o None.

`fetch_gold_api()`: GET a api.gold-api.com/price/XAU, retorna PriceData o None.

`get_price(source)`: lógica de fallback + actualiza tick buffer + freshness:

```python
async def get_price(source="tradingview"):
    if source == "goldapi":
        p = await fetch_gold_api() or await fetch_tradingview_oanda()
    else:
        p = await fetch_tradingview_oanda() or await fetch_gold_api()

    if p is None:
        p = PriceData(price=STATE["last_price"] or 2650, ...)

    if p.price != STATE["last_price"]:
        STATE["last_price_change_at"] = now
    STATE["last_price"] = p.price
    STATE["ticks"].append((now, p.price))
    p.fresh_seconds = now - STATE["last_price_change_at"]
    return p
```

### 9.5 TV Technical Analysis (líneas 175-220)

```python
def _build_tv_fields():
    base = ["close", "change", "high", "low", "volume"]
    per_tf = ["RSI", "MACD.macd", "MACD.signal", "CCI20", "Mom",
              "Recommend.All", "Recommend.MA", "Recommend.Other",
              "BB.upper", "BB.lower", "ATR"]
    # Genera fields como: RSI, RSI|1, RSI|5, RSI|15, RSI|30, RSI|60, RSI|240, RSI|1D, RSI|1W
    return ",".join([...])

async def fetch_tv_analysis():
    # Cache 8s
    if cache_fresh: return cache
    GET scanner.tradingview.com/symbol with all fields
    cache = data
    return data
```

### 9.6 analyze_timeframe_tv (líneas 223-281)

```python
def analyze_timeframe_tv(tv, timeframe, current_price):
    tf_code = TV_TIMEFRAMES[timeframe]   # "1", "5", "15", "60", ...

    rsi_v = _get_tv(tv, "RSI", tf_code, default=50)
    macd_line = _get_tv(tv, "MACD.macd", tf_code, default=0)
    macd_sig = _get_tv(tv, "MACD.signal", tf_code, default=0)
    cci_v = _get_tv(tv, "CCI20", tf_code, default=0)
    mom_v = _get_tv(tv, "Mom", tf_code, default=0)
    bb_up = _get_tv(tv, "BB.upper", tf_code, default=current_price)
    bb_lo = _get_tv(tv, "BB.lower", tf_code, default=current_price)
    rec_all = _get_tv(tv, "Recommend.All", tf_code, default=0)  # -1..+1
    atr_v = _get_tv(tv, "ATR", tf_code,
                    default=_get_tv(tv, "ATR", None, current_price * 0.0008))

    bb_pos = (current_price - bb_lo) / (bb_up - bb_lo) if bb_up != bb_lo else 0.5

    score = int(rec_all * 100)
    if rsi_v < 30: score += 8
    elif rsi_v > 70: score -= 8
    if macd_line > macd_sig: score += 5
    else: score -= 5
    if cci_v > 100: score += 5
    elif cci_v < -100: score -= 5
    score = clamp(score, -100, 100)

    if score >= 25:   direction = "BUY"
    elif score <= -25: direction = "SELL"
    else:             direction = "NEUTRAL"
    confidence = min(99, abs(score) + 30)

    return { direction, score, confidence, rsi, macd, macd_hist,
             cci, bb_pos, momentum, atr, close, tv_recommend }
```

### 9.7 compute_confluence (líneas 285-314)

```python
confluence_map = {
    "1m":  ["1m", "5m", "15m"],
    "5m":  ["5m", "15m", "1h"],
    "15m": ["5m", "15m", "1h"],
    "30m": ["15m", "30m", "1h"],
    "1h":  ["15m", "1h", "4h"],
    "4h":  ["1h", "4h", "1d"],
    "1d":  ["4h", "1d"],
}

def compute_confluence(tv, price, primary_tf):
    tfs = confluence_map[primary_tf]   # 2 o 3 timeframes
    analyses = [analyze_timeframe_tv(tv, t, price) for t in tfs]
    buy = count(a.direction == "BUY")
    sell = count(a.direction == "SELL")
    aligned = max(buy, sell)
    direction = "BUY" if buy > sell else "SELL" if sell > buy else "NEUTRAL"
    avg_score = mean(|a.score| for a in analyses)
    return { timeframes, aligned_count, total_count, direction, avg_strength, details }
```

### 9.8 compute_probability (líneas 317-346)

```python
def compute_probability(analysis, confluence, session_label):
    base_score = abs(analysis.score)
    confl_pct = aligned_count / total_count      # 0..1
    confl_match = confluence.direction == analysis.direction

    session_bonus = 5 if "LONDRES" in session_label or "NUEVA YORK" in session_label else 0

    prob = base_score * 0.6
         + (confl_pct * 100 if confl_match else 0) * 0.3
         + session_bonus
    prob = clamp(int(prob), 0, 99)

    if prob >= 80 and aligned_count >= 3:
        label = "ULTRA"; take = True
    elif prob >= 65 and aligned_count >= 2:
        label = "ALTA"; take = True
    elif prob >= 50:
        label = "MEDIA"; take = False
    else:
        label = "BAJA"; take = False

    return { label, percent, take, reason }
```

### 9.9 _make_signal (líneas 604-653)

```python
def _make_signal(analysis, timeframe, price_now, confluence, probability):
    if analysis.direction == "NEUTRAL": return None
    if probability.label == "BAJA": return None
    if confluence.direction not in (analysis.direction, "NEUTRAL"): return None

    a = max(analysis.atr, 0.5)
    eff_a = a * tf_atr_scale[timeframe]

    if direction == "BUY":
        entry = price_now
        sl = entry - eff_a * 1.2
        tp1 = entry + eff_a * 1.0
        tp2 = entry + eff_a * 2.0
        tp3 = entry + eff_a * 3.5
    else:  # SELL
        entry = price_now
        sl = entry + eff_a * 1.2
        tp1 = entry - eff_a * 1.0
        tp2 = entry - eff_a * 2.0
        tp3 = entry - eff_a * 3.5

    expires_minutes = expiration_map[timeframe]
    return Signal(
        id=uuid4(),
        confidence=probability.percent,
        entry=entry, sl=sl, tp1=tp1, tp2=tp2, tp3=tp3,
        created_at=now,
        expires_at=now + timedelta(minutes=expires_minutes),
        ...
    )
```

### 9.10 compute_recommendation (líneas 370-510)

Es el motor de 8 reglas priorizadas. Pseudocódigo:

```
si signal == None:
    return ESPERAR (Mercado neutral, NO TOMAR, prob.reason)

# Variables comunes
take_flag = probability.take
take_label = "RECOMENDABLE" if take_flag else "NO RECOMENDABLE"

# Regla 1: SL hit (precio actual, no MFE)
si (BUY y price <= sl) o (SELL y price >= sl):
    return STOP_LOSS_HIT (urgency=high, tone=danger)

# Reglas 2-4: TPs (precio actual)
si TP3 alcanzado: return TOMAR_GANANCIAS "TP3 ALCANZADO" (cerrar todo)
si TP2 alcanzado: return TOMAR_GANANCIAS "TP2 ALCANZADO" (cerrar 60%)
si TP1 alcanzado: return TOMAR_GANANCIAS "TP1 ALCANZADO" (cerrar 30-50%)

# Regla 5: reverso brusco vía ticks
si detect_sudden_move(...).reversal:
    return CERRAR_REVERSO (urgency=high, tone=danger)

# Regla 6: cerca de entrada
si |price - entry|/entry <= 0.0015 y confidence >= 70:
    si take_flag: return TOMAR_AHORA (urgency=high)
    sino:         return NO_TOMAR (urgency=medium)

# Regla 7: precio se alejó
si |price - entry|/entry × 100 > 0.3:
    return ESPERAR "precio se alejó"

# Regla 8: default
return MANTENER POSICIÓN
```

### 9.11 detect_sudden_move (líneas 350-367)

```python
def detect_sudden_move(direction_against, atr_value):
    ticks = list(STATE["ticks"])
    if len(ticks) < 6: return no_reversal

    now_ts = ticks[-1].ts
    window = [t for t in ticks if now_ts - t.ts <= 45]   # ventana 45s
    if len(window) < 3: return no_reversal

    delta = window[-1].price - window[0].price
    threshold = max(atr_value / 30.0, 0.4)

    if direction_against == "BUY" and delta < -threshold:
        return reversal=True, delta=delta
    if direction_against == "SELL" and delta > threshold:
        return reversal=True, delta=delta
    return no_reversal
```

### 9.12 api_active_signal (líneas 661-734) — el endpoint clave

```python
@api_router.get("/signal/active")
async def api_active_signal(timeframe="5m"):
    # 1. Datos
    tv = await fetch_tv_analysis()
    price = await get_price("tradingview")
    analysis = analyze_timeframe_tv(tv, timeframe, price.price)
    confluence = compute_confluence(tv, price.price, timeframe)
    sess_label = await _session_label()
    probability = compute_probability(analysis, confluence, sess_label)

    # 2. ¿Hay señal activa para este TF?
    cur = STATE["active_signals"].get(timeframe)
    if cur and not_expired(cur):
        # Actualizar pnl_pct
        pnl = ((price - cur.entry)/cur.entry)*100  if BUY else (cur.entry-price)/cur.entry*100
        cur.pnl_pct = pnl

        # Actualizar MFE
        prev_mfe = cur.max_favorable or cur.entry
        cur.max_favorable = max(prev_mfe, price) if BUY else min(prev_mfe, price)

        # Sticky TP hits usando MFE
        for tp in ["tp1","tp2","tp3"]:
            if cur.tp_hits[tp]: continue
            if BUY and mfe >= cur[tp]: cur.tp_hits[tp] = True
            if SELL and mfe <= cur[tp]: cur.tp_hits[tp] = True

        # Sticky SL hit (precio actual)
        if not cur.sl_hit:
            cur.sl_hit = (BUY and price <= cur.sl) or (SELL and price >= cur.sl)

        rec = compute_recommendation(cur, price, analysis, probability)
        return {signal: cur, analysis, price, recommendation: rec, confluence, probability}

    # 3. Limpiar expirada
    if cur and expired: STATE["active_signals"].pop(timeframe)

    # 4. Cooldown
    if time.time() < STATE["signal_cooldown"].get(timeframe, 0):
        rec = compute_recommendation(None, price, analysis, probability)
        return {signal: None, ..., recommendation: rec, ...}

    # 5. Generar nueva señal
    new_sig = _make_signal(analysis, timeframe, price.price, confluence, probability)
    if new_sig:
        STATE["active_signals"][timeframe] = new_sig.dict()
        STATE["history"].insert(0, new_sig.dict()); STATE["history"][:50]
        STATE["stats"]["total"] += 1
        STATE["signal_cooldown"][timeframe] = time.time() + (expires_min * 60 * 0.5)

    rec = compute_recommendation(STATE["active_signals"].get(timeframe), price, analysis, probability)
    return {signal, analysis, price, recommendation: rec, confluence, probability}
```

---

## 10. ESTRUCTURA DEL FRONTEND — COMPONENTE POR COMPONENTE

### 10.1 Dashboard.jsx (página única)

- Estados: `source` ("tradingview"|"goldapi"), `tf` (timeframe activo), `voiceSettings`
- 8 instancias de `usePolling` con intervalos distintos
- `useVoiceAlerts` para disparar voz cuando cambia la señal/recomendación
- Layout: header + 3 columnas (left/center/right)

### 10.2 usePolling.js (crítico — fix de race condition)

```javascript
function usePolling(fn, intervalMs, deps=[]) {
    const [data, setData] = useState(null);
    const genRef = useRef(0);

    useEffect(() => {
        genRef.current += 1;
        const myGen = genRef.current;
        let timer = null;
        let cancelled = false;

        const run = async () => {
            const res = await fn();
            if (cancelled || myGen !== genRef.current) return;
            setData(res);
            if (!cancelled) timer = setTimeout(run, intervalMs);
        };
        run();
        return () => { cancelled = true; if (timer) clearTimeout(timer); };
    }, deps);

    return { data };
}
```

**Por qué generation counter**: cuando cambian deps (ej. el usuario cambia TF), el efecto se desmonta y se remonta. Sin gen counter, respuestas en vuelo de la versión anterior contaminarían el nuevo state.

### 10.3 useVoiceAlerts.js

```javascript
const COOLDOWN_MS = 8000;

function useVoiceAlerts({ signal, recommendation, settings, timeframe }) {
    const lastKey = useRef(null);
    const lastSpokenAt = useRef(0);
    const initialized = useRef(false);

    // Reset on TF change
    useEffect(() => {
        lastKey.current = null;
        initialized.current = false;
    }, [timeframe]);

    useEffect(() => {
        const key = `${signal?.id || "none"}|${recommendation?.label}`;

        if (!initialized.current) { lastKey.current = key; initialized.current = true; return; }
        if (key === lastKey.current) return;
        if (Date.now() - lastSpokenAt.current < COOLDOWN_MS) { lastKey.current = key; return; }

        // Decide phrase based on action and call speak(phrase)
        ...
        lastSpokenAt.current = Date.now();
        lastKey.current = key;
    }, [signal?.id, recommendation?.label, ...]);
}
```

### 10.4 voice.js

```javascript
function speak(text, settings) {
    if (!settings.enabled) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.voice = selectedVoice;
    u.rate = settings.rate;
    u.volume = settings.volume;
    u.lang = u.voice?.lang || "es-ES";
    window.speechSynthesis.speak(u);
}
```

### 10.5 ActiveSignalCard.jsx

Contiene TODO inline (después de iteración 5):
- Header con dirección, confianza, prob badge
- Precio en vivo + P&L
- Entrada
- TP1/TP2/TP3 con **badge "ALCANZADO" sticky** (lee `signal.tp_hits[tpN]`)
- Stop Loss con **"SL ALCANZADO" sticky** (lee `signal.sl_hit`)
- Análisis textual
- Recomendación inline (label + headline + RECOMENDABLE/NO RECOMENDABLE)
- CTA TOMAR/ESPERAR (deshabilitado si `!recommendation.take`)
- Toggle de voz rápido en el header

---

## 11. APIs Y CONTRATOS

| Método | Ruta | Parámetros | Descripción |
|---|---|---|---|
| GET | `/api/` | — | Health |
| GET | `/api/price` | `source=tradingview\|goldapi` | Precio spot + freshness |
| GET | `/api/sessions` | — | 4 sesiones + label compuesto |
| GET | `/api/multi-timeframe` | — | Análisis para los 7 TFs |
| GET | `/api/strength` | — | Barras de fuerza (5 métricas) |
| GET | `/api/signal/active` | `timeframe=5m` | Señal + recomendación |
| GET | `/api/signal/history` | — | Hasta 50 señales |
| GET | `/api/binary/next-candle` | — | 1m + 5m CALL/PUT |
| GET | `/api/stats` | — | Win rate in-memory |
| GET | `/api/recommendation` | `timeframe=5m` | Solo recomendación |

### Ejemplo de response `/api/signal/active?timeframe=5m`

```json
{
  "signal": {
    "id": "uuid",
    "direction": "BUY",
    "timeframe": "5m",
    "confidence": 60,
    "entry": 4609.56,
    "tp1": 4637.89, "tp2": 4666.22, "tp3": 4708.72,
    "stop_loss": 4575.56,
    "analysis": "Tendencia alcista fuerte · 3/3 TFs alineados · SCALPING",
    "created_at": "2026-02-05T00:36:00Z",
    "expires_at": "2026-02-05T00:51:00Z",
    "status": "active",
    "pnl_pct": 0.012,
    "tp_hits": {"tp1": false, "tp2": false, "tp3": false},
    "sl_hit": false,
    "max_favorable": 4612.10
  },
  "analysis": { score, rsi, macd, macd_hist, cci, bb_pos, momentum, atr, close, tv_recommend },
  "price": { price, change, change_pct, spread, source, timestamp, fresh_seconds },
  "recommendation": {
    "action": "TOMAR",
    "label": "TOMAR AHORA",
    "headline": "...",
    "message": "...",
    "urgency": "high",
    "tone": "buy",
    "take": true,
    "take_label": "RECOMENDABLE",
    "take_reason": "3/3 TFs alineados con dirección BUY. Recomendable tomar.",
    "probability": "ALTA"
  },
  "confluence": { timeframes, aligned_count, total_count, direction, avg_strength, details },
  "probability": { label, percent, take, reason }
}
```

---

## 12. MANEJO DE ESTADO EN MEMORIA

```python
STATE = {
    "history": [],                    # FIFO truncado a 50
    "active_signals": {},             # {tf: Signal_dict}
    "signal_cooldown": {},            # {tf: unix_ts_until_can_emit}
    "last_price": None,               # último precio visto
    "last_price_at": None,            # ISO timestamp de última consulta
    "last_price_change_at": None,     # unix_ts del último cambio REAL
    "ticks": deque(maxlen=600),       # ring buffer ~20min @ 2s
    "stats": {"total": 0, "wins": 0, "losses": 0},
    "ta_cache": {"ts": 0, "data": None},
}
```

**Pérdida de datos**: al reiniciar el backend, todo se pierde. No hay persistencia.

---

## 13. SISTEMA DE ALERTAS DE VOZ

- Web Speech API (gratis, sin servidor)
- Componente: `VoiceSettings.jsx`
- Toggleable: nueva señal, TOMAR_AHORA, TP alcanzado, Stop Loss, reverso, ESPERAR
- Selector de voz (lee voces disponibles del navegador, prioriza español)
- Persistencia: `localStorage` key `xauusd.voice.settings.v1`
- 3 mecanismos anti-spam (composite key, cooldown 8s, reset on TF change)

---

## 14. SESIONES DE MERCADO

```python
sessions = [
    {"name": "Sydney",   "open": 22, "close": 7,  "tz": "AEDT"},
    {"name": "Tokyo",    "open": 0,  "close": 9,  "tz": "JST"},
    {"name": "London",   "open": 8,  "close": 17, "tz": "GMT"},
    {"name": "New York", "open": 13, "close": 22, "tz": "EST"},
]
# Todas las horas son UTC

# Cálculo:
h = now.hour + now.minute / 60.0
for session in sessions:
    if open < close:
        active = open <= h < close
    else:  # cruza medianoche (Sydney)
        active = h >= open or h < close

# Label compuesto:
"LONDRES" si solo Londres activa
"LONDRES/NY" si ambas
"NUEVA YORK" si solo NY
"ASIA" si solo Asia
```

**Bonus en probability**: +5 si Londres o NY activas.

---

## 15. GESTIÓN DE RIESGO

| Mecanismo | Implementación |
|---|---|
| Stop Loss | `entry ∓ ATR × tf_scale × 1.2` |
| Take Profits | TP1/TP2/TP3 con ratios 1×, 2×, 3.5× ATR |
| Filtro de baja calidad | `probability ≠ BAJA` no emite señal |
| Filtro de confluencia | Bloqueo si confluencia contradictoria |
| Cooldown anti-spam | 50% del tiempo de expiración por TF |
| Detección de reverso | Ticks 45s + threshold ATR/30 |
| Sesión líquida | Bonus de probabilidad solo en Londres/NY |
| Expiración automática | Por TF (3min a 24h) |

**Lo que NO hay**: tamaño de lote, gestión de cuenta, drawdown máximo, correlación entre TFs, filtros de noticias.

---

## 16. DEBILIDADES Y FORTALEZAS

### Fortalezas

| ✅ | Detalle |
|---|---|
| Coherencia de feed | Mismo OANDA que MT4 — sin desfase |
| Indicadores robustos | Pre-calculados por TradingView (no hay bugs locales) |
| Filtro multi-TF | Elimina contra-tendencias |
| State per-TF | Evita regeneración en loop |
| MFE sticky | TPs no se "borran" por retroceso |
| Sin credenciales | Funciona sin claves API |
| Cooldown | Anti-spam por TF |

### Debilidades

| ⚠️ | Detalle |
|---|---|
| Polling 2s | Latencia mínima vs WebSocket |
| Dependencia de TV público | Sin SLA, pueden cambiar el endpoint |
| Probabilidad heurística | No validada contra datos históricos reales |
| Win rate ficticio | Stats in-memory desde último restart |
| ATR único para todos TFs | (Mejora ya aplicada: per-TF) |
| Sin filtro de noticias | No suprime alrededor de NFP, FOMC, CPI |
| Sin gestión de tamaño de posición | El usuario tiene que decidir su lot size |
| Sin backtest | No hay forma de validar la estrategia históricamente |
| Win rate calculado al expirar | Si la posición se cierra antes en TP1, no se registra como "won" |
| `analysis.atr` puede no ser per-TF | En implementaciones previas usaba ATR default |

---

## 17. ¿HAY IA / LLM?

**NO.** El sistema es **100% determinista** basado en reglas matemáticas. No usa:
- Ningún LLM (OpenAI, Anthropic, Gemini, etc.)
- Ningún modelo de ML entrenado
- Ningún sistema de prompts
- Ningún algoritmo de aprendizaje

Lo único que podría confundirse con "IA" es el `Recommend.All` de TradingView, que es **una agregación estadística** de ~26 indicadores técnicos (no es ML).

---

## 18. REPAINTING, LAG Y RIESGOS TÉCNICOS

### Repainting

**Riesgo bajo**. La entrada se fija con `price_now` al momento de generar la señal. Los TPs/SL son fijos. Lo único que se actualiza en cada poll es:
- `pnl_pct` (cálculo a partir de precio actual)
- `max_favorable` (monotónico — solo aumenta para BUY, disminuye para SELL)
- `tp_hits` (sticky — solo pasa de False a True)
- `sl_hit` (sticky)

⚠️ **Posible repainting si el TV scanner cambia su valor "close" durante una vela en formación**. TradingView usualmente devuelve el último tick, pero el cierre real solo se confirma al cerrar la vela.

### Fuentes de lag

1. **HTTP polling overhead**: ~50-200ms por request
2. **TA cache 8s**: el análisis puede estar hasta 8s desactualizado
3. **TradingView rate limit**: si se excede, falla con HTTP 429
4. **Frontend re-renders**: 8 hooks polling pueden generar re-renders excesivos (no optimizado con memo)
5. **Recharts**: el gauge usa SVG inline ahora, no Recharts (más rápido)

### Causas de falla

- Si **scanner.tradingview.com** cambia el formato de campos → toda la estrategia se rompe
- Si **gold-api.com** desaparece → fallback no funciona (pero TV sigue funcionando)
- Si **Recommend.All** se reformatea → score base distorsionado
- Cambios en escala ATR per-TF afectarían SL/TP retroactivamente

---

## 19. CÓMO OPTIMIZAR Y ESCALAR

### Optimizaciones inmediatas (sin romper la lógica)

1. **WebSocket directo a OANDA o Polygon.io** para sub-segundo (requiere API key)
2. **Persistencia MongoDB del historial** → win rate real
3. **ATR per-TF** (ya aplicado en última iteración)
4. **Backtesting** con datos históricos de Yahoo/Polygon para validar la estrategia
5. **Filtro de noticias** vía API económica (ForexFactory, Investing) — suprime señales 15min antes/después de eventos high-impact
6. **Memoización de componentes React** con `useMemo` y `React.memo`
7. **Server-Sent Events (SSE)** en vez de polling para reducir overhead HTTP

### Escalabilidad

- **Cache distribuido** (Redis) si múltiples instancias backend
- **Worker dedicado** para fetch_tv_analysis (con BackgroundTasks o Celery)
- **CDN edge caching** para endpoints públicos con TTL corto
- **Rate-limit por IP** en API pública

---

## 20. GUÍA DE MIGRACIÓN A CLAUDE / OTRO FRAMEWORK

### 20.1 Si quieres migrarlo a Claude para que la IA INTERPRETE las señales

Esta es la migración más útil — usar Claude como capa de "asesor" sobre las señales determinísticas:

```python
# Prompt sugerido al recibir una señal:
"""
Eres un trader experto en XAU/USD. Analiza la siguiente señal:

DATOS:
- Dirección: {direction}
- Timeframe: {timeframe}
- Score: {score}/100
- RSI({tf}): {rsi}
- MACD: {macd}, MACD hist: {macd_hist}
- CCI: {cci}
- ATR: {atr}
- Bollinger position: {bb_pos}
- Confluencia: {aligned_count}/{total_count} TFs apuntan a {confl_direction}
- Sesión actual: {session_label}

CONTEXTO:
- Probabilidad calculada: {probability_label} ({probability_percent}%)
- Entrada: {entry}, SL: {sl}, TPs: {tp1}/{tp2}/{tp3}
- Recomendación del sistema: {recommendation_label}

TAREA:
1. Valida si la señal tiene sentido lógico
2. Identifica posibles riesgos no contemplados
3. Sugiere ajustes a TP/SL si los ratios no son óptimos
4. Da una recomendación final con justificación
"""
```

### 20.2 Si quieres replicar el sistema EXACTAMENTE en otra plataforma

**Reemplazos necesarios:**

| Componente actual | Reemplazo posible |
|---|---|
| FastAPI | Express.js, Flask, Django, NestJS |
| httpx async | axios, fetch, requests |
| Pydantic | Zod, Joi, Yup, dataclasses |
| MongoDB (Motor) | PostgreSQL, SQLite, Firebase |
| TradingView scanner | TwelveData, Polygon, Alpha Vantage |
| Gold-API.com | metals-api.com, goldprice.org |
| React 19 | Vue 3, Svelte, Next.js, vanilla JS |
| Recharts (no usado en gauge) | Chart.js, ApexCharts, D3 |
| Web Speech API | Sigue funcionando en cualquier navegador |
| Tailwind | UnoCSS, Bootstrap, CSS modules |

**Lo CRÍTICO que no debe cambiar (es el "alma" del sistema):**

1. **La fórmula del score**: `score = int(Recommend.All * 100) + ajustes RSI/MACD/CCI`
2. **El mapeo de confluencia** (qué 3 TFs analizar para cada TF primario)
3. **La fórmula de probabilidad**: `prob = |score|*0.6 + confl*30 + sesión*5`
4. **Los thresholds**: ULTRA≥80+3aligned, ALTA≥65+2aligned, MEDIA≥50, BAJA resto
5. **Los multiplicadores ATR**: 1.2× SL, 1×/2×/3.5× TPs
6. **El escalado tf_atr_scale** por timeframe
7. **El cooldown** del 50% de expiración
8. **La detección de reverso brusco**: ventana 45s, threshold `max(ATR/30, 0.4)`
9. **El sticky de TP/SL** vía MFE
10. **Los tiempos de expiración** por TF

### 20.3 Cosas que pueden romper el sistema si se cambian

- ❌ Cambiar el endpoint de TradingView a uno no equivalente
- ❌ Calcular indicadores localmente con librerías distintas (los valores no coinciden con MT4)
- ❌ Cambiar el orden de evaluación en `compute_recommendation` (SL debe evaluarse antes que TPs)
- ❌ Eliminar el cooldown (vuelve el loop infinito)
- ❌ Eliminar el `max_favorable` MFE (los TPs se desmarcan al retroceder)
- ❌ Cambiar la generation counter en `usePolling` (vuelven las race conditions)
- ❌ Cambiar el confluence_map (cambia toda la calidad de las señales)

### 20.4 Mejoras que sí pueden hacerse

- ✅ Cambiar UI completamente (es solo presentación)
- ✅ Cambiar la voz a ElevenLabs (requiere API key paga)
- ✅ Agregar más timeframes
- ✅ Agregar más pares (EURUSD, BTC, etc.) replicando el flujo
- ✅ Agregar persistencia (MongoDB, SQL)
- ✅ Agregar webhooks salientes (Telegram, Discord, MT4)
- ✅ Agregar autenticación de usuarios
- ✅ Agregar backtesting

---

## 21. PSEUDOCÓDIGO MAESTRO

```pseudocode
# === BACKEND: TODA LA LÓGICA EN UN BUCLE LÓGICO ===

cada vez que /api/signal/active es llamado con timeframe = TF:

    # 1. OBTENER DATOS FRESCOS
    tv_data = HTTP_GET("scanner.tradingview.com/symbol?symbol=OANDA:XAUUSD&fields=...")
           # cacheado 8 segundos
    price = HTTP_GET("scanner.tradingview.com/symbol?symbol=OANDA:XAUUSD&fields=close,bid,ask")
           # fallback: Gold-API si TV falla
    push_to_tick_buffer(price)

    # 2. ANALIZAR EL TF SELECCIONADO
    score_TF = Recommend.All[TF] * 100
    if RSI[TF] < 30: score_TF += 8
    elif RSI[TF] > 70: score_TF -= 8
    if MACD.macd[TF] > MACD.signal[TF]: score_TF += 5 else: score_TF -= 5
    if CCI20[TF] > 100: score_TF += 5 elif CCI20[TF] < -100: score_TF -= 5
    score_TF = clamp(score_TF, -100, +100)

    if score_TF >= +25:   direction = BUY
    elif score_TF <= -25: direction = SELL
    else:                 direction = NEUTRAL

    confidence = min(99, |score_TF| + 30)

    # 3. CALCULAR CONFLUENCIA (3 TFs adyacentes)
    confluence_tfs = lookup_in_confluence_map(TF)  # ej. ["5m","15m","1h"]
    para cada t en confluence_tfs:
        analyses[t] = analyze_timeframe_tv(tv_data, t, price)
    buy_count = count(a.direction == BUY)
    sell_count = count(a.direction == SELL)
    aligned = max(buy_count, sell_count)
    confl_dir = mayoria(buy_count, sell_count)

    # 4. CALCULAR PROBABILIDAD
    confl_match = (confl_dir == direction)
    prob = |score_TF| * 0.6
        + (aligned/total * 100 if confl_match else 0) * 0.3
        + (5 si sesión Londres o NY)
    prob = clamp(int(prob), 0, 99)

    if prob >= 80 y aligned >= 3:  probability = ULTRA, take = true
    elif prob >= 65 y aligned >= 2: probability = ALTA,  take = true
    elif prob >= 50:                probability = MEDIA, take = false
    else:                           probability = BAJA,  take = false

    # 5. ¿HAY SEÑAL ACTIVA PARA ESTE TF?
    cur = STATE.active_signals[TF]
    si cur y cur no expirada:
        # Actualizar P&L
        pnl = (price - entry)/entry * 100 si BUY else (entry - price)/entry * 100
        cur.pnl_pct = pnl

        # MFE
        cur.max_favorable = max(prev, price) si BUY else min(prev, price)

        # Sticky TP hits
        para tp en [tp1, tp2, tp3]:
            si cur.tp_hits[tp] continúa
            si (BUY y mfe >= cur[tp]) o (SELL y mfe <= cur[tp]):
                cur.tp_hits[tp] = true

        # Sticky SL
        si no cur.sl_hit:
            cur.sl_hit = (BUY y price <= cur.sl) o (SELL y price >= cur.sl)

        recommendation = compute_recommendation(cur, price, analysis, probability)
        return cur + recommendation

    # 6. SI EXPIRÓ → LIMPIAR
    si cur expirada: STATE.active_signals.delete(TF)

    # 7. COOLDOWN
    si time.now < STATE.signal_cooldown[TF]:
        return signal=null + recommendation(none, probability)

    # 8. CREAR NUEVA SEÑAL si pasa filtros
    si direction != NEUTRAL y probability != BAJA y confl_dir compatible:
        atr = analyses[TF].atr
        eff_atr = atr * tf_atr_scale[TF]

        entry = price
        si BUY:
            sl = entry - eff_atr * 1.2
            tp1 = entry + eff_atr * 1.0
            tp2 = entry + eff_atr * 2.0
            tp3 = entry + eff_atr * 3.5
        sino:  # SELL
            sl = entry + eff_atr * 1.2
            tp1 = entry - eff_atr * 1.0
            tp2 = entry - eff_atr * 2.0
            tp3 = entry - eff_atr * 3.5

        nueva_signal = {
            id: uuid4(),
            direction, timeframe: TF, confidence: prob,
            entry, sl, tp1, tp2, tp3,
            created_at: now, expires_at: now + expires_min[TF],
            status: active, tp_hits: {tp1:false,tp2:false,tp3:false},
            sl_hit: false, max_favorable: null
        }
        STATE.active_signals[TF] = nueva_signal
        STATE.history.insert(0, nueva_signal)
        STATE.signal_cooldown[TF] = now + (expires_min[TF] * 60 * 0.5)

    # 9. RECOMENDACIÓN (8 reglas priorizadas)
    sig = STATE.active_signals[TF]
    si sig == null:
        return recommendation = ESPERAR (no signal) + take=false

    # Regla 1: SL hit
    si (BUY y price <= sl) o (SELL y price >= sl):
        return STOP_LOSS_HIT (urgent, danger)

    # Reglas 2-4: TPs
    si TP3 alcanzado: return "TP3 ALCANZADO" (cerrar todo)
    si TP2 alcanzado: return "TP2 ALCANZADO" (cerrar 60%)
    si TP1 alcanzado: return "TP1 ALCANZADO" (cerrar 30-50%)

    # Regla 5: reverso brusco vía ticks
    ticks_45s = STATE.ticks últimos 45 segundos
    delta = último.price - primero.price
    threshold = max(atr/30, 0.4)
    si BUY y delta < -threshold: return CERRAR_REVERSO (urgent, danger)
    si SELL y delta > threshold: return CERRAR_REVERSO (urgent, danger)

    # Regla 6: cerca de entrada
    si |price-entry|/entry <= 0.0015 y confidence >= 70:
        si take_flag: return TOMAR_AHORA (urgent, buy/sell)
        sino:         return NO_TOMAR (medium, neutral)

    # Regla 7: precio se alejó
    si |price-entry|/entry * 100 > 0.3:
        return ESPERAR "precio se alejó" (low, neutral)

    # Regla 8: default
    return MANTENER POSICIÓN (low, buy/sell)


# === FRONTEND: BUCLE DE POLLING ===
cada 2 segundos: GET /api/price
cada 4 segundos: GET /api/binary/next-candle
cada 6 segundos: GET /api/signal/active?timeframe=<tf>
cada 10 segundos: GET /api/strength
cada 15 segundos: GET /api/multi-timeframe, /api/signal/history, /api/stats
cada 30 segundos: GET /api/sessions

# === USEVOICEALERTS ===
cuando cambia signal.id o recommendation.label:
    composite_key = signal.id + "|" + recommendation.label
    si composite_key == lastKey: no hablar
    si (now - lastSpokenAt) < 8000ms: no hablar
    sino:
        speak(phrase_basado_en_action)
        lastSpokenAt = now
        lastKey = composite_key

cuando cambia timeframe:
    resetear lastKey y initialized
```

---

## 22. NOTAS FINALES PARA REPLICACIÓN

1. **El "secreto"** del sistema NO está en el código sino en el endpoint público de TradingView que entrega indicadores calculados con la **misma data que ven los traders reales** en sus brokers. Si reproduces el sistema con tu propio cálculo de RSI/MACD/CCI sobre velas de Yahoo o Binance, **los valores serán distintos** y la estrategia perderá su ventaja.

2. **La probabilidad NO es estadística histórica** — es una heurística que combina score actual + confluencia + sesión. NO refleja win rate real comprobado.

3. **El win rate mostrado en `/api/stats` es ficticio** — empieza en 100% hasta que haya señales cerradas, y solo se actualiza cuando una señal expira (no cuando hace TP).

4. **El sistema es DETERMINISTA** — dadas las mismas entradas (precio + indicadores), produce el mismo output. No hay aleatoriedad ni IA.

5. **No usa velas OHLC** — todo el análisis viene de indicadores agregados de TradingView. No procesa velas individuales para detectar patrones (no hay engulfing, doji, hammer, etc.).

6. **No detecta consolidaciones, rompimientos, fakeouts explícitamente** — solo confía en que los indicadores de TradingView ya capturan estos contextos a través del `Recommend.All` consensuado.

---

**Fin del documento de auditoría técnica.**
