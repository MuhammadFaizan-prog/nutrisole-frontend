"""G4.5 ripeness output (unripe / ripe / overripe), SEPARATE from fresh/rotten quality and from the A/B/C grade.
EXACT mirror: native/src/cv/pipeline/ripeness.ts (parity: native/tests/cvRipeness.test.ts replays
ml/eval/fixtures/ripeness_parity.json produced by this module).

Rules:
  * Only for classes where ripeness matters to a buyer: banana, mango, tomato, guava (+ citrus colour, opt-in).
  * Abstain (status 'unknown') when the top probability < minConfidence or the margin to the runner-up < minMargin.
  * Never changes the grade: the app shows it as a separate chip until human graders validate a mapping.
  * Classes with no ripeness model get no ripeness field at all (not 'unknown')."""
from __future__ import annotations

STAGES = ["unripe", "ripe", "overripe"]
RIPENESS_CLASSES = ["banana", "mango", "tomato", "guava"]
DEFAULT_RIPENESS = dict(minConfidence=0.6, minMargin=0.15, includeCitrus=False)


def ripeness_from_probs(class_name: str, probs: list[float], params: dict | None = None):
    p = {**DEFAULT_RIPENESS, **(params or {})}
    allowed = RIPENESS_CLASSES + (["citrus"] if p["includeCitrus"] else [])
    if class_name not in allowed:
        return None
    if len(probs) != len(STAGES) or any(not (0.0 <= v <= 1.0) for v in probs):
        return dict(stage="unknown", status="unknown")
    order = sorted(range(len(STAGES)), key=lambda i: (-probs[i], i))
    top, second = probs[order[0]], probs[order[1]]
    if top < p["minConfidence"] or top - second < p["minMargin"]:
        return dict(stage="unknown", status="unknown", confidence=round(top, 4))
    return dict(stage=STAGES[order[0]], status="assessed", confidence=round(top, 4))


# ---- G7.1 per-fruit ripeness head (optional, config default OFF) ----
# Model classes are "<fruit>_<stage>" (Kaggle nutrisole-g7-ripeness). The detector's class selects that fruit's stage
# classes (conditional softmax). "Unable to assess" (stage/status 'unknown') when the classifier puts < minFruitMass of its
# probability on the detector's fruit, or the conditional chip rule (minConfidence / minMargin) fails. A detector class with
# no ripeness classes in the model gets no ripeness field (None). Never merged into the A/B/C grade.
DEFAULT_PERFRUIT = dict(enabled=False, minFruitMass=0.5, minConfidence=0.6, minMargin=0.15, fruitMap={"citrus": "orange"})


def ripeness_per_fruit(class_name: str, model_classes: list[str], probs: list[float], params: dict | None = None):
    p = {**DEFAULT_PERFRUIT, **(params or {})}
    if not p["enabled"]:
        return None
    fruit = p["fruitMap"].get(class_name, class_name)
    idx = [next((i for i, c in enumerate(model_classes) if c == f"{fruit}_{s}"), -1) for s in STAGES]
    if all(i < 0 for i in idx):
        return None
    if len(probs) != len(model_classes) or any(not (0.0 <= v <= 1.0) for v in probs):
        return dict(stage="unknown", status="unknown")
    sp = [probs[i] if i >= 0 else 0.0 for i in idx]
    mass = sum(sp)
    if mass < p["minFruitMass"]:
        return dict(stage="unknown", status="unknown", confidence=round(mass, 4))
    cp = [v / mass for v in sp]
    order = sorted(range(3), key=lambda i: (-cp[i], i))
    top, second = cp[order[0]], cp[order[1]]
    if top < p["minConfidence"] or top - second < p["minMargin"]:
        return dict(stage="unknown", status="unknown", confidence=round(top, 4))
    return dict(stage=STAGES[order[0]], status="assessed", confidence=round(top, 4))


def make_perfruit_fixture(path: str, model_classes: list[str]):
    import json
    import random
    rnd = random.Random(0); cases = []
    names = ["banana", "mango", "tomato", "apple", "citrus", "potato", "guava"]
    for _ in range(300):
        raw = [rnd.random() ** 3 for _ in model_classes]; s = sum(raw); pr = [round(v / s, 6) for v in raw]
        cls = rnd.choice(names); prm = dict(enabled=True) if rnd.random() > 0.1 else {}
        cases.append(dict(cls=cls, probs=pr, params=prm, expected=ripeness_per_fruit(cls, model_classes, pr, prm)))
    json.dump(dict(model_classes=model_classes, cases=cases), open(path, "w"))
