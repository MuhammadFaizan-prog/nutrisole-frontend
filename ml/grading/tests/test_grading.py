"""Unit tests on synthetic images + golden rule cases (shared with the TS port)."""
import json, os, sys
import numpy as np, cv2, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from grading.measure import measure, dark_defect_area, shape_metrics, colour_bands, object_mask  # noqa: E402
from grading.rules import grade  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def synth(colour_rgb, size=200, axes=(70, 55), bg=(200, 200, 200), spots=0.0, seed=0):
    img = np.full((size, size, 3), bg, np.uint8)
    m = np.zeros((size, size), np.uint8)
    cv2.ellipse(m, (size // 2, size // 2), axes, 0, 0, 360, 255, -1)
    img[m > 0] = colour_rgb
    rng = np.random.default_rng(seed)
    img = np.clip(img.astype(int) + rng.integers(-6, 7, img.shape), 0, 255).astype(np.uint8)
    if spots > 0:
        area = (m > 0).sum()
        target = spots * area
        dark = np.zeros_like(m)
        while (dark > 0).sum() < target:
            cx, cy = rng.integers(size // 2 - axes[0] // 2, size // 2 + axes[0] // 2), rng.integers(size // 2 - axes[1] // 2, size // 2 + axes[1] // 2)
            cv2.circle(dark, (int(cx), int(cy)), 6, 255, -1)
            dark &= m
        img[dark > 0] = (40, 25, 15)
        return img, m > 0, (dark > 0).sum() / area
    return img, m > 0, 0.0


def test_clean_item_has_no_defects_and_regular_shape():
    img, m, _ = synth((220, 30, 30))
    d = dark_defect_area(img, m)
    assert d < 1.0
    sol, ell = shape_metrics(m)
    assert sol > 0.97 and 0.95 < ell < 1.05


@pytest.mark.parametrize("frac", [0.05, 0.15, 0.30])
def test_defect_area_tracks_ground_truth(frac):
    img, m, true = synth((230, 200, 40), spots=frac, seed=int(frac * 100))
    d = dark_defect_area(img, m)
    # erosion of the silhouette edge and opening make it slightly conservative
    assert abs(d - 100 * true) < 5.0, (d, 100 * true)


def test_star_shape_low_solidity():
    m = np.zeros((200, 200), np.uint8)
    pts = []
    for k in range(10):
        r = 90 if k % 2 == 0 else 35
        a = k * np.pi / 5
        pts.append((100 + r * np.cos(a), 100 + r * np.sin(a)))
    cv2.fillPoly(m, [np.array(pts, np.int32)], 255)
    sol, _ = shape_metrics(m > 0)
    assert sol < 0.7


def test_colour_bands_banana():
    yellow = cv2.cvtColor(np.uint8([[[28, 200, 220]]]), cv2.COLOR_HSV2RGB)[0, 0]
    img, m, _ = synth(tuple(int(x) for x in yellow))
    bands, dom = colour_bands(img, m, "banana")
    assert dom == "yellow" and bands["yellow"] > 90
    green = cv2.cvtColor(np.uint8([[[60, 200, 180]]]), cv2.COLOR_HSV2RGB)[0, 0]
    img, m, _ = synth(tuple(int(x) for x in green))
    assert colour_bands(img, m, "banana")[1] == "green"


def test_red_apple_band_wraps_hue():
    img, m, _ = synth((200, 20, 30))
    bands, dom = colour_bands(img, m, "apple")
    assert dom == "red" and bands["red"] > 90


def test_unknown_produce_has_no_bands():
    img, m, _ = synth((200, 180, 140))
    assert colour_bands(img, m, "potato") == ({}, "unknown")


def test_object_mask_finds_item():
    img, m, _ = synth((220, 30, 30))
    est, method = object_mask(img)
    iou = (est & m).sum() / (est | m).sum()
    assert iou > 0.85, (iou, method)


def test_measure_end_to_end_and_grade():
    img, _, _ = synth((210, 25, 35), spots=0.30, seed=3)
    md = measure(img, "apple").to_dict()
    g = grade("apple", 0.9, {"fresh": 0.8, "rotten": 0.2}, md)
    assert g["grade"] == "Reject" and any("Dark marks" in r for r in g["reasons"])
    img, _, _ = synth((210, 25, 35))
    md = measure(img, "apple").to_dict()
    g = grade("apple", 0.9, {"fresh": 0.9, "rotten": 0.1}, md)
    assert g["grade"] == "A", g


def test_flat_blurry_image_is_ungradable():
    img = np.full((120, 120, 3), 128, np.uint8)
    md = measure(img, "apple").to_dict()
    g = grade("apple", 0.9, {"fresh": 0.9, "rotten": 0.1}, md)
    assert g["grade"] == "ungradable"


GOLDEN = json.load(open(os.path.join(HERE, "golden_rules.json")))


@pytest.mark.parametrize("case", GOLDEN, ids=[c["name"] for c in GOLDEN])
def test_golden_rules(case):
    g = grade(case["produce"], case["det"], case["probs"], case["m"])
    assert g["grade"] == case["grade"] and g["status"] == case["status"], g
    assert len(g["reasons"]) >= 1 and len(g["reasons"]) <= 2


def test_no_safety_claims_in_reasons():
    banned = ["safe", "disease", "formalin", "shelf", "calorie", "price", "toxic"]
    for c in GOLDEN:
        for r in grade(c["produce"], c["det"], c["probs"], c["m"])["reasons"]:
            assert not any(b in r.lower() for b in banned), r
