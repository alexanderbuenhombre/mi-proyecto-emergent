"""
XAUUSD Real-Time Signals Backend
- Live spot price from TradingView (OANDA) and Gold-API.com (no auth)
- OHLC candles from Yahoo Finance (XAUUSD=X) for indicators
- Multi-timeframe signal generation (RSI, MACD, CCI, Bollinger, Volume, Momentum)
- In-memory signal history
"""
from fastapi import FastAPI, APIRouter, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import time
import asyncio
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import numpy as np
import pandas as pd
import yfinance as yf

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="XAUUSD Signals API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------- In-memory state ----------------
STATE: Dict[str, Any] = {
    "history": [],            # list of completed/active signals
    "active_signal": None,
    "last_price": None,
    "last_price_at": None,
    "stats": {"total": 0, "wins": 0, "losses": 0},
    "candles_cache": {},      # interval -> (ts, df)
}

# Yahoo Finance symbol mappings for XAU/USD spot
YF_SYMBOL = "GC=F"  # COMEX Gold Futures - tracks XAU/USD closely; used for indicators only
TF_MAP = {
    "1m": ("1m", "1d"),
    "5m": ("5m", "5d"),
    "15m": ("15m", "5d"),
    "30m": ("30m", "1mo"),
    "1h": ("60m", "1mo"),
    "4h": ("60m", "3mo"),  # we'll resample
    "1d": ("1d", "6mo"),
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
    """Public TradingView scanner endpoint for OANDA:XAUUSD."""
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
    """Gold-API.com public spot price (no auth)."""
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
        # last-resort fallback to last cached
        last = STATE.get("last_price") or 2650.0
        p = PriceData(
            price=last, change=0.0, change_pct=0.0, spread=0.30,
            source="cache", timestamp=datetime.now(timezone.utc).isoformat(),
        )
    STATE["last_price"] = p.price
    STATE["last_price_at"] = p.timestamp
    return p


# ---------------- Candles & indicators ----------------
def _fetch_candles_sync(interval: str, period: str) -> pd.DataFrame:
    df = yf.download(YF_SYMBOL, interval=interval, period=period, progress=False, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.title)
    df = df.dropna()
    return df


async def get_candles(timeframe: str) -> pd.DataFrame:
    if timeframe not in TF_MAP:
        timeframe = "5m"
    cached = STATE["candles_cache"].get(timeframe)
    now = time.time()
    if cached and now - cached[0] < 30:
        return cached[1]
    interval, period = TF_MAP[timeframe]
    try:
        df = await asyncio.to_thread(_fetch_candles_sync, interval, period)
        if timeframe == "4h" and not df.empty:
            df = df.resample("4H").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum"
            }).dropna()
    except Exception as e:
        logger.warning(f"yfinance fetch failed {timeframe}: {e}")
        df = pd.DataFrame()
    STATE["candles_cache"][timeframe] = (now, df)
    return df


def rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff().dropna()
    if len(delta) < period:
        return 50.0
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    avg_up = up.ewm(alpha=1 / period, adjust=False).mean()
    avg_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_up / avg_down.replace(0, np.nan)
    rsi_v = 100 - (100 / (1 + rs))
    val = float(rsi_v.iloc[-1]) if not rsi_v.empty else 50.0
    return round(val if not np.isnan(val) else 50.0, 2)


def macd(series: pd.Series) -> Dict[str, float]:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    return {
        "macd": round(float(macd_line.iloc[-1]), 3),
        "signal": round(float(signal_line.iloc[-1]), 3),
        "hist": round(float(hist.iloc[-1]), 3),
    }


def cci(df: pd.DataFrame, period: int = 20) -> float:
    if len(df) < period:
        return 0.0
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=False)
    cci_v = (tp - sma) / (0.015 * mad.replace(0, np.nan))
    val = float(cci_v.iloc[-1])
    return round(val if not np.isnan(val) else 0.0, 2)


def bollinger(series: pd.Series, period: int = 20, num_std: float = 2.0) -> Dict[str, float]:
    if len(series) < period:
        last = float(series.iloc[-1])
        return {"upper": last, "mid": last, "lower": last, "pos": 0.5}
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    last = float(series.iloc[-1])
    u = float(upper.iloc[-1]); l = float(lower.iloc[-1]); m = float(sma.iloc[-1])
    pos = (last - l) / (u - l) if u != l else 0.5
    return {"upper": round(u, 2), "mid": round(m, 2), "lower": round(l, 2), "pos": round(pos, 3)}


def momentum(series: pd.Series, period: int = 10) -> float:
    if len(series) < period + 1:
        return 0.0
    return round(float(series.iloc[-1] - series.iloc[-period - 1]), 2)


def atr(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < period + 1:
        return float(df["Close"].iloc[-1]) * 0.001 if not df.empty else 1.0
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return round(float(tr.rolling(period).mean().iloc[-1]), 2)


def analyze_timeframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Return signal analysis for a given OHLC dataframe."""
    if df.empty or len(df) < 30:
        return {
            "direction": "NEUTRAL", "score": 0, "confidence": 0,
            "rsi": 50, "macd": 0, "cci": 0, "bb_pos": 0.5,
            "momentum": 0, "atr": 0, "close": 0, "volume_ratio": 1.0,
        }
    close = df["Close"]
    r = rsi(close)
    m = macd(close)
    c = cci(df)
    bb = bollinger(close)
    mom = momentum(close)
    a = atr(df)
    last_close = round(float(close.iloc[-1]), 2)

    vol_ratio = 1.0
    if "Volume" in df.columns:
        try:
            vmean = float(df["Volume"].rolling(20).mean().iloc[-1])
            vlast = float(df["Volume"].iloc[-1])
            if vmean > 0:
                vol_ratio = round(vlast / vmean, 2)
        except Exception:
            pass

    # Scoring (-100..100)
    score = 0
    # RSI: oversold->buy, overbought->sell
    if r < 30: score += 20
    elif r < 45: score += 10
    elif r > 70: score -= 20
    elif r > 55: score -= 10
    # MACD histogram
    if m["hist"] > 0: score += 15
    elif m["hist"] < 0: score -= 15
    # MACD line vs signal
    if m["macd"] > m["signal"]: score += 10
    else: score -= 10
    # CCI
    if c > 100: score += 15
    elif c > 0: score += 7
    elif c < -100: score -= 15
    elif c < 0: score -= 7
    # Bollinger position
    if bb["pos"] < 0.2: score += 15  # near lower band -> buy
    elif bb["pos"] > 0.8: score -= 15
    # Momentum
    if mom > 0: score += 10
    elif mom < 0: score -= 10
    # Volume confirmation
    if vol_ratio > 1.3: score = int(score * 1.1)

    score = int(max(-100, min(100, score)))
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
        "rsi": r,
        "macd": m["macd"],
        "macd_hist": m["hist"],
        "cci": c,
        "bb_pos": bb["pos"],
        "momentum": mom,
        "atr": a,
        "close": last_close,
        "volume_ratio": vol_ratio,
    }


# ---------------- API endpoints ----------------
@api_router.get("/")
async def root():
    return {"service": "XAUUSD Signals API", "ok": True}


@api_router.get("/price")
async def api_price(source: str = Query("tradingview", pattern="^(tradingview|goldapi)$")):
    p = await get_price(source)
    return p.model_dump()


@api_router.get("/sessions")
async def api_sessions():
    """Market sessions in UTC."""
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
        if o < c:
            active = o <= h < c
        else:
            active = h >= o or h < c
        if active:
            active_count += 1
        out.append({
            "name": s["name"], "active": active, "tz": s["tz"],
            "open": s["open"], "close": s["close"],
        })
    # Determine session label
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
    results = {}
    for tf in timeframes:
        df = await get_candles(tf)
        results[tf] = analyze_timeframe(df)
    return {"timeframes": results, "updated_at": datetime.now(timezone.utc).isoformat()}


@api_router.get("/strength")
async def api_strength():
    """Combined strength bars based on 5m + 15m + 1h."""
    df5 = await get_candles("5m")
    df15 = await get_candles("15m")
    df1h = await get_candles("1h")

    a5 = analyze_timeframe(df5)
    a15 = analyze_timeframe(df15)
    a1h = analyze_timeframe(df1h)

    trend = round((abs(a5["score"]) + abs(a15["score"]) + abs(a1h["score"])) / 3)
    momentum_score = round(min(100, abs(a5["momentum"] / max(a5["atr"], 0.01)) * 30 + 30))
    # Volatility from ATR % of price
    last = a5["close"] or STATE["last_price"] or 2650
    vol_pct = round(min(100, (a5["atr"] / max(last, 1)) * 1000))
    volume = round(min(100, a5["volume_ratio"] * 50))
    confidence = round((trend + momentum_score) / 2)
    return {
        "trend": trend,
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
    if direction == "BUY":
        entry = price_now
        sl = round(entry - a * 1.2, 2)
        tp1 = round(entry + a * 1.0, 2)
        tp2 = round(entry + a * 2.0, 2)
        tp3 = round(entry + a * 3.5, 2)
    else:
        entry = price_now
        sl = round(entry + a * 1.2, 2)
        tp1 = round(entry - a * 1.0, 2)
        tp2 = round(entry - a * 2.0, 2)
        tp3 = round(entry - a * 3.5, 2)

    expires_minutes = {"1m": 3, "5m": 15, "15m": 45, "30m": 90, "1h": 240, "4h": 960, "1d": 1440}.get(timeframe, 15)
    now = datetime.now(timezone.utc)
    macd_v = analysis.get("macd", 0)
    label = "alcista fuerte" if direction == "BUY" else "bajista fuerte"
    analysis_text = f"Tendencia {label} - MACD {macd_v} (SCALPING)"

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
    if timeframe not in TF_MAP:
        timeframe = "5m"
    df = await get_candles(timeframe)
    analysis = analyze_timeframe(df)
    price = await get_price("tradingview")

    # If active signal still valid for same timeframe, return it
    cur = STATE.get("active_signal")
    if cur and cur["timeframe"] == timeframe:
        if datetime.fromisoformat(cur["expires_at"]) > datetime.now(timezone.utc):
            # Update P&L
            entry = cur["entry"]
            if cur["direction"] == "BUY":
                pnl = ((price.price - entry) / entry) * 100
            else:
                pnl = ((entry - price.price) / entry) * 100
            cur["pnl_pct"] = round(pnl, 3)
            return {"signal": cur, "analysis": analysis, "price": price.model_dump()}

    new_sig = _make_signal(analysis, timeframe, price.price)
    if new_sig:
        STATE["active_signal"] = new_sig.model_dump()
        STATE["history"].insert(0, STATE["active_signal"])
        STATE["history"] = STATE["history"][:50]
        STATE["stats"]["total"] += 1
    return {
        "signal": STATE.get("active_signal") if (new_sig and STATE["active_signal"]["id"] == new_sig.id) else None,
        "analysis": analysis,
        "price": price.model_dump(),
    }


@api_router.get("/signal/history")
async def api_history():
    # Update outcomes for expired signals
    now = datetime.now(timezone.utc)
    last_price = STATE.get("last_price") or 0
    for s in STATE["history"]:
        if s["status"] != "active":
            continue
        if datetime.fromisoformat(s["expires_at"]) < now:
            entry = s["entry"]
            if s["direction"] == "BUY":
                pnl = ((last_price - entry) / entry) * 100
            else:
                pnl = ((entry - last_price) / entry) * 100
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
    """Predict CALL/PUT for 1m and 5m next candles."""
    df1 = await get_candles("1m")
    df5 = await get_candles("5m")
    a1 = analyze_timeframe(df1)
    a5 = analyze_timeframe(df5)

    def to_binary(a):
        if a["score"] > 0:
            return {"direction": "CALL", "confidence": min(99, max(50, abs(a["score"]) + 30))}
        elif a["score"] < 0:
            return {"direction": "PUT", "confidence": min(99, max(50, abs(a["score"]) + 30))}
        return {"direction": "NEUTRAL", "confidence": 50}

    # Seconds until next minute boundary (UTC)
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
    avg_conf = 0
    if STATE["history"]:
        avg_conf = round(sum(x["confidence"] for x in STATE["history"]) / len(STATE["history"]), 1)
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
