"""Backend tests for XAUUSD signals API - Iteration 2.

Coverage:
- /api/price (tradingview, goldapi) + fresh_seconds field
- /api/sessions
- /api/multi-timeframe (TradingView OANDA spot, no Yahoo GC=F)
- /api/strength
- /api/signal/active (now includes recommendation)
- /api/recommendation (new endpoint)
- /api/signal/history
- /api/binary/next-candle
- /api/stats
- Tick buffer / fresh_seconds incrementing
- Recommendation engine (action labels)
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# -------------------- Price --------------------
def test_price_tradingview(client):
    r = client.get(f"{API}/price?source=tradingview", timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d["price"], (int, float)) and d["price"] > 100
    assert "TradingView" in d["source"] or d["source"] == "cache"
    for k in ["spread", "change", "change_pct", "timestamp", "fresh_seconds"]:
        assert k in d
    assert isinstance(d["fresh_seconds"], int)
    assert d["fresh_seconds"] >= 0


def test_price_goldapi(client):
    r = client.get(f"{API}/price?source=goldapi", timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert d["price"] > 100
    assert "fresh_seconds" in d


def test_price_no_yahoo_source(client):
    """Source must be TradingView or Gold-API, never Yahoo GC=F."""
    r = client.get(f"{API}/price?source=tradingview", timeout=20)
    src = r.json().get("source", "")
    assert "Yahoo" not in src and "GC=F" not in src and "yfinance" not in src


def test_price_fresh_seconds_progression(client):
    """fresh_seconds should increment over multiple calls if price doesn't change,
    and be small (or reset to ~0) when price ticks change."""
    samples = []
    for _ in range(5):
        r = client.get(f"{API}/price?source=tradingview", timeout=15)
        assert r.status_code == 200
        samples.append(r.json())
        time.sleep(1.1)
    # Always integer >= 0
    for s in samples:
        assert isinstance(s["fresh_seconds"], int) and s["fresh_seconds"] >= 0
    # At least one of: fresh_seconds increased OR price changed (resets timer)
    increased_or_changed = False
    for i in range(1, len(samples)):
        if samples[i]["fresh_seconds"] > samples[i - 1]["fresh_seconds"]:
            increased_or_changed = True; break
        if samples[i]["price"] != samples[i - 1]["price"]:
            increased_or_changed = True; break
    assert increased_or_changed, f"fresh_seconds neither incremented nor price changed: {[(s['price'], s['fresh_seconds']) for s in samples]}"


# -------------------- Sessions --------------------
def test_sessions(client):
    r = client.get(f"{API}/sessions", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert len(d["sessions"]) == 4
    for s in d["sessions"]:
        assert isinstance(s["active"], bool)


# -------------------- Multi-Timeframe (TradingView only) --------------------
def test_multi_timeframe_tradingview_only(client):
    r = client.get(f"{API}/multi-timeframe", timeout=60)
    assert r.status_code == 200
    d = r.json()
    # Source must be TradingView OANDA spot (NO Yahoo / GC=F)
    src = d.get("source", "")
    assert "TradingView" in src and "OANDA" in src
    assert "Yahoo" not in src and "GC=F" not in src

    tfs = d["timeframes"]
    for tf in ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]:
        assert tf in tfs, f"missing {tf}"
        a = tfs[tf]
        for k in ["rsi", "macd", "cci", "bb_pos", "momentum", "atr", "score", "direction", "confidence"]:
            assert k in a, f"{tf} missing {k}"
        assert a["direction"] in ("BUY", "SELL", "NEUTRAL")
        # RSI sanity
        assert 0 <= a["rsi"] <= 100
        # bb_pos roughly 0..1 (allow small drift)
        assert -0.5 <= a["bb_pos"] <= 1.5


# -------------------- Strength --------------------
def test_strength(client):
    r = client.get(f"{API}/strength", timeout=60)
    assert r.status_code == 200
    d = r.json()
    for k in ["trend", "momentum", "volatility", "volume", "confidence"]:
        assert k in d
        assert 0 <= d[k] <= 100


# -------------------- Active signal + recommendation --------------------
def test_active_signal_includes_recommendation(client):
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "analysis" in d and "price" in d and "recommendation" in d
    rec = d["recommendation"]
    for k in ["action", "label", "headline", "message", "urgency", "tone"]:
        assert k in rec, f"recommendation missing {k}"
    assert rec["action"] in (
        "TOMAR", "ESPERAR", "MANTENER", "TOMAR_GANANCIAS", "CERRAR_REVERSO", "STOP_LOSS_HIT"
    )
    assert rec["urgency"] in ("low", "medium", "high")
    assert rec["tone"] in ("buy", "sell", "success", "danger", "neutral")


def test_active_signal_idempotency(client):
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=60)
    d = r.json()
    sig = d.get("signal")
    if sig:
        time.sleep(2)
        r2 = client.get(f"{API}/signal/active?timeframe=5m", timeout=30)
        d2 = r2.json()
        if d2.get("signal"):
            assert d2["signal"]["id"] == sig["id"]


# -------------------- Standalone recommendation endpoint --------------------
def test_recommendation_endpoint(client):
    r = client.get(f"{API}/recommendation?timeframe=5m", timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ["recommendation", "price", "signal_id", "signal_direction"]:
        assert k in d
    rec = d["recommendation"]
    for k in ["action", "label", "headline", "message", "urgency", "tone"]:
        assert k in rec
    assert d["price"]["price"] > 100


# -------------------- History / Binary / Stats --------------------
def test_history(client):
    r = client.get(f"{API}/signal/history", timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json()["history"], list)


def test_binary(client):
    r = client.get(f"{API}/binary/next-candle", timeout=60)
    assert r.status_code == 200
    d = r.json()
    for k in ["one_min", "five_min"]:
        assert d[k]["direction"] in ("CALL", "PUT", "NEUTRAL")
        assert isinstance(d[k]["seconds_left"], int) and d[k]["seconds_left"] >= 0


def test_stats(client):
    r = client.get(f"{API}/stats", timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ["active_signals", "total_signals", "win_rate", "avg_confidence"]:
        assert k in d


# -------------------- Recommendation engine logic (unit-style via API) --------------------
def test_recommendation_engine_actions_present():
    """Inspect server.compute_recommendation for the required action labels."""
    import importlib.util
    path = os.path.join(os.path.dirname(__file__), "..", "server.py")
    src = open(path).read()
    for label in ["TOMAR", "ESPERAR", "MANTENER", "TOMAR_GANANCIAS",
                  "CERRAR_REVERSO", "STOP_LOSS_HIT"]:
        assert f'"{label}"' in src, f"missing action label {label} in compute_recommendation"
