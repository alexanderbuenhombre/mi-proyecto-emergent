"""
Unit and Mathematical Tests for XAU/USD Scalping Engine Refactoring
===================================================================
Run with: python -m unittest backend/tests/test_math_engine.py
"""
import unittest
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from trading_engine import (
    compute_continuous_score,
    evaluate_market_regime,
    compute_adaptive_targets,
    evaluate_sudden_reversal,
    calculate_choppiness_index,
)


class TestMathematicalScalpingEngine(unittest.TestCase):

    def test_continuous_score_bullish(self):
        score, direction, conf = compute_continuous_score(
            recommend_all=0.55,
            rsi=58.0,
            macd_line=0.45,
            macd_signal=0.10,
            cci=110.0,
            bb_pos=0.60,
            atr=3.20,
            current_price=2650.0,
        )
        self.assertEqual(direction, "BUY")
        self.assertGreaterEqual(score, 25.0)
        self.assertGreaterEqual(conf, 60.0)

    def test_continuous_score_bearish(self):
        score, direction, conf = compute_continuous_score(
            recommend_all=-0.60,
            rsi=42.0,
            macd_line=-0.50,
            macd_signal=-0.10,
            cci=-120.0,
            bb_pos=0.40,
            atr=3.20,
            current_price=2650.0,
        )
        self.assertEqual(direction, "SELL")
        self.assertLessEqual(score, -25.0)

    def test_overbought_location_ceiling_rejection(self):
        """When price is pressed against BB upper band (>0.85), buying score must be dampened."""
        score_normal, _, _ = compute_continuous_score(
            recommend_all=0.40, rsi=65.0, macd_line=0.2, macd_signal=0.1,
            cci=90.0, bb_pos=0.50, atr=3.0, current_price=2650.0
        )
        score_ceiling, _, _ = compute_continuous_score(
            recommend_all=0.40, rsi=65.0, macd_line=0.2, macd_signal=0.1,
            cci=90.0, bb_pos=0.98, atr=3.0, current_price=2650.0
        )
        self.assertLess(score_ceiling, score_normal)

    def test_choppiness_detection(self):
        """High Choppiness Index (>61.8) without squeeze should flag CHOPPY_RANGE."""
        # BB width is wide (12 dollars -> bbw_pct ~ 0.45%, no squeeze),
        # but price oscillates in a tight sub-range (high-low=4 while 14*ATR=28) -> High Choppiness
        regime = evaluate_market_regime(
            atr=2.0,
            bb_upper=2656.0,
            bb_lower=2644.0,
            current_price=2650.0,
            high=2652.0,
            low=2648.0,
        )
        self.assertTrue(regime["is_choppy"])
        self.assertFalse(regime["trade_permitted"])
        self.assertEqual(regime["regime"], "CHOPPY_RANGE")

    def test_squeeze_detection(self):
        """Extreme BB compression should flag Squeeze."""
        regime = evaluate_market_regime(
            atr=0.5,
            bb_upper=2650.5,
            bb_lower=2649.5,
            current_price=2650.0,
        )
        self.assertTrue(regime["is_squeeze"])
        self.assertFalse(regime["trade_permitted"])

    def test_positive_expectation_targets(self):
        """TP1 must provide an R:R >= 1.25 to guarantee positive expectancy."""
        targets = compute_adaptive_targets(
            entry=2650.0,
            direction="BUY",
            timeframe="5m",
            atr=3.5,
            spread=0.25,
        )
        self.assertGreater(targets["tp1"], targets["entry"] if "entry" in targets else 2650.0)
        self.assertLess(targets["stop_loss"], 2650.0)
        self.assertGreaterEqual(targets["risk_reward_tp1"], 1.25)
        # Verify distance ordering: entry < tp1 < tp2 < tp3
        self.assertLess(targets["tp1"], targets["tp2"])
        self.assertLess(targets["tp2"], targets["tp3"])

    def test_sudden_reversal_noise_rejection(self):
        """Micro movements like $0.35 in gold must NOT trigger panic reversal exits."""
        ticks = [
            (100.0, 2650.0),
            (110.0, 2650.1),
            (120.0, 2649.8),
            (130.0, 2649.65), # delta = -0.35
        ]
        rev = evaluate_sudden_reversal(
            ticks=ticks,
            direction="BUY",
            eff_atr=1.1,
            spread=0.25,
        )
        self.assertFalse(rev["reversal"], "Normal spread/micro fluctuations should not trigger exit")

    def test_sudden_reversal_real_spike(self):
        """Significant adverse spikes exceeding threshold must trigger reversal."""
        ticks = [
            (100.0, 2650.0),
            (110.0, 2649.2),
            (120.0, 2648.5),
            (130.0, 2647.8), # delta = -2.20
        ]
        rev = evaluate_sudden_reversal(
            ticks=ticks,
            direction="BUY",
            eff_atr=1.1,
            spread=0.25,
        )
        self.assertTrue(rev["reversal"], "Adverse price spike must trigger emergency exit")


if __name__ == "__main__":
    unittest.main()
