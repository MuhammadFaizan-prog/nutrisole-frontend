"""G7 autolabel merge: matching, status/flag logic on a synthetic clip (no video needed)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import merge  # noqa: E402


def _clip(tmp, dets, tracks):
    d = tmp / "cX"; d.mkdir()
    frames = [dict(fi=i * 6, t=i * 0.25, dets=dets, tracks=tracks) for i in range(9)]
    json.dump(dict(w=960, h=540, frames=frames), open(d / "frames.json", "w"))
    json.dump(dict(keyframes=[dict(file="kf_000024.jpg", fi=24, t=1.0)]), open(d / "keyframes.json", "w"))
    return str(tmp)


def test_iou_and_match():
    a = [dict(box=[0, 0, 0.5, 0.5])]; b = [dict(box=[0.01, 0.01, 0.5, 0.5]), dict(box=[0.6, 0.6, 0.9, 0.9])]
    m, ua, ub = merge.match(a, b)
    assert m == [(0, 0)] and ua == {0} and ub == {0}
    assert merge.iou([0, 0, 1, 1], [2, 2, 3, 3]) == 0


def test_statuses(tmp_path):
    dets = [dict(box=[0.1, 0.1, 0.3, 0.4], classId=1, score=0.8),   # apple, OWL says apple -> agree
            dict(box=[0.5, 0.1, 0.7, 0.4], classId=3, score=0.7),   # citrus, OWL says lemon -> dispute
            dict(box=[0.8, 0.1, 0.95, 0.4], classId=7, score=0.5)]  # tomato, OWL nothing -> g3_only
    tracks = [dict(id=1, box=[0.1, 0.1, 0.3, 0.4], label=1, score=0.8)]
    s1 = _clip(tmp_path, dets, tracks)
    owl = {"kf_000024.jpg": [dict(box=[0.1, 0.1, 0.3, 0.4], cls=1, prompt="an apple", score=0.5),
                             dict(box=[0.5, 0.1, 0.7, 0.4], cls=6, prompt="a lemon", score=0.4),
                             dict(box=[0.1, 0.6, 0.3, 0.9], cls=2, prompt="a mango", score=0.3),
                             dict(box=[0.1, 0.6, 0.3, 0.9], cls=-1, prompt="an onion", score=0.3)]}
    r = merge.merge_clip("cX", s1, owl, "produce")
    st = sorted(b["status"] for b in r["keyframes"][0]["boxes"])
    assert st == ["agree", "class_dispute", "g3_only", "owl_only"]
    disp = [b for b in r["keyframes"][0]["boxes"] if b["status"] == "class_dispute"][0]
    assert disp["label"] == "disputed:citrus|lemon_lime"  # never silently resolved to the max-confidence class
    owl_only = [b for b in r["keyframes"][0]["boxes"] if b["status"] == "owl_only"][0]
    assert "unsupported_overlap" in owl_only["flags"]
    assert r["keyframes"][0]["priority"] > 0


def test_negative_priority(tmp_path):
    s1 = _clip(tmp_path, [dict(box=[0.1, 0.1, 0.3, 0.4], classId=1, score=0.5)], [])
    r = merge.merge_clip("cX", s1, {"kf_000024.jpg": []}, "negative")
    assert r["keyframes"][0]["priority"] == 2.0  # a supported box on a negative clip -> absence-check item
