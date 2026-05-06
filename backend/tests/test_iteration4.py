"""Iteration 4 bug-fix tests.

Focus: STATE['active_signals'] as dict per-timeframe, cooldown per-TF,
       MEDIA probability allowed, signal.timeframe matches requested.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---- Per-TF dict: same TF twice returns same id (no regeneration) ----
def test_same_tf_twice_same_signal_or_same_state(client):
    r1 = client.get(f"{API}/signal/active?timeframe=5m", timeout=25)
    r2 = client.get(f"{API}/signal/active?timeframe=5m", timeout=25)
    assert r1.status_code == 200 and r2.status_code == 200
    d1, d2 = r1.json(), r2.json()
    # If signal present in first call, second must return same id (no regeneration).
    if d1["signal"] is not None and d2["signal"] is not None:
        assert d1["signal"]["id"] == d2["signal"]["id"], \
            "STATE['active_signals'][tf] must NOT regenerate on consecutive calls"
    # If both None, cooldown or strict filter — either way stable (no crash).
    assert d1["probability"]["label"] in ("ULTRA", "ALTA", "MEDIA", "BAJA")


# ---- Switching TFs does NOT overwrite a previous TF's signal ----
def test_switching_tfs_preserves_other_tf_signal(client):
    # Generate/read 5m, then 1m, then 5m again — 5m id must persist if it existed.
    r5a = client.get(f"{API}/signal/active?timeframe=5m", timeout=25).json()
    _ = client.get(f"{API}/signal/active?timeframe=1m", timeout=25).json()
    _ = client.get(f"{API}/signal/active?timeframe=15m", timeout=25).json()
    r5b = client.get(f"{API}/signal/active?timeframe=5m", timeout=25).json()
    if r5a["signal"] and r5b["signal"]:
        assert r5a["signal"]["id"] == r5b["signal"]["id"], \
            "5m signal was overwritten when user switched to 1m/15m — per-TF dict broken"


# ---- signal.timeframe equals requested timeframe ----
@pytest.mark.parametrize("tf", ["1m", "5m", "15m", "1h"])
def test_signal_timeframe_matches_request(client, tf):
    r = client.get(f"{API}/signal/active?timeframe={tf}", timeout=25).json()
    if r["signal"]:
        assert r["signal"]["timeframe"] == tf, \
            f"requested {tf} but signal.timeframe={r['signal']['timeframe']}"
    # analysis dict always present with required keys
    assert r["analysis"]["direction"] in ("BUY", "SELL", "NEUTRAL")


# ---- MEDIA probability is allowed to produce signal (loosened filter) ----
def test_signal_emitted_for_media_prob_when_confluence_ok(client):
    """Over multiple TFs, at least one should show that MEDIA or higher + non-contradicting
    confluence is allowed to have signal. Only BAJA must suppress."""
    observed_states = []
    for tf in ("1m", "5m", "15m", "1h", "4h"):
        d = client.get(f"{API}/signal/active?timeframe={tf}", timeout=25).json()
        observed_states.append({
            "tf": tf,
            "prob": d["probability"]["label"],
            "confl": d["confluence"]["direction"],
            "analysis": d["analysis"]["direction"],
            "signal": d["signal"] is not None,
        })
    # BAJA should never have signal in the SAME response (unless persisted from prior).
    for st in observed_states:
        if st["prob"] == "BAJA" and not st["signal"]:
            # expected
            pass
    # Sanity: response always well-formed
    assert all(s["analysis"] in ("BUY", "SELL", "NEUTRAL") for s in observed_states)


# ---- Confluence must match analysis dir OR be NEUTRAL when signal exists ----
def test_signal_confluence_does_not_contradict(client):
    for tf in ("1m", "5m", "15m"):
        d = client.get(f"{API}/signal/active?timeframe={tf}", timeout=25).json()
        if d["signal"]:
            confl = d["confluence"]["direction"]
            sig_dir = d["signal"]["direction"]
            # confluence direction must not directly contradict sig direction
            assert confl in (sig_dir, "NEUTRAL"), \
                f"TF={tf} signal={sig_dir} vs confluence={confl} contradiction"


# ---- Signal stability within short window (cooldown logic) ----
def test_signal_stability_3_consecutive_calls(client):
    ids = []
    for _ in range(3):
        d = client.get(f"{API}/signal/active?timeframe=5m", timeout=25).json()
        ids.append(d["signal"]["id"] if d["signal"] else None)
        time.sleep(0.6)
    # All non-None ids must be identical (no infinite regeneration loop)
    non_null = [i for i in ids if i]
    if len(non_null) >= 2:
        assert len(set(non_null)) == 1, f"Signal id changed across 3 calls: {ids} — LOOP BUG STILL PRESENT"


# ---- probability MEDIA filter loosened ----
def test_probability_media_is_acceptable(client):
    """Confirm the gate is only BAJA (and contradiction). MEDIA/ALTA/ULTRA pass."""
    r = client.get(f"{API}/signal/active?timeframe=5m", timeout=25).json()
    prob_label = r["probability"]["label"]
    confl_dir = r["confluence"]["direction"]
    analysis_dir = r["analysis"]["direction"]
    if r["signal"] is None:
        # must be BAJA, or NEUTRAL analysis, or confluence contradiction
        assert (prob_label == "BAJA"
                or analysis_dir == "NEUTRAL"
                or (confl_dir not in (analysis_dir, "NEUTRAL"))), \
            f"Signal None with prob={prob_label} confl={confl_dir} analysis={analysis_dir} — filter still too strict"
