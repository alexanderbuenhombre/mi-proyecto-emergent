"""Backend tests for XAUUSD signals API."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://xauusd-trader-hub-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# Price endpoints
def test_price_tradingview(client):
    r = client.get(f"{API}/price?source=tradingview", timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d["price"], (int, float)) and d["price"] > 100
    assert "source" in d and "timestamp" in d
    assert "spread" in d and "change" in d and "change_pct" in d


def test_price_goldapi(client):
    r = client.get(f"{API}/price?source=goldapi", timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d["price"], (int, float)) and d["price"] > 100


# Sessions
def test_sessions(client):
    r = client.get(f"{API}/sessions", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert len(d["sessions"]) == 4
    names = [s["name"] for s in d["sessions"]]
    assert names == ["Sydney", "Tokyo", "London", "New York"]
    for s in d["sessions"]:
        assert isinstance(s["active"], bool)
    assert "label" in d and "active_count" in d


# Multi-timeframe
def test_multi_timeframe(client):
    r = client.get(f"{API}/multi-timeframe", timeout=60)
    assert r.status_code == 200
    d = r.json()
    tfs = d["timeframes"]
    for tf in ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]:
        assert tf in tfs, f"missing {tf}"
        a = tfs[tf]
        for k in ["rsi", "macd", "cci", "bb_pos", "momentum", "atr", "score", "direction", "confidence"]:
            assert k in a, f"{tf} missing {k}"
        assert a["direction"] in ("BUY", "SELL", "NEUTRAL")


# Strength
def test_strength(client):
    r = client.get(f"{API}/strength", timeout=60)
    assert r.status_code == 200
    d = r.json()
    for k in ["trend", "momentum", "volatility", "volume", "confidence"]:
        assert k in d
        assert 0 <= d[k] <= 100


# Active signal
def test_active_signal_and_idempotency(client):
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "analysis" in d and "price" in d
    sig = d.get("signal")
    if sig is not None:
        for k in ["id", "direction", "entry", "tp1", "tp2", "tp3", "stop_loss", "confidence", "analysis", "expires_at"]:
            assert k in sig
        assert sig["direction"] in ("BUY", "SELL")
        # Second call should return same id with updated pnl
        time.sleep(2)
        r2 = client.get(f"{API}/signal/active?timeframe=5m", timeout=30)
        d2 = r2.json()
        if d2.get("signal"):
            assert d2["signal"]["id"] == sig["id"]


# History
def test_history(client):
    r = client.get(f"{API}/signal/history", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d["history"], list)


# Binary
def test_binary(client):
    r = client.get(f"{API}/binary/next-candle", timeout=60)
    assert r.status_code == 200
    d = r.json()
    for k in ["one_min", "five_min"]:
        assert k in d
        assert d[k]["direction"] in ("CALL", "PUT", "NEUTRAL")
        assert isinstance(d[k]["confidence"], (int, float))
        assert isinstance(d[k]["seconds_left"], int) and d[k]["seconds_left"] >= 0


# Stats
def test_stats(client):
    r = client.get(f"{API}/stats", timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ["active_signals", "total_signals", "win_rate", "avg_confidence"]:
        assert k in d
