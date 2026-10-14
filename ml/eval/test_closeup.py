"""G9 Stage G: Python reference tests for the close-up path (run: python -m pytest ml/eval/test_closeup.py)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from ml.eval.closeup import detector_to_frame, crop_rect, quality_reasons, GradeGate, FROZEN_GATE, id_policy, roi_from_tap
from ml.prices.display import category_price, graded_price

GOOD = dict(sidePx=200, blurVar=300, meanV=150, touchesEdge=False, visibleFrac=0.6, maxProb=0.99, margin=0.98, blockiness=1.05)


def test_small_detector_box_on_4k_frame_is_about_96px():
    fb = detector_to_frame([200, 200, 212, 212], 3840, 2160)
    assert 95 <= crop_rect(fb, 3840, 2160)["sidePx"] <= 97


def test_each_degradation_refuses_and_confidence_alone_never_grades():
    assert quality_reasons(GOOD, FROZEN_GATE) == []
    for patch in (dict(sidePx=95), dict(blurVar=10), dict(meanV=60), dict(meanV=250), dict(touchesEdge=True), dict(visibleFrac=0.2), dict(margin=0.1), dict(blockiness=2.0)):
        assert quality_reasons({**GOOD, **patch}, FROZEN_GATE), patch
    assert "too_small: move closer" in quality_reasons({**GOOD, "sidePx": 24, "maxProb": 1.0, "margin": 1.0}, FROZEN_GATE)


def test_gate_needs_three_agreeing_assessments():
    g = GradeGate(FROZEN_GATE); a = dict(ok=True, grade="B", pFresh=0.9, reasons=[])
    assert [g.push(a)["status"] for _ in range(3)] == ["pending", "pending", "graded"]
    assert g.push(dict(a, grade="A"))["status"] == "pending"
    assert g.push(dict(a, ok=False, reasons=["blurry"]))["status"] == "not_graded"


def test_id_policy_and_roi_fallback():
    assert id_policy(1, 0.49, 9)["status"] == "unable" and id_policy(1, 0.9, 3)["status"] == "identified"
    assert roi_from_tap([0.5, 0.5], 1920, 1080, [])["source"] == "tap_roi"


def test_price_contract_never_shows_stale_unverified_or_low_grade():
    S = [json.load(open(os.path.join(os.path.dirname(__file__), "..", "prices", "fixtures", f"parsed_{k}_2026-10-12.json"))) for k in ("fruit", "vegetable")]
    ok = category_price(True, "apple", S, "2026-10-14")
    assert ok["show"] and all(ok["line"][k] for k in ("source", "listDate", "location", "unit")) and "seller" in ok["line"]["label"]
    assert not category_price(False, "apple", S, "2026-10-14")["show"]
    assert not category_price(True, "apple", S, "2026-10-20")["show"]
    assert not graded_price(True, "apple", "Reject", S, "2026-10-14")["show"]
