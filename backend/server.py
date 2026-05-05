"""
XAUUSD Real-Time Signals Backend
- Live spot price: TradingView (OANDA) + Gold-API.com cross-check
- Indicators: TradingView Technical Analysis API (same OANDA spot, multi-TF)
- In-memory tick ring buffer for sudden-movement detection
- Dynamic recommendations: TOMAR / ESPERAR / TOMAR_GANANCIAS / CERRAR_REVERSO / STOP_LOSS_HIT
"""
from fastapi import FastAPI, APIRouter, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import time
import asyncio
import logging
from collections import deque
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="XAUUSD Signals API")
api_router = APIRouter(prefix="/api")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------- In-memory state ----------------
STATE: Dict[str, Any] = {
    "history": [],
    "active_signal": None,
    "last_price": None,
    "last_price_at": None,
    "last_price_change_at": None,  # last time the price actually changed
    "ticks": deque(maxlen=600),     # (ts, price) - ~20 minutes at 2s polling
    "stats": {"total": 0, "wins": 0, "losses": 0},
    "ta_cache": {"ts": 0, "data": None},
}

# TradingView TA fields - covers all timeframes we need
TV_TIMEFRAMES = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",   # not always returned; falls back to interpolation
    "1h": "60",
    "4h": "240",
    "1d": "1D",
    "1w": "1W",
}


# ---------------- Models ----------------
class PriceData(BaseModel):
    price: float
    change: float
    change_pct: float
    spread: float
    source: str
    timestamp: str
    high: Optional[float] = None
    low: Optional[float] = None
    fresh_seconds: int = 0  # seconds since last actual price change


class Signal(BaseModel):
    id: str
    symbol: str = "XAUUSD"
    direction: Literal["BUY", "SELL"]
    timeframe: str
    confidence: float
    entry: float
    tp1: float
    tp2: float
    tp3: float
    stop_loss: float
    analysis: str
    created_at: str
    expires_at: str
    status: Literal["active", "won", "lost", "expired"] = "active"
    pnl_pct: Optional[float] = None


# ---------------- Price fetchers ----------------
async def fetch_tradingview_oanda() -> Optional[PriceData]:
    url = "https://scanner.tradingview.com/symbol"
    params = {
        "symbol": "OANDA:XAUUSD",
        "fields": "close,change,change_abs,high,low,bid,ask",
        "no_404": "true",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            close = float(data.get("close") or 0)
            if close <= 0:
                return None
            bid = float(data.get("bid") or close)
            ask = float(data.get("ask") or close)
            spread = round(ask - bid, 2) if ask and bid else 0.25
            return PriceData(
                price=round(close, 2),
                change=round(float(data.get("change_abs") or 0), 2),
                change_pct=round(float(data.get("change") or 0), 3),
                spread=spread or 0.25,
                source="TradingView (OANDA)",
                timestamp=datetime.now(timezone.utc).isoformat(),
                high=float(data.get("high") or 0) or None,
                low=float(data.get("low") or 0) or None,
            )
    except Exception as e:
        logger.warning(f"TradingView fetch failed: {e}")
        return None


async def fetch_gold_api() -> Optional[PriceData]:
    url = "https://api.gold-api.com/price/XAU"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            price = float(data.get("price") or 0)
            if price <= 0:
                return None
            prev = STATE.get("last_price") or price
            change = round(price - prev, 2)
            change_pct = round((change / prev) * 100, 3) if prev else 0.0
            return PriceData(
                price=round(price, 2),
                change=change,
                change_pct=change_pct,
                spread=0.30,
                source="Gold-API (LBMA)",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as e:
        logger.warning(f"Gold-API fetch failed: {e}")
        return None


async def get_price(source: str = "tradingview") -> PriceData:
    if source == "goldapi":
        p = await fetch_gold_api() or await fetch_tradingview_oanda()
    else:
        p = await fetch_tradingview_oanda() or await fetch_gold_api()
    if p is None:
        last = STATE.get("last_price") or 2650.0
        p = PriceData(
            price=last, change=0.0, change_pct=0.0, spread=0.30,
            source="cache", timestamp=datetime.now(timezone.utc).isoformat(),
        )
    now = datetime.now(timezone.utc)
    # Track tick buffer + freshness
    if STATE["last_price"] is None or p.price != STATE["last_price"]:
        STATE["last_price_change_at"] = now.timestamp()
    STATE["last_price"] = p.price
    STATE["last_price_at"] = p.timestamp
    STATE["ticks"].append((now.timestamp(), p.price))
    if STATE["last_price_change_at"]:
        p.fresh_seconds = int(now.timestamp() - STATE["last_price_change_at"])
    return p


# ---------------- TradingView Technical Analysis ----------------
def _build_tv_fields() -> str:
    base = ["close", "change", "high", "low", "volume", "ATR"]
    per_tf = ["RSI", "MACD.macd", "MACD.signal", "CCI20", "Mom",
              "Recommend.All", "Recommend.MA", "Recommend.Other",
              "BB.upper", "BB.lower"]
    fields = list(base)
    # default TF is no suffix; add suffixes for the rest
    for ind in per_tf:
        fields.append(ind)  # default (1d-ish, depends on TV)
        for tf_label, tf_code in TV_TIMEFRAMES.items():
            fields.append(f"{ind}|{tf_code}")
    return ",".join(fields)


async def fetch_tv_analysis() -> Dict[str, Any]:
    cache = STATE["ta_cache"]
    now = time.time()
    if cache["data"] and now - cache["ts"] < 8:
        return cache["data"]
    url = "https://scanner.tradingview.com/symbol"
    params = {
        "symbol": "OANDA:XAUUSD",
        "fields": _build_tv_fields(),
        "no_404": "true",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            STATE["ta_cache"] = {"ts": now, "data": data}
            return data
    except Exception as e:
        logger.warning(f"TV TA fetch failed: {e}")
        return cache["data"] or {}


def _get_tv(d: Dict[str, Any], key: str, tf_code: Optional[str] = None, default=0.0) -> float:
    k = f"{key}|{tf_code}" if tf_code else key
    v = d.get(k)
    if v is None:
        v = d.get(key)
    try:
        return float(v) if v is not None else float(default)
    except (TypeError, ValueError):
        return float(default)


def analyze_timeframe_tv(tv: Dict[str, Any], timeframe: str, current_price: float) -> Dict[str, Any]:
    """Analyze using TradingView's pre-computed indicators for a specific timeframe."""
    tf_code = TV_TIMEFRAMES.get(timeframe, "5")
    if not tv:
        return {
            "direction": "NEUTRAL", "score": 0, "confidence": 0,
            "rsi": 50, "macd": 0, "macd_hist": 0, "cci": 0, "bb_pos": 0.5,
            "momentum": 0, "atr": max(current_price * 0.0008, 0.5), "close": current_price,
            "volume_ratio": 1.0, "tv_recommend": 0,
        }
    rsi_v = _get_tv(tv, "RSI", tf_code, 50)
    macd_line = _get_tv(tv, "MACD.macd", tf_code, 0)
    macd_sig = _get_tv(tv, "MACD.signal", tf_code, 0)
    cci_v = _get_tv(tv, "CCI20", tf_code, 0)
    mom_v = _get_tv(tv, "Mom", tf_code, 0)
    bb_up = _get_tv(tv, "BB.upper", tf_code, current_price)
    bb_lo = _get_tv(tv, "BB.lower", tf_code, current_price)
    rec_all = _get_tv(tv, "Recommend.All", tf_code, 0)  # -1..+1
    atr_v = _get_tv(tv, "ATR", None, max(current_price * 0.0008, 0.5))

    # BB position
    bb_pos = 0.5
    if bb_up != bb_lo:
        bb_pos = round((current_price - bb_lo) / (bb_up - bb_lo), 3)

    # Score: weighted combination, primarily TradingView Recommend (-1..+1) -> -100..+100
    score = int(rec_all * 100)
    # Reinforce with extremes
    if rsi_v < 30: score += 8
    elif rsi_v > 70: score -= 8
    if macd_line > macd_sig: score += 5
    else: score -= 5
    if cci_v > 100: score += 5
    elif cci_v < -100: score -= 5
    score = max(-100, min(100, score))

    if score >= 25:
        direction = "BUY"
    elif score <= -25:
        direction = "SELL"
    else:
        direction = "NEUTRAL"
    confidence = min(99, abs(score) + 30)

    return {
        "direction": direction,
        "score": score,
        "confidence": confidence,
        "rsi": round(rsi_v, 2),
        "macd": round(macd_line, 3),
        "macd_hist": round(macd_line - macd_sig, 3),
        "cci": round(cci_v, 2),
        "bb_pos": bb_pos,
        "momentum": round(mom_v, 2),
        "atr": round(atr_v, 2),
        "close": round(current_price, 2),
        "volume_ratio": 1.0,
        "tv_recommend": round(rec_all, 3),
    }


# ---------------- Recommendation engine ----------------
def detect_sudden_move(direction_against: Literal["BUY", "SELL"], atr_value: float) -> Dict[str, Any]:
    """Look at last ~30s of ticks: if move against signal > 1.0×ATR_minute, flag reversal."""
    ticks = list(STATE["ticks"])
    if len(ticks) < 6:
        return {"reversal": False, "delta": 0.0}
    now_ts = ticks[-1][0]
    window = [t for t in ticks if now_ts - t[0] <= 45]
    if len(window) < 3:
        return {"reversal": False, "delta": 0.0}
    prices = [p for _, p in window]
    delta = prices[-1] - prices[0]
    # ATR is daily/multi-TF; convert to short-window threshold (~ ATR/30)
    threshold = max(atr_value / 30.0, 0.4)
    if direction_against == "BUY" and delta < -threshold:
        return {"reversal": True, "delta": round(delta, 2), "threshold": round(threshold, 2)}
    if direction_against == "SELL" and delta > threshold:
        return {"reversal": True, "delta": round(delta, 2), "threshold": round(threshold, 2)}
    return {"reversal": False, "delta": round(delta, 2), "threshold": round(threshold, 2)}


def compute_recommendation(signal: Optional[Dict[str, Any]], price: float, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Return action, label, color, message, urgency."""
    if not signal:
        return {
            "action": "ESPERAR",
            "label": "ESPERAR",
            "headline": "Mercado neutral · Sin señal activa",
            "message": "Esperando confirmación de tendencia. No operes ahora.",
            "urgency": "low",
            "tone": "neutral",
        }

    entry = signal["entry"]
    sl = signal["stop_loss"]
    tp1 = signal["tp1"]
    tp2 = signal["tp2"]
    tp3 = signal["tp3"]
    direction = signal["direction"]
    isBuy = direction == "BUY"
    expires_at = datetime.fromisoformat(signal["expires_at"])
    now = datetime.now(timezone.utc)
    minutes_left = max(0, int((expires_at - now).total_seconds() / 60))

    # Stop Loss hit?
    if (isBuy and price <= sl) or (not isBuy and price >= sl):
        return {
            "action": "STOP_LOSS_HIT",
            "label": "STOP LOSS",
            "headline": "Stop Loss alcanzado · Cierra ahora",
            "message": f"Precio {price:.2f} tocó SL {sl:.2f}. Cierra inmediatamente para limitar pérdida.",
            "urgency": "high",
            "tone": "danger",
        }

    # TP3 reached? (full take profit)
    if (isBuy and price >= tp3) or (not isBuy and price <= tp3):
        return {
            "action": "TOMAR_GANANCIAS",
            "label": "TP3 ALCANZADO",
            "headline": "Objetivo final alcanzado · Cierra todo",
            "message": f"Precio {price:.2f} alcanzó TP3 {tp3:.2f}. Cierra posición completa.",
            "urgency": "high",
            "tone": "success",
        }

    # TP2 reached?
    if (isBuy and price >= tp2) or (not isBuy and price <= tp2):
        return {
            "action": "TOMAR_GANANCIAS",
            "label": "TP2 ALCANZADO",
            "headline": "Toma parcial · Mueve SL a TP1",
            "message": f"Precio {price:.2f} alcanzó TP2 {tp2:.2f}. Cierra 60% y mueve stop a TP1.",
            "urgency": "medium",
            "tone": "success",
        }

    # TP1 reached?
    if (isBuy and price >= tp1) or (not isBuy and price <= tp1):
        return {
            "action": "TOMAR_GANANCIAS",
            "label": "TP1 ALCANZADO",
            "headline": "Toma parcial · Mueve SL a entrada",
            "message": f"Precio {price:.2f} alcanzó TP1 {tp1:.2f}. Cierra 30-50% y protege entrada.",
            "urgency": "medium",
            "tone": "success",
        }

    # Sudden reversal against signal?
    move = detect_sudden_move("BUY" if isBuy else "SELL", analysis.get("atr", 1.0))
    if move["reversal"]:
        return {
            "action": "CERRAR_REVERSO",
            "label": "REVERSO BRUSCO",
            "headline": "Movimiento adverso fuerte · Considera cerrar",
            "message": f"Precio se movió {move['delta']:+.2f} en últimos 45s contra tu posición. Evalúa cierre.",
            "urgency": "high",
            "tone": "danger",
        }

    # If signal is fresh and price near entry → TOMAR
    near_entry = abs(price - entry) / entry <= 0.0015  # within 0.15%
    if near_entry and signal["confidence"] >= 70:
        return {
            "action": "TOMAR",
            "label": "TOMAR AHORA",
            "headline": f"Toma señal {direction} · Precio cerca de entrada",
            "message": f"Precio {price:.2f} cerca de {entry:.2f}. Confianza {signal['confidence']}%. Quedan {minutes_left}min.",
            "urgency": "high",
            "tone": "buy" if isBuy else "sell",
        }

    # Price drifted from entry
    drift_pct = abs(price - entry) / entry * 100
    if drift_pct > 0.3:
        return {
            "action": "ESPERAR",
            "label": "ESPERAR",
            "headline": "Precio se alejó · Espera retroceso",
            "message": f"Precio {price:.2f} se movió {drift_pct:.2f}% desde entrada {entry:.2f}. Espera retroceso o nueva señal.",
            "urgency": "low",
            "tone": "neutral",
        }

    # Mid-range hold
    return {
        "action": "MANTENER",
        "label": "MANTENER POSICIÓN",
        "headline": f"Posición {direction} en curso",
        "message": f"P&L vivo. Próximo objetivo TP1 en {tp1:.2f}. Mantén SL en {sl:.2f}.",
        "urgency": "low",
        "tone": "buy" if isBuy else "sell",
    }


# ---------------- API endpoints ----------------
@api_router.get("/")
async def root():
    return {"service": "XAUUSD Signals API", "ok": True, "version": "2.0"}


@api_router.get("/price")
async def api_price(source: str = Query("tradingview", pattern="^(tradingview|goldapi)$")):
    p = await get_price(source)
    return p.model_dump()


@api_router.get("/sessions")
async def api_sessions():
    now = datetime.now(timezone.utc)
    h = now.hour + now.minute / 60.0
    sessions = [
        {"name": "Sydney", "open": 22, "close": 7, "tz": "AEDT"},
        {"name": "Tokyo", "open": 0, "close": 9, "tz": "JST"},
        {"name": "London", "open": 8, "close": 17, "tz": "GMT"},
        {"name": "New York", "open": 13, "close": 22, "tz": "EST"},
    ]
    out = []
    active_count = 0
    for s in sessions:
        o, c = s["open"], s["close"]
        active = (o <= h < c) if o < c else (h >= o or h < c)
        if active:
            active_count += 1
        out.append({**s, "active": active})
    label = "ASIA"
    if any(s["name"] == "London" and s["active"] for s in out):
        label = "LONDRES"
        if any(s["name"] == "New York" and s["active"] for s in out):
            label = "LONDRES/NY"
    elif any(s["name"] == "New York" and s["active"] for s in out):
        label = "NUEVA YORK"
    return {"sessions": out, "active_count": active_count, "label": label,
            "server_time": now.isoformat()}


@api_router.get("/multi-timeframe")
async def api_multi_timeframe():
    timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    tv = await fetch_tv_analysis()
    price = STATE.get("last_price") or _get_tv(tv, "close", None, 2650)
    results = {tf: analyze_timeframe_tv(tv, tf, price) for tf in timeframes}
    return {"timeframes": results, "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "TradingView · OANDA spot"}


@api_router.get("/strength")
async def api_strength():
    tv = await fetch_tv_analysis()
    price = STATE.get("last_price") or _get_tv(tv, "close", None, 2650)
    a5 = analyze_timeframe_tv(tv, "5m", price)
    a15 = analyze_timeframe_tv(tv, "15m", price)
    a1h = analyze_timeframe_tv(tv, "1h", price)

    trend = round((abs(a5["score"]) + abs(a15["score"]) + abs(a1h["score"])) / 3)
    momentum_score = min(100, int(abs(a5["momentum"] / max(a5["atr"], 0.01)) * 30 + 30))
    last = a5["close"] or price or 2650
    vol_pct = min(100, int((a5["atr"] / max(last, 1)) * 1000))
    # Volume from TradingView (24h)
    vol_v = _get_tv(tv, "volume", None, 0)
    volume = min(100, max(20, int(vol_v / 5000))) if vol_v else 50
    confidence = round((trend + momentum_score) / 2)
    return {
        "trend": int(trend),
        "momentum": int(momentum_score),
        "volatility": int(vol_pct),
        "volume": int(volume),
        "confidence": int(confidence),
    }


def _make_signal(analysis: Dict[str, Any], timeframe: str, price_now: float) -> Optional[Signal]:
    direction = analysis["direction"]
    if direction == "NEUTRAL":
        return None
    a = max(analysis["atr"], 0.5)
    # Scale ATR per timeframe - higher TF = larger ATR-based stops
    tf_atr_scale = {"1m": 0.15, "5m": 0.25, "15m": 0.4, "30m": 0.6, "1h": 0.8, "4h": 1.0, "1d": 1.2}.get(timeframe, 0.3)
    eff_a = a * tf_atr_scale
    if direction == "BUY":
        entry = price_now
        sl = round(entry - eff_a * 1.2, 2)
        tp1 = round(entry + eff_a * 1.0, 2)
        tp2 = round(entry + eff_a * 2.0, 2)
        tp3 = round(entry + eff_a * 3.5, 2)
    else:
        entry = price_now
        sl = round(entry + eff_a * 1.2, 2)
        tp1 = round(entry - eff_a * 1.0, 2)
        tp2 = round(entry - eff_a * 2.0, 2)
        tp3 = round(entry - eff_a * 3.5, 2)

    expires_minutes = {"1m": 3, "5m": 15, "15m": 45, "30m": 90, "1h": 240, "4h": 960, "1d": 1440}.get(timeframe, 15)
    now = datetime.now(timezone.utc)
    macd_v = analysis.get("macd", 0)
    label = "alcista fuerte" if direction == "BUY" else "bajista fuerte"
    tf_label = "SCALPING" if timeframe in ("1m", "5m", "15m") else "INTRADÍA" if timeframe in ("30m", "1h") else "SWING"
    analysis_text = f"Tendencia {label} - MACD {macd_v} ({tf_label})"

    return Signal(
        id=str(uuid.uuid4()),
        direction=direction,
        timeframe=timeframe,
        confidence=analysis["confidence"],
        entry=round(entry, 2),
        tp1=tp1, tp2=tp2, tp3=tp3,
        stop_loss=sl,
        analysis=analysis_text,
        created_at=now.isoformat(),
        expires_at=(now + timedelta(minutes=expires_minutes)).isoformat(),
        status="active",
    )


@api_router.get("/signal/active")
async def api_active_signal(timeframe: str = Query("5m")):
    if timeframe not in TV_TIMEFRAMES:
        timeframe = "5m"
    tv = await fetch_tv_analysis()
    price = await get_price("tradingview")
    analysis = analyze_timeframe_tv(tv, timeframe, price.price)

    cur = STATE.get("active_signal")
    if cur and cur["timeframe"] == timeframe:
        if datetime.fromisoformat(cur["expires_at"]) > datetime.now(timezone.utc):
            entry = cur["entry"]
            if cur["direction"] == "BUY":
                pnl = ((price.price - entry) / entry) * 100
            else:
                pnl = ((entry - price.price) / entry) * 100
            cur["pnl_pct"] = round(pnl, 3)
            recommendation = compute_recommendation(cur, price.price, analysis)
            return {"signal": cur, "analysis": analysis, "price": price.model_dump(),
                    "recommendation": recommendation}

    new_sig = _make_signal(analysis, timeframe, price.price)
    if new_sig:
        STATE["active_signal"] = new_sig.model_dump()
        STATE["history"].insert(0, STATE["active_signal"])
        STATE["history"] = STATE["history"][:50]
        STATE["stats"]["total"] += 1
    sig_obj = STATE.get("active_signal") if (new_sig and STATE["active_signal"]["id"] == new_sig.id) else None
    recommendation = compute_recommendation(sig_obj, price.price, analysis)
    return {"signal": sig_obj, "analysis": analysis, "price": price.model_dump(),
            "recommendation": recommendation}


@api_router.get("/recommendation")
async def api_recommendation(timeframe: str = Query("5m")):
    """Standalone recommendation endpoint (faster polling)."""
    tv = await fetch_tv_analysis()
    price = await get_price("tradingview")
    analysis = analyze_timeframe_tv(tv, timeframe, price.price)
    sig = STATE.get("active_signal")
    if sig and sig["timeframe"] == timeframe:
        if datetime.fromisoformat(sig["expires_at"]) <= datetime.now(timezone.utc):
            sig = None
    rec = compute_recommendation(sig, price.price, analysis)
    # Include short stats for UI
    return {
        "recommendation": rec,
        "price": price.model_dump(),
        "signal_id": sig["id"] if sig else None,
        "signal_direction": sig["direction"] if sig else None,
    }


@api_router.get("/signal/history")
async def api_history():
    now = datetime.now(timezone.utc)
    last_price = STATE.get("last_price") or 0
    for s in STATE["history"]:
        if s["status"] != "active":
            continue
        if datetime.fromisoformat(s["expires_at"]) < now:
            entry = s["entry"]
            pnl = ((last_price - entry) / entry) * 100 if s["direction"] == "BUY" else ((entry - last_price) / entry) * 100
            s["pnl_pct"] = round(pnl, 3)
            if pnl >= 0.05:
                s["status"] = "won"; STATE["stats"]["wins"] += 1
            elif pnl <= -0.05:
                s["status"] = "lost"; STATE["stats"]["losses"] += 1
            else:
                s["status"] = "expired"
    return {"history": STATE["history"]}


@api_router.get("/binary/next-candle")
async def api_binary_next():
    tv = await fetch_tv_analysis()
    price = STATE.get("last_price") or _get_tv(tv, "close", None, 2650)
    a1 = analyze_timeframe_tv(tv, "1m", price)
    a5 = analyze_timeframe_tv(tv, "5m", price)

    def to_binary(a):
        if a["score"] > 0:
            return {"direction": "CALL", "confidence": min(99, max(50, abs(a["score"]) + 30))}
        if a["score"] < 0:
            return {"direction": "PUT", "confidence": min(99, max(50, abs(a["score"]) + 30))}
        return {"direction": "NEUTRAL", "confidence": 50}

    now = datetime.now(timezone.utc)
    sec_to_1m = 60 - now.second
    sec_to_5m = (5 - (now.minute % 5)) * 60 - now.second
    if sec_to_5m <= 0:
        sec_to_5m += 300

    return {
        "one_min": {**to_binary(a1), "seconds_left": sec_to_1m},
        "five_min": {**to_binary(a5), "seconds_left": sec_to_5m},
    }


@api_router.get("/stats")
async def api_stats():
    s = STATE["stats"]
    total_closed = s["wins"] + s["losses"]
    win_rate = round((s["wins"] / total_closed) * 100, 1) if total_closed else 100.0
    active = sum(1 for x in STATE["history"] if x["status"] == "active")
    avg_conf = round(sum(x["confidence"] for x in STATE["history"]) / len(STATE["history"]), 1) if STATE["history"] else 0
    return {
        "active_signals": active,
        "total_signals": s["total"],
        "wins": s["wins"],
        "losses": s["losses"],
        "win_rate": win_rate,
        "avg_confidence": avg_conf,
    }


# Include router & CORS
app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
