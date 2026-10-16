"""G6.4 unit tests for the ByteTrack research adapter (python -m pytest -q ml/eval/test_bytetrack_adapter.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bytetrack_adapter import ByteTrackTracker  # noqa: E402

A = dict(box=[0.30, 0.30, 0.60, 0.60], classId=1, score=0.8)


def test_id_persists_through_short_gap_and_reset_clears():
    t = ByteTrackTracker(track_buffer=8)
    ids = set()
    for f in range(6):
        for o in t.update([A], f * 100.0):
            ids.add(o["id"])
    assert t.update([], 700.0) == []                     # missed frame: nothing shown (no ghost box)
    back = t.update([dict(A, box=[0.31, 0.30, 0.61, 0.60])], 800.0)
    assert back and back[0]["id"] in ids                 # same physical object keeps its id
    t.reset()
    assert t.update([], 900.0) == [] and t.state == {}   # reset between unrelated clips


def test_low_score_detection_never_starts_a_track():
    t = ByteTrackTracker()
    for f in range(5):
        out = t.update([dict(box=[0.7, 0.7, 0.8, 0.8], classId=3, score=0.2)], f * 100.0)
    assert out == []


def test_label_hysteresis_needs_consecutive_evidence():
    t = ByteTrackTracker()
    for f in range(4):
        t.update([A], f * 100.0)
    out = t.update([dict(A, classId=7, score=0.9)], 400.0)  # one frame of a different class does not flip the label
    assert out[0]["label"] == 1


def test_bytetrack_parity_fixture_is_current(tmp_path):
    """G7.3: the committed TS parity fixture must equal a fresh regeneration from the adapter."""
    import json, os
    import bytetrack_adapter as b
    p = tmp_path / "bt.json"
    b.make_parity_fixture(str(p))
    here = os.path.dirname(os.path.abspath(__file__))
    assert json.load(open(p)) == json.load(open(os.path.join(here, "fixtures", "bytetrack_parity.json")))


def test_botsort_option_runs_and_missed_frag_metric():
    """G7: BoT-SORT (no ReID, no GMC) research option keeps the same interface; missed/fragmentation helper."""
    from bytetrack_adapter import BotSortTracker
    import video_gauntlet as vg
    t = BotSortTracker(track_buffer=15)
    out = []
    for f in range(6):
        out = t.update([dict(box=[0.3, 0.3, 0.6, 0.6], classId=1, score=0.8)], f * 33.0)
    assert len(out) == 1 and out[0]["label"] == 1
    m = vg.missed_and_frag([False, True, True, False, True], 10)
    assert m["missed_frames"] == 2 and m["fragmentations"] == 1 and m["longest_missed_gap_s"] == 0.1
