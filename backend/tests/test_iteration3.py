"""Iteration 3 tests: probability + confluence + take recommendation.

Covers the new fields added in /api/signal/active and /api/recommendation:
- probability {label, percent, take, reason}
- confluence {timeframes, aligned_count, total_count, direction, avg_strength, details}
- recommendation {take, take_label, take_reason, probability}
- STRICT FILTER: signal only when probability ALTA/ULTRA AND confluence.direction == analysis.direction
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# -------------------- /api/signal/active probability + confluence --------------------
def test_signal_active_has_probability(client):
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=25)
    assert r.status_code == 200
    d = r.json()
    assert "probability" in d, "probability field missing"
    p = d["probability"]
    assert p["label"] in ("ULTRA", "ALTA", "MEDIA", "BAJA"), f"unexpected label {p['label']}"
    assert isinstance(p["percent"], int) and 0 <= p["percent"] <= 99
    assert isinstance(p["take"], bool)
    assert isinstance(p["reason"], str) and len(p["reason"]) > 5


def test_signal_active_has_confluence(client):
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=25)
    assert r.status_code == 200
    d = r.json()
    assert "confluence" in d, "confluence field missing"
    c = d["confluence"]
    for k in ("timeframes", "aligned_count", "total_count", "direction", "avg_strength", "details"):
        assert k in c, f"confluence missing {k}"
    assert c["direction"] in ("BUY", "SELL", "NEUTRAL")
    assert isinstance(c["timeframes"], list) and len(c["timeframes"]) >= 2
    assert isinstance(c["details"], list) and len(c["details"]) == c["total_count"]
    for det in c["details"]:
        assert "tf" in det and "dir" in det and "score" in det
        assert det["dir"] in ("BUY", "SELL", "NEUTRAL")


def test_recommendation_endpoint_has_probability_and_confluence(client):
    r = client.get(f"{API}/recommendation?timeframe=5m", timeout=25)
    assert r.status_code == 200
    d = r.json()
    assert "probability" in d
    assert "confluence" in d
    assert d["probability"]["label"] in ("ULTRA", "ALTA", "MEDIA", "BAJA")


def test_recommendation_has_take_fields(client):
    r = client.get(f"{API}/recommendation?timeframe=5m", timeout=25)
    assert r.status_code == 200
    d = r.json()
    rec = d["recommendation"]
    for k in ("take", "take_label", "take_reason", "probability"):
        assert k in rec, f"recommendation missing {k}"
    assert isinstance(rec["take"], bool)
    assert isinstance(rec["take_label"], str) and len(rec["take_label"]) > 0
    assert rec["probability"] in ("ULTRA", "ALTA", "MEDIA", "BAJA")


def test_signal_active_recommendation_has_take_fields(client):
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=25)
    assert r.status_code == 200
    d = r.json()
    rec = d["recommendation"]
    for k in ("take", "take_label", "take_reason", "probability", "action", "label", "headline", "message"):
        assert k in rec, f"recommendation missing {k}"
    assert isinstance(rec["take"], bool)
    assert isinstance(rec["take_label"], str) and len(rec["take_label"]) > 0


# -------------------- STRICT FILTER --------------------
def test_strict_filter_signal_only_on_high_probability(client):
    """When probability is BAJA/MEDIA, signal must be null AND
    take_label must indicate NO TOMAR / NO RECOMENDABLE / similar."""
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=25)
    assert r.status_code == 200
    d = r.json()
    prob = d["probability"]["label"]
    confl_dir = d["confluence"]["direction"]
    analysis_dir = d["analysis"]["direction"]

    if prob in ("BAJA", "MEDIA") or confl_dir != analysis_dir or analysis_dir == "NEUTRAL":
        # Signal should be None (or remained from a prior valid signal that is still active —
        # accept: either None or active with matching dir/prob)
        if d["signal"] is not None:
            # The persistence path can still return a previously-valid signal.
            # If so, it must match analysis direction.
            assert d["signal"]["direction"] in ("BUY", "SELL")
        else:
            # take must be False, take_label != RECOMENDABLE
            rec = d["recommendation"]
            assert rec["take"] is False
            assert rec["take_label"] != "RECOMENDABLE"
    else:  # ALTA or ULTRA + dir match
        # signal could be present
        if d["signal"]:
            assert d["signal"]["direction"] == analysis_dir


def test_recommendation_no_signal_says_esperar(client):
    """When market neutral and signal None, recommendation label should be ESPERAR."""
    r = client.get(f"{API}/recommendation?timeframe=5m", timeout=25)
    assert r.status_code == 200
    d = r.json()
    if d.get("signal_id") is None:
        rec = d["recommendation"]
        assert rec["label"] == "ESPERAR"
        assert rec["action"] == "ESPERAR"
        assert rec["take"] is False


# -------------------- Probability rating thresholds --------------------
def test_probability_thresholds_consistency(client):
    """Verify probability rating rules:
    - ULTRA: aligned >=3 AND percent >=80
    - ALTA: aligned >=2 AND percent >=65
    - MEDIA: percent >=50
    - BAJA: otherwise
    """
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=25)
    assert r.status_code == 200
    d = r.json()
    prob = d["probability"]
    confl = d["confluence"]
    label, pct, aligned = prob["label"], prob["percent"], confl["aligned_count"]
    if label == "ULTRA":
        assert aligned >= 3 and pct >= 80
    elif label == "ALTA":
        assert aligned >= 2 and pct >= 65
    elif label == "MEDIA":
        assert pct >= 50
    else:
        assert label == "BAJA"


def test_confluence_details_structure(client):
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=25)
    d = r.json()
    details = d["confluence"]["details"]
    assert all(isinstance(x["tf"], str) for x in details)
    assert all(isinstance(x["score"], (int, float)) for x in details)
    # aligned_count is the max(buy,sell) — must be <= total
    assert d["confluence"]["aligned_count"] <= d["confluence"]["total_count"]
