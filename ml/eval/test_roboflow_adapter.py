"""G9: roboflow_adapter mapping tests (no weights needed). Run: python ml/eval/test_roboflow_adapter.py"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roboflow_adapter import CLASS_MAPS, EXPLICITLY_UNMAPPED, MODELS, NAMES, RoboflowDet, coverage  # noqa: E402
from geometry import decode  # noqa: E402


def stub(name, boxes, cls_names, scores):
    d = object.__new__(RoboflowDet)
    d.name, d.spec = name, MODELS[name]
    d.tgt = np.array([NAMES.index(CLASS_MAPS[name][c]) if c in CLASS_MAPS[name] else -1 for c in MODELS[name]["classes"]])
    cl = np.array([MODELS[name]["classes"].index(c) for c in cls_names])
    d.infer_src = lambda img: (np.array(boxes, float), cl, np.array(scores, float))
    d._frame, d._tf = None, dict(scaleX=0.5, scaleY=0.5, padX=10, padY=0)
    return d


def test_maps_are_explicit():
    for m in MODELS:
        for s, t in CLASS_MAPS[m].items():
            assert s in MODELS[m]["classes"] and t in NAMES
        assert not set(CLASS_MAPS[m]) & set(EXPLICITLY_UNMAPPED[m])
    assert coverage("snapml")["n"] == 11 and coverage("snapml")["missing"] == ["guava"]
    assert coverage("calories")["n"] == 9 and set(coverage("calories")["missing"]) == {"pomegranate", "lemon_lime", "carrot"}


def test_unmapped_dropped_not_rerouted():
    d = stub("calories", [[0, 0, 100, 100], [200, 0, 300, 100], [0, 200, 100, 300]], ["Green Chili", "Capsicum", "oren"], [0.9, 0.6, 0.8])
    out = d.run(None, {})[0]
    dets = decode(out, "raw", 0.35)
    assert [NAMES[x["classId"]] for x in dets] == ["capsicum"]
    b = dets[0]["box"]  # src px -> letterbox: x*0.5+10
    assert np.allclose(b, [110, 0, 160, 50])


def test_grapefruit_not_counted_lemon_separate():
    d = stub("snapml", [[0, 0, 10, 10], [20, 20, 40, 40], [50, 50, 90, 90]], ["Grapefruit", "Lemon", "Orange"], [0.9, 0.7, 0.5])
    dets = decode(d.run(None, {})[0], "raw", 0.35)
    assert sorted(NAMES[x["classId"]] for x in dets) == ["citrus", "lemon_lime"]


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k)
