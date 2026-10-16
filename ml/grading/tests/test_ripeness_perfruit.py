"""G7.1 per-fruit ripeness head (config default OFF)."""
import json
import os

from grading.ripeness import DEFAULT_PERFRUIT, ripeness_per_fruit  # noqa: E402

C = ["apple_overripe", "apple_ripe", "apple_unripe", "banana_overripe", "banana_ripe", "banana_unripe", "mango_overripe", "mango_ripe",
     "mango_unripe", "orange_overripe", "orange_ripe", "orange_unripe", "tomato_overripe", "tomato_ripe", "tomato_unripe"]


def probs(peak, mass=0.9):
    return [mass if c == peak else (1 - mass) / (len(C) - 1) for c in C]


def test_off_by_default():
    assert DEFAULT_PERFRUIT["enabled"] is False
    assert ripeness_per_fruit("banana", C, probs("banana_ripe")) is None


def test_assessed_and_unable():
    on = dict(enabled=True)
    assert ripeness_per_fruit("banana", C, probs("banana_overripe"), on)["stage"] == "overripe"
    assert ripeness_per_fruit("citrus", C, probs("orange_unripe"), on)["stage"] == "unripe"  # detector citrus -> orange
    r = ripeness_per_fruit("banana", C, probs("mango_ripe"), on)  # classifier disagrees on the fruit
    assert r["status"] == "unknown"
    assert ripeness_per_fruit("potato", C, probs("banana_ripe"), on) is None


def test_fixture_is_current():
    here = os.path.dirname(os.path.abspath(__file__))
    fx = json.load(open(os.path.join(here, "..", "..", "eval", "fixtures", "ripeness_perfruit_parity.json")))
    for c in fx["cases"]:
        assert ripeness_per_fruit(c["cls"], fx["model_classes"], c["probs"], c["params"]) == c["expected"]
