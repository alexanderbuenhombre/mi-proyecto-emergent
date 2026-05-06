"""
Iteration 5 tests:
- Signal model includes tp_hits (dict tp1/tp2/tp3:bool), sl_hit (bool), max_favorable (optional float)
- GET /api/signal/active?timeframe=5m returns those fields when signal is active
- Sticky tp_hits and sl_hit; max_favorable is monotonic (max for BUY, min for SELL)
"""
import os
import time
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
TIMEOUT = 20


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


class TestActiveSignalFields:
    """Validate new fields in Signal payload."""

    def test_active_signal_has_new_fields(self, session):
        r = session.get(f"{BASE_URL}/api/signal/active", params={"timeframe": "5m"}, timeout=TIMEOUT)
        assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
        data = r.json()
        assert "signal" in data
        assert "recommendation" in data
        assert "price" in data
        sig = data["signal"]
        if sig is None:
            # No active signal — empty state; validate recommendation still present
            rec = data["recommendation"]
            assert "take_label" in rec
            assert "take_reason" in rec
            assert "label" in rec
            pytest.skip("No active signal — sticky-TP tests need active signal. Empty state validated.")

        # Signal is present — verify new fields
        assert "tp_hits" in sig, f"tp_hits missing in signal: {list(sig.keys())}"
        assert "sl_hit" in sig
        assert "max_favorable" in sig

        tp_hits = sig["tp_hits"]
        assert isinstance(tp_hits, dict)
        for k in ("tp1", "tp2", "tp3"):
            assert k in tp_hits, f"tp_hits missing key {k}"
            assert isinstance(tp_hits[k], bool)

        assert isinstance(sig["sl_hit"], bool)
        assert sig["max_favorable"] is None or isinstance(sig["max_favorable"], (int, float))

    def test_sticky_tp_hits_and_mfe_monotonic(self, session):
        """Poll twice: any tp_hit that was True must remain True; max_favorable must be
        monotonic in signal direction (non-decreasing for BUY, non-increasing for SELL)."""
        r1 = session.get(f"{BASE_URL}/api/signal/active", params={"timeframe": "5m"}, timeout=TIMEOUT)
        assert r1.status_code == 200
        d1 = r1.json()
        s1 = d1["signal"]
        if s1 is None:
            pytest.skip("No active signal to test stickiness")

        time.sleep(3)
        r2 = session.get(f"{BASE_URL}/api/signal/active", params={"timeframe": "5m"}, timeout=TIMEOUT)
        assert r2.status_code == 200
        d2 = r2.json()
        s2 = d2["signal"]
        assert s2 is not None, "Signal disappeared between polls"
        # Same signal (same id) — otherwise state comparison is invalid
        if s1["id"] != s2["id"]:
            pytest.skip("Signal id changed between polls (expired/regenerated)")

        # Sticky tp_hits
        for k in ("tp1", "tp2", "tp3"):
            if s1["tp_hits"].get(k) is True:
                assert s2["tp_hits"].get(k) is True, f"{k} un-stuck (True -> False)!"

        # Sticky sl_hit
        if s1.get("sl_hit") is True:
            assert s2.get("sl_hit") is True, "sl_hit un-stuck (True -> False)"

        # MFE monotonic
        mfe1 = s1.get("max_favorable")
        mfe2 = s2.get("max_favorable")
        if mfe1 is not None and mfe2 is not None:
            if s1["direction"] == "BUY":
                assert mfe2 >= mfe1, f"BUY max_favorable decreased {mfe1} -> {mfe2}"
            else:
                assert mfe2 <= mfe1, f"SELL max_favorable decreased {mfe1} -> {mfe2}"

    def test_tp_hits_consistent_with_mfe(self, session):
        """If max_favorable reaches TP level, tp_hits for that level must be True."""
        r = session.get(f"{BASE_URL}/api/signal/active", params={"timeframe": "5m"}, timeout=TIMEOUT)
        data = r.json()
        sig = data.get("signal")
        if sig is None:
            pytest.skip("No active signal")
        mfe = sig.get("max_favorable")
        if mfe is None:
            pytest.skip("No max_favorable value yet")
        is_buy = sig["direction"] == "BUY"
        for n in (1, 2, 3):
            reached = (is_buy and mfe >= sig[f"tp{n}"]) or ((not is_buy) and mfe <= sig[f"tp{n}"])
            if reached:
                assert sig["tp_hits"][f"tp{n}"] is True, \
                    f"TP{n} reached by MFE {mfe} but tp_hits[tp{n}] is False"


class TestRecommendationShape:
    """Validate recommendation still has fields needed by inline card."""

    def test_recommendation_has_take_fields(self, session):
        r = session.get(f"{BASE_URL}/api/signal/active", params={"timeframe": "5m"}, timeout=TIMEOUT)
        assert r.status_code == 200
        rec = r.json()["recommendation"]
        for key in ("label", "headline", "take", "take_label", "take_reason", "probability"):
            assert key in rec, f"recommendation missing {key}"
        assert isinstance(rec["take"], bool)
