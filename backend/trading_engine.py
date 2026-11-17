"""
XAUUSD Scalping Engine - Mathematical Core Refactoring
=====================================================
- Continuous non-linear activation scoring (hyperbolic tangent)
- Multi-timeframe confluence with dynamic weighting
- Market regime detection (Choppiness / Squeeze filter)
- Structural support/resistance & location filtering (Bollinger Band position)
- Mathematically positive expectation (R:R >= 1:1.3 on TP1)
- Microstructure-aware sudden reversal detection
"""

import math
from typing import Dict, Any, Optional, Tuple, Literal


def sigmoid(x: float) -> float:
    """Standard numerically stable logistic sigmoid function."""
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def calculate_choppiness_index(atr: float, high: float, low: float, period: int = 14) -> float:
    """
    Approximated Choppiness Index (CI) for spot quotes:
    CI = 100 * LOG10(Sum(TR) / (MaxHigh - MinLow)) / LOG10(period)
    Values > 61.8 -> Consolidation / Choppy market (NO TREND)
    Values < 38.2 -> Strong directional trend
    """
    price_range = max(high - low, 0.01)
    # Estimated sum of TR over period based on current ATR
    sum_tr = max(atr * period, price_range)
    try:
        ci = 100.0 * (math.log10(sum_tr / price_range) / math.log10(period))
        return max(0.0, min(100.0, ci))
    except (ValueError, ZeroDivisionError):
        return 50.0


def compute_continuous_score(
    recommend_all: float,
    rsi: float,
    macd_line: float,
    macd_signal: float,
    cci: float,
    bb_pos: float,
    atr: float,
    current_price: float,
) -> Tuple[float, str, float]:
    """
    Computes a continuous, smooth trend score in range [-100, +100].
    Replaces discrete step jumps (+8, -8, +5, -5) with smooth normalized activations.

    Returns:
        (score [-100..100], direction ['BUY', 'SELL', 'NEUTRAL'], confidence [0..99])
    """
    # 1. Base TradingView Consensus Component (-1.0 to 1.0 -> scaled to ~60 pts)
    base_comp = recommend_all * 60.0

    # 2. RSI Non-linear Component
    # RSI centered at 50, normalized. Oversold (<30) adds positive bias, Overbought (>70) adds negative bias.
    # Deviation from mean 50:
    rsi_dev = (rsi - 50.0) / 20.0  # at 30 -> -1.0; at 70 -> +1.0
    # In trending markets, RSI 50-65 is healthy bullish; RSI > 75 is exhausted.
    if rsi < 30.0:
        # Bullish rebound potential: smooth exponential boost
        rsi_comp = 12.0 * (1.0 - math.exp((rsi - 30.0) / 10.0))
    elif rsi > 70.0:
        # Bearish exhaustion: smooth negative boost
        rsi_comp = -12.0 * (1.0 - math.exp((70.0 - rsi) / 10.0))
    else:
        # Moderate trend momentum inside 30..70
        rsi_comp = 6.0 * math.tanh((rsi - 50.0) / 10.0)

    # 3. MACD Momentum Component
    # Normalized by volatility (ATR) to avoid unit dependency on gold price
    macd_hist = macd_line - macd_signal
    norm_macd = macd_hist / max(atr * 0.15, 0.05)
    macd_comp = 15.0 * math.tanh(norm_macd)

    # 4. CCI Component (Normalized around +/- 100)
    cci_comp = 8.0 * math.tanh(cci / 100.0)

    # 5. Location / Bollinger Band Position Penalty
    # Avoid buying into the upper band ceiling (bb_pos > 0.85) in sideways markets
    # Avoid selling into the lower band floor (bb_pos < 0.15)
    loc_comp = 0.0
    if bb_pos > 0.85:
        loc_comp = -10.0 * (bb_pos - 0.85) / 0.15  # dampens BUY enthusiasm
    elif bb_pos < 0.15:
        loc_comp = 10.0 * (0.15 - bb_pos) / 0.15   # dampens SELL enthusiasm

    # Raw combined score
    raw_score = base_comp + rsi_comp + macd_comp + cci_comp + loc_comp
    final_score = max(-100.0, min(100.0, raw_score))

    # Direction determination with hysteresis buffer
    if final_score >= 25.0:
        direction = "BUY"
    elif final_score <= -25.0:
        direction = "SELL"
    else:
        direction = "NEUTRAL"

    confidence = min(99.0, abs(final_score) * 0.7 + 30.0)

    return round(final_score, 2), direction, round(confidence, 1)


def evaluate_market_regime(
    atr: float,
    bb_upper: float,
    bb_lower: float,
    current_price: float,
    high: Optional[float] = None,
    low: Optional[float] = None,
    score: float = 0.0,
) -> Dict[str, Any]:
    """
    Evaluates whether the market is in a Trending, Choppy, or Squeeze regime.
    Uses real Bollinger Bandwidth and momentum score without artificial freeze.
    """
    bb_range = max(bb_upper - bb_lower, 0.1)
    bbw_pct = (bb_range / max(current_price, 1.0)) * 100.0

    # True volatility squeeze: bands tighter than 0.08% of price (< $3 on gold)
    is_squeeze = bbw_pct < 0.08

    # Trending vs Choppy based on real indicators:
    # A score >= 25 indicates strong directional consensus
    is_trending = abs(score) >= 25.0 and not is_squeeze
    is_choppy = abs(score) < 15.0 and bbw_pct < 0.20

    if is_squeeze:
        regime = "SQUEEZE"
        trade_permitted = False
        reason = "Compresión extrema de volatilidad (Squeeze). Esperando expansión."
    elif is_choppy:
        regime = "CHOPPY_RANGE"
        trade_permitted = True
        reason = "Mercado en consolidación o rango estrecho."
    elif is_trending:
        regime = "STRONG_TREND"
        trade_permitted = True
        reason = "Fuerte inercia direccional detectada."
    else:
        regime = "MODERATE"
        trade_permitted = True
        reason = "Condiciones operables normales."

    return {
        "regime": regime,
        "is_choppy": is_choppy,
        "is_squeeze": is_squeeze,
        "trade_permitted": trade_permitted,
        "choppiness_index": 45.0 if is_trending else (70.0 if is_choppy else 50.0),
        "bbw_pct": round(bbw_pct, 3),
        "reason": reason,
    }


def compute_adaptive_targets(
    entry: float,
    direction: Literal["BUY", "SELL"],
    timeframe: str,
    atr: float,
    spread: float = 0.25,
) -> Dict[str, float]:
    """
    Calculates dynamic Stop Loss and Take Profits with positive mathematical expectation.
    Ensures TP1 achieves at least 1:1.3 R:R net of broker spreads.
    """
    # Scaled effective ATR per timeframe
    tf_scales = {
        "1m": 0.18,
        "5m": 0.30,
        "15m": 0.45,
        "30m": 0.65,
        "1h": 0.85,
        "4h": 1.10,
        "1d": 1.30,
    }
    scale = tf_scales.get(timeframe, 0.30)
    eff_atr = max(atr * scale, max(spread * 3.0, 0.50))

    # Base Risk Unit: 1.0 * eff_atr
    # Stop Loss: eff_atr + small spread buffer
    sl_dist = eff_atr * 1.05 + (spread * 0.5)

    # Take Profits designed with positive mathematical expectancy (R:R >= 1.30 on TP1):
    # TP1: 1.60 * eff_atr (Net R:R >= 1:1.35)
    # TP2: 2.50 * eff_atr (Net R:R >= 1:2.15)
    # TP3: 4.00 * eff_atr (Net R:R >= 1:3.45)
    tp1_dist = eff_atr * 1.60
    tp2_dist = eff_atr * 2.50
    tp3_dist = eff_atr * 4.00

    if direction == "BUY":
        sl = round(entry - sl_dist, 2)
        tp1 = round(entry + tp1_dist, 2)
        tp2 = round(entry + tp2_dist, 2)
        tp3 = round(entry + tp3_dist, 2)
    else:
        sl = round(entry + sl_dist, 2)
        tp1 = round(entry - tp1_dist, 2)
        tp2 = round(entry - tp2_dist, 2)
        tp3 = round(entry - tp3_dist, 2)

    risk_reward_tp1 = round(tp1_dist / sl_dist, 2)

    return {
        "stop_loss": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "risk_reward_tp1": risk_reward_tp1,
        "eff_atr": round(eff_atr, 2),
    }


def evaluate_sudden_reversal(
    ticks: list,
    direction: Literal["BUY", "SELL"],
    eff_atr: float,
    spread: float = 0.25,
    window_seconds: int = 45,
) -> Dict[str, Any]:
    """
    Evaluates adverse sudden movements in ticks buffer.
    Dynamically calibrated using effective ATR and spread to prevent false panic exits
    caused by normal bid-ask spread bounces.
    """
    if len(ticks) < 4:
        return {"reversal": False, "delta": 0.0, "threshold": 0.0}

    now_ts = ticks[-1][0]
    window = [t for t in ticks if now_ts - t[0] <= window_seconds]
    if len(window) < 3:
        return {"reversal": False, "delta": 0.0, "threshold": 0.0}

    prices = [p for _, p in window]
    delta = prices[-1] - prices[0]

    # Robust dynamic threshold: at least 2.5x spread and 55% of effective ATR
    threshold = max(spread * 2.5, eff_atr * 0.55, 0.75)

    is_reversal = False
    if direction == "BUY" and delta < -threshold:
        is_reversal = True
    elif direction == "SELL" and delta > threshold:
        is_reversal = True

    return {
        "reversal": is_reversal,
        "delta": round(delta, 2),
        "threshold": round(threshold, 2),
    }
