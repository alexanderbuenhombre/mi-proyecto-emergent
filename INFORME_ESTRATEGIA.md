# 📊 Informe técnico — Estrategia XAU/USD y manejo de tiempo real

> Auditoría basada en el código real de `/app/backend/server.py` y `/app/frontend/src/`.
> Sin especulaciones: cada número y fórmula proviene del código fuente.

---

## 1. Estrategia de detección de señales

### 1.1 Fuente única de verdad — TradingView Technical Analysis

La estrategia **no calcula indicadores localmente** con pandas/numpy. En su lugar, consume el endpoint público de TradingView que devuelve indicadores **pre-calculados** sobre el mismo feed spot que usan los brokers reales:

```
GET https://scanner.tradingview.com/symbol
    ?symbol=OANDA:XAUUSD
    &fields=RSI|5,MACD.macd|5,MACD.signal|5,CCI20|5,Mom|5,
            BB.upper|5,BB.lower|5,Recommend.All|5,ATR|5,close,volume,...
```

El sufijo `|<code>` indica la temporalidad: `1` (1m), `5` (5m), `15`, `30`, `60` (1h), `240` (4h), `1D`, `1W`.

**Por qué importa**: como el precio mostrado proviene del mismo feed OANDA, los indicadores **coinciden con MT4 / Exness / XM / IC Markets sin desfase**. El cache local es de 8s (`STATE["ta_cache"]`) para evitar rate-limit.

### 1.2 Indicadores utilizados

| Indicador | Función en la estrategia | Período / parámetro |
|---|---|---|
| **Recommend.All** | Score base — consenso de ~26 indicadores TV | Devuelve −1.0 a +1.0 |
| **RSI** | Sobrecompra / sobreventa | 14 (default TV) |
| **MACD** (línea + señal) | Confirma momentum direccional | 12 / 26 / 9 |
| **CCI20** | Condiciones extremas | 20 |
| **Momentum** | Fuerza del movimiento reciente | 10 |
| **Bollinger Bands** | Posición relativa al canal | 20, 2σ |
| **ATR** | Calcula SL/TP y umbral de reverso | 14 (per-TF) |

### 1.3 Fórmula del score por timeframe — `analyze_timeframe_tv`

```python
score = int(Recommend.All * 100)          # base: -100 a +100

if RSI < 30:    score += 8                # sobreventa → refuerza COMPRA
elif RSI > 70:  score -= 8                # sobrecompra → refuerza VENTA

if MACD_line > MACD_signal: score += 5    # momentum alcista
else:                       score -= 5    # momentum bajista

if CCI > +100:   score += 5               # impulso fuerte alcista
elif CCI < -100: score -= 5               # impulso fuerte bajista

score = clamp(score, -100, +100)
```

**Decisión de dirección por TF:**

```
score ≥ +25  → BUY
score ≤ -25  → SELL
en medio     → NEUTRAL
confidence = min(99, |score| + 30)
```

### 1.4 Confluencia multi-timeframe (filtro anti-falsos)

Antes de emitir señal, se evalúan **3 TFs adyacentes**:

| TF primario | Confluencia analizada |
|---|---|
| 1m  | [1m, 5m, 15m]  |
| 5m  | [5m, 15m, 1h]  |
| 15m | [5m, 15m, 1h]  |
| 30m | [15m, 30m, 1h] |
| 1h  | [15m, 1h, 4h]  |
| 4h  | [1h, 4h, 1d]   |
| 1d  | [4h, 1d]       |

Se cuenta cuántos coinciden en BUY vs SELL → `aligned_count` (máximo entre ambos).

### 1.5 Probabilidad (ULTRA / ALTA / MEDIA / BAJA)

```python
prob = |score| * 0.6
     + (aligned_count / total) * 100 * 0.3   # solo si confluencia coincide
     + 5                                      # bonus si Londres o NY activa

ULTRA : prob ≥ 80  Y  aligned ≥ 3      → take = True
ALTA  : prob ≥ 65  Y  aligned ≥ 2      → take = True
MEDIA : prob ≥ 50                       → take = False (visible pero NO recomendable)
BAJA  : resto                           → no se emite señal
```

### 1.6 Filtros que evitan señales falsas

1. **Score mínimo absoluto**: `|score| ≥ 25` para considerar dirección
2. **Probabilidad ≠ BAJA**: bloquea condiciones débiles
3. **Confluencia no contradictoria**: si la mayoría de TFs dice lo contrario, bloqueado
4. **Cooldown por TF**: tras emitir señal en TF=X, no puede emitirse otra hasta el **50% del tiempo de expiración**
5. **Sesión líquida**: bonus +5 al score si Londres o NY están activas

### 1.7 Cálculo de Entrada, Stop Loss y Take Profits

```python
# ATR escalado por timeframe (factor empírico para ajustar volatilidad esperada)
tf_atr_scale = {
    "1m": 0.15, "5m": 0.25, "15m": 0.4, "30m": 0.6,
    "1h": 0.8,  "4h": 1.0,  "1d": 1.2
}
eff_atr = ATR_per_TF * tf_atr_scale[timeframe]

entry = precio_spot_actual

# BUY (inverso para SELL):
SL  = entry − eff_atr × 1.2       # riesgo
TP1 = entry + eff_atr × 1.0       # R:R ≈ 1:0.83
TP2 = entry + eff_atr × 2.0       # R:R ≈ 1:1.66
TP3 = entry + eff_atr × 3.5       # R:R ≈ 1:2.9
```

### 1.8 Tracking de TPs y SL (sticky)

Cada poll actualiza `max_favorable` — el mejor precio alcanzado en dirección de la señal (`max` para BUY, `min` para SELL). Una vez `tp_hits["tpN"] = True`, **queda marcado aunque el precio retroceda** — usa MFE (Maximum Favorable Excursion), no precio actual. El SL es trigger duro y usa precio actual.

### 1.9 Motor de recomendaciones — prioridad de decisiones

```
1. STOP_LOSS_HIT        → precio cruzó SL                          [URGENTE]
2. TP3 alcanzado        → objetivo final, cerrar todo
3. TP2 alcanzado        → cerrar 60% + mover SL → TP1
4. TP1 alcanzado        → cerrar 30-50% + SL → entrada
5. REVERSO_BRUSCO       → Δ ticks contra señal > ATR/30 en 45s     [cerrar]
6. TOMAR_AHORA          → cerca de entrada (±0.15%) + conf ≥ 70 + take=True
   NO_TOMAR             → mismo punto pero take=False (probabilidad MEDIA)
7. ESPERAR              → precio se alejó > 0.3% de entrada
8. MANTENER             → caso por defecto
```

Tiempos de expiración por TF: 1m=3min · 5m=15min · 15m=45min · 30m=90min · 1h=4h · 4h=16h · 1d=24h.

---

## 2. Manejo de tiempo real

### 2.1 Precio — polling rápido (no WebSockets)

**Backend — `get_price()`:**

- **Primaria**: TradingView scanner (`OANDA:XAUUSD`) → `close`, `change`, `bid`, `ask`
- **Fallback**: Gold-API.com (LBMA) si TradingView falla
- **Último recurso**: cache (`STATE["last_price"]`)

**Frontend — `usePolling`:**

- `/api/price?source=tradingview` cada **2 segundos**
- Hook con **generation counter** que cancela respuestas obsoletas al cambiar deps (evita race condition cuando el usuario cambia parámetros)

**Tick buffer** (`STATE["ticks"]`):

- `deque(maxlen=600)` → ~20 minutos a 2s/tick
- Tuplas `(timestamp, price)`
- Usado por `detect_sudden_move()` para detectar reversos bruscos en ventana de 45s

**Frescura** (`fresh_seconds`):

- Cada vez que el precio realmente **cambia** (no solo se consulta), actualiza `last_price_change_at`
- Frontend muestra `tick Ns` → verde ≤ 5s, ámbar ≤ 15s, rojo > 15s

### 2.2 Señales en tiempo real

**Estado per-TF** (clave para evitar regeneración en loop):

```python
STATE["active_signals"] = {
    "1m":  {signal dict},
    "5m":  {signal dict},
    "15m": {signal dict},
    ...
}
STATE["signal_cooldown"] = { "5m": ts_until_can_regenerate, ... }
```

Cada TF mantiene su **señal independiente** → cambiar de timeframe en el frontend no destruye señales activas en otros TFs.

**Polling desde frontend:**

| Endpoint | Intervalo | Propósito |
|---|---|---|
| `/api/price` | 2s | Precio spot |
| `/api/binary/next-candle` | 4s | Predicción CALL/PUT 1m y 5m |
| `/api/signal/active` | 6s | Señal del TF seleccionado |
| `/api/strength` | 10s | Barras de fuerza |
| `/api/multi-timeframe` | 15s | Análisis de los 7 TFs |
| `/api/signal/history` | 15s | Historial in-memory |
| `/api/stats` | 15s | Estadísticas |
| `/api/sessions` | 30s | Sesiones Sydney / Tokyo / Londres / NY |

### 2.3 Ciclo lógico de una señal — paso a paso

```
[Frontend, cada 6s] ──► GET /api/signal/active?timeframe=5m
                       │
                       ▼
  ┌─────────────────────────────────────────────────┐
  │ 1. fetch_tv_analysis()  (cache 8s)              │  ← TradingView TA multi-TF
  │ 2. get_price("tradingview")                     │  ← precio spot fresco
  │ 3. analyze_timeframe_tv(tv, "5m", p)            │  ← score, RSI, MACD, CCI...
  │ 4. compute_confluence(tv, p, "5m")              │  ← analiza 5m + 15m + 1h
  │ 5. compute_probability(...)                     │  ← ULTRA / ALTA / MEDIA / BAJA
  └─────────────────────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────┐
  │ ¿Hay active_signals["5m"] no expirada?          │
  │   SÍ → actualiza pnl_pct, max_favorable,        │
  │        tp_hits[sticky], sl_hit[sticky],         │
  │        retorna mismo signal                     │
  │   NO → ¿cooldown vigente?                       │
  │        SÍ → retorna signal=null                 │
  │        NO → _make_signal(...)                   │
  └─────────────────────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────┐
  │ _make_signal — filtros estrictos                │
  │  - direction ≠ NEUTRAL                          │
  │  - probability ≠ BAJA                           │
  │  - confluence no contradictoria                 │
  │  Si pasa → crea Signal con TP/SL desde ATR     │
  │  → guarda en active_signals[tf]                 │
  │  → set signal_cooldown[tf] = +50% expiración    │
  └─────────────────────────────────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────────────┐
  │ compute_recommendation(signal, price, ...)      │
  │  → action (TOMAR / ESPERAR / CERRAR / ...)      │
  │  → take + take_label + take_reason              │
  └─────────────────────────────────────────────────┘
                       │
                       ▼
  Response: {
    signal,        // dirección, entrada, TPs, SL, tp_hits, sl_hit, pnl_pct
    analysis,      // score, RSI, MACD, CCI, ATR
    price,         // precio actual + freshness
    recommendation,// TOMAR / NO_TOMAR / TP_HIT / SL_HIT / ESPERAR
    confluence,    // detalles de los 3 TFs
    probability    // ULTRA / ALTA / MEDIA / BAJA + take + reason
  }
```

### 2.4 Alertas de voz — cliente, sin backend

Web Speech API del navegador (`window.speechSynthesis`). Hook `useVoiceAlerts` con tres mecanismos anti-spam:

1. **Composite key** `signal.id + recommendation.label` → solo habla si cambia
2. **Cooldown global de 8 segundos** entre cualquier dos utterances
3. **Reset al cambiar timeframe** (evita disparo en cambio de TF)

Eventos disparadores (cada uno toggleable en `VoiceSettings`):

- Nueva señal generada
- `TOMAR_AHORA`
- TP1 / TP2 / TP3 alcanzado
- Stop Loss alcanzado
- Reverso brusco
- `ESPERAR` (apagado por defecto)

---

## 3. Diagrama de arquitectura

```
┌────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Dashboard.jsx                                            │  │
│  │  ├─ usePolling × 8 (price 2s, signal 6s, mt-tf 15s, ...) │  │
│  │  ├─ useVoiceAlerts (dedup + 8s cooldown)                 │  │
│  │  └─ Componentes:                                          │  │
│  │       PriceHeader · BullsBearsGauge · ConfluencePanel    │  │
│  │       ActiveSignalCard (TPs sticky · recomendación)      │  │
│  │       MultiTimeframe · StrengthBars · MarketSessions     │  │
│  │       NextCandleBinary · SignalHistory · SystemStats     │  │
│  │       SourceSelector · VoiceSettings                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                          │ HTTP (REACT_APP_BACKEND_URL/api/*)
                          ▼
┌────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  server.py                                                │  │
│  │  ├─ Price fetchers (httpx async)                          │  │
│  │  ├─ TV Technical Analysis (cache 8s)                      │  │
│  │  ├─ analyze_timeframe_tv (score + indicadores)            │  │
│  │  ├─ compute_confluence (3 TFs)                            │  │
│  │  ├─ compute_probability (ULTRA/ALTA/MEDIA/BAJA)           │  │
│  │  ├─ _make_signal (filtros + ATR-based TP/SL)              │  │
│  │  ├─ compute_recommendation (8 acciones priorizadas)       │  │
│  │  └─ detect_sudden_move (ticks 45s window)                 │  │
│  │                                                            │  │
│  │  STATE in-memory:                                          │  │
│  │   · active_signals[tf]  · signal_cooldown[tf]              │  │
│  │   · ticks (deque 600)   · ta_cache (8s)                    │  │
│  │   · history (50 last)   · stats                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                  │                                  │
                  ▼                                  ▼
   ┌─────────────────────────────┐   ┌─────────────────────────────┐
   │  TradingView Scanner API    │   │      Gold-API.com           │
   │  scanner.tradingview.com    │   │      api.gold-api.com       │
   │  → spot OANDA + indicadores │   │      → fallback LBMA spot   │
   └─────────────────────────────┘   └─────────────────────────────┘
```

---

## 4. Resumen ejecutivo

- **Estrategia**: confluencia multi-TF (3 timeframes) usando indicadores pre-calculados de TradingView sobre el feed OANDA spot
- **Indicadores**: `Recommend.All` como base + RSI, MACD, CCI, Momentum, Bollinger, ATR (todos period default)
- **Filtros anti-falsos**: score ≥ 25, probabilidad ≠ BAJA, confluencia no contradictoria, cooldown por TF, bonus de sesión líquida
- **SL / TP**: derivados de ATR × factor por TF — ratio R:R hasta 1:2.9 en TP3
- **Sticky tracking**: TPs y SL se quedan marcados una vez tocados (no se "borran" si el precio retrocede)
- **Tiempo real**: polling HTTP cada 2 s para precio, 6 s para señal — buffer de 600 ticks (~20 min) para detectar reversos bruscos
- **Voz**: Web Speech del navegador, sin costos, con cooldown y dedup para evitar spam
